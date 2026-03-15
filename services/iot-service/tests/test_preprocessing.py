from app.models.lectura_iot import LecturaIoT
from app.services.preprocessing_service import SENSOR_FIELDS, build_feature_vector


def test_build_feature_vector_returns_all_fields():
    lectura = LecturaIoT(
        so2_ppb=25.43,
        h2s_ppb=2.18,
        reaction_temp=35.0,
        izs_temp=34.2,
        pmt_temp=36.1,
        sample_flow=452.3,
        pressure=29.76,
        uv_lamp_intensity=403.5,
        box_temp=33.7,
        hvps_v=671.2,
        conv_temp=35.9,
        ozone_flow=480.5,
    )
    vector = build_feature_vector(lectura)
    assert len(vector) == len(SENSOR_FIELDS)
    for field in SENSOR_FIELDS:
        assert field in vector
    assert vector["so2_ppb"] == 25.43
    assert vector["ozone_flow"] == 480.5


def test_build_feature_vector_handles_none():
    lectura = LecturaIoT(so2_ppb=10.0)
    vector = build_feature_vector(lectura)
    assert vector["so2_ppb"] == 10.0
    assert vector["h2s_ppb"] is None
