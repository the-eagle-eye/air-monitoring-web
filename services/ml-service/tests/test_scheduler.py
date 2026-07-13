"""Tests del scheduler APScheduler del ml-service.

Cubre:
  - Job wrappers (_watchdog_job, _metrics_job, _theta_recal_job,
    _retrain_check_job, _autoclose_job): cierran la sesión y absorben
    excepciones para que un fallo no tumbe el scheduler.
  - start_scheduler(): idempotente, apagado total (todos los flags off ->
    None), habilitación selectiva (crea un job por flag activo).
  - shutdown_scheduler(): idempotente.
"""
import importlib
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sched(monkeypatch):
    """Importa `app.scheduler` con los flags apagados por defecto (conftest ya lo hace)
    y garantiza que el módulo esté limpio antes/después de cada test.
    """
    from app import scheduler as sched_mod
    # asegurar que no queda un scheduler global entre tests
    sched_mod._scheduler = None
    yield sched_mod
    # tear-down: apagar y limpiar
    if sched_mod._scheduler is not None:
        try:
            sched_mod._scheduler.shutdown(wait=False)
        except Exception:
            pass
        sched_mod._scheduler = None


# --------------------------------------------------------------------------
# Job wrappers
# --------------------------------------------------------------------------


def test_watchdog_job_llama_al_servicio_y_cierra_db(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(sched.watchdog_service, "run_watchdog") as run:
        sched._watchdog_job()
    run.assert_called_once_with(fake_db)
    fake_db.close.assert_called_once()


def test_watchdog_job_absorbe_excepcion(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.watchdog_service, "run_watchdog", side_effect=RuntimeError("boom")
         ):
        # no debe propagar la excepción (protege el scheduler)
        sched._watchdog_job()
    fake_db.close.assert_called_once()


def test_metrics_job_llama_y_absorbe_excepcion(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.metrics_service, "compute_and_store_metrics",
             side_effect=RuntimeError("kaboom"),
         ):
        sched._metrics_job()
    fake_db.close.assert_called_once()


def test_metrics_job_ok_llama_al_servicio(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.metrics_service, "compute_and_store_metrics"
         ) as compute:
        sched._metrics_job()
    compute.assert_called_once_with(fake_db)
    fake_db.close.assert_called_once()


def test_theta_recal_job_ok(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(sched.theta_service, "recalibrate_all") as rec:
        sched._theta_recal_job()
    rec.assert_called_once_with(fake_db)
    fake_db.close.assert_called_once()


def test_theta_recal_job_absorbe_excepcion(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.theta_service, "recalibrate_all", side_effect=ValueError("x")
         ):
        sched._theta_recal_job()
    fake_db.close.assert_called_once()


def test_retrain_check_dispara_reentrenamiento_solo_cuando_flag_retrain(sched):
    fake_db = MagicMock()
    resultados = [
        {"retrain": True, "station_id": "T101", "reasons": ["degrada"]},
        {"retrain": False, "station_id": "T102", "reasons": []},
    ]
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
            patch.object(
                sched.retrain_service,
                "evaluate_all",
                return_value=iter(resultados),
            ), \
            patch.object(
                sched.retrain_service, "retrain_station"
            ) as retrain:
        sched._retrain_check_job()
    # solo T101 dispara reentrenamiento
    retrain.assert_called_once_with(fake_db, "T101")
    fake_db.close.assert_called_once()


def test_retrain_check_absorbe_excepcion(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.retrain_service, "evaluate_all", side_effect=RuntimeError("x")
         ):
        sched._retrain_check_job()
    fake_db.close.assert_called_once()


def test_autoclose_job_ok(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(sched.autoclose_service, "run_autoclose") as run:
        sched._autoclose_job()
    run.assert_called_once_with(fake_db)
    fake_db.close.assert_called_once()


def test_autoclose_job_absorbe_excepcion(sched):
    fake_db = MagicMock()
    with patch.object(sched, "SessionLocal", return_value=fake_db), \
         patch.object(
             sched.autoclose_service, "run_autoclose", side_effect=Exception("x")
         ):
        sched._autoclose_job()
    fake_db.close.assert_called_once()


# --------------------------------------------------------------------------
# start_scheduler / shutdown_scheduler
# --------------------------------------------------------------------------


def _reload_with_env(monkeypatch, **envs):
    """Recarga app.scheduler con nuevos env vars para las banderas."""
    import app.scheduler as sched_mod
    # asegurar que la instancia global esté limpia antes del reload
    if sched_mod._scheduler is not None:
        try:
            sched_mod._scheduler.shutdown(wait=False)
        except Exception:
            pass
        sched_mod._scheduler = None
    for k, v in envs.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(sched_mod)


def test_start_scheduler_todo_off_devuelve_none(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )
    assert mod.start_scheduler() is None
    # tear-down: dejar el módulo en su estado por defecto de tests
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_con_todos_los_jobs_habilitados(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="1",
        METRICS_ENABLED="1",
        THETA_RECAL_ENABLED="1",
        RETRAIN_CHECK_ENABLED="1",
        AUTOCLOSE_ENABLED="1",
    )

    # instrumentamos BackgroundScheduler para no arrancar hilos reales
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        result = mod.start_scheduler()

    assert result is fake
    # los 5 jobs se agregaron
    assert fake.add_job.call_count == 5
    fake.start.assert_called_once()

    # idempotencia: segunda llamada devuelve la misma instancia sin re-agregar
    with patch.object(mod, "BackgroundScheduler", return_value=MagicMock()) as bs2:
        result2 = mod.start_scheduler()
    assert result2 is fake
    bs2.assert_not_called()

    # tear-down: reset y volver al estado por defecto de tests
    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_solo_watchdog(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="1",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        mod.start_scheduler()
    assert fake.add_job.call_count == 1
    # el id del job del watchdog
    args, kwargs = fake.add_job.call_args
    assert kwargs.get("id") == "transmission_watchdog"

    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_solo_metrics(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="1",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        mod.start_scheduler()
    assert fake.add_job.call_count == 1
    args, kwargs = fake.add_job.call_args
    assert kwargs.get("id") == "model_metrics"

    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_solo_theta(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="1",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        mod.start_scheduler()
    assert fake.add_job.call_count == 1
    args, kwargs = fake.add_job.call_args
    assert kwargs.get("id") == "theta_recalibration"

    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_solo_retrain(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="1",
        AUTOCLOSE_ENABLED="0",
    )
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        mod.start_scheduler()
    assert fake.add_job.call_count == 1
    args, kwargs = fake.add_job.call_args
    assert kwargs.get("id") == "retrain_degradation_check"

    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_start_scheduler_solo_autoclose(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="1",
    )
    fake = MagicMock()
    with patch.object(mod, "BackgroundScheduler", return_value=fake):
        mod.start_scheduler()
    assert fake.add_job.call_count == 1
    args, kwargs = fake.add_job.call_args
    assert kwargs.get("id") == "itil_autoclose"

    mod._scheduler = None
    _reload_with_env(
        monkeypatch,
        WATCHDOG_ENABLED="0",
        METRICS_ENABLED="0",
        THETA_RECAL_ENABLED="0",
        RETRAIN_CHECK_ENABLED="0",
        AUTOCLOSE_ENABLED="0",
    )


def test_shutdown_scheduler_es_noop_si_no_arranco(sched):
    # _scheduler es None -> shutdown no debe romper
    sched.shutdown_scheduler()
    assert sched._scheduler is None


def test_shutdown_scheduler_apaga_y_limpia_instancia(sched):
    fake = MagicMock()
    sched._scheduler = fake
    sched.shutdown_scheduler()
    fake.shutdown.assert_called_once_with(wait=False)
    assert sched._scheduler is None
