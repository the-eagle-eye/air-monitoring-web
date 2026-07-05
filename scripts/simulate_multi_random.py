# -*- coding: utf-8 -*-
"""
Simulación multi-equipo con estados ALEATORIOS: CA-CH-04, CA-ILO-01, CA-UCHU-01.

Cada ciclo (cada --interval s) elige un estado aleatorio (SANO/EN_RIESGO/CRITICO)
para cada equipo y le inyecta lecturas al endpoint /health-monitor/evaluate.

Valores calibrados por equipo contra su propio modelo (θ distinto cada uno).

Anti-parpadeo (§5.1): para que un descenso de severidad (p.ej. CRITICO->SANO) se
haga visible, cuando el estado objetivo es de MENOR severidad que el actual se
envían N_CONSEC=3 lecturas seguidas. Subir a CRITICO es inmediato.

Uso:
    python scripts/simulate_multi_random.py                 # 6 ciclos, 30s
    python scripts/simulate_multi_random.py --cycles 8 --interval 30 --seed 7
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

import httpx

LOGIN = {"email": "admin@oefa.gob.pe", "password": "admin123"}

# Valores calibrados (ppb, flow, temp, lamp) por equipo y estado.
DEVICES = {
    "CA-CH-04": {
        "SANO":      (2.0, 0.45, 30.7, 102.0),
        "EN_RIESGO": (2.45, 0.431, 32.8, 100.65),
        "CRITICO":   (3.0, 0.41, 35.0, 99.5),
    },
    "CA-ILO-01": {
        "SANO":      (4.91, 0.421, 30.65, 93.38),
        "EN_RIESGO": (6.81, 0.37, 34.45, 91.48),
        "CRITICO":   (7.19, 0.36, 35.2, 91.11),
    },
    "CA-UCHU-01": {
        "SANO":      (2.86, 0.387, 31.59, 101.28),
        "EN_RIESGO": (3.05, 0.381, 32.0, 101.0),   # err ~1.25 (entre 2θ y 3θ)
        "CRITICO":   (3.76, 0.363, 33.4, 100.38),
    },
}

SEVERITY = {"SANO": 0, "EN_RIESGO": 2, "CRITICO": 3}
STATES = ["SANO", "EN_RIESGO", "CRITICO"]
N_CONSEC = 3


def login(client, base):
    r = client.post(f"{base}/api/v1/auth/login", json=LOGIN, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def evaluate(client, base, token, device, values):
    ppb, flow, temp, lamp = values
    payload = {
        "device_id": device,
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
    ap.add_argument("--cycles", type=int, default=6)
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    with httpx.Client() as client:
        token = login(client, args.url)
        current = {d: "SANO" for d in DEVICES}  # estado publicado asumido
        print(f"Simulación multi-equipo aleatoria — {args.cycles} ciclos cada {args.interval}s")
        print(f"{'ciclo':6s} {'equipo':12s} {'target':10s} {'-> publicado':>14s} {'err':>9s}")
        print("-" * 56)

        for c in range(1, args.cycles + 1):
            for device in DEVICES:
                target = rng.choice(STATES)
                # Anti-parpadeo: solo subir a CRITICO es inmediato (1 lectura).
                # Cualquier otro cambio (subir a EN_RIESGO, o bajar de severidad)
                # requiere N_CONSEC lecturas para confirmarse.
                if target == "CRITICO" and SEVERITY[target] > SEVERITY[current[device]]:
                    reps = 1
                elif target == current[device]:
                    reps = 1
                else:
                    reps = N_CONSEC
                out = None
                for _ in range(reps):
                    out = evaluate(client, args.url, token, device, DEVICES[device][target])
                    if reps > 1:
                        time.sleep(1)  # pequeña pausa entre lecturas del mismo estado
                current[device] = out["health_state"]
                err = out["recon_error"]
                err_s = f"{err:.3f}" if err is not None else "  —"
                print(f"c{c:<5d} {device:12s} {target:10s} {out['health_state']:>14s} {err_s:>9s}")
            print()
            if c < args.cycles:
                time.sleep(args.interval)

        print("-" * 56)
        for device in DEVICES:
            r = client.get(f"{args.url}/api/v1/health-monitor/{device}/state",
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
            print(f"{device}: {r.json()['health_state']}")


if __name__ == "__main__":
    main()
