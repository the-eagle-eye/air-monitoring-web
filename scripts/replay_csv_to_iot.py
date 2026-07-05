# -*- coding: utf-8 -*-
"""Replay a slice of a training CSV as IoT readings.

The v3 anomaly detectors were trained on real Thermo 43iQ output. Current
iot-service seed scripts (`seed_*.py`) use fabricated baselines calibrated
to the legacy v1 synthetic model — the scales don't match v3's training
distribution.

This script bridges the gap during the pre-deployment period by streaming
rows from Daniel's dataset CSVs into iot-service as if they were live
telemetry from a real datalogger. Once physical analyzers are wired to
CR310s, this script becomes obsolete.

Usage:
    # Last 200 rows of Uchucarcco into T103, healthy tail:
    python scripts/replay_csv_to_iot.py --station CA-UCHU-01 --device T103

    # Pre-failure slice (last 500 rows before the penultimate failure):
    python scripts/replay_csv_to_iot.py --station CA-UCHU-01 --device T103 \\
        --slice pre_failure --n 500

Options:
    --station    Station code (CA-UCHU-01, CA-ILO-01, …)
    --device     IoT device_id (T101, T103, …) — must exist in iot-service
    --slice      "tail" (default) | "pre_failure" | "healthy"
    --n          Number of rows to stream (default 200)
    --url        iot-service ingestion endpoint (default localhost:8001)
    --db         Postgres URL, used to clear existing readings first
    --keep       If set, do NOT clear existing readings for this device
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "services" / "ml-proposal" / "dataset"

STATION_CSV = {
    "CA-CHILLO-01": "CA-CHILLO-01_DATASET_v2_LIMPIO.csv",
    "CA-CC-01":     "CA-CC-01_OROYA_DATASET.csv",
    "CA-UCHU-01":   "CA-UCHU-01_UCHUCARCCO_DATASET.csv",
    "CA-CH-05":     "CA-CH-05_GARCILASO_DATASET.csv",
    "CA-CH-04":     "CA-CH-04_GRAU_DATASET.csv",
    "CA-ILO-01":    "CA-ILO-01_BOLOGNESI_DATASET.csv",
}

# Training-CSV column name → iot-service payload key (mixed case).
# Must stay in sync with services/ml-service-isolation/app/ml/station_registry.py
CSV_TO_IOT = {
    "SO2_PPB":           "SO2_ppb",
    "SO2_FLOW":          "SampleFlow",
    "SO2_LAMP_INT":      "UVLampIntensity",
    "SO2_INTERNAL_TEMP": "Reaction_Temp",
    "SO2_PMT_VOLTAGE":   "HVPS_V",
    "SO2_BENCH_TEMP":    "Box_Temp",
    "SO2_BENCH_PRESS":   "Pressure",
    "SO2_CHAMBER_TEMP":  "Reaction_Temp",
    "SO2_CONV_TEMP":     "Conv_Temp",
}


def select_slice(df: pd.DataFrame, kind: str, n: int) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    d = df[df["valido"] == True]  # only valid rows

    if kind == "tail":
        return d.tail(n)

    if kind == "healthy":
        h = d.dropna(subset=["rul_days"])
        h = h[h["rul_days"] > 20]
        if h.empty:
            print("warn: no healthy slice found, falling back to tail")
            return d.tail(n)
        # Middle third of healthy — avoid post-failure recovery periods
        mid = len(h) // 2
        half = n // 2
        return h.iloc[max(0, mid - half): mid + half + n % 2]

    if kind == "pre_failure":
        r = d.dropna(subset=["rul_days"])
        fallas = sorted(
            {g["date"].max() for _cid, g in r.groupby("ciclo_id")}
        )
        if len(fallas) < 2:
            print("warn: <2 failures, using tail")
            return d.tail(n)
        target = fallas[-2]  # penultimate — CSV end isn't a real failure
        window = d[d["date"] <= target].tail(n)
        return window

    raise ValueError(f"unknown slice kind: {kind}")


def clear_readings(db_url: str, device: str) -> int:
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM lecturas_iot
                WHERE device_id = (SELECT id FROM equipos WHERE device_id = %s)
                """,
                (device,),
            )
            deleted = cur.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def build_payload(row: pd.Series, device: str, ts: datetime) -> dict:
    payload: dict = {
        "equipo": device,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }
    for csv_col, iot_key in CSV_TO_IOT.items():
        if csv_col not in row.index:
            continue
        val = row[csv_col]
        if pd.isna(val):
            continue
        payload[iot_key] = round(float(val), 4)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--station", required=True, choices=sorted(STATION_CSV))
    ap.add_argument("--device", required=True, help="iot device_id, e.g. T103")
    ap.add_argument("--slice", default="tail",
                    choices=["tail", "healthy", "pre_failure"])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--url", default="http://localhost:8001/api/v1/iot/readings")
    ap.add_argument("--db", default="postgresql://airmon:airmon123@localhost:5432/airmonitoring")
    ap.add_argument("--keep", action="store_true",
                    help="Skip clearing existing readings")
    args = ap.parse_args()

    csv_path = DATASET_DIR / STATION_CSV[args.station]
    if not csv_path.exists():
        print(f"error: dataset not found: {csv_path}", file=sys.stderr)
        return 1

    print(f"[{args.station} → {args.device}] loading {csv_path.name}…")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    print(f"  loaded {len(df):,} rows")

    slc = select_slice(df, args.slice, args.n)
    if slc.empty:
        print("error: empty slice", file=sys.stderr)
        return 2
    print(f"  slice='{args.slice}' n={len(slc)} "
          f"range={slc['date'].min()} → {slc['date'].max()}")

    if not args.keep:
        deleted = clear_readings(args.db, args.device)
        print(f"  cleared {deleted} existing readings for {args.device}")

    # Restamp: end at "now", 5-min cadence backwards
    now = datetime.now(timezone.utc).replace(microsecond=0)
    step = timedelta(minutes=5)
    ok = err = 0
    for i, (_idx, row) in enumerate(slc.iterrows()):
        ts = now - step * (len(slc) - 1 - i)
        payload = build_payload(row, args.device, ts)
        try:
            r = httpx.post(args.url, json=payload, timeout=10.0)
            if r.status_code in (200, 201):
                ok += 1
            else:
                err += 1
                if err <= 3:
                    print(f"  ERR {r.status_code}: {r.text[:200]}")
        except httpx.RequestError as exc:
            err += 1
            if err <= 3:
                print(f"  CONNECTION ERROR: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(slc)}  ok={ok} err={err}")

    print(f"\ndone: ok={ok} err={err}")
    if err == 0:
        print("\ntip: run a v3 prediction to see realistic anomaly scores:")
        print(
            f'  curl -X POST http://localhost:8004/api/v1/predictions/run '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"device_id":"{args.device}"}}\''
        )
    return 0 if err == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
