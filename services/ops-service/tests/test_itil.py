"""Tests ITIL v4 — priorización, ciclo de vida, SLA, problemas, dedup con resuelto.
docs/spec-itil-v4-incidencias.md (IT-01..IT-09).
"""
import pytest

from app.services import incidencia_service, priority_service
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate


# --- I5.1 · Matriz Impacto × Urgencia (IT-01) --------------------------------

@pytest.mark.parametrize("impacto,urgencia,esperado", [
    ("alta", "alta", "alta"),   ("alta", "media", "alta"),  ("alta", "baja", "media"),
    ("media", "alta", "alta"),  ("media", "media", "media"),("media", "baja", "baja"),
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
