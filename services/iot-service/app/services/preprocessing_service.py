from app.models.lectura_iot import LecturaIoT

# Canonical legacy sensor names — kept for backwards-compatible feature vectors
# consumed by ml-service. New sensor keys are passed through transparently.
SENSOR_FIELDS = [
    "SO2_ppb",
    "H2S_ppb",
    "Reaction_Temp",
    "IZS_Temp",
    "PMT_Temp",
    "SampleFlow",
    "Pressure",
    "UVLampIntensity",
    "Box_Temp",
    "HVPS_V",
    "Conv_Temp",
    "Ozone_flow",
]


def build_feature_vector(reading: LecturaIoT) -> dict[str, float | None]:
    """Extract a dict of features from a LecturaIoT instance.

    Reads from the flexible ``sensors`` JSONB column. Guarantees each
    legacy SENSOR_FIELDS key is present (None when absent) and includes
    any additional sensors the datalogger reported.
    """
    sensors = reading.sensors or {}
    vector: dict[str, float | None] = {
        field: sensors.get(field) for field in SENSOR_FIELDS
    }
    for k, v in sensors.items():
        if k not in vector:
            vector[k] = v
    return vector
