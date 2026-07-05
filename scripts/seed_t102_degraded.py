
"""
Seed heavily degraded readings for T102 to produce RUL < 30 predictions.

Generates 300 readings with progressive sensor degradation matching the
patterns used in model training (high degradation profile). Prediction
must be triggered manually from the app.

Usage:
    python scripts/seed_t102_degraded.py [--url URL]
"""

import argparse
import random
from datetime import datetime, timezone, timedelta

import httpx

DEVICE = "T102"

# Healthy baselines from real T101 CR310 data (P5-P95 ranges)
HEALTHY_BASELINES = {
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

FIELD_TO_API = {
    "SO2_ppb": "SO2_ppb",
    "H2S_ppb": "H2S_ppb",
    "Reaction_Temp": "Reaction_Temp",
    "IZS_Temp": "IZS_Temp",
    "PMT_Temp": "PMT_Temp",
    "SampleFlow": "SampleFlow",
    "Pressure": "Pressure",
    "UVLampIntensity": "UVLampIntensity",
    "Box_Temp": "Box_Temp",
    "HVPS_V": "HVPS_V",
    "Conv_Temp": "Conv_Temp",
    "Ozone_flow": "Ozone_flow",
}

# Snake case names used by degradation logic (match seed_prediction_data.py)
FIELD_TO_SNAKE = {
    "SO2_ppb": "so2_ppb",
    "H2S_ppb": "h2s_ppb",
    "Reaction_Temp": "reaction_temp",
    "IZS_Temp": "izs_temp",
    "PMT_Temp": "pmt_temp",
    "SampleFlow": "sample_flow",
    "Pressure": "pressure",
    "UVLampIntensity": "uv_lamp_intensity",
    "Box_Temp": "box_temp",
    "HVPS_V": "hvps_v",
    "Conv_Temp": "conv_temp",
    "Ozone_flow": "ozone_flow",
}

N_READINGS = 300
# High degradation: progress from 0.85 to 0.98 (same as seed_prediction_data "high" profile)
PROGRESS_START = 0.85
PROGRESS_END = 0.98


def main():
    parser = argparse.ArgumentParser(description="Seed degraded readings for T102")
    parser.add_argument(
        "--url",
        default="http://localhost:8001/api/v1/iot/readings",
        help="IoT service readings endpoint URL",
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    rng = random.Random(102)

    print(f"\n--- Seeding {N_READINGS} degraded readings for {DEVICE} (RUL < 30 target) ---")
    ok = 0
    err = 0

    for i in range(N_READINGS):
        # Linear progress from PROGRESS_START to PROGRESS_END
        progress = PROGRESS_START + (PROGRESS_END - PROGRESS_START) * i / max(N_READINGS - 1, 1)

        ts = now - timedelta(minutes=5 * (N_READINGS - i))
        payload = {
            "equipo": DEVICE,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        }

        for field, (low, high) in HEALTHY_BASELINES.items():
            snake = FIELD_TO_SNAKE[field]
            baseline = (low + high) / 2
            noise_std = (high - low) * 0.02 if (high - low) > 0 else 0.01
            value = baseline + rng.gauss(0, noise_std)

            # Apply degradation patterns (same logic as seed_prediction_data.py)
            if snake == "uv_lamp_intensity":
                value -= baseline * 0.50 * progress
            elif snake in ("reaction_temp", "box_temp", "conv_temp"):
                value += (high - low) * 2.0 * progress
            elif snake == "sample_flow":
                value -= baseline * 0.35 * progress
            elif snake == "hvps_v":
                instability = progress ** 2 * (high - low) * 4
                value += rng.gauss(0, 1) * instability
            elif snake in ("so2_ppb", "h2s_ppb"):
                value += abs(baseline) * 0.45 * progress
            elif snake == "pmt_temp":
                value += (high - low) * 1.2 * progress

            anomaly_prob = 0.02 + 0.20 * progress ** 2
            if rng.random() < anomaly_prob:
                anomaly_mag = rng.uniform(1.0, 3.0) * (high - low) if (high - low) > 0 else 1.5
                value += rng.choice([-1, 1]) * anomaly_mag

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
    print("\nNow run the prediction for T102 from the app.")


if __name__ == "__main__":
    main()
