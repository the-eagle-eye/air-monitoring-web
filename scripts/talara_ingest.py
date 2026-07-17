# -*- coding: utf-8 -*-
"""Fase 9 del auto-training onboarding: backfill del dataset real de TALARA.

Reads `services/ml-proposal/dataset/CA-TA-01_TALARA_DATASET.csv` y postea CADA
fila como una lectura IoT en `/api/v1/iot/readings`. Al no ir por cadencia real
(sino en un shot, sin sleep), 52k lecturas simulan ~6 meses de operación en
minutos, lo que permite validar E2E:

  1. C8 auto-onboarding: primera lectura auto-crea `CA-TA-01` en cuarentena.
  2. C1 iot->ml notify: cada lectura llama al ensemble; hasta que la estación
     tenga θ propio, el ensemble responde SIN_DATOS.
  3. C11 warm-up: cuando el conteo de lecturas válidas cruza WARMUP_MIN_ROWS
     (default 2016), el trigger dispara `training_service.train_station` en
     fire-and-forget → theta_CA-TA-01.json + artefactos escritos.
  4. Post-training: siguientes lecturas se evalúan con θ propio, el dashboard
     muestra `CA-TA-01` con health_state real.

Ver docs/spec-auto-training-onboarding.md §3.1 (reglas de mapeo) y §9 (CA).

Uso:
    python scripts/talara_ingest.py --limit 100                # smoke test
    python scripts/talara_ingest.py                            # backfill completo
    python scripts/talara_ingest.py --url http://localhost:8001  # bypass gateway
    python scripts/talara_ingest.py --dry-run                  # imprime payloads

Requiere: pandas, httpx. Servicios levantados (docker compose up).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = (
    REPO_ROOT
    / "services"
    / "ml-proposal"
    / "dataset"
    / "CA-TA-01_TALARA_DATASET.csv"
)
DEVICE_ID = "CA-TA-01"

# Reglas del spec §3.1: sólo las 4 features raw del ensemble. NO enviar
# SO2_PMT_VOLTAGE (no está en el modelo), NO enviar `valido` (iot lo re-deriva),
# NO enviar las 45 rolling features / rul_days / ciclo_id.
CSV_TO_PAYLOAD = {
    "SO2_PPB": "so2_ppb",
    "SO2_FLOW": "so2_flow",
    "SO2_INTERNAL_TEMP": "so2_internal_temp",
    "SO2_LAMP_INT": "so2_lamp_int",
}


def _row_to_payload(row: pd.Series) -> dict:
    """Construye el payload minimal para /iot/readings a partir de una fila del
    CSV. Los sensores van como campos extra (extra='allow' en LecturaIoTCreate)
    y quedan persistidos en `sensors` JSONB."""
    payload = {
        "equipo": DEVICE_ID,
        "timestamp": str(row["date"]),
    }
    for csv_col, api_key in CSV_TO_PAYLOAD.items():
        value = row[csv_col]
        if pd.isna(value):
            continue  # dejar que iot-service marque valido=0 vía _in_oefa_scale
        payload[api_key] = float(value)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                    help=f"Ruta al CSV (default: {DEFAULT_CSV})")
    ap.add_argument("--url", default="http://localhost:8000",
                    help="Base URL (gateway :8000 o iot :8001).")
    ap.add_argument("--limit", type=int, default=None,
                    help="Sólo N filas (útil para smoke test).")
    ap.add_argument("--start", type=int, default=0,
                    help="Empezar desde la fila N (skip inicial).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Imprime payloads sin hacer POST.")
    ap.add_argument("--progress-every", type=int, default=500,
                    help="Log cada N filas.")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"ERROR: no existe {args.csv}", file=sys.stderr)
        return 2

    print(f"Leyendo {args.csv} …")
    df = pd.read_csv(
        args.csv,
        usecols=["date"] + list(CSV_TO_PAYLOAD.keys()),
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if args.start:
        df = df.iloc[args.start:].reset_index(drop=True)
    if args.limit:
        df = df.iloc[: args.limit].reset_index(drop=True)
    print(f"  → {len(df):,} filas a postear en {DEVICE_ID}")

    url = f"{args.url.rstrip('/')}/api/v1/iot/readings"
    if args.dry_run:
        for _, r in df.head(5).iterrows():
            print(_row_to_payload(r))
        print(f"[dry-run] no se envió nada. Total: {len(df)} filas listas.")
        return 0

    ok = 0
    fail = 0
    t0 = time.time()
    with httpx.Client(timeout=15.0) as client:
        for i, row in df.iterrows():
            payload = _row_to_payload(row)
            try:
                resp = client.post(url, json=payload)
                if resp.status_code >= 400:
                    fail += 1
                    if fail <= 5:
                        print(
                            f"  fila {i} status={resp.status_code} "
                            f"body={resp.text[:200]}",
                            file=sys.stderr,
                        )
                else:
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                if fail <= 5:
                    print(f"  fila {i} exc: {exc}", file=sys.stderr)

            if (i + 1) % args.progress_every == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / max(elapsed, 0.001)
                print(
                    f"  {i + 1:>6,}/{len(df):,} "
                    f"ok={ok} fail={fail} rate={rate:.1f}/s"
                )

    dt = time.time() - t0
    print(f"\nCompletado en {dt:.1f}s — ok={ok:,} fail={fail:,}")
    print(
        f"Verificar: GET {args.url}/api/v1/health-monitor/training-state "
        f"— {DEVICE_ID} debe aparecer con readings_valid_count subiendo."
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
