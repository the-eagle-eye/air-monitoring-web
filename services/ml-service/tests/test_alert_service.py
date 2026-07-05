from datetime import datetime, timezone
from unittest.mock import patch

from app.models.prediccion import Prediccion
from app.models.alerta import Alerta
from app.services.alert_service import evaluate_and_create_alert, get_alerts, deactivate_alerts


def _create_prediccion(db, device_id="T101", rul=50, risk="media", prob=0.3):
    pred = Prediccion(
        device_id=device_id,
        model_version="1.0.0",
        prediction_timestamp=datetime.now(timezone.utc),
        failure_probability=prob,
        remaining_useful_life_days=rul,
        risk_level=risk,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


@patch("app.services.alert_service._notify_ops_alert")
def test_evaluate_creates_alta_alert(mock_notify, db_session):
    pred = _create_prediccion(db_session, rul=25, risk="alta", prob=0.85)
    alerta = evaluate_and_create_alert(db_session, pred)
    assert alerta.nivel_riesgo == "alta"
    assert alerta.device_id == "T101"
    assert alerta.prediccion_id == pred.id
    assert "ALERTA ALTA" in alerta.descripcion


def test_evaluate_creates_media_alert(db_session):
    pred = _create_prediccion(db_session, rul=50, risk="media", prob=0.4)
    alerta = evaluate_and_create_alert(db_session, pred)
    assert alerta.nivel_riesgo == "media"
    assert "ALERTA MEDIA" in alerta.descripcion


def test_evaluate_creates_baja_alert(db_session):
    pred = _create_prediccion(db_session, rul=80, risk="baja", prob=0.1)
    alerta = evaluate_and_create_alert(db_session, pred)
    assert alerta.nivel_riesgo == "baja"
    assert "ALERTA BAJA" in alerta.descripcion


@patch("app.services.alert_service._notify_ops_alert")
def test_get_alerts_filters(mock_notify, db_session):
    pred1 = _create_prediccion(db_session, device_id="T101", rul=25, risk="alta")
    evaluate_and_create_alert(db_session, pred1)
    pred2 = _create_prediccion(db_session, device_id="T102", rul=80, risk="baja")
    evaluate_and_create_alert(db_session, pred2)

    # Filter by device
    items, total = get_alerts(db_session, device_id="T101")
    assert total == 1
    assert items[0].device_id == "T101"

    # Filter by nivel_riesgo
    items, total = get_alerts(db_session, nivel_riesgo="alta")
    assert total == 1
    assert items[0].nivel_riesgo == "alta"

    # All alerts
    items, total = get_alerts(db_session)
    assert total == 2


# RETIRO RF: el flujo RF ya NO crea incidencias (lo hace el monitor de salud).
# evaluate_and_create_alert persiste la Alerta pero no notifica a ops.
# Ver docs/spec-racionalizacion-dashboard-e-incidencias.md (Decisión B1+C1).
@patch("app.services.alert_service._notify_ops_alert")
def test_rf_no_longer_notifies_ops(mock_notify, db_session):
    """Tras el retiro del RF, evaluate_and_create_alert NO dispara incidencias."""
    pred = _create_prediccion(db_session, rul=25, risk="alta", prob=0.85)
    evaluate_and_create_alert(db_session, pred)
    mock_notify.assert_not_called()


@patch("app.services.alert_service._notify_ops_alert")
def test_deactivate_alerts_by_device(mock_notify, db_session):
    """Deactivate should set all activa alerts for device to inactiva."""
    pred1 = _create_prediccion(db_session, device_id="T101", rul=25, risk="alta", prob=0.85)
    pred2 = _create_prediccion(db_session, device_id="T101", rul=20, risk="alta", prob=0.9)
    pred3 = _create_prediccion(db_session, device_id="T102", rul=25, risk="alta", prob=0.85)
    evaluate_and_create_alert(db_session, pred1)
    evaluate_and_create_alert(db_session, pred2)
    evaluate_and_create_alert(db_session, pred3)

    count = deactivate_alerts(db_session, "T101")
    assert count == 2

    # T101 alerts now inactiva
    items, total = get_alerts(db_session, device_id="T101", estado="activa")
    assert total == 0
    items, total = get_alerts(db_session, device_id="T101", estado="inactiva")
    assert total == 2

    # T102 unaffected
    items, total = get_alerts(db_session, device_id="T102", estado="activa")
    assert total == 1


@patch("app.services.alert_service._notify_ops_alert")
def test_deactivate_alerts_idempotent(mock_notify, db_session):
    """Second deactivate call returns 0."""
    pred = _create_prediccion(db_session, device_id="T101", rul=25, risk="alta", prob=0.85)
    evaluate_and_create_alert(db_session, pred)

    assert deactivate_alerts(db_session, "T101") == 1
    assert deactivate_alerts(db_session, "T101") == 0


def test_notify_ops_is_noop_after_rf_retirement():
    """_notify_ops_alert quedó como no-op tras el retiro del RF; no debe lanzar."""
    from app.services.alert_service import _notify_ops_alert
    _notify_ops_alert("T101", "alta")  # no-op, no debe lanzar
