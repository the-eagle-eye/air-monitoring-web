"""Tests ITIL v4 — priorización, ciclo de vida, SLA, problemas, dedup con resuelto.
docs/spec-itil-v4-incidencias.md (IT-01..IT-09).
"""
import pytest

from app.services import incidencia_service, priority_service
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate


# --- I5.1 · Matriz Impacto × Urgencia (IT-01) --------------------------------

@pytest.mark.parametrize("impacto,urgencia,esperado", [
    ("alta", "alta", "alta"),   ("alta", "media", "alta"),  ("alta", "baja", "media"),
    ("media", "alta", "alta"),  ("media", "media", "media"), ("media", "baja", "baja"),
    ("baja", "alta", "media"),  ("baja", "media", "baja"),  ("baja", "baja", "baja"),
])
def test_priority_matrix(impacto, urgencia, esperado):
    assert priority_service.derive_priority(impacto, urgencia) == esperado


def test_priority_matrix_unknown_defaults_media():
    assert priority_service.derive_priority("xxx", "yyy") == "media"


def test_urgency_from_severity():
    assert priority_service.urgency_from_severity("CRITICO") == "alta"
    assert priority_service.urgency_from_severity("EN_RIESGO") == "media"
    assert priority_service.urgency_from_severity("OBSERVADO") == "baja"
    assert priority_service.urgency_from_severity("SANO") == "media"  # default


# --- I5.1b · prioridad derivada al crear -------------------------------------

def test_create_derives_priority_from_impacto_urgencia(db_session):
    inc = incidencia_service.create_incidencia(
        db_session,
        IncidenciaCreate(device_id="T101", tipo="correctiva",
                         impacto="baja", urgencia="baja"),
    )
    assert inc.prioridad == "baja"   # baja×baja
    assert inc.impacto == "baja"


def test_create_explicit_priority_respected(db_session):
    inc = incidencia_service.create_incidencia(
        db_session,
        IncidenciaCreate(device_id="T101", tipo="correctiva", prioridad="alta"),
    )
    assert inc.prioridad == "alta"


# --- I5.2 · Transiciones de ciclo de vida (IT-02) ----------------------------

def _create(db):
    return incidencia_service.create_incidencia(
        db, IncidenciaCreate(device_id="T101", tipo="correctiva", prioridad="media"))


def test_valid_transition_chain(db_session):
    inc = _create(db_session)
    for estado in ("en_ejecucion", "resuelto", "finalizado"):
        r = incidencia_service.update_incidencia(
            db_session, inc.id, IncidenciaUpdate(estado=estado))
        assert r.estado == estado


def test_invalid_transition_pendiente_to_finalizado(db_session):
    inc = _create(db_session)
    with pytest.raises(incidencia_service.InvalidTransition):
        incidencia_service.update_incidencia(
            db_session, inc.id, IncidenciaUpdate(estado="finalizado"))


def test_invalid_transition_from_terminal(db_session):
    inc = _create(db_session)
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="cancelado"))
    with pytest.raises(incidencia_service.InvalidTransition):
        incidencia_service.update_incidencia(
            db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))


def test_cancel_from_pendiente_valid(db_session):
    inc = _create(db_session)
    r = incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="cancelado"))
    assert r.estado == "cancelado"


# --- I5.3 · Timestamps SLA (IT-04) -------------------------------------------

def test_sla_timestamps_sealed(db_session):
    inc = _create(db_session)
    assert inc.fecha_asignacion is None
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))
    db_session.refresh(inc)
    assert inc.fecha_asignacion is not None
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="resuelto"))
    db_session.refresh(inc)
    assert inc.fecha_resolucion is not None
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="finalizado"))
    db_session.refresh(inc)
    assert inc.fecha_cierre is not None


# --- I5.4 · resuelto cuenta como abierto en dedup (IT-06) --------------------

def test_resuelto_counts_as_open_for_dedup(db_session):
    # crea incidencia del monitor, llévala a resuelto, y verifica que el dedup
    # NO crea otra (sigue "abierta")
    inc, accion = incidencia_service.create_or_escalate_monitor_incidencia(
        db_session, "T101", "EN_RIESGO")
    assert accion == "created"
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="resuelto"))
    # en resuelto: el dedup debe seguir viéndola como abierta
    inc2, accion2 = incidencia_service.create_or_escalate_monitor_incidencia(
        db_session, "T101", "EN_RIESGO")
    assert accion2 in ("noop", "escalated")
    assert inc2.id == inc.id  # la misma, no una nueva


