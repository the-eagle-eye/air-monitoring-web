from app.models.lectura_iot import LecturaIoT
from app.services.preprocessing_service import SENSOR_FIELDS, build_feature_vector


def test_build_feature_vector_returns_all_fields():
    lectura = LecturaIoT(
        sensors={
            "SO2_ppb": 25.43,
            "H2S_ppb": 2.18,
            "Reaction_Temp": 35.0,
            "IZS_Temp": 34.2,
            "PMT_Temp": 36.1,
            "SampleFlow": 452.3,
            "Pressure": 29.76,
            "UVLampIntensity": 403.5,
            "Box_Temp": 33.7,
            "HVPS_V": 671.2,
            "Conv_Temp": 35.9,
            "Ozone_flow": 480.5,
        }
    )
    vector = build_feature_vector(lectura)
    for field in SENSOR_FIELDS:
        assert field in vector
    assert vector["SO2_ppb"] == 25.43
    assert vector["Ozone_flow"] == 480.5


def test_build_feature_vector_handles_missing_keys():
    lectura = LecturaIoT(sensors={"SO2_ppb": 10.0})
    vector = build_feature_vector(lectura)
    assert vector["SO2_ppb"] == 10.0
    assert vector["H2S_ppb"] is None


def test_build_feature_vector_passes_through_extra_sensors():
    lectura = LecturaIoT(sensors={"SO2_ppb": 5.0, "CO2_ppm": 412.5})
    vector = build_feature_vector(lectura)
    assert vector["SO2_ppb"] == 5.0
    assert vector["CO2_ppm"] == 412.5
