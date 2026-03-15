from app.models.lectura_iot import LecturaIoT

SENSOR_FIELDS = [
    "so2_ppb",
    "h2s_ppb",
    "reaction_temp",
    "izs_temp",
    "pmt_temp",
    "sample_flow",
    "pressure",
    "uv_lamp_intensity",
    "box_temp",
    "hvps_v",
    "conv_temp",
    "ozone_flow",
]


def build_feature_vector(reading: LecturaIoT) -> dict[str, float | None]:
    """Extract a dict of 13 numeric features from a LecturaIoT instance.

    Used by ml-service for prediction input.
    """
    return {field: getattr(reading, field, None) for field in SENSOR_FIELDS}
