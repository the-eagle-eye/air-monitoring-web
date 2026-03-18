"""
Seed healthy readings for T102 and T103 to generate low-risk predictions.

Generates 300 readings per device with stable sensor values matching the
real T101 healthy baselines from the CR310 CSV data (used to train the model).

Usage:
    python scripts/seed_healthy_readings.py [--url URL]
"""

import argparse
import random
from datetime import datetime, timezone, timedelta

import httpx

DEVICES = ["T102", "T103"]

# Healthy baselines extracted from REAL T101 CR310 data (P5-P95 ranges)
# These match the data the ML model was trained on (calibrated_multi_profile)
HEALTHY_VALUES = {
    "SO2_ppb": (-2.2, -1.3),           # real T101: -2.17 to -1.36
    "H2S_ppb": (-1.4, -0.3),           # real T101: -1.33 to -0.37
    "Reaction_Temp": (49.7, 50.1),      # real T101: 49.75 to 50.03
    "IZS_Temp": (0.0, 0.0),            # real T101: constant 0
    "PMT_Temp": (8.5, 10.0),           # real T101: 8.56 to 10.00
    "SampleFlow": (590.0, 640.0),       # real T101: 592 to 640
    "Pressure": (17.2, 18.5),           # real T101: 17.28 to 18.50
    "UVLampIntensity": (1930.0, 1955.0),  # real T101: 1931 to 1951 (HIGH = healthy)
    "Box_Temp": (33.9, 35.3),           # real T101: 33.99 to 35.24
    "HVPS_V": (643.0, 648.0),           # real T101: 643.65 to 647.71
    "Conv_Temp": (312.0, 314.0),        # real T101: 312 to 314
    "Ozone_flow": (0.0, 0.0),          # real T101: constant 0
}

N_READINGS = 300  # > 288 (24h window at 5-min intervals)


def main():
    parser = argparse.ArgumentParser(description="Seed healthy readings")
    parser.add_argument(
        "--url",
        default="http://localhost:8001/api/v1/iot/readings",
        help="IoT service readings endpoint URL",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    for device_id in DEVICES:
        print(f"\n--- Seeding {N_READINGS} healthy readings for {device_id} ---")
        ok = 0
        err = 0

        for i in range(N_READINGS):
            ts = now - timedelta(minutes=5 * (N_READINGS - i))
            payload = {
                "equipo": device_id,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for field, (low, high) in HEALTHY_VALUES.items():
                if low == high:
                    payload[field] = low
                else:
                    payload[field] = round(random.uniform(low, high), 2)

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
                print(f"  {device_id}: {i+1}/{N_READINGS} sent ({ok} ok, {err} err)")

        print(f"  {device_id} DONE: {ok} ok, {err} errors")

    print("\nAll done! Now run predictions from the app for T102 and T103.")


if __name__ == "__main__":
    main()
