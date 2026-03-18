"""
Seed massive readings + predictions for dashboard visualization.

Generates multiple batches of degraded readings per device and triggers
the ML prediction pipeline after each batch, producing varied RUL values
for the "Tendencia de Predicciones" chart.

Predictions are spread across dates from START_DATE (2026-03-01) to today,
so the trends chart shows a realistic timeline.

Usage:
    python scripts/seed_prediction_data.py
    python scripts/seed_prediction_data.py --iot-url http://localhost:8001/api/v1/iot/readings --ml-url http://localhost:8002/api/v1/predictions/run
"""

import argparse
import random
import time
from datetime import datetime, timedelta, timezone

import httpx
import psycopg2

# --- Configuration ---
START_DATE = datetime(2026, 3, 1, tzinfo=timezone.utc)

DEVICE_TARGETS = {
    "T101": 15,
    "T102": 20,
    "T103": 40,
    "T104": 10,
}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "airmonitoring",
    "user": "airmon",
    "password": "airmon123",
}

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

DEGRADATION_PROFILES = [
    ("low", (0.05, 0.20)),
    ("medium", (0.50, 0.70)),
    ("high", (0.85, 0.98)),
]

N_READINGS = 300


def compute_prediction_dates(target: int) -> list[datetime]:
    """Distribute prediction dates evenly from START_DATE to now."""
    now = datetime.now(timezone.utc)
    if target == 1:
        return [START_DATE + (now - START_DATE) / 2]
    step = (now - START_DATE) / (target - 1)
    return [START_DATE + step * i for i in range(target)]


