# -*- coding: utf-8 -*-
"""
Job nocturno de simulación de flota — CA-ILO-01, CA-UCHU-01, CA-CH-04, CA-CH-05.

Cada `--interval` segundos (5 min por defecto) envía, POR CADA equipo:
  1. POST /iot/readings          -> persiste una lectura_iot (payload CR310, como
                                    lo haría un equipo real en campo).
  2. POST /health-monitor/evaluate -> alimenta el ensemble de salud (recon_error,
                                    IsolationForest, AND) y actualiza el estado que
                                    ve el dashboard.

Puentea el GAP C1 (iot-service NO dispara el ensemble al ingerir) desde el cliente:
mandamos ambos endpoints con estados COHERENTES entre sí (misma "salud" en la
lectura CR310 y en la evaluación de salud).

Comportamiento "mayormente sano + eventos":
  - La flota emite SANO la mayor parte de la noche.
  - Con probabilidad `--event-prob` por ciclo se inyecta una degradación
    (EN_RIESGO o CRITICO) en UNO de los equipos. Respeta el anti-parpadeo:
    subir a CRITICO es inmediato; subir a EN_RIESGO o bajar de severidad requiere
    N_CONSEC=3 lecturas estables, que se emiten dentro del mismo ciclo.

Termina automáticamente a las 08:00 (hora Perú, UTC-5) del día siguiente, o antes
si se interrumpe con Ctrl-C.

Uso:
    python scripts/nightly_fleet_job.py
    python scripts/nightly_fleet_job.py --interval 300 --event-prob 0.15
    python scripts/nightly_fleet_job.py --stop "2026-07-05 08:00" --url http://localhost:8000

Requiere: httpx. Servicios levantados (docker compose up).
"""
from __future__ import annotations

import argparse
import random
import signal
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

PERU_TZ = timezone(timedelta(hours=-5))
LOGIN = {"email": "admin@oefa.gob.pe", "password": "admin123"}
N_CONSEC = 3  # lecturas para confirmar anti-parpadeo (§5.1)
SEVERITY = {"SANO": 0, "EN_RIESGO": 2, "CRITICO": 3}

# ---------------------------------------------------------------------------
# Valores calibrados para el ENSEMBLE (/health-monitor/evaluate).
# (so2_ppb, so2_flow, so2_internal_temp, so2_lamp_int) — calibrados contra el θ
# de cada equipo. Fuente: scripts/simulate_multi_random.py y simulate_ca_ch_05.py.
# ---------------------------------------------------------------------------
ENSEMBLE_VALUES = {
    "CA-ILO-01": {
        "SANO":      (4.91, 0.421, 30.65, 93.38),
        "EN_RIESGO": (6.81, 0.37, 34.45, 91.48),
        "CRITICO":   (7.19, 0.36, 35.2, 91.11),
    },
    "CA-UCHU-01": {
        "SANO":      (2.86, 0.387, 31.59, 101.28),
        "EN_RIESGO": (3.05, 0.381, 32.0, 101.0),
        "CRITICO":   (3.76, 0.363, 33.4, 100.38),
    },
    "CA-CH-04": {
        "SANO":      (2.0, 0.45, 30.7, 102.0),
        "EN_RIESGO": (2.45, 0.431, 32.8, 100.65),
        "CRITICO":   (3.0, 0.41, 35.0, 99.5),
    },
    "CA-CH-05": {
        "SANO":      (6.34, 0.46, 32.09, 101.54),
        "EN_RIESGO": (8.53, 0.402, 36.4, 99.24),
        "CRITICO":   (9.34, 0.38, 38.09, 98.54),
    },
}
DEVICES = list(ENSEMBLE_VALUES.keys())

