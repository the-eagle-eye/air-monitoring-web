from datetime import datetime, timezone

from app.models.prediccion import Prediccion
from app.models.alerta import Alerta
from app.services.alert_service import evaluate_and_create_alert, get_alerts


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


def test_evaluate_creates_alta_alert(db_session):
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


def test_get_alerts_filters(db_session):
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
