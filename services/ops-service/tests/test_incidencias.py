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


class TestConsolidacionMonitorSalud:
    """Regla de consolidacion de alertas del monitor de salud (CA-01..CA-08).
    docs/regla-consolidacion-alertas.md"""

    def _monitor_alert(self, client, device_id, severidad):
        return client.post("/api/v1/incidencias/monitor-alert", json={
            "device_id": device_id, "severidad": severidad,
        })

    def _open_monitor_incidencias(self, client, device_id):
        resp = client.get(f"/api/v1/incidencias?device_id={device_id}")
        return [
            i for i in resp.json()["items"]
            if i["origen"] == "monitor_salud"
            and i["estado"] in ("pendiente", "en_ejecucion")
        ]

    # CA-01/02/03 — creacion por nivel
    def test_ca01_observado_crea_prioridad_baja(self, client):
        resp = self._monitor_alert(client, "CA-CH-04", "OBSERVADO")
        assert resp.status_code == 201
        data = resp.json()
        assert data["accion"] == "created"
        assert data["incidencia"]["prioridad"] == "baja"
        assert data["incidencia"]["tipo"] == "correctiva"
        assert data["incidencia"]["origen"] == "monitor_salud"

    def test_ca02_en_riesgo_crea_prioridad_media(self, client):
        resp = self._monitor_alert(client, "CA-CH-05", "EN_RIESGO")
        assert resp.status_code == 201
        assert resp.json()["incidencia"]["prioridad"] == "media"

    def test_ca03_critico_crea_prioridad_alta(self, client):
        resp = self._monitor_alert(client, "CA-ILO-01", "CRITICO")
        assert resp.status_code == 201
        assert resp.json()["incidencia"]["prioridad"] == "alta"

    # CA-04 — dedup: no crea segundo incidente si ya hay uno abierto
    def test_ca04_dedup_no_crea_segundo(self, client):
        self._monitor_alert(client, "CA-CH-04", "OBSERVADO")
        resp = self._monitor_alert(client, "CA-CH-04", "OBSERVADO")
        assert resp.status_code == 200
        assert resp.json()["accion"] == "noop"
        assert len(self._open_monitor_incidencias(client, "CA-CH-04")) == 1

    # CA-05 — escalada: sube prioridad, no crea otro; nunca baja
    def test_ca05_escalada_sube_prioridad(self, client):
        self._monitor_alert(client, "CA-CH-04", "OBSERVADO")  # baja
        resp = self._monitor_alert(client, "CA-CH-04", "CRITICO")  # -> alta
        assert resp.status_code == 200
        assert resp.json()["accion"] == "escalated"
        assert resp.json()["incidencia"]["prioridad"] == "alta"
        assert len(self._open_monitor_incidencias(client, "CA-CH-04")) == 1

    def test_ca05_no_baja_prioridad(self, client):
        self._monitor_alert(client, "CA-CH-04", "CRITICO")  # alta
        resp = self._monitor_alert(client, "CA-CH-04", "OBSERVADO")  # sigue alta
        assert resp.status_code == 200
        assert resp.json()["accion"] == "noop"
        abiertas = self._open_monitor_incidencias(client, "CA-CH-04")
        assert abiertas[0]["prioridad"] == "alta"

    # CA-06 — reapertura: tras cerrar, puede crear otro nuevo
    def test_ca06_reapertura_tras_cierre(self, client):
        r1 = self._monitor_alert(client, "CA-CH-04", "EN_RIESGO")
        inc_id = r1.json()["incidencia"]["id"]
        # cerrar
        client.put(f"/api/v1/incidencias/{inc_id}", json={"estado": "cancelado"})
        # nueva anomalia -> nuevo incidente
        r2 = self._monitor_alert(client, "CA-CH-04", "EN_RIESGO")
        assert r2.status_code == 201
        assert r2.json()["accion"] == "created"
        assert r2.json()["incidencia"]["id"] != inc_id

    # CA-07 — calibracion manual abierta no bloquea
    def test_ca07_calibracion_manual_no_bloquea(self, client):
        client.post("/api/v1/incidencias", json={
            "device_id": "CA-UCHU-01", "tipo": "calibracion",
            "origen": "manual",
        })
        resp = self._monitor_alert(client, "CA-UCHU-01", "EN_RIESGO")
        assert resp.status_code == 201
        assert resp.json()["accion"] == "created"

    def test_ca07_correctiva_manual_no_bloquea(self, client):
        # una correctiva manual (no del monitor) EN PENDIENTE tampoco bloquea al
        # monitor: sólo 'en_ejecucion' (intervención activa) silencia (C9).
        client.post("/api/v1/incidencias", json={
            "device_id": "CA-UCHU-02", "tipo": "correctiva", "origen": "manual",
        })
        resp = self._monitor_alert(client, "CA-UCHU-02", "OBSERVADO")
        assert resp.status_code == 201
        assert resp.json()["accion"] == "created"

    # CA-08 — verifica que la severidad invalida no crea nada
    def test_severidad_invalida_noop(self, client):
        resp = self._monitor_alert(client, "CA-CH-04", "SANO")
        assert resp.status_code == 200
        assert resp.json()["accion"] == "noop"
        assert len(self._open_monitor_incidencias(client, "CA-CH-04")) == 0


