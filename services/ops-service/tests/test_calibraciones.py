class TestCalibraciones:
    def test_create_calibracion_without_incidencia(self, client):
        resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
            "nota": "Calibracion anual programada",
            "proveedor_id": 1,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["device_id"] == "T101"
        assert data["incidencia_id"] is None
        assert data["estado"] == "pendiente"

    def test_create_calibracion_with_incidencia(self, client):
        # Create calibracion-type incidencia first
        inc_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "calibracion",
        })
        inc_id = inc_resp.json()["id"]

        resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
            "incidencia_id": inc_id,
            "nota": "Calibracion post-mantenimiento",
        })
        assert resp.status_code == 201
        assert resp.json()["incidencia_id"] == inc_id

    def test_list_calibraciones(self, client):
        client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
        })
        client.post("/api/v1/calibraciones", json={
            "device_id": "T102",
        })

        resp = client.get("/api/v1/calibraciones")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_calibraciones_filter_device(self, client):
        client.post("/api/v1/calibraciones", json={"device_id": "T101"})
        client.post("/api/v1/calibraciones", json={"device_id": "T102"})

        resp = client.get("/api/v1/calibraciones?device_id=T101")
        assert resp.json()["total"] == 1

    def test_get_calibracion(self, client):
        create_resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
        })
        cal_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/calibraciones/{cal_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == cal_id

    def test_get_calibracion_not_found(self, client):
        resp = client.get("/api/v1/calibraciones/999")
        assert resp.status_code == 404

    def test_update_calibracion(self, client):
        create_resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
        })
        cal_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/calibraciones/{cal_id}", json={
            "certificado_url": "https://s3.example.com/cert.pdf",
            "nota": "Calibracion completada",
        })
        assert resp.status_code == 200
        assert resp.json()["certificado_url"] == "https://s3.example.com/cert.pdf"
        assert resp.json()["estado"] == "pendiente"  # Not all 4 fields yet

    def test_update_calibracion_completada(self, client):
        create_resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T101",
        })
        cal_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/calibraciones/{cal_id}", json={
            "fecha_calibracion": "2026-03-17T00:00:00Z",
            "nota": "Calibracion completada",
            "certificado_url": "https://s3.example.com/cert.pdf",
            "proveedor_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["estado"] == "completada"
        assert resp.json()["incidencia_id"] is None
