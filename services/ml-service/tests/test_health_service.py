"""Tests del monitor de salud no supervisado (ensemble AE+IF+AND).

Cubre la lógica del SPEC:
  §3.0 gate de transmisión (valido=0 / feature faltante -> SIN_DATOS)
  §3.4 compuerta AND · §3.5 graduación de severidad
  §4.4 hours_since_prev online sobre timestamps
  §5.1 estabilización anti-parpadeo
  §6.3 persistencia (health_readings + health_device_state)
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.models.health_state import HealthDeviceState, HealthReading
from app.schemas.health import HealthEvaluateRequest
from app.services import health_service as hs


# --------------------------------------------------------------------------
# Doble de prueba del ensemble: AE que devuelve un error controlado, IF que
# devuelve anomalía controlada. Evita depender de los .pkl reales.
# --------------------------------------------------------------------------
class _FakeAE:
    def __init__(self, sq_error):
        self._sq = sq_error  # error cuadrático medio a devolver

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        # x̂ tal que mean((x - x̂)^2) == self._sq
        return X - np.sqrt(self._sq)


class _FakeIF:
    def __init__(self, anomaly):
        self._a = anomaly

    def predict(self, X):
        return np.array([-1 if self._a else 1] * len(X))


class _FakeScaler:
    def transform(self, X):
        return np.asarray(X, dtype=float)


@pytest.fixture
def bundle_factory():
    """Inyecta un bundle controlado en el registry para un device dado."""
    def _make(device_id, recon_error, if_anomaly, theta=0.02):
        hs.registry._cache[device_id] = {
            "scaler": _FakeScaler(),
            "ae": _FakeAE(recon_error),
            "iforest": _FakeIF(if_anomaly),
            "theta": theta,
        }
        return theta
    yield _make
    hs.registry._cache.clear()


def _req(device_id, valido=1, ts=None, ppb=4.0, flow=0.4, temp=31.0, lamp=92.0):
    return HealthEvaluateRequest(
        device_id=device_id,
        timestamp=ts or datetime(2025, 7, 1, tzinfo=timezone.utc),
        so2_ppb=ppb, so2_flow=flow, so2_internal_temp=temp, so2_lamp_int=lamp,
        valido=valido,
    )


# --------------------------------------------------------------------------
# §3.0 Gate de transmisión
# --------------------------------------------------------------------------
def test_gate_sin_transmision_devuelve_sin_datos(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=99.0, if_anomaly=True)
    out = hs.evaluate(db_session, _req("DEV1", valido=0,
                                       ppb=None, flow=None, temp=None, lamp=None))
    assert out["health_state"] == "SIN_DATOS"
    assert out["and_alert"] is False
    assert out["recon_error"] is None
    assert out["if_anomaly"] is None


def test_gate_feature_faltante_devuelve_sin_datos(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=99.0, if_anomaly=True)
    # valido=1 pero una feature es None -> no evaluable -> SIN_DATOS
    out = hs.evaluate(db_session, _req("DEV1", valido=1, flow=None))
    assert out["health_state"] == "SIN_DATOS"
    assert out["and_alert"] is False


def test_sin_modelo_devuelve_sin_datos(db_session):
    # device sin bundle en el registry (registry.get -> None)
    hs.registry._cache["NOMODEL"] = None
    out = hs.evaluate(db_session, _req("NOMODEL"))
    assert out["health_state"] == "SIN_DATOS"
    hs.registry._cache.clear()


# --------------------------------------------------------------------------
# §3.4 AND + §3.5 graduación
# --------------------------------------------------------------------------
def test_error_bajo_theta_es_sano(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.01, if_anomaly=True, theta=0.02)
    out = hs.evaluate(db_session, _req("DEV1"))
    assert out["health_state"] == "SANO"
    assert out["and_alert"] is False


def test_error_alto_pero_if_normal_no_alerta(db_session, bundle_factory):
    # error > theta pero IF dice normal -> AND bloquea (falso positivo evitado)
    bundle_factory("DEV1", recon_error=0.05, if_anomaly=False, theta=0.02)
    out = hs.evaluate(db_session, _req("DEV1"))
    assert out["health_state"] == "SANO"
    assert out["and_alert"] is False


# --------------------------------------------------------------------------
# Bug de escala C10 (memory/project_c1_scale_bug.md)
# Una lectura en escala equivocada (Thermo enviada a estación OEFA) produce un
# recon_error absurdo (~1e9). Estos tests documentan que el RESULTADO lo decide
# el AND, NO la magnitud del recon:
#   - recon gigante + IF normal  -> SANO (el equipo roto queda ENMASCARADO)
#   - recon gigante + IF anómalo -> CRITICO
# Es el hallazgo clave: un recon_error enorme NO garantiza detección.
# --------------------------------------------------------------------------
def test_escala_recon_gigante_if_normal_queda_sano(db_session, bundle_factory):
    # simula la lectura Thermo-a-OEFA: recon ~1.28e9 pero el IF (entrenado en
    # escala OEFA) clasifica el punto extremo como normal -> AND bloquea -> SANO
    bundle_factory("DEV1", recon_error=1.28e9, if_anomaly=False, theta=0.39)
    out = hs.evaluate(db_session, _req("DEV1"))
    assert out["recon_error"] > 1e8          # el recon SÍ explota
    assert out["and_alert"] is False          # pero el AND lo bloquea
    assert out["health_state"] == "SANO"      # riesgo: equipo roto enmascarado


def test_escala_recon_gigante_if_anomalo_es_critico(db_session, bundle_factory):
    # si el IF SÍ marca anomalía, el recon gigante -> CRITICO (>3θ)
    theta = bundle_factory("DEV1", recon_error=1.28e9, if_anomaly=True, theta=0.39)
    # subir a CRITICO es inmediato (anti-parpadeo §5.1), no requiere N_CONSEC
    out = hs.evaluate(db_session, _req("DEV1"))
    assert out["and_alert"] is True
    assert out["health_state"] == "CRITICO"


def test_escala_causa_raiz_scaler_amplifica_fuera_de_escala():
    """Causa raíz del bug C10: un StandardScaler ajustado a escala OEFA
    transforma un valor en escala Thermo a decenas de miles de σ. Determinista,
    sin depender de los .pkl reales."""
    from sklearn.preprocessing import StandardScaler
    # SampleFlow OEFA ~0.45 con ruido pequeño (escala real de entrenamiento)
    oefa_flow = np.array([[0.44], [0.45], [0.46], [0.45], [0.44]], dtype=float)
    scaler = StandardScaler().fit(oefa_flow)
    # un flow en escala Thermo (~600) cae a miles de σ
    z = scaler.transform([[600.0]])[0][0]
    assert abs(z) > 1000  # amplificación extrema -> recon del AE explota


def _evaluate_stabilized(db_session, device):
    """Evalúa N_CONSEC lecturas para superar el anti-parpadeo (§5.1) y devuelve
    la última salida (el estado ya confirmado/publicado)."""
    t0 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    out = None
    for i in range(hs.N_CONSEC):
        out = hs.evaluate(db_session, _req(device, ts=t0 + timedelta(minutes=5 * i)))
    return out


def test_graduacion_observado(db_session, bundle_factory):
    # theta < error <= 2*theta  y AND -> OBSERVADO (tras estabilizar)
    bundle_factory("DEV1", recon_error=0.03, if_anomaly=True, theta=0.02)
    out = _evaluate_stabilized(db_session, "DEV1")
    assert out["health_state"] == "OBSERVADO"
    assert out["and_alert"] is True
    assert out["severity"] == "Advertencia"


def test_graduacion_en_riesgo(db_session, bundle_factory):
    # 2*theta < error <= 3*theta -> EN_RIESGO (tras estabilizar)
    bundle_factory("DEV1", recon_error=0.05, if_anomaly=True, theta=0.02)
    out = _evaluate_stabilized(db_session, "DEV1")
    assert out["health_state"] == "EN_RIESGO"
    assert out["severity"] == "Alerta"


def test_graduacion_critico(db_session, bundle_factory):
    # error > 3*theta
    bundle_factory("DEV1", recon_error=0.1, if_anomaly=True, theta=0.02)
    out = hs.evaluate(db_session, _req("DEV1"))
    assert out["health_state"] == "CRITICO"
    assert out["severity"] == "Crítico"


# --------------------------------------------------------------------------
# §4.4 hours_since_prev online sobre timestamps
# --------------------------------------------------------------------------
def test_hours_since_prev_resetea_al_recuperar_transmision(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.01, if_anomaly=False, theta=0.02)
    t0 = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    # falla
    hs.evaluate(db_session, _req("DEV1", valido=0, ts=t0,
                                 ppb=None, flow=None, temp=None, lamp=None))
    # recupera transmisión -> hsp = 0
    out = hs.evaluate(db_session, _req("DEV1", valido=1, ts=t0 + timedelta(minutes=5)))
    assert out["hours_since_prev"] == 0.0


def test_hours_since_prev_crece_sobre_timestamps(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.01, if_anomaly=False, theta=0.02)
    t0 = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    hs.evaluate(db_session, _req("DEV1", valido=0, ts=t0,
                                 ppb=None, flow=None, temp=None, lamp=None))
    hs.evaluate(db_session, _req("DEV1", valido=1, ts=t0 + timedelta(minutes=5)))  # reset
    # 2 horas después
    out = hs.evaluate(db_session, _req("DEV1", valido=1, ts=t0 + timedelta(hours=2, minutes=5)))
    assert out["hours_since_prev"] == pytest.approx(2.0, abs=0.01)


# --------------------------------------------------------------------------
# §5.1 Estabilización anti-parpadeo
# --------------------------------------------------------------------------
def test_critico_escala_inmediato(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.1, if_anomaly=True, theta=0.02)
    out = hs.evaluate(db_session, _req("DEV1"))
    # CRITICO se publica en la primera lectura (sin esperar N_CONSEC)
    assert out["health_state"] == "CRITICO"


def test_observado_requiere_n_consec(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.03, if_anomaly=True, theta=0.02)
    t0 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    # OBSERVADO es promoción desde SANO -> requiere N_CONSEC lecturas
    states = []
    for i in range(hs.N_CONSEC):
        out = hs.evaluate(db_session, _req("DEV1", ts=t0 + timedelta(minutes=5 * i)))
        states.append(out["health_state"])
    # las primeras N_CONSEC-1 siguen en SANO; la N_CONSEC-ésima confirma OBSERVADO
    assert states[-1] == "OBSERVADO"
    assert states[0] == "SANO"


# --------------------------------------------------------------------------
# §6.3 Persistencia
# --------------------------------------------------------------------------
def test_persiste_reading_y_estado(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.01, if_anomaly=False, theta=0.02)
    hs.evaluate(db_session, _req("DEV1"))
    assert db_session.query(HealthReading).filter_by(device_id="DEV1").count() == 1
    state = db_session.get(HealthDeviceState, "DEV1")
    assert state is not None
    assert state.health_state == "SANO"


def test_get_device_state(db_session, bundle_factory):
    bundle_factory("DEV1", recon_error=0.01, if_anomaly=False, theta=0.02)
    hs.evaluate(db_session, _req("DEV1"))
    st = hs.get_device_state(db_session, "DEV1")
    assert st.device_id == "DEV1"
    assert hs.get_device_state(db_session, "NOEXISTE") is None


# --------------------------------------------------------------------------
# Regla de consolidacion de alertas (docs/regla-consolidacion-alertas.md)
# --------------------------------------------------------------------------
class _CapturePost:
    """Doble de httpx.post que captura las llamadas a monitor-alert."""
    def __init__(self):
        self.calls = []

    def __call__(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json})

        class _Resp:
            status_code = 201
            content = b'{"accion": "created"}'

            def json(self_inner):
                return {"accion": "created"}
        return _Resp()


@pytest.fixture
def capture_post(monkeypatch):
    cap = _CapturePost()
    monkeypatch.setattr(hs.httpx, "post", cap)
    return cap


def _window_start_helper():
    # bucket alineado a medianoche UTC del ts base de _req (2025-07-01 00:00)
    return datetime(2025, 7, 1, tzinfo=timezone.utc)


def test_window_start_alinea_medianoche():
    ts = datetime(2025, 7, 1, 14, 30, tzinfo=timezone.utc)
    assert hs._window_start(ts) == datetime(2025, 7, 1, tzinfo=timezone.utc)
    # dentro del mismo dia siempre cae en la misma medianoche
    ts2 = datetime(2025, 7, 1, 23, 59, tzinfo=timezone.utc)
    assert hs._window_start(ts2) == datetime(2025, 7, 1, tzinfo=timezone.utc)


def test_count_in_window_por_nivel(db_session, bundle_factory):
    # 3 lecturas OBSERVADO (recon 0.03, theta 0.02) en la misma ventana
    bundle_factory("DEVW", recon_error=0.03, if_anomaly=True, theta=0.02)
    base = _window_start_helper()
    for i in range(3):
        hs.evaluate(db_session, _req("DEVW", ts=base + timedelta(minutes=5 * i)))
    assert hs._count_in_window(db_session, "DEVW", "OBSERVADO", base) == 3
    # EN_RIESGO no debe contar las OBSERVADO (CA-08 independiente por nivel)
    assert hs._count_in_window(db_session, "DEVW", "EN_RIESGO", base) == 0


def test_critico_dispara_inmediato(db_session, bundle_factory, capture_post):
    bundle_factory("DEVC", recon_error=0.10, if_anomaly=True, theta=0.02)  # >3θ
    hs.evaluate(db_session, _req("DEVC"))
    assert len(capture_post.calls) == 1
    call = capture_post.calls[0]
    assert call["json"] == {"device_id": "DEVC", "severidad": "CRITICO"}
    assert "monitor-alert" in call["url"]


def test_observado_dispara_al_quinto(db_session, bundle_factory, capture_post):
    bundle_factory("DEVO", recon_error=0.03, if_anomaly=True, theta=0.02)  # θ–2θ
    base = _window_start_helper()
    for i in range(5):
        hs.evaluate(db_session, _req("DEVO", ts=base + timedelta(minutes=5 * i)))
    # solo la 5.a lectura cruza el umbral (>=5) -> 1 sola llamada
    assert len(capture_post.calls) == 1
    assert capture_post.calls[0]["json"]["severidad"] == "OBSERVADO"


def test_observado_no_dispara_antes_del_umbral(db_session, bundle_factory,
                                               capture_post):
    bundle_factory("DEVO2", recon_error=0.03, if_anomaly=True, theta=0.02)
    base = _window_start_helper()
    for i in range(4):  # solo 4 < 5
        hs.evaluate(db_session, _req("DEVO2", ts=base + timedelta(minutes=5 * i)))
    assert len(capture_post.calls) == 0


def test_en_riesgo_dispara_al_tercero(db_session, bundle_factory, capture_post):
    bundle_factory("DEVR", recon_error=0.05, if_anomaly=True, theta=0.02)  # 2θ–3θ
    base = _window_start_helper()
    for i in range(3):
        hs.evaluate(db_session, _req("DEVR", ts=base + timedelta(minutes=5 * i)))
    assert len(capture_post.calls) == 1
    assert capture_post.calls[0]["json"]["severidad"] == "EN_RIESGO"


def test_sin_datos_no_dispara(db_session, bundle_factory, capture_post):
    bundle_factory("DEVS", recon_error=0.10, if_anomaly=True, theta=0.02)
    # valido=0 -> gate SIN_DATOS -> no cuenta ni dispara
    for _ in range(3):
        hs.evaluate(db_session, _req("DEVS", valido=0,
                                     ppb=None, flow=None, temp=None, lamp=None))
    assert len(capture_post.calls) == 0


def test_sano_no_dispara(db_session, bundle_factory, capture_post):
    bundle_factory("DEVN", recon_error=0.01, if_anomaly=True, theta=0.02)  # <θ
    for i in range(6):
        hs.evaluate(db_session, _req("DEVN",
                                     ts=_window_start_helper() + timedelta(minutes=i)))
    assert len(capture_post.calls) == 0


def test_disparo_no_rompe_si_ops_cae(db_session, bundle_factory, monkeypatch):
    # si httpx.post lanza, evaluate no debe fallar (fire-and-forget)
    def _boom(*a, **k):
        raise RuntimeError("ops caido")
    monkeypatch.setattr(hs.httpx, "post", _boom)
    bundle_factory("DEVB", recon_error=0.10, if_anomaly=True, theta=0.02)
    out = hs.evaluate(db_session, _req("DEVB"))  # no debe lanzar
    assert out["and_alert"] is True


# --------------------------------------------------------------------------
# M3 — el endpoint /readings expone el desglose de los 2 detectores por lectura
# (recon_error, θ, veredicto IF, resultado AND, severidad). El veredicto del AE
# se deriva en el cliente como (recon_error > theta).
# --------------------------------------------------------------------------
def test_m3_readings_expone_desglose_detectores(db_session, bundle_factory,
                                                 client, capture_post):
    # una lectura CRITICO: AE error alto, IF anómalo -> AND alerta
    bundle_factory("DEVM3", recon_error=0.10, if_anomaly=True, theta=0.02)
    hs.evaluate(db_session, _req("DEVM3"))

    resp = client.get("/api/v1/health-monitor/DEVM3/readings")
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) >= 1
    p = points[-1]  # la lectura recién creada
    # campos del desglose presentes y coherentes
    assert p["if_anomaly"] is True          # Isolation Forest: anómalo
    assert p["and_alert"] is True           # compuerta AND: alerta
    assert p["recon_error"] > p["theta"]    # AE (derivado): error > θ
    assert p["severity"] is not None        # severidad de la lectura


def test_m3_readings_if_normal_no_alerta(db_session, bundle_factory, client):
    # AE error alto pero IF normal -> AND NO alerta (falso positivo evitado);
    # el desglose debe reflejar if_anomaly=False y and_alert=False.
    bundle_factory("DEVM3B", recon_error=0.05, if_anomaly=False, theta=0.02)
    hs.evaluate(db_session, _req("DEVM3B"))

    resp = client.get("/api/v1/health-monitor/DEVM3B/readings")
    assert resp.status_code == 200
    p = resp.json()["points"][-1]
    assert p["if_anomaly"] is False
    assert p["and_alert"] is False