class TestC9VentanaMantenimiento:
    """C9: ventana de mantenimiento silencia el monitor mientras el equipo está
    bajo intervención activa (correctiva en_ejecucion).
    docs/regla-consolidacion-alertas.md §C9."""

    _DEV = "CA-MANT-01"
    _TECNICO_ID = 2  # seed conftest: tecnico@test.com

    def _monitor_alert(self, client, severidad, device_id=None):
        return client.post("/api/v1/incidencias/monitor-alert", json={
            "device_id": device_id or self._DEV, "severidad": severidad,
        })

    def _asignar(self, client, inc_id):
        """Coordinador asigna técnico -> pendiente pasa a en_ejecucion (ITIL)."""
        return client.put(f"/api/v1/incidencias/{inc_id}",
                          json={"responsable_id": self._TECNICO_ID})

    # C9-01: en_ejecucion (técnico asignado) -> anomalía silenciada por completo
    def test_c9_01_en_ejecucion_silencia(self, client):
        r1 = self._monitor_alert(client, "EN_RIESGO")
        inc_id = r1.json()["incidencia"]["id"]
        assert self._asignar(client, inc_id).json()["estado"] == "en_ejecucion"

        # nueva anomalía (peor severidad) -> NO escala, silenciada
        resp = self._monitor_alert(client, "CRITICO")
        assert resp.status_code == 200
        assert resp.json()["accion"] == "maintenance"

        # la incidencia conserva su prioridad (no escaló a alta)
        got = client.get(f"/api/v1/incidencias/{inc_id}").json()
        assert got["prioridad"] != "alta"
        assert got["estado"] == "en_ejecucion"

    # C9-02: pendiente (sin asignar) SÍ escala — la ventana aún no arrancó
    def test_c9_02_pendiente_aun_escala(self, client):
        dev = "CA-MANT-02"
        self._monitor_alert(client, "OBSERVADO", device_id=dev)  # baja, pendiente
        resp = self._monitor_alert(client, "CRITICO", device_id=dev)  # -> alta
        assert resp.status_code == 200
        assert resp.json()["accion"] == "escalated"
        assert resp.json()["incidencia"]["prioridad"] == "alta"

    # C9-03: al cerrar la incidencia, la ventana termina y el monitor vuelve a crear
    def test_c9_03_cierre_termina_ventana(self, client):
        dev = "CA-MANT-03"
        r1 = self._monitor_alert(client, "EN_RIESGO", device_id=dev)
        inc_id = r1.json()["incidencia"]["id"]
        self._asignar(client, inc_id)  # en_ejecucion (ventana activa)
        # cerrar por el ciclo válido: en_ejecucion -> cancelado
        client.put(f"/api/v1/incidencias/{inc_id}", json={"estado": "cancelado"})

        # ventana terminada -> nueva anomalía crea otra incidencia
        resp = self._monitor_alert(client, "EN_RIESGO", device_id=dev)
        assert resp.status_code == 201
        assert resp.json()["accion"] == "created"
        assert resp.json()["incidencia"]["id"] != inc_id

    # C9-04: una correctiva MANUAL en_ejecucion también silencia (intervención real)
    def test_c9_04_correctiva_manual_tambien_silencia(self, client):
        dev = "CA-MANT-04"
        created = client.post("/api/v1/incidencias", json={
            "device_id": dev, "tipo": "correctiva", "origen": "manual",
        })
        inc_id = created.json()["id"]
        self._asignar(client, inc_id)  # manual correctiva -> en_ejecucion

        resp = self._monitor_alert(client, "CRITICO", device_id=dev)
        assert resp.status_code == 200
        assert resp.json()["accion"] == "maintenance"


