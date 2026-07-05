"""C8: validación del formato de device_id para onboarding automático."""
import pytest

from app.services.device_onboarding import is_valid_device_id


@pytest.mark.parametrize("device_id", [
    "T101", "T500", "T999",              # esquema Thermo/laboratorio
    "CA-CH-04", "CA-CHILLO-01", "CA-UCHU-01", "CA-PUNO-07",  # estación de campo
])
def test_device_ids_validos(device_id):
    assert is_valid_device_id(device_id) is True


@pytest.mark.parametrize("device_id", [
    "t101",          # minúscula
    "T10", "T1234",  # dígitos incorrectos
    "TABC",          # sin dígitos
    "CA-", "CA-CH", "CA-CH-",  # truncados
    "UNKNOWN", "",   # basura / vacío
    "T101; DROP TABLE equipos;--",  # inyección
    "CA CH 04",      # espacios
])
def test_device_ids_invalidos(device_id):
    assert is_valid_device_id(device_id) is False
