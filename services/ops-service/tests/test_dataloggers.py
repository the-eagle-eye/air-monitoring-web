class TestDataloggers:
    def test_list_dataloggers(self, client):
        resp = client.get("/api/v1/dataloggers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["codigo_interno"] == "DL-TEST-001"

    def test_create_datalogger(self, client):
        resp = client.post("/api/v1/dataloggers", json={
            "nombre": "CR310 Nuevo",
            "codigo_interno": "DL-NEW-001",
            "numero_serie": "SN-NEW",
            "ubicacion": "Estacion Nueva",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "CR310 Nuevo"
        assert data["codigo_interno"] == "DL-NEW-001"
        assert data["estado"] == "activo"

    def test_create_datalogger_duplicate(self, client):
        resp = client.post("/api/v1/dataloggers", json={
            "nombre": "Duplicado",
            "codigo_interno": "DL-TEST-001",
        })
        assert resp.status_code == 409

    def test_get_datalogger(self, client):
        # Get seeded datalogger (id=1)
        resp = client.get("/api/v1/dataloggers/1")
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "CR310 Test"

    def test_get_datalogger_not_found(self, client):
        resp = client.get("/api/v1/dataloggers/999")
        assert resp.status_code == 404

    def test_update_datalogger(self, client):
        resp = client.put("/api/v1/dataloggers/1", json={
            "ubicacion": "Nueva ubicacion",
        })
        assert resp.status_code == 200
        assert resp.json()["ubicacion"] == "Nueva ubicacion"
        assert resp.json()["updated_at"] is not None
