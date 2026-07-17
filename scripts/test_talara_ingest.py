"""Test unitario para el mapeo de talara_ingest.py.

No ejecuta HTTP — sólo verifica que _row_to_payload cumple las reglas del
spec §3.1 (lowercase, drop SO2_PMT_VOLTAGE, drop valido/rolling/rul_days).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from talara_ingest import _row_to_payload, CSV_TO_PAYLOAD, DEVICE_ID


def _row(**extras):
    base = {
        "date": "2026-01-01 00:00:00",
        "SO2_PPB": 2.72,
        "SO2_FLOW": 0.45,
        "SO2_INTERNAL_TEMP": 31.3,
        "SO2_LAMP_INT": 102.1,
    }
    base.update(extras)
    return pd.Series(base)


class TestRowToPayload:
    def test_produces_lowercase_ensemble_keys(self):
        payload = _row_to_payload(_row())
        assert payload["so2_ppb"] == 2.72
        assert payload["so2_flow"] == 0.45
        assert payload["so2_internal_temp"] == 31.3
        assert payload["so2_lamp_int"] == 102.1

    def test_includes_equipo_and_timestamp(self):
        payload = _row_to_payload(_row())
        assert payload["equipo"] == DEVICE_ID
        assert payload["timestamp"] == "2026-01-01 00:00:00"

    def test_does_not_include_pmt_voltage(self):
        """Spec §3.1 regla 2: SO2_PMT_VOLTAGE NO se envía (no está en el ensemble)."""
        payload = _row_to_payload(_row(SO2_PMT_VOLTAGE=-625.4))
        assert "SO2_PMT_VOLTAGE" not in payload
        assert "so2_pmt_voltage" not in payload
        assert "hvps_v" not in payload

    def test_does_not_include_valido_or_derived(self):
        """Spec §3.1 regla 3-4: valido / rul_days / rolling features NO se envían."""
        payload = _row_to_payload(_row(
            valido=True, rul_days=8.34, ciclo_id=0,
            SO2_PPB_mean_1h=2.5,
        ))
        assert "valido" not in payload
        assert "rul_days" not in payload
        assert "ciclo_id" not in payload
        assert not any(k.endswith("_mean_1h") for k in payload)

    def test_skips_nan_features(self):
        """Fila con NaN en una feature: la key no se envía → iot-service lo
        contará como valido=0 vía _in_oefa_scale (fallback seguro)."""
        row = _row(SO2_PPB=float("nan"))
        payload = _row_to_payload(row)
        assert "so2_ppb" not in payload
        assert "so2_flow" in payload  # las otras siguen ahí

    def test_csv_to_payload_map_is_exactly_four_features(self):
        assert set(CSV_TO_PAYLOAD.values()) == {
            "so2_ppb", "so2_flow", "so2_internal_temp", "so2_lamp_int",
        }
        assert "SO2_PMT_VOLTAGE" not in CSV_TO_PAYLOAD


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
