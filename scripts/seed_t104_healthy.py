"""
Seed healthy readings for T104 to produce RUL > 90 predictions.

Generates 300 readings with stable sensor values matching real T101 healthy
baselines (no degradation). Prediction must be triggered manually from the app.

Usage:
    python scripts/seed_t104_healthy.py [--url URL]
"""

import argparse
import random
from datetime import datetime, timezone, timedelta

import httpx

DEVICE = "T104"

# Healthy baselines from real T101 CR310 data (P5-P95 ranges)
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

N_READINGS = 300  # > 288 (24h window at 5-min intervals)


def main():
    parser = argparse.ArgumentParser(description="Seed healthy readings for T104")
    parser.add_argument(
        "--url",
        default="http://localhost:8001/api/v1/iot/readings",
        help="IoT service readings endpoint URL",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    rng = random.Random(104)

    print(f"\n--- Seeding {N_READINGS} healthy readings for {DEVICE} ---")
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
                # Tight gaussian around center for very stable readings
                center = (low + high) / 2
                std = (high - low) * 0.15
                value = rng.gauss(center, std)
                # Clamp within range
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
    print("\nNow run the prediction for T104 from the app.")


if __name__ == "__main__":
    main()
