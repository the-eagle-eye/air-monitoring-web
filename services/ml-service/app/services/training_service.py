"""Reusable trainer for the AE+IF+AND ensemble (warm-up + retrain).

Ver docs/spec-auto-training-onboarding.md §4.3 (warm-up) y §5 (retrain con CR-04).

Duplicado consciente de FEATURE_KEYS / OEFA_RANGES / _in_oefa_scale desde
services/iot-service/app/services/ensemble_notify_service.py (spec §12 shim):
mantener sincronizados. La duplicación es preferible a acoplar iot↔ml.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models.iot_view import EquipoView, LecturaIoTView
from app.models.station_training import StationTrainingState
from app.services import health_service

logger = logging.getLogger(__name__)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


WARMUP_MIN_ROWS = _env_int("WARMUP_MIN_ROWS", 2016)
WARMUP_MAX_ROWS = _env_int("WARMUP_MAX_ROWS", int(2016 * 1.5))
RETRAIN_WINDOW_DAYS = _env_int("RETRAIN_WINDOW_DAYS", 90)
RETRAIN_MIN_ROWS = _env_int("RETRAIN_MIN_ROWS", 3000)
THETA_PERCENTILE = _env_int("THETA_PERCENTILE", 95)
CONTAM = _env_float("CONTAM", 0.05)
RANDOM_SEED = _env_int("TRAINING_RANDOM_SEED", 42)
CR04_MULT = _env_float("CR04_MULT", 2.0)

# Espejo de services/iot-service/app/services/ensemble_notify_service.py.
# Cambiar aquí y allá en conjunto (spec §12).
FEATURE_KEYS: dict[str, tuple[str, ...]] = {
    "so2_ppb": ("SO2_ppb", "SO2_PPB", "so2_ppb"),
    "so2_flow": ("SampleFlow", "SO2_flow", "SO2_FLOW", "so2_flow", "sample_flow"),
    "so2_lamp_int": (
        "UVLampIntensity",
        "SO2_lamp_int",
        "SO2_LAMP_INT",
        "so2_lamp_int",
        "uv_lamp_intensity",
    ),
    "so2_internal_temp": (
        "Reaction_Temp",
        "SO2_internal_temp",
        "SO2_INTERNAL_TEMP",
        "so2_internal_temp",
        "reaction_temp",
    ),
}
FEATURES = tuple(FEATURE_KEYS.keys())
BASE_COLUMNS = list(FEATURES)
TRAIN_FEATURES = BASE_COLUMNS + ["hours_since_prev"]

OEFA_RANGES: dict[str, tuple[float, float]] = {
    "so2_ppb": (-5.0, 100.0),
    "so2_flow": (0.05, 10.0),
    "so2_internal_temp": (0.0, 60.0),
    "so2_lamp_int": (30.0, 300.0),
}


def _coerce_number(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _in_oefa_scale(features: dict) -> bool:
    for feature, (lo, hi) in OEFA_RANGES.items():
        v = features.get(feature)
        if v is None or not (lo <= v <= hi):
            return False
    return True


def _extract_features(sensors: dict) -> dict:
    sensors = sensors or {}
    out = {}
    for feature, keys in FEATURE_KEYS.items():
        val = None
        for k in keys:
            if k in sensors:
                val = _coerce_number(sensors[k])
                if val is not None:
                    break
        out[feature] = val
    return out


def _load_readings(db: Session, station_id: str, source: str) -> pd.DataFrame:
    """Carga lecturas_iot para la estación. Devuelve DataFrame con timestamp +
    4 features + valido derivado. Se aplica ventana temporal sólo en retrain."""
    q = (
        db.query(LecturaIoTView.timestamp_lectura, LecturaIoTView.sensors)
        .join(EquipoView, LecturaIoTView.device_id == EquipoView.id)
        .filter(EquipoView.device_id == station_id)
        .order_by(LecturaIoTView.timestamp_lectura.asc())
    )
    if source == "retrain":
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETRAIN_WINDOW_DAYS)
        q = q.filter(LecturaIoTView.timestamp_lectura >= cutoff)

    rows = q.all()
    records = []
    for ts, sensors in rows:
        feats = _extract_features(sensors)
        valido = 1 if _in_oefa_scale(feats) else 0
        record = {"timestamp": ts, "valido": valido}
        record.update(feats)
        records.append(record)
    return pd.DataFrame(records)


def _compute_hsp_offline(df: pd.DataFrame) -> pd.DataFrame:
    """hours_since_prev calculado offline sobre la serie temporal (equivalente al
    online de health_service._hours_since_prev_online)."""
    if df.empty:
        df = df.copy()
        df["hours_since_prev"] = pd.Series(dtype=float)
        return df

    df = df.sort_values("timestamp").reset_index(drop=True)
    isf = (df["valido"].values == 0)
    n = len(df)
    h = np.full(n, np.nan)
    last_end = None
    in_fail = False
    ts = pd.to_datetime(df["timestamp"]).values
    for i in range(n):
        if isf[i]:
            in_fail = True
            continue
        if in_fail:
            last_end = i
        in_fail = False
        if last_end is not None:
            delta = (ts[i] - ts[last_end]) / np.timedelta64(1, "h")
            h[i] = max(0.0, float(delta))
    df = df.copy()
    df["hours_since_prev"] = h
    return df


def _train_bundle(df: pd.DataFrame) -> dict:
    """Entrena scaler + AE + IF y calcula θ_train = P95 sobre recon_error del train."""
    valid = df[(df["valido"] == 1) & df[BASE_COLUMNS].notna().all(axis=1)].copy()
    if len(valid) == 0:
        raise ValueError("no rows with valido=1 and complete features")

    med = valid["hours_since_prev"].median()
    if pd.isna(med):
        med = 0.0
    valid["hours_since_prev"] = valid["hours_since_prev"].fillna(med)

    X = valid[TRAIN_FEATURES].values
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    ae = MLPRegressor(
        hidden_layer_sizes=(3,),
        max_iter=300,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=RANDOM_SEED,
    ).fit(Xs, Xs)
    iforest = IsolationForest(
        n_estimators=200,
        contamination=CONTAM,
        random_state=RANDOM_SEED,
    ).fit(Xs)
    err = np.mean((Xs - ae.predict(Xs)) ** 2, axis=1)
    theta_train = float(np.percentile(err, THETA_PERCENTILE))

    return {
        "scaler": scaler,
        "ae": ae,
        "iforest": iforest,
        "theta": theta_train,
        "theta_train": theta_train,
        "rows_train": int(len(valid)),
        "median_hsp": float(med),
        "_valid_df": valid,
    }


def _write_artifacts_atomic(art_dir: str, sid: str, bundle: dict, meta: dict) -> None:
    """Escribe scaler/AE/IF/theta como `.tmp` y luego `os.replace` atómico.
    Ante excepción: limpia .tmp huérfanos y NO promueve nada (spec §4.3)."""
    os.makedirs(art_dir, exist_ok=True)
    # Registrar tmp path ANTES de escribir, para que la limpieza atrape hasta el
    # archivo que se estaba escribiendo si `joblib.dump` / `json.dump` explotan.
    pending: list[tuple[str, str]] = []
    try:
        for obj_key, filename in (
            ("scaler", f"scaler_{sid}.pkl"),
            ("ae", f"autoencoder_{sid}.pkl"),
            ("iforest", f"iforest_{sid}.pkl"),
        ):
            tmp = os.path.join(art_dir, filename + ".tmp")
            pending.append((tmp, os.path.join(art_dir, filename)))
            joblib.dump(bundle[obj_key], tmp)

        theta_tmp = os.path.join(art_dir, f"theta_{sid}.json.tmp")
        theta_final = os.path.join(art_dir, f"theta_{sid}.json")
        pending.append((theta_tmp, theta_final))
        with open(theta_tmp, "w") as f:
            json.dump(meta, f, indent=2)

        for tmp, final in pending:
            os.replace(tmp, final)
    except Exception:
        for tmp, _ in pending:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        raise


def _load_previous_theta_train(art_dir: str, sid: str):
    path = os.path.join(art_dir, f"theta_{sid}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f).get("theta_train")
    except Exception:
        return None


def _cr04_check(bundle: dict, valid_df: pd.DataFrame,
                previous_theta_train: float | None):
    """CR-04: rechaza el bundle si su recon_error mediano sobre un holdout supera
    CR04_MULT × θ_train_anterior. Devuelve (ok, motivo). Sin baseline → acepta."""
    if previous_theta_train is None:
        return True, None
    n = len(valid_df)
    if n < 20:
        return True, None

    rng = np.random.RandomState(RANDOM_SEED)
    idx = rng.choice(n, size=max(10, n // 5), replace=False)
    holdout = valid_df.iloc[idx]
    Xh = bundle["scaler"].transform(holdout[TRAIN_FEATURES].values)
    err_med = float(np.median(np.mean((Xh - bundle["ae"].predict(Xh)) ** 2, axis=1)))
    threshold = CR04_MULT * previous_theta_train
    if err_med > threshold:
        return False, (
            f"recon_error mediano {err_med:.4f} > {CR04_MULT}× theta_train_prev "
            f"({threshold:.4f})"
        )
    return True, None


def _model_version(sid: str, now: datetime) -> str:
    return f"vigishield-ensemble-v1-{sid}-{now.strftime('%Y%m%dT%H%M%SZ')}"


def _get_or_create_state(db: Session, sid: str) -> StationTrainingState:
    row = db.get(StationTrainingState, sid)
    if row is None:
        row = StationTrainingState(device_id=sid)
        db.add(row)
        db.flush()
    return row


def _mark_state(db: Session, sid: str, **fields) -> StationTrainingState:
    row = _get_or_create_state(db, sid)
    for k, v in fields.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return row


def train_station(db: Session, station_id: str, *, source: str = "warmup") -> dict:
    """Entrena scaler + AE + IF + θ para `station_id`.

    Fases:
      1. Carga lecturas de la estación (con ventana según source).
      2. Deriva valido + hours_since_prev.
      3. Si valid_count < min_rows: skip (recolectando).
      4. Entrena bundle.
      5. source="retrain": CR-04 vs. θ_train anterior — si falla, rechaza.
      6. Escribe artefactos atómicamente + invalida registry + sella state.
    """
    if source not in ("warmup", "retrain"):
        raise ValueError(f"source inválido: {source!r}")

    art_dir = health_service.ART_DIR
    min_rows = WARMUP_MIN_ROWS if source == "warmup" else RETRAIN_MIN_ROWS

    try:
        df = _load_readings(db, station_id, source)
        if df.empty:
            _mark_state(db, station_id, state="recolectando",
                        readings_valid_count=0)
            return {
                "station_id": station_id, "action": "skipped",
                "reason": "no readings", "rows_valid": 0,
            }

        df = _compute_hsp_offline(df)
        valid_count = int((df["valido"] == 1).sum())
        if valid_count < min_rows:
            _mark_state(db, station_id, state="recolectando",
                        readings_valid_count=valid_count)
            return {
                "station_id": station_id, "action": "skipped",
                "reason": f"insufficient valid rows ({valid_count} < {min_rows})",
                "rows_valid": valid_count,
            }

        if source == "warmup":
            df = df.head(WARMUP_MAX_ROWS)

        bundle = _train_bundle(df)

        if source == "retrain":
            prev = _load_previous_theta_train(art_dir, station_id)
            ok, reason = _cr04_check(bundle, bundle["_valid_df"], prev)
            if not ok:
                existing = db.get(StationTrainingState, station_id)
                attempts = (existing.attempts if existing else 0) + 1
                _mark_state(
                    db, station_id, state="error",
                    attempts=attempts,
                    last_error=f"CR-04: {reason}",
                )
                return {
                    "station_id": station_id, "action": "rejected_cr04",
                    "reason": reason,
                }

        now = datetime.now(timezone.utc)
        model_version = _model_version(station_id, now)
        meta = {
            "station_id": station_id,
            "theta": bundle["theta"],
            "theta_train": bundle["theta_train"],
            "theta_source": f"trained_{source}",
            "theta_percentile": THETA_PERCENTILE,
            "model_version": model_version,
            "rows_train": bundle["rows_train"],
            "rows_normal": bundle["rows_train"],
            "median_hsp": bundle["median_hsp"],
            "trained_at": now.isoformat(),
            "training_source": source,
        }

        _write_artifacts_atomic(art_dir, station_id, bundle, meta)
        health_service.registry.invalidate(station_id)

        _mark_state(
            db, station_id,
            state="entrenado",
            readings_valid_count=valid_count,
            training_completed_at=now,
            model_version=model_version,
            last_error=None,
        )

        return {
            "station_id": station_id,
            "action": "trained",
            "source": source,
            "rows_train": bundle["rows_train"],
            "theta": bundle["theta"],
            "theta_train": bundle["theta_train"],
            "model_version": model_version,
        }
    except Exception as exc:
        logger.exception("Training failed for %s", station_id)
        try:
            existing = db.get(StationTrainingState, station_id)
            attempts = (existing.attempts if existing else 0) + 1
            _mark_state(db, station_id, state="error",
                        attempts=attempts, last_error=str(exc)[:2000])
        except Exception:
            pass
        raise
