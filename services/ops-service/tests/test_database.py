"""Tests del context manager get_db() del ops-service.

get_db es un generator FastAPI dependency: cede una Session y la cierra en el
finally, incluso ante excepciones del consumidor.
"""
import pytest

from app.database import SessionLocal, get_db


def test_get_db_yields_a_session():
    gen = get_db()
    session = next(gen)
    assert hasattr(session, "query")
    assert hasattr(session, "close")
    with pytest.raises(StopIteration):
        next(gen)


def test_get_db_closes_on_generator_close():
    """El finally de get_db se ejecuta al hacer .close() del generador."""
    gen = get_db()
    session = next(gen)
    closed = {"v": False}
    orig = session.close

    def _observed():
        closed["v"] = True
        orig()
    session.close = _observed
    gen.close()
    assert closed["v"] is True


def test_get_db_closes_on_exception_in_consumer():
    gen = get_db()
    session = next(gen)
    closed = {"v": False}
    orig = session.close

    def _observed():
        closed["v"] = True
        orig()
    session.close = _observed
    # simular que el consumidor lanza una excepción
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
    assert closed["v"] is True


def test_session_local_returns_usable_session():
    s = SessionLocal()
    try:
        assert hasattr(s, "query")
    finally:
        s.close()
