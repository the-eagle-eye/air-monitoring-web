"""
Seed stable readings for T108 to produce alerta BAJA (RUL >= 60 dias).

Generates 300 readings with sensor values very close to healthy baselines,
minimal drift. Prediction must be triggered manually from the app.

Expected result after prediction:
  - risk_level: baja
  - RUL >= 60 dias
  - failure_probability < 0.3

Usage:
    python scripts/seed_t108_low_alert.py [--url URL] [--db DB_URL]
"""

import argparse
import random
from datetime import datetime, timezone, timedelta

import httpx
import psycopg2

DEVICE = "T108"

HEALTHY_VALUES = {
    "SO2_ppb": (-2.2, -1.3),
    "H2S_ppb": (-1.4, -0.3),
    "Reaction_Temp": (49.7, 50.1),
    "IZS_Temp": (0.0, 0.0),
    "PMT_Temp": (8.5, 10.0),
    "SampleFlow": (590.0, 640.0),
    "Pressure": (17.2, 18.5),
    "UVLampIntensity": (1930.0, 1955.0),
    "Box_Temp": (33.9, 35.3),
    "HVPS_V": (643.0, 648.0),
    "Conv_Temp": (312.0, 314.0),
    "Ozone_flow": (0.0, 0.0),
}

N_READINGS = 300


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


def main():
    parser = argparse.ArgumentParser(description="Seed stable readings for T108 (alerta baja)")
    parser.add_argument(
        "--url",
        default="http://localhost:8001/api/v1/iot/readings",
        help="IoT service readings endpoint URL",
    )
    parser.add_argument(
        "--db",
        default="postgresql://airmon:airmon123@localhost:5432/airmonitoring",
        help="PostgreSQL connection URL",
    )
    args = parser.parse_args()

    print(f"\n--- Clearing existing readings for {DEVICE} ---")
    deleted = clear_readings(args.db, DEVICE)
    print(f"  Deleted {deleted} rows")

    now = datetime.now(timezone.utc)
    rng = random.Random(108)

    print(f"\n--- Seeding {N_READINGS} stable readings for {DEVICE} (alerta BAJA target: RUL >= 60) ---")
    ok = 0
    err = 0

    for i in range(N_READINGS):
        ts = now - timedelta(minutes=5 * (N_READINGS - i))
        payload = {
            "equipo": DEVICE,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for field, (low, high) in HEALTHY_VALUES.items():
            if low == high:
                payload[field] = low
            else:
                center = (low + high) / 2
                std = (high - low) * 0.10
                value = rng.gauss(center, std)
                value = max(low, min(high, value))
                payload[field] = round(value, 2)

        try:
            resp = httpx.post(args.url, json=payload, timeout=10.0)
            if resp.status_code in (200, 201):
                ok += 1
            else:
                err += 1
                if err <= 3:
                    print(f"  ERR {resp.status_code}: {resp.text[:200]}")
        except httpx.RequestError as e:
            err += 1
            if err <= 3:
                print(f"  CONNECTION ERROR: {e}")

        if (i + 1) % 50 == 0:
            print(f"  {DEVICE}: {i+1}/{N_READINGS} sent ({ok} ok, {err} err)")

    print(f"  {DEVICE} DONE: {ok} ok, {err} errors")
    print(f"\nNow run the prediction for {DEVICE} from the app.")
    print("Expected: risk_level=baja, RUL >= 60 dias, failure_probability < 0.3")


if __name__ == "__main__":
    main()