# ---------------------------------------------------------------------------
# Rangos CR310 para la LECTURA persistida (/iot/readings), por estado.
# Escala real (T101): ppb negativos, flow ~600, lamp ~1940. SANO = baselines
# reales; EN_RIESGO/CRITICO degradan lámpara UV y suben temperaturas (patrón de
# degradación físico observado en la bitácora).
# ---------------------------------------------------------------------------
CR310_VALUES = {
    "SANO": {
        "SO2_ppb": (-2.2, -1.3), "H2S_ppb": (-1.4, -0.3),
        "Reaction_Temp": (49.7, 50.1), "IZS_Temp": (0.0, 0.0),
        "PMT_Temp": (8.5, 10.0), "SampleFlow": (590.0, 640.0),
        "Pressure": (17.2, 18.5), "UVLampIntensity": (1930.0, 1955.0),
        "Box_Temp": (33.9, 35.3), "HVPS_V": (643.0, 648.0),
        "Conv_Temp": (312.0, 314.0), "Ozone_flow": (0.0, 0.0),
    },
    "EN_RIESGO": {
        "SO2_ppb": (-1.0, 0.5), "H2S_ppb": (-0.3, 0.8),
        "Reaction_Temp": (50.1, 50.6), "IZS_Temp": (0.0, 0.0),
        "PMT_Temp": (10.0, 12.0), "SampleFlow": (560.0, 590.0),
        "Pressure": (16.8, 17.2), "UVLampIntensity": (1870.0, 1910.0),
        "Box_Temp": (35.3, 37.0), "HVPS_V": (640.0, 643.0),
        "Conv_Temp": (309.0, 312.0), "Ozone_flow": (0.0, 0.0),
    },
    "CRITICO": {
        "SO2_ppb": (0.5, 2.5), "H2S_ppb": (0.8, 2.0),
        "Reaction_Temp": (50.6, 51.5), "IZS_Temp": (0.0, 0.0),
        "PMT_Temp": (12.0, 15.0), "SampleFlow": (520.0, 560.0),
        "Pressure": (16.2, 16.8), "UVLampIntensity": (1800.0, 1860.0),
        "Box_Temp": (37.0, 39.5), "HVPS_V": (636.0, 640.0),
        "Conv_Temp": (305.0, 309.0), "Ozone_flow": (0.0, 0.0),
    },
}

_stop = False


def _handle_sigint(signum, frame):
    global _stop
    _stop = True
    print("\n[!] Señal recibida — terminando tras el ciclo actual...", flush=True)


def login(client: httpx.Client, base: str) -> str:
    r = client.post(f"{base}/api/v1/auth/login", json=LOGIN, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _cr310_payload(device: str, state: str, ts: datetime, rng: random.Random) -> dict:
    payload = {"equipo": device, "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")}
    for field, (low, high) in CR310_VALUES[state].items():
        payload[field] = low if low == high else round(rng.uniform(low, high), 2)
    return payload


def _ensemble_payload(device: str, state: str, ts: datetime) -> dict:
    ppb, flow, temp, lamp = ENSEMBLE_VALUES[device][state]
    return {
        "device_id": device,
        "timestamp": ts.isoformat(),
        "so2_ppb": ppb, "so2_flow": flow,
        "so2_internal_temp": temp, "so2_lamp_int": lamp,
        "valido": 1,
    }


def send_reading(client, base, token, device, state, rng):
    """Envía a AMBOS endpoints una lectura coherente. Devuelve (ok_iot, evaluate_json)."""
    now = datetime.now(timezone.utc)
    headers = {"Authorization": f"Bearer {token}"}

    # 1) Ingesta IoT (lectura_iot). Timestamp en hora Perú (ingestion espera naive local).
    ts_peru = now.astimezone(PERU_TZ)
    ok_iot = False
    try:
        r = client.post(f"{base}/api/v1/iot/readings",
                        json=_cr310_payload(device, state, ts_peru, rng),
                        headers=headers, timeout=15)
        ok_iot = r.status_code in (200, 201)
        if not ok_iot:
            print(f"    [iot ERR {r.status_code}] {r.text[:150]}", flush=True)
    except httpx.RequestError as e:
        print(f"    [iot CONN ERR] {e}", flush=True)

    # 2) Ensemble de salud.
    out = None
    try:
        r = client.post(f"{base}/api/v1/health-monitor/evaluate",
                        json=_ensemble_payload(device, state, now),
                        headers=headers, timeout=15)
        if r.status_code == 200:
            out = r.json()
        else:
            print(f"    [eval ERR {r.status_code}] {r.text[:150]}", flush=True)
    except httpx.RequestError as e:
        print(f"    [eval CONN ERR] {e}", flush=True)

    return ok_iot, out


def _reps_for(target: str, current: str) -> int:
    """Anti-parpadeo: subir a CRITICO = 1; resto de transiciones = N_CONSEC."""
    if target == current:
        return 1
    if target == "CRITICO" and SEVERITY[target] > SEVERITY[current]:
        return 1
    return N_CONSEC


def parse_stop(value: str | None) -> datetime:
    """Hora de parada en UTC. Default: 08:00 Perú del día siguiente."""
    if value:
        naive = datetime.strptime(value, "%Y-%m-%d %H:%M")
        return naive.replace(tzinfo=PERU_TZ).astimezone(timezone.utc)
    now_peru = datetime.now(PERU_TZ)
    tomorrow = (now_peru + timedelta(days=1)).replace(
        hour=8, minute=0, second=0, microsecond=0)
    return tomorrow.astimezone(timezone.utc)


