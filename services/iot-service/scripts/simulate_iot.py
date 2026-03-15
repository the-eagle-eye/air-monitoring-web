"""
Temporary development script that simulates CR310 datalogger equipment
sending readings to the IoT service endpoint.

In production, real CR310 devices send directly to POST /api/v1/iot/readings.

Usage:
    python scripts/simulate_iot.py [--url URL] [--interval SECONDS]
"""

import argparse
import random
import time
from datetime import datetime, timezone

import httpx

DEVICES = ["T101", "T102", "T103"]

# Realistic baseline values for Thermo 450i SO2/H2S analyzer
BASELINES = {
    "SO2_ppb": (20.0, 50.0),
    "H2S_ppb": (1.0, 5.0),
    "Reaction_Temp": (33.0, 37.0),
    "IZS_Temp": (32.0, 36.0),
    "PMT_Temp": (34.0, 38.0),
    "SampleFlow": (440.0, 460.0),
    "Pressure": (29.0, 30.5),
    "UVLampIntensity": (380.0, 420.0),
    "Box_Temp": (30.0, 36.0),
    "HVPS_V": (660.0, 680.0),
    "Conv_Temp": (34.0, 37.0),
    "Ozone_flow": (470.0, 490.0),
}


def generate_reading(device_id: str) -> dict:
    now = datetime.now(timezone.utc)
    payload = {"equipo": device_id, "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")}
    for field, (low, high) in BASELINES.items():
        value = random.uniform(low, high)
        payload[field] = round(value, 2)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Simulate CR310 IoT readings")
    parser.add_argument(
        "--url",
        default="http://localhost:8001/api/v1/iot/readings",
        help="IoT service readings endpoint URL",
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Seconds between readings"
    )
    args = parser.parse_args()

    print(f"Sending simulated readings to {args.url} every {args.interval}s")
    print(f"Devices: {', '.join(DEVICES)}")
    print("Press Ctrl+C to stop\n")

    count = 0
    while True:
        for device_id in DEVICES:
            payload = generate_reading(device_id)
            try:
                resp = httpx.post(args.url, json=payload, timeout=10.0)
                count += 1
                status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
                print(
                    f"[{count}] {device_id} @ {payload['timestamp']} -> {status}"
                )
            except httpx.RequestError as e:
                print(f"[{count}] {device_id} -> CONNECTION ERROR: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