# --- I5.6 · Re-derivación de prioridad al cambiar impacto/urgencia -----------

def test_update_impacto_rederives_priority(db_session):
    inc = incidencia_service.create_incidencia(
        db_session, IncidenciaCreate(device_id="T101", tipo="correctiva",
                                     impacto="baja", urgencia="baja"))
    assert inc.prioridad == "baja"
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(impacto="alta", urgencia="alta"))
    db_session.refresh(inc)
    assert inc.prioridad == "alta"  # re-derivada


# --- I5.6 · Gestión de Problemas (IT-03) — vía API ---------------------------

def test_problema_crud(client):
    r = client.post("/api/v1/problemas", json={
        "titulo": "Lámpara UV falla recurrente", "device_id": "T101",
        "descripcion": "3 fallas en 2 semanas"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["estado"] == "abierto"

    r = client.get(f"/api/v1/problemas/{pid}")
    assert r.status_code == 200

    r = client.put(f"/api/v1/problemas/{pid}", json={
        "estado": "investigacion", "causa_raiz": "lámpara defectuosa lote X"})
    assert r.json()["estado"] == "investigacion"
    assert r.json()["causa_raiz"] == "lámpara defectuosa lote X"


def test_link_incidencia_to_problema(client):
    # crear problema + incidencia, vincular, y listar incidentes del problema
    prob = client.post("/api/v1/problemas", json={"titulo": "P1"}).json()
    inc = client.post("/api/v1/incidencias", json={
        "device_id": "T101", "tipo": "correctiva"}).json()

    r = client.post(f"/api/v1/incidencias/{inc['id']}/problema",
                    json={"problema_id": prob["id"]})
    assert r.status_code == 200
    assert r.json()["problema_id"] == prob["id"]

    r = client.get(f"/api/v1/problemas/{prob['id']}/incidencias")
    assert r.status_code == 200
    assert any(i["id"] == inc["id"] for i in r.json())


def test_link_unknown_problema_fails(client):
    inc = client.post("/api/v1/incidencias", json={
        "device_id": "T101", "tipo": "correctiva"}).json()
    r = client.post(f"/api/v1/incidencias/{inc['id']}/problema",
                    json={"problema_id": 99999})
    assert r.status_code == 404


def test_update_incidencia_invalid_transition_returns_400(client):
    inc = client.post("/api/v1/incidencias", json={
        "device_id": "T101", "tipo": "correctiva"}).json()
    # pendiente -> finalizado es inválido
    r = client.put(f"/api/v1/incidencias/{inc['id']}", json={
        "estado": "finalizado"})
    assert r.status_code == 400


# --- Flujo por rol: transiciones automáticas por acción ----------------------

def test_asignar_responsable_auto_en_ejecucion(db_session):
    """Coordinador asigna responsable a incidencia pendiente -> auto en_ejecucion."""
    from app.models.usuario import Usuario
    tec = db_session.query(Usuario).filter(Usuario.rol == "tecnico").first()
    inc = _create(db_session)
    assert inc.estado == "pendiente"
    updated = incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(responsable_id=tec.id))
    assert updated.estado == "en_ejecucion"       # auto-avanzó
    assert updated.responsable_id == tec.id
    assert updated.fecha_asignacion is not None


def test_asignar_no_reabre_si_ya_avanzada(db_session):
    """Asignar sobre una incidencia ya en_ejecucion no la retrocede."""
    from app.models.usuario import Usuario
    tec = db_session.query(Usuario).filter(Usuario.rol == "tecnico").first()
    inc = _create(db_session)
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))
    updated = incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(responsable_id=tec.id))
    assert updated.estado == "en_ejecucion"  # no cambia


def test_submit_mantenimiento_auto_resuelto(db_session):
    """Técnico registra mantenimiento -> incidencia auto a 'resuelto'."""
    from app.services import mantenimiento_service
    from app.schemas.mantenimiento import MantenimientoCreate
    inc = _create(db_session)
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))
    mantenimiento_service.submit_mantenimiento(
        db_session, inc.id,
        MantenimientoCreate(diagnostico="d", acciones_realizadas="a",
                            conclusion="c"))
    db_session.refresh(inc)
    assert inc.estado == "resuelto"
    assert inc.fecha_resolucion is not None


