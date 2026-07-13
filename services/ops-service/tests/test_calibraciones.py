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

    def test_update_calibracion_not_found(self, client):
        """PUT sobre un id inexistente -> 404 (línea 103 del router)."""
        resp = client.put("/api/v1/calibraciones/9999", json={
            "nota": "no existe",
        })
        assert resp.status_code == 404

    def test_get_calibracion_incluye_incidencia_estado(self, client):
        """Cubre línea 36: cuando la calibración tiene incidencia asociada,
        se propaga `incidencia_estado` a la respuesta."""
        inc_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T500", "tipo": "calibracion",
        })
        inc_id = inc_resp.json()["id"]

        cal_resp = client.post("/api/v1/calibraciones", json={
            "device_id": "T500",
            "incidencia_id": inc_id,
        })
        cal_id = cal_resp.json()["id"]

        resp = client.get(f"/api/v1/calibraciones/{cal_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["incidencia_id"] == inc_id
        # el campo lo agrega el helper _calibracion_with_estado
        assert body["incidencia_estado"] == "pendiente"

    def test_list_calibraciones_tecnico_filtra_por_responsable(self, client):
        """Cubre líneas 51-55: si el header x-user-rol=tecnico se envía con
        x-user-id numérico, sólo devuelve calibraciones cuya incidencia esté
        asignada a ese técnico."""
        # crear dos calibraciones sueltas (sin incidencia) -> técnico no las ve
        client.post("/api/v1/calibraciones", json={"device_id": "T101"})
        client.post("/api/v1/calibraciones", json={"device_id": "T102"})

        resp = client.get(
            "/api/v1/calibraciones",
            headers={"x-user-rol": "tecnico", "x-user-id": "2"},
        )
        assert resp.status_code == 200
        # ninguna incidencia asignada al técnico id=2 -> 0 items
        assert resp.json()["total"] == 0

    def test_list_calibraciones_tecnico_x_user_id_no_numerico_ignora(self, client):
        """Cubre la rama except ValueError: si x-user-id no es int, el filtro
        NO se aplica y devuelve las calibraciones normalmente."""
        client.post("/api/v1/calibraciones", json={"device_id": "T101"})
        client.post("/api/v1/calibraciones", json={"device_id": "T102"})

        resp = client.get(
            "/api/v1/calibraciones",
            headers={"x-user-rol": "tecnico", "x-user-id": "no-es-int"},
        )
        assert resp.status_code == 200
        # sin filtro -> ambas
        assert resp.json()["total"] == 2

    def test_check_annual_endpoint(self, client, monkeypatch):
        """Cubre líneas 20-30 del router: POST /calibraciones/check-annual."""
        from app.api.v1 import calibraciones as calibraciones_router

        monkeypatch.setattr(
            calibraciones_router.incidencia_service,
            "check_annual_calibrations",
            lambda db, url: [],
        )
        resp = client.post("/api/v1/calibraciones/check-annual")
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] == 0
        assert body["incidencias"] == []
