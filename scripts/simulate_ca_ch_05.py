# -*- coding: utf-8 -*-
"""
Simulación en vivo de CA-CH-05: inyecta lecturas al endpoint /health-monitor/evaluate
cada 30 s para recorrer CRITICO -> SANO -> CRITICO -> EN_RIESGO.

Valores calibrados contra el modelo real de CA-CH-05 (θ=0.2066): producen el error de
reconstrucción de cada banda Y activan el Isolation Forest para que el AND confirme.

NOTA sobre anti-parpadeo (§5.1): SUBIR a CRITICO es inmediato (1 lectura), pero BAJAR
de severidad (CRITICO->SANO, CRITICO->EN_RIESGO) requiere N_CONSEC=3 lecturas estables.
Por eso las fases descendentes envían 3 lecturas seguidas.

Secuencia pedida: CRITICO -> SANO -> CRITICO -> EN_RIESGO

Uso:
    python scripts/simulate_ca_ch_05.py
    python scripts/simulate_ca_ch_05.py --interval 30
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import httpx

DEVICE = "CA-CH-05"
LOGIN = {"email": "admin@oefa.gob.pe", "password": "admin123"}

# Inputs calibrados por estado (ppb, flow, temp, lamp). valido=1 siempre.
READINGS = {
    "SANO":      (6.34, 0.46, 32.09, 101.54),   # err ~0.066
    "EN_RIESGO": (8.53, 0.402, 36.4, 99.24),    # err ~0.51 (2θ–3θ)
    "CRITICO":   (9.34, 0.38, 38.09, 98.54),    # err ~0.88 (>3θ)
}

# Secuencia: (estado, repeticiones). Descensos usan 3 lecturas por anti-parpadeo.
SEQUENCE = [
    ("CRITICO", 1),     # sube inmediato
    ("SANO", 3),        # baja: requiere 3 estables
    ("CRITICO", 1),     # sube inmediato
    ("EN_RIESGO", 3),   # baja de crítico a en_riesgo: requiere 3 estables
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
        print(f"Secuencia: CRITICO -> SANO -> CRITICO -> EN_RIESGO")
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
        r = client.get(f"{args.url}/api/v1/health-monitor/{DEVICE}/state",
                       headers={"Authorization": f"Bearer {token}"}, timeout=10)
        print(f"Estado vigente final: {r.json()['health_state']}")


if __name__ == "__main__":
    main()