def test_cerrar_desde_resuelto_genera_calibracion(db_session):
    """Coordinador cierra (resuelto -> finalizado) y se auto-crea calibración."""
    from app.services import mantenimiento_service
    from app.schemas.mantenimiento import MantenimientoCreate
    from app.models.incidencia import Incidencia
    inc = _create(db_session)
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="en_ejecucion"))
    mantenimiento_service.submit_mantenimiento(
        db_session, inc.id,
        MantenimientoCreate(diagnostico="d", acciones_realizadas="a", conclusion="c"))
    # ahora resuelto -> finalizar
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="finalizado"))
    # se creó una incidencia de calibración para el mismo equipo
    cal = (db_session.query(Incidencia)
           .filter(Incidencia.device_id == inc.device_id,
                   Incidencia.tipo == "calibracion").first())
    assert cal is not None


# --- Calibraciones del técnico (completar las suyas) -------------------------

def test_calibracion_hereda_responsable_de_correctiva(db_session):
    """Al finalizar una correctiva asignada a un técnico, la calibración
    auto-creada hereda ese responsable (no el coordinador)."""
    from app.models.usuario import Usuario
    from app.models.incidencia import Incidencia
    from app.services import mantenimiento_service
    from app.schemas.mantenimiento import MantenimientoCreate
    tec = db_session.query(Usuario).filter(Usuario.rol == "tecnico").first()

    inc = incidencia_service.create_incidencia(
        db_session, IncidenciaCreate(device_id="T101", tipo="correctiva"))
    # asignar al técnico -> en_ejecucion
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(responsable_id=tec.id))
    # técnico completa mantenimiento -> resuelto
    mantenimiento_service.submit_mantenimiento(
        db_session, inc.id,
        MantenimientoCreate(diagnostico="d", acciones_realizadas="a", conclusion="c"))
    # coordinador finaliza -> auto-crea calibración
    incidencia_service.update_incidencia(
        db_session, inc.id, IncidenciaUpdate(estado="finalizado"))

    cal_inc = (db_session.query(Incidencia)
               .filter(Incidencia.device_id == "T101",
                       Incidencia.tipo == "calibracion").first())
    assert cal_inc is not None
    assert cal_inc.responsable_id == tec.id  # heredó el técnico


def test_list_calibraciones_filtra_por_tecnico(db_session):
    """list_calibraciones con responsable_id solo devuelve las del técnico."""
    from app.models.usuario import Usuario
    from app.models.calibracion import Calibracion
    from app.services import calibracion_service
    tec = db_session.query(Usuario).filter(Usuario.rol == "tecnico").first()
    coord = db_session.query(Usuario).filter(Usuario.rol == "coordinador").first()

    # incidencia de calibración del técnico
    inc_tec = incidencia_service.create_incidencia(
        db_session, IncidenciaCreate(device_id="T101", tipo="calibracion",
                                     responsable_id=tec.id))
    db_session.add(Calibracion(incidencia_id=inc_tec.id, device_id="T101"))
    # incidencia de calibración de otro (coordinador)
    inc_otro = incidencia_service.create_incidencia(
        db_session, IncidenciaCreate(device_id="T102", tipo="calibracion",
                                     responsable_id=coord.id))
    db_session.add(Calibracion(incidencia_id=inc_otro.id, device_id="T102"))
    db_session.commit()

    items, total = calibracion_service.list_calibraciones(
        db_session, responsable_id=tec.id)
    assert total == 1
    assert items[0].device_id == "T101"

    # sin filtro: ve todas
    items_all, total_all = calibracion_service.list_calibraciones(db_session)
    assert total_all == 2


# --- Detección de recurrencia (sugerencia de Problema) -----------------------

