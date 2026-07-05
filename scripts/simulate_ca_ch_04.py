# -*- coding: utf-8 -*-
"""
Simulación en vivo de CA-CH-04: inyecta lecturas al endpoint /health-monitor/evaluate
cada 30 s para recorrer SANO -> EN_RIESGO -> CRITICO -> SANO y ver el dashboard
reaccionar en tiempo real.

Los valores de sensor por estado están calibrados contra el modelo real de CA-CH-04
(θ=0.08): producen el error de reconstrucción de cada banda Y activan el Isolation
Forest para que el AND confirme.

NOTA sobre anti-parpadeo (§5.1): OBSERVADO/EN_RIESGO requieren N_CONSEC=3 lecturas
consecutivas para confirmarse; CRITICO escala inmediato. Por eso, para que EN_RIESGO
sea visible, se envían 3 lecturas seguidas (cada 30 s) en esa fase antes de pasar a
CRITICO. Bajar de severidad (volver a SANO) también requiere 3 lecturas estables.

Uso:
    python scripts/simulate_ca_ch_04.py
    python scripts/simulate_ca_ch_04.py --interval 30 --url http://localhost:8000
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import httpx

DEVICE = "CA-CH-04"
LOGIN = {"email": "admin@oefa.gob.pe", "password": "admin123"}

# Inputs calibrados por estado (ppb, flow, temp, lamp). valido=1 siempre.
READINGS = {
    "SANO":      (2.0, 0.45, 30.7, 102.0),
    "EN_RIESGO": (2.45, 0.431, 32.8, 100.65),
    "CRITICO":   (3.0, 0.41, 35.0, 99.5),
}

# Secuencia de fases. Cada entrada: (input_state, repeticiones).
# EN_RIESGO x3 para superar el anti-parpadeo; SANO x3 al final para bajar de severidad.
SEQUENCE = [
    ("SANO", 1),
    ("EN_RIESGO", 3),
    ("CRITICO", 1),
    ("SANO", 3),
]


def login(client, base):
    r = client.post(f"{base}/api/v1/auth/login", json=LOGIN, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def evaluate(client, base, token, values):
    ppb, flow, temp, lamp = values
    payload = {
        "device_id": DEVICE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "so2_ppb": ppb, "so2_flow": flow,
        "so2_internal_temp": temp, "so2_lamp_int": lamp,
        "valido": 1,
    }
    r = client.post(f"{base}/api/v1/health-monitor/evaluate", json=payload,
                    headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()

    with httpx.Client() as client:
        token = login(client, args.url)
        print(f"Simulación en vivo de {DEVICE} — intervalo {args.interval}s")
        print(f"{'hora':8s} {'input':10s} {'err':>10s} {'AND':>5s} {'-> ESTADO PUBLICADO':>22s}")
        print("-" * 60)

        steps = [(s, i) for s, n in SEQUENCE for i in range(n)]
        for idx, (input_state, _) in enumerate(steps):
            out = evaluate(client, args.url, token, READINGS[input_state])
            err = out["recon_error"]
            hora = datetime.now().strftime("%H:%M:%S")
            err_s = f"{err:.4f}" if err is not None else "  —"
            print(f"{hora} {input_state:10s} {err_s:>10s} "
                  f"{str(out['and_alert']):>5s} {out['health_state']:>22s}")
            if idx < len(steps) - 1:
                time.sleep(args.interval)

        print("-" * 60)
        # estado vigente final
        r = client.get(f"{args.url}/api/v1/health-monitor/{DEVICE}/state",
                       headers={"Authorization": f"Bearer {token}"}, timeout=10)
        print(f"Estado vigente final: {r.json()['health_state']}")


if __name__ == "__main__":
    main()
