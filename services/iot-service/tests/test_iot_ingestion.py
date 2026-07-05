from tests.conftest import VALID_READING_PAYLOAD


class TestPostReading:
    def test_post_valid_reading(self, client):
        response = client.post("/api/v1/iot/readings", json=VALID_READING_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["equipo_device_id"] == "T101"
        assert data["sensors"]["SO2_ppb"] == 25.43
        assert data["sensors"]["H2S_ppb"] == 2.18
        assert data["sensors"]["H2S_flow"] == 0.91
        assert data["sensors"]["H2S_lamp_int"] == 76.5
        assert data["procesado"] is False

    def test_post_reading_unknown_equipo(self, client):
        payload = {**VALID_READING_PAYLOAD, "equipo": "UNKNOWN"}
        response = client.post("/api/v1/iot/readings", json=payload)
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_post_reading_accepts_any_extra_sensor(self, client):
        # Any new sensor key must be accepted without 422
        payload = {**VALID_READING_PAYLOAD, "CO2_ppm": 412.5, "cabinet_temp": 29.0}
        response = client.post("/api/v1/iot/readings", json=payload)
        assert response.status_code == 200
        sensors = response.json()["sensors"]
        assert sensors["CO2_ppm"] == 412.5
        assert sensors["cabinet_temp"] == 29.0

    def test_post_reading_persisted(self, client):
        client.post("/api/v1/iot/readings", json=VALID_READING_PAYLOAD)
        response = client.get("/api/v1/iot/readings/T101")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["sensors"]["SO2_ppb"] == 25.43


class TestGetReadings:
    def test_get_readings_paginated(self, client):
        for i in range(3):
            payload = {
                **VALID_READING_PAYLOAD,
                "timestamp": f"2025-10-27 18:3{i}:00",
            }
            client.post("/api/v1/iot/readings", json=payload)

        response = client.get("/api/v1/iot/readings/T101?page=1&page_size=2")
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_get_readings_unknown_equipo(self, client):
        response = client.get("/api/v1/iot/readings/UNKNOWN")
        assert response.status_code == 404

    def test_get_latest_reading(self, client):
        for ts in ["2025-10-27 18:00:00", "2025-10-27 19:00:00"]:
            payload = {**VALID_READING_PAYLOAD, "timestamp": ts}
            client.post("/api/v1/iot/readings", json=payload)

        response = client.get("/api/v1/iot/readings/T101/latest")
        assert response.status_code == 200
        data = response.json()
        assert "2025-10-28T00:00:00" in data["timestamp_lectura"]
        assert "raw_payload" in data

    def test_get_latest_no_readings(self, client):
        response = client.get("/api/v1/iot/readings/T102/latest")
        assert response.status_code == 404


class TestEquipos:
    def test_list_equipos(self, client):
        response = client.get("/api/v1/iot/equipos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        device_ids = [e["device_id"] for e in data]
        assert "T101" in device_ids

    def test_get_equipo(self, client):
        response = client.get("/api/v1/iot/equipos/T101")
        assert response.status_code == 200
        assert response.json()["device_id"] == "T101"

    def test_get_equipo_not_found(self, client):
        response = client.get("/api/v1/iot/equipos/UNKNOWN")
        assert response.status_code == 404

    def test_create_equipo(self, client):
        response = client.post("/api/v1/iot/equipos", json={
            "device_id": "T200",
            "nombre": "Analizador Nuevo",
            "tipo": "Thermo 450i",
            "ubicacion": "Estacion Nueva",
            "serie": "SN-T200-00001",
            "marca": "Teledyne API",
            "modelo": "T200",
            "parametro_medicion": "O3",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == "T200"
        assert data["serie"] == "SN-T200-00001"
        assert data["marca"] == "Teledyne API"

    def test_create_equipo_duplicate(self, client):
        response = client.post("/api/v1/iot/equipos", json={
            "device_id": "T101",
            "nombre": "Duplicado",
        })
        assert response.status_code == 409

    def test_update_equipo(self, client):
        response = client.put("/api/v1/iot/equipos/T101", json={
            "nombre": "Analizador Actualizado",
            "marca": "Teledyne API",
            "rango_medicion": "0 - 500 ppb",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Analizador Actualizado"
        assert data["marca"] == "Teledyne API"
        assert data["fecha_actualizacion"] is not None

    def test_update_equipo_not_found(self, client):
        response = client.put("/api/v1/iot/equipos/UNKNOWN", json={
            "nombre": "No existe",
        })
        assert response.status_code == 404

    def test_delete_equipo(self, client):
        response = client.delete("/api/v1/iot/equipos/T103")
        assert response.status_code == 200
        assert response.json()["detail"] == "Equipo eliminado"

        # Verify soft-deleted
        get_resp = client.get("/api/v1/iot/equipos/T103")
        assert get_resp.json()["estado"] == "inactivo"

    def test_delete_equipo_not_found(self, client):
        response = client.delete("/api/v1/iot/equipos/UNKNOWN")
        assert response.status_code == 404
