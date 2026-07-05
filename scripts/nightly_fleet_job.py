# -*- coding: utf-8 -*-
"""
Job nocturno de simulación de flota — CA-ILO-01, CA-UCHU-01, CA-CH-04, CA-CH-05.

Cada `--interval` segundos (5 min por defecto) envía, POR CADA equipo, UNA lectura
a `POST /iot/readings` — exactamente como lo haría un datalogger real en campo.

Desde que se cerró el GAP C1, iot-service dispara el ensemble de salud
(AE+IF+AND) automáticamente al persistir la lectura (ensemble_notify_service),
así que NO llamamos a /health-monitor/evaluate: la cadena
`lectura → iot ingest → ml evaluate → salud/incidencias` corre sola.

ESCALA — importante:
Estas 4 estaciones OEFA operan en la MISMA escala con la que se entrenó el
ensemble (SO2 ppb ~1-9, flow ~0.45, temp interna ~30, lámpara ~102). NO es la
escala Thermo/CR310 de los equipos T101… (ppb negativos, flow ~600, lamp ~1940).
Enviar escala Thermo a estas estaciones dispara recon_error astronómico → CRITICO
falso. Por eso los valores de abajo están en escala OEFA, calibrados por equipo
contra su propio θ (fuente: scripts/simulate_multi_random.py, simulate_ca_ch_05.py).

C1 mapea estas claves del payload -> features del ensemble:
    SO2_ppb          -> so2_ppb
    SampleFlow       -> so2_flow
    Reaction_Temp    -> so2_internal_temp
    UVLampIntensity  -> so2_lamp_int
Las 4 deben venir numéricas o el gate marca SIN_DATOS (valido=0).

Comportamiento "mayormente sano + eventos":
  - La flota emite SANO la mayor parte de la noche.
  - Con probabilidad `--event-prob` por ciclo se inyecta una degradación
    (EN_RIESGO o CRITICO) en UNO de los equipos. Respeta el anti-parpadeo:
    subir a CRITICO es inmediato; subir a EN_RIESGO o bajar de severidad requiere
    N_CONSEC=3 lecturas estables, que se emiten dentro del mismo ciclo.

Termina automáticamente a las 08:00 (hora Perú, UTC-5) del día siguiente, o antes
si se interrumpe con Ctrl-C / SIGTERM.

Uso:
    python scripts/nightly_fleet_job.py
    python scripts/nightly_fleet_job.py --interval 300 --event-prob 0.15
    python scripts/nightly_fleet_job.py --stop "2026-07-05 08:00" --url http://localhost:8000

Requiere: httpx. Servicios levantados (docker compose up) con ENSEMBLE_NOTIFY_ENABLED=1.
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
# Valores calibrados en ESCALA OEFA por equipo y estado.
# Claves = nombres que C1 (ensemble_notify_service) mapea a las features del
# ensemble. Tupla = (SO2_ppb, SampleFlow, Reaction_Temp, UVLampIntensity).
# ---------------------------------------------------------------------------
FLEET = {
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
DEVICES = list(FLEET.keys())

_stop = False


def _handle_signal(signum, frame):
    global _stop
    _stop = True
    print("\n[!] Señal recibida — terminando tras el equipo actual...", flush=True)


def login(client: httpx.Client, base: str) -> str:
    r = client.post(f"{base}/api/v1/auth/login", json=LOGIN, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _payload(device: str, state: str, ts_peru: datetime, rng: random.Random) -> dict:
    """Lectura CR310-style en escala OEFA, con pequeño jitter para que no sea plana."""
    ppb, flow, temp, lamp = FLEET[device][state]
    j = lambda v, s: round(rng.gauss(v, s), 4)  # noqa: E731
    return {
        "equipo": device,
        "timestamp": ts_peru.strftime("%Y-%m-%d %H:%M:%S"),
        "SO2_ppb": j(ppb, 0.03),
        "SampleFlow": j(flow, 0.003),
        "Reaction_Temp": j(temp, 0.15),
        "UVLampIntensity": j(lamp, 0.08),
    }


def send_reading(client, base, token, device, state, rng) -> bool:
    """POST /iot/readings. C1 dispara el ensemble solo. Devuelve True si persistió."""
    ts_peru = datetime.now(PERU_TZ)
    try:
        r = client.post(f"{base}/api/v1/iot/readings",
                        json=_payload(device, state, ts_peru, rng),
                        headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code in (200, 201):
            return True
        print(f"    [ERR {r.status_code}] {device}: {r.text[:150]}", flush=True)
    except httpx.RequestError as e:
        print(f"    [CONN ERR] {device}: {e}", flush=True)
    return False


def _reps_for(target: str, current: str) -> int:
    """Anti-parpadeo: subir a CRITICO = 1 lectura; resto de transiciones = N_CONSEC."""
    if target == current:
        return 1
    if target == "CRITICO" and SEVERITY[target] > SEVERITY[current]:
        return 1
    return N_CONSEC


def get_state(client, base, token, device) -> str | None:
    try:
        r = client.get(f"{base}/api/v1/health-monitor/{device}/state",
                       headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code == 200:
            return r.json().get("health_state")
    except httpx.RequestError:
        pass
    return None


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
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    now_peru = datetime.now(PERU_TZ)
    stop_peru = stop_utc.astimezone(PERU_TZ)
    print("=" * 68)
    print(" JOB NOCTURNO — SIMULACIÓN DE FLOTA DE MONITOREO DE AIRE")
    print("=" * 68)
    print(f" Equipos     : {', '.join(DEVICES)}")
    print(f" Endpoint    : POST /iot/readings  (C1 dispara el ensemble solo)")
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

        # Estado publicado real (lo consultamos, no lo asumimos) para respetar
        # el anti-parpadeo con exactitud.
        current = {d: (get_state(client, args.url, token, d) or "SANO") for d in DEVICES}
        token_ts = time.monotonic()
        cycle = 0

        while not _stop and datetime.now(timezone.utc) < stop_utc:
            cycle += 1
            if time.monotonic() - token_ts > 1200:  # refrescar token cada ~20 min
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
                if _stop:
                    break
                target = targets[device]
                reps = _reps_for(target, current[device])
                ok = False
                for _ in range(reps):
                    ok = send_reading(client, args.url, token, device, target, rng) or ok
                    if reps > 1:
                        time.sleep(1)
                published = get_state(client, args.url, token, device) or current[device]
                current[device] = published
                print(f"    {device:12s} target={target:9s} -> {published:12s} "
                      f"iot={'ok' if ok else 'FAIL'}", flush=True)

            # Dormir en tramos cortos para reaccionar a Ctrl-C y a la hora de parada.
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