def main():
    ap = argparse.ArgumentParser(description="Job nocturno de simulación de flota")
    ap.add_argument("--interval", type=float, default=300, help="segundos entre ciclos (def 300 = 5 min)")
    ap.add_argument("--url", default="http://localhost:8000", help="base del api-gateway")
    ap.add_argument("--event-prob", type=float, default=0.15,
                    help="probabilidad por ciclo de inyectar un evento en un equipo (def 0.15)")
    ap.add_argument("--stop", default=None,
                    help="hora de parada 'YYYY-MM-DD HH:MM' (Perú). Def: 08:00 mañana")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    stop_utc = parse_stop(args.stop)
    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    now_peru = datetime.now(PERU_TZ)
    stop_peru = stop_utc.astimezone(PERU_TZ)
    print("=" * 68)
    print(" JOB NOCTURNO — SIMULACIÓN DE FLOTA DE MONITOREO DE AIRE")
    print("=" * 68)
    print(f" Equipos     : {', '.join(DEVICES)}")
    print(f" Endpoints   : /iot/readings + /health-monitor/evaluate")
    print(f" Intervalo   : {args.interval:.0f}s   Prob. evento/ciclo: {args.event_prob}")
    print(f" Inicio      : {now_peru:%Y-%m-%d %H:%M:%S} (Perú)")
    print(f" Parada      : {stop_peru:%Y-%m-%d %H:%M:%S} (Perú)")
    print(f" Gateway     : {args.url}")
    print("=" * 68, flush=True)

    with httpx.Client() as client:
        try:
            token = login(client, args.url)
        except Exception as e:
            print(f"[FATAL] No se pudo autenticar en {args.url}: {e}", file=sys.stderr)
            sys.exit(1)

        current = {d: "SANO" for d in DEVICES}
        token_ts = time.monotonic()
        cycle = 0

        while not _stop and datetime.now(timezone.utc) < stop_utc:
            cycle += 1
            # Refrescar token cada ~20 min por si el access_token caduca.
            if time.monotonic() - token_ts > 1200:
                try:
                    token = login(client, args.url)
                    token_ts = time.monotonic()
                except Exception as e:
                    print(f"    [WARN] refresh token falló: {e}", flush=True)

            # ¿Evento este ciclo? -> un equipo pasa a EN_RIESGO/CRITICO; el resto SANO.
            targets = {d: "SANO" for d in DEVICES}
            event_dev = None
            if rng.random() < args.event_prob:
                event_dev = rng.choice(DEVICES)
                targets[event_dev] = rng.choice(["EN_RIESGO", "CRITICO"])

            hora = datetime.now(PERU_TZ).strftime("%H:%M:%S")
            tag = f"evento={event_dev}:{targets[event_dev]}" if event_dev else "todos SANO"
            print(f"[c{cycle:04d} {hora}] {tag}", flush=True)

            for device in DEVICES:
                target = targets[device]
                reps = _reps_for(target, current[device])
                out = None
                iot_ok_any = False
                for _ in range(reps):
                    iot_ok, out = send_reading(client, args.url, token, device, target, rng)
                    iot_ok_any = iot_ok_any or iot_ok
                    if reps > 1:
                        time.sleep(1)
                if out is not None:
                    current[device] = out["health_state"]
                    err = out.get("recon_error")
                    err_s = f"{err:.3f}" if err is not None else "—"
                    iot_s = "ok" if iot_ok_any else "FAIL"
                    print(f"    {device:12s} target={target:9s} "
                          f"-> {out['health_state']:12s} err={err_s:>8s} iot={iot_s}",
                          flush=True)
                else:
                    print(f"    {device:12s} target={target:9s} -> [sin respuesta ensemble]",
                          flush=True)

            # Dormir hasta el próximo ciclo, en tramos cortos para reaccionar a Ctrl-C
            # y no pasarnos de la hora de parada.
            slept = 0.0
            while (slept < args.interval and not _stop
                   and datetime.now(timezone.utc) < stop_utc):
                chunk = min(2.0, args.interval - slept)
                time.sleep(chunk)
                slept += chunk

        fin = datetime.now(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")
        reason = "Ctrl-C / señal" if _stop else "hora de parada alcanzada"
        print("=" * 68)
        print(f" FIN ({reason}) — {fin} Perú — {cycle} ciclos ejecutados")
        print("=" * 68, flush=True)


if __name__ == "__main__":
    main()