class TestVisibilidadPorTecnico:
    """Un técnico (header x-user-rol=tecnico) ve SOLO las correctivas asignadas a él.
    Cubre el gap que dejó pasar la confusión de 'no veo mis incidencias': las
    correctivas del monitor / manuales se asignan al coordinador o quedan sin asignar,
    y el técnico correctamente NO las ve hasta que se le asignan.
    Seed conftest: tecnico id=2, coordinador id=3."""

    _TEC = {"x-user-rol": "tecnico", "x-user-id": "2"}

    def _crear(self, client, device_id, responsable_id=None):
        inc = client.post("/api/v1/incidencias", json={
            "device_id": device_id, "tipo": "correctiva",
        }).json()
        if responsable_id is not None:
            client.put(f"/api/v1/incidencias/{inc['id']}",
                       json={"responsable_id": responsable_id})
        return inc["id"]

    def test_tecnico_ve_solo_las_suyas(self, client):
        mia = self._crear(client, "T101", responsable_id=2)     # asignada al técnico
        self._crear(client, "T102", responsable_id=3)           # del coordinador
        self._crear(client, "T103", responsable_id=None)        # sin asignar

        resp = client.get("/api/v1/incidencias", headers=self._TEC)
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ids == [mia]                                     # solo la suya

    def test_tecnico_no_ve_las_del_coordinador(self, client):
        self._crear(client, "T102", responsable_id=3)           # del coordinador
        resp = client.get("/api/v1/incidencias", headers=self._TEC)
        assert resp.json()["total"] == 0

    def test_tecnico_no_ve_las_sin_asignar(self, client):
        self._crear(client, "T103", responsable_id=None)        # sin asignar
        resp = client.get("/api/v1/incidencias", headers=self._TEC)
        assert resp.json()["total"] == 0

    def test_coordinador_ve_todas(self, client):
        self._crear(client, "T101", responsable_id=2)
        self._crear(client, "T102", responsable_id=3)
        self._crear(client, "T103", responsable_id=None)
        # sin headers de técnico (coordinador/admin) -> ve todas
        resp = client.get("/api/v1/incidencias")
        assert resp.json()["total"] == 3

    def test_tras_reasignar_al_tecnico_ya_la_ve(self, client):
        # regresión del bug real: una correctiva del coordinador NO la ve el técnico
        # hasta que se le RE-ASIGNA (responsable_id=2); entonces sí aparece.
        inc_id = self._crear(client, "T102", responsable_id=3)  # coordinador
        antes = client.get("/api/v1/incidencias", headers=self._TEC)
        assert antes.json()["total"] == 0

        client.put(f"/api/v1/incidencias/{inc_id}", json={"responsable_id": 2})
        despues = client.get("/api/v1/incidencias", headers=self._TEC)
        assert [i["id"] for i in despues.json()["items"]] == [inc_id]