class TestReincidentes:
    """ITIL: equipos con correctivas recurrentes → sugiere abrir un Problema.
    GET /api/v1/problemas/reincidentes (default >=3 correctivas en 90 días)."""

    def _crear_correctivas(self, client, device_id, n):
        for _ in range(n):
            client.post("/api/v1/incidencias", json={
                "device_id": device_id, "tipo": "correctiva"})

    def test_equipo_con_3_correctivas_es_reincidente(self, client):
        self._crear_correctivas(client, "T101", 3)
        self._crear_correctivas(client, "T102", 1)  # no llega al umbral

        r = client.get("/api/v1/problemas/reincidentes")
        assert r.status_code == 200
        items = r.json()["items"]
        ids = {i["device_id"] for i in items}
        assert "T101" in ids
        assert "T102" not in ids
        t101 = next(i for i in items if i["device_id"] == "T101")
        assert t101["correctivas"] == 3
        assert len(t101["incidencia_ids"]) == 3  # para vincular al crear el problema

    def test_umbral_configurable(self, client):
        self._crear_correctivas(client, "T101", 2)
        # con umbral 2, T101 (2 correctivas) sí es reincidente
        r = client.get("/api/v1/problemas/reincidentes?min_correctivas=2")
        assert "T101" in {i["device_id"] for i in r.json()["items"]}
        # con el default (3), no
        r = client.get("/api/v1/problemas/reincidentes")
        assert "T101" not in {i["device_id"] for i in r.json()["items"]}

    def test_excluye_equipo_con_problema_abierto(self, client):
        # T101 reincidente PERO ya tiene un problema abierto -> no se sugiere
        self._crear_correctivas(client, "T101", 3)
        # estado=abierto
        client.post("/api/v1/problemas", json={
            "titulo": "Falla recurrente lámpara", "device_id": "T101"})

        r = client.get("/api/v1/problemas/reincidentes")
        assert "T101" not in {i["device_id"] for i in r.json()["items"]}

    def test_problema_cerrado_no_excluye(self, client):
        # si el problema previo está CERRADO, una nueva racha sí se vuelve a sugerir
        self._crear_correctivas(client, "T101", 3)
        prob = client.post("/api/v1/problemas", json={
            "titulo": "Falla previa", "device_id": "T101"}).json()
        client.put(f"/api/v1/problemas/{prob['id']}", json={"estado": "cerrado"})

        r = client.get("/api/v1/problemas/reincidentes")
        assert "T101" in {i["device_id"] for i in r.json()["items"]}

    def test_resumen_cuenta_por_estado(self, client):
        client.post("/api/v1/problemas", json={"titulo": "A"})  # abierto
        p2 = client.post("/api/v1/problemas", json={"titulo": "B"}).json()
        client.put(f"/api/v1/problemas/{p2['id']}", json={"estado": "cerrado"})

        r = client.get("/api/v1/problemas/resumen")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["abiertos"] == 1  # solo A (abierto); B está cerrado
        assert data["por_estado"]["abierto"] == 1
        assert data["por_estado"]["cerrado"] == 1


# --- Router problemas: listado + 404s ----------------------------------------

class TestProblemasRouter:
    """Cobertura de list_problemas y ramas 404 del router de problemas."""

    def test_list_problemas_devuelve_todos(self, client):
        client.post("/api/v1/problemas", json={"titulo": "A", "device_id": "T101"})
        client.post("/api/v1/problemas", json={"titulo": "B", "device_id": "T102"})

        r = client.get("/api/v1/problemas")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        titulos = {p["titulo"] for p in body["items"]}
        assert titulos == {"A", "B"}

    def test_list_problemas_filtra_por_estado_y_device(self, client):
        client.post("/api/v1/problemas", json={"titulo": "A", "device_id": "T101"})
        p2 = client.post(
            "/api/v1/problemas", json={"titulo": "B", "device_id": "T102"},
        ).json()
        client.put(f"/api/v1/problemas/{p2['id']}", json={"estado": "cerrado"})

        r = client.get("/api/v1/problemas?estado=abierto")
        assert r.status_code == 200
        assert {p["titulo"] for p in r.json()["items"]} == {"A"}

        r = client.get("/api/v1/problemas?device_id=T102")
        assert r.status_code == 200
        assert {p["titulo"] for p in r.json()["items"]} == {"B"}

    def test_get_problema_inexistente_devuelve_404(self, client):
        r = client.get("/api/v1/problemas/99999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Problema no encontrado"

    def test_get_incidencias_de_problema_inexistente_devuelve_404(self, client):
        r = client.get("/api/v1/problemas/99999/incidencias")
        assert r.status_code == 404
        assert r.json()["detail"] == "Problema no encontrado"

    def test_update_problema_inexistente_devuelve_404(self, client):
        r = client.put(
            "/api/v1/problemas/99999",
            json={"estado": "cerrado"},
        )
        assert r.status_code == 404
        assert r.json()["detail"] == "Problema no encontrado"