def generate_degraded_batch(
    progress_range: tuple[float, float],
    n_readings: int,
    rng: random.Random,
    prediction_date: datetime,
) -> list[dict]:
    """Generate a batch of readings ending at prediction_date."""
    progress_values = [
        progress_range[0] + (progress_range[1] - progress_range[0]) * i / max(n_readings - 1, 1)
        for i in range(n_readings)
    ]

    # Readings span 24h+ before the prediction date
    base_time = prediction_date - timedelta(minutes=5 * n_readings)
    readings = []

    for i, progress in enumerate(progress_values):
        payload = {}
        for field, (low, high) in HEALTHY_BASELINES.items():
            snake = FIELD_TO_SNAKE[field]
            baseline = (low + high) / 2
            noise_std = (high - low) * 0.02 if (high - low) > 0 else 0.01
            value = baseline + rng.gauss(0, noise_std)

            if snake == "uv_lamp_intensity":
                value -= baseline * 0.4 * progress
            elif snake in ("reaction_temp", "box_temp", "conv_temp"):
                value += (high - low) * 1.5 * progress
            elif snake in ("sample_flow", "ozone_flow"):
                value -= baseline * 0.25 * progress
            elif snake == "hvps_v":
                instability = progress ** 2 * (high - low) * 3
                value += rng.gauss(0, 1) * instability
            elif snake in ("so2_ppb", "h2s_ppb"):
                value += baseline * 0.3 * progress

            anomaly_prob = 0.01 + 0.15 * progress ** 2
            if rng.random() < anomaly_prob:
                anomaly_mag = rng.uniform(0.5, 2.0) * (high - low) if (high - low) > 0 else 1.0
                value += rng.choice([-1, 1]) * anomaly_mag

            payload[field] = round(value, 2)

        payload["timestamp"] = (base_time + timedelta(minutes=5 * i)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        readings.append(payload)

    return readings


def post_readings(readings: list[dict], equipo: str, iot_url: str) -> tuple[int, int]:
    """POST readings to IoT service."""
    ok, err = 0, 0
    with httpx.Client(timeout=10.0) as client:
        for reading in readings:
            reading["equipo"] = equipo
            try:
                resp = client.post(iot_url, json=reading)
                if resp.status_code in (200, 201):
                    ok += 1
                else:
                    err += 1
                    if err <= 2:
                        print(f"    READ ERR {resp.status_code}: {resp.text[:120]}")
            except httpx.RequestError as e:
                err += 1
                if err <= 2:
                    print(f"    CONNECTION ERR: {e}")
    return ok, err


def run_prediction(device_id: str, ml_url: str) -> dict | None:
    """Trigger prediction for a device and return the result."""
    try:
        resp = httpx.post(ml_url, json={"device_id": device_id}, timeout=30.0)
        if resp.status_code in (200, 201):
            data = resp.json()
            return data[0] if isinstance(data, list) and data else data
        else:
            print(f"    PRED ERR {resp.status_code}: {resp.text[:120]}")
            return None
    except httpx.RequestError as e:
        print(f"    PRED CONNECTION ERR: {e}")
        return None


def update_prediction_date(pred_id: int, target_date: datetime, db_conn):
    """Update prediction_timestamp and created_at directly in PostgreSQL."""
    with db_conn.cursor() as cur:
        # Update prediction
        cur.execute(
            """UPDATE predicciones
               SET prediction_timestamp = %s, created_at = %s
               WHERE id = %s""",
            (target_date, target_date, pred_id),
        )
        # Update associated alerts to match
        cur.execute(
            """UPDATE alertas
               SET created_at = %s
               WHERE prediccion_id = %s""",
            (target_date, pred_id),
        )
    db_conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed readings + predictions for dashboards")
    parser.add_argument("--iot-url", default="http://localhost:8001/api/v1/iot/readings")
    parser.add_argument("--ml-url", default="http://localhost:8002/api/v1/predictions/run")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--db-host", default=DB_CONFIG["host"])
    parser.add_argument("--db-port", type=int, default=DB_CONFIG["port"])
    args = parser.parse_args()

    rng = random.Random(args.seed)
    total_predictions = 0

    # Connect to PostgreSQL for date updates
    db_conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )
    print(f"Connected to PostgreSQL at {args.db_host}:{args.db_port}")

    try:
        for device_id, target in DEVICE_TARGETS.items():
            dates = compute_prediction_dates(target)

            print(f"\n{'='*60}")
            print(f"  {device_id}: generating {target} predictions")
            print(f"  Date range: {dates[0].strftime('%Y-%m-%d')} -> {dates[-1].strftime('%Y-%m-%d')}")
            print(f"{'='*60}")

            for pred_num, target_date in enumerate(dates, 1):
                level_name, progress_range = rng.choice(DEGRADATION_PROFILES)

                print(f"\n  [{pred_num}/{target}] {device_id} - {target_date.strftime('%Y-%m-%d %H:%M')} "
                      f"- degradation={level_name}")

                # Generate readings with timestamps ending at target_date
                readings = generate_degraded_batch(progress_range, N_READINGS, rng, target_date)
                ok, err = post_readings(readings, device_id, args.iot_url)
                print(f"    Readings: {ok} ok, {err} errors")

                if ok == 0:
                    print(f"    SKIP prediction (no readings posted)")
                    continue

                # Run prediction via ML service
                result = run_prediction(device_id, args.ml_url)
                if result:
                    pred_id = result.get("id")
                    rul = result.get("remaining_useful_life_days", "?")
                    prob = result.get("failure_probability", "?")
                    risk = result.get("risk_level", "?")
                    print(f"    Prediction #{pred_id}: RUL={rul} days, prob={prob}, risk={risk}")

                    # Update the date in DB to spread across the timeline
                    if pred_id:
                        update_prediction_date(pred_id, target_date, db_conn)
                        print(f"    Date updated -> {target_date.strftime('%Y-%m-%d %H:%M')}")

                    total_predictions += 1
                else:
                    print(f"    Prediction FAILED")

                time.sleep(0.3)

    finally:
        db_conn.close()

    print(f"\n{'='*60}")
    print(f"  DONE: {total_predictions} predictions generated")
    print(f"  Date range: {START_DATE.strftime('%Y-%m-%d')} -> now")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
