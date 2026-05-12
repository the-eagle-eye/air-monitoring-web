class TestIncidencias:
    def test_create_incidencia_correctiva(self, client):
        resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101",
            "tipo": "correctiva",
            "descripcion": "Falla detectada en sensor SO2",
            "prioridad": "alta",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["device_id"] == "T101"
        assert data["tipo"] == "correctiva"
        assert data["estado"] == "pendiente"
        assert data["prioridad"] == "alta"

    def test_create_incidencia_calibracion(self, client):
        resp = client.post("/api/v1/incidencias", json={
            "device_id": "T102",
            "tipo": "calibracion",
            "descripcion": "Calibracion anual",
        })
        assert resp.status_code == 201
        assert resp.json()["tipo"] == "calibracion"

    def test_list_incidencias(self, client):
        # Create 2 incidencias
        client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        client.post("/api/v1/incidencias", json={
            "device_id": "T102", "tipo": "calibracion",
        })

        resp = client.get("/api/v1/incidencias")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_incidencias_filter_tipo(self, client):
        client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        client.post("/api/v1/incidencias", json={
            "device_id": "T102", "tipo": "calibracion",
        })

        resp = client.get("/api/v1/incidencias?tipo=correctiva")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["tipo"] == "correctiva"

    def test_get_incidencia(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        inc_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/incidencias/{inc_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == inc_id

    def test_get_incidencia_not_found(self, client):
        resp = client.get("/api/v1/incidencias/999")
        assert resp.status_code == 404

    def test_update_incidencia_estado(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        inc_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/incidencias/{inc_id}", json={
            "estado": "en_ejecucion",
        })
        assert resp.status_code == 200
        assert resp.json()["estado"] == "en_ejecucion"
        assert resp.json()["updated_at"] is not None

    def test_update_incidencia_assign_responsable(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        inc_id = create_resp.json()["id"]

        resp = client.put(f"/api/v1/incidencias/{inc_id}", json={
            "responsable_id": 2,  # tecnico seeded
        })
        assert resp.status_code == 200
        assert resp.json()["responsable_id"] == 2

    def test_submit_mantenimiento(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        inc_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/incidencias/{inc_id}/mantenimiento", json={
            "diagnostico": "Sensor SO2 degradado",
            "acciones_realizadas": "Reemplazo de sensor",
            "conclusion": "Equipo operativo",
            "repuesto_ids": [1],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["diagnostico"] == "Sensor SO2 degradado"
        assert data["incidencia_id"] == inc_id

    def test_submit_mantenimiento_on_calibracion_fails(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "calibracion",
        })
        inc_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/incidencias/{inc_id}/mantenimiento", json={
            "diagnostico": "Test",
        })
        assert resp.status_code == 400

    def test_alert_trigger_alta(self, client):
        resp = client.post("/api/v1/incidencias/alert-trigger", json={
            "device_id": "T101",
        })
        assert resp.status_code in (200, 201)

    def test_alert_trigger_media(self, client):
        resp = client.post("/api/v1/incidencias/alert-trigger", json={
            "device_id": "T103",
            "nivel_riesgo": "media",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["prioridad"] == "media"
        assert data["tipo"] == "correctiva"

    def test_submit_mantenimiento_duplicate(self, client):
        create_resp = client.post("/api/v1/incidencias", json={
            "device_id": "T101", "tipo": "correctiva",
        })
        inc_id = create_resp.json()["id"]

        client.post(f"/api/v1/incidencias/{inc_id}/mantenimiento", json={
            "diagnostico": "Primera vez",
        })
        resp = client.post(f"/api/v1/incidencias/{inc_id}/mantenimiento", json={
            "diagnostico": "Duplicado",
        })
        assert resp.status_code == 409
