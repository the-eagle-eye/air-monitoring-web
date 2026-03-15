"""Load real CSV readings into the IoT service via HTTP.

Usage:
    python scripts/load_csv_readings.py --csv PATH [--equipo T101] [--all]
    python scripts/load_csv_readings.py --csv ../../dataset/datalogger_db.cr310_readings.csv --all
"""

import argparse
import sys
import time

import requests

sys.path.insert(0, ".")
from app.ml.real_data_loader import COLUMN_MAP, load_csv, filter_by_equipo

IOT_BASE_URL = "http://localhost:8001/api/v1/iot/readings"

# Reverse mapping: snake_case -> CSV column name (for payload)
REVERSE_MAP = {v: k for k, v in COLUMN_MAP.items()}


def post_readings(df, equipo: str, base_url: str = IOT_BASE_URL):
    """POST each row as an IoT reading."""
    success = 0
    errors = 0

    for _, row in df.iterrows():
        payload = {"equipo": equipo}
        for sensor_snake, col_csv in REVERSE_MAP.items():
            val = row.get(sensor_snake)
            if val is not None:
                payload[col_csv] = float(val)
        payload["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        try:
            resp = requests.post(base_url, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                success += 1
            else:
                errors += 1
                print(f"  ERROR {resp.status_code}: {resp.text[:100]}")
        except requests.RequestException as e:
            errors += 1
            print(f"  CONNECTION ERROR: {e}")

    return success, errors


def main():
    parser = argparse.ArgumentParser(description="Load CSV readings into IoT service")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--equipo", help="Filter by specific equipment")
    parser.add_argument("--all", action="store_true", help="Load all equipment")
    parser.add_argument(
        "--iot-url", default=IOT_BASE_URL, help="IoT service readings URL"
    )
    args = parser.parse_args()

    df = load_csv(args.csv)
    equipos = df["equipo"].unique()
    print(f"CSV loaded: {len(df)} readings, equipos: {list(equipos)}")

    if args.equipo:
        targets = [args.equipo]
    elif args.all:
        targets = list(equipos)
    else:
        print("ERROR: Specify --equipo or --all")
        sys.exit(1)

    total_success = 0
    total_errors = 0

    for equipo in targets:
        equipo_df = filter_by_equipo(df, equipo)
        print(f"\nLoading {len(equipo_df)} readings for {equipo}...")
        s, e = post_readings(equipo_df, equipo, args.iot_url)
        total_success += s
        total_errors += e
        print(f"  {equipo}: {s} OK, {e} errors")

    print(f"\nTotal: {total_success} OK, {total_errors} errors")


if __name__ == "__main__":
    main()
