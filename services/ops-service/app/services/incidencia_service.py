import logging
from datetime import date, datetime, timezone, timedelta

import httpx
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

from app.models.incidencia import Incidencia
from app.models.calibracion import Calibracion
from app.models.usuario import Usuario
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate
from app.services import email_service


def create_incidencia(db: Session, data: IncidenciaCreate) -> Incidencia:
    incidencia = Incidencia(
        device_id=data.device_id,
        tipo=data.tipo,
        descripcion=data.descripcion,
        prioridad=data.prioridad,
        responsable_id=data.responsable_id,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
    return incidencia


def get_incidencia(db: Session, incidencia_id: int) -> Incidencia | None:
    from app.models.mantenimiento import MantenimientoCorrectivo, MantenimientoRepuesto
    return (
        db.query(Incidencia)
        .options(
            joinedload(Incidencia.mantenimiento_correctivo)
            .joinedload(MantenimientoCorrectivo.repuestos_usados)
            .joinedload(MantenimientoRepuesto.repuesto),
            joinedload(Incidencia.calibracion),
            joinedload(Incidencia.responsable),
        )
        .filter(Incidencia.id == incidencia_id)
        .first()
    )


def list_incidencias(
    db: Session,
    device_id: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    page: int = 1,
    page_size: int = 50,
    responsable_id: int | None = None,
) -> tuple[list[Incidencia], int]:
    query = db.query(Incidencia)

    if device_id:
        query = query.filter(Incidencia.device_id == device_id)
    if tipo:
        query = query.filter(Incidencia.tipo == tipo)
    if estado:
        query = query.filter(Incidencia.estado == estado)
    if responsable_id is not None:
        query = query.filter(Incidencia.responsable_id == responsable_id)

    query = query.order_by(desc(Incidencia.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_incidencia(
    db: Session, incidencia_id: int, data: IncidenciaUpdate
) -> Incidencia | None:
    incidencia = db.query(Incidencia).filter(
        Incidencia.id == incidencia_id
    ).first()
    if not incidencia:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(incidencia, field, value)
    incidencia.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(incidencia)

    # Regla: si correctiva se finaliza, auto-crear calibracion + desactivar alertas
    if (
        incidencia.tipo == "correctiva"
        and incidencia.estado == "finalizado"
    ):
        try:
            from app.config import settings
            _auto_create_calibracion(db, incidencia, settings.IOT_SERVICE_URL)
        except Exception:
            logger.exception(
                "Error creando calibracion automatica para incidencia %s",
                incidencia.id,
            )
        try:
            from app.config import settings
            _deactivate_device_alerts(incidencia.device_id, settings.ML_SERVICE_URL)
        except Exception:
            logger.exception(
                "Error desactivando alertas para equipo %s",
                incidencia.device_id,
            )

    return incidencia


def _get_coordinador(db: Session) -> Usuario | None:
    """Obtener primer coordinador activo."""
    return (
        db.query(Usuario)
        .filter(Usuario.rol == "coordinador", Usuario.estado == "activo")
        .first()
    )


def _fetch_equipo_data(iot_service_url: str, device_id: str) -> dict:
    """Obtener datos de equipo desde iot-service."""
    try:
        resp = httpx.get(
            f"{iot_service_url}/api/v1/iot/equipos/{device_id}",
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, Exception):
        return {"device_id": device_id}


def _deactivate_device_alerts(device_id: str, ml_service_url: str) -> None:
    """Desactivar alertas activas en ml-service (fire-and-forget)."""
    try:
        resp = httpx.patch(
            f"{ml_service_url}/api/v1/alerts/deactivate/{device_id}",
            timeout=10.0,
        )
        resp.raise_for_status()
        logger.info("Alertas desactivadas para equipo %s", device_id)
    except Exception:
        logger.exception(
            "Error desactivando alertas en ml-service para %s", device_id
        )


def _auto_create_calibracion(
    db: Session, correctiva: Incidencia, iot_service_url: str = ""
) -> Incidencia:
    """Crear incidencia de calibracion cuando una correctiva finaliza."""
    coordinador = _get_coordinador(db)

    cal_incidencia = Incidencia(
        device_id=correctiva.device_id,
        tipo="calibracion",
        descripcion=(
            f"Calibracion requerida post-mantenimiento correctivo "
            f"(incidencia #{correctiva.id})"
        ),
        prioridad="alta",
        responsable_id=coordinador.id if coordinador else None,
    )
    db.add(cal_incidencia)
    db.commit()
    db.refresh(cal_incidencia)

    calibracion = Calibracion(
        incidencia_id=cal_incidencia.id,
        device_id=correctiva.device_id,
    )
    db.add(calibracion)
    db.commit()

    equipo_data = _fetch_equipo_data(iot_service_url, correctiva.device_id)
    email_service.send_calibracion_notification(
        db, equipo_data, cal_incidencia.id, motivo="post_correctiva"
    )

    return cal_incidencia


def create_alert_triggered_incidencia(
    db: Session, device_id: str, iot_service_url: str = "",
    nivel_riesgo: str = "alta",
) -> Incidencia | None:
    """Crear incidencia correctiva cuando se detecta alerta alta o media.

    Idempotente: no crea duplicados si ya existe una correctiva hoy para el equipo.
    Retorna la incidencia creada, o None si ya existia.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    existing = (
        db.query(Incidencia)
        .filter(
            Incidencia.device_id == device_id,
            Incidencia.tipo == "correctiva",
            Incidencia.created_at >= today_start,
        )
        .first()
    )
    if existing:
        return None

    coordinador = _get_coordinador(db)
    prioridad = "alta" if nivel_riesgo == "alta" else "media"
    rul_desc = "< 30" if nivel_riesgo == "alta" else "< 60"

    incidencia = Incidencia(
        device_id=device_id,
        tipo="correctiva",
        descripcion=(
            f"Incidencia automatica: alerta {nivel_riesgo} detectada "
            f"para equipo {device_id} (RUL {rul_desc} dias)"
        ),
        prioridad=prioridad,
        responsable_id=coordinador.id if coordinador else None,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)

    equipo_data = _fetch_equipo_data(iot_service_url, device_id)
    email_service.send_alerta_correctiva_notification(
        db, equipo_data, incidencia.id
    )

    return incidencia


def evaluate_alerts(db: Session, ml_service_url: str) -> list[Incidencia]:
    """Evaluar alertas alta y media del ml-service y crear incidencias automaticas."""
    created_incidencias: list[Incidencia] = []
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    for nivel in ("alta", "media"):
        try:
            response = httpx.get(
                f"{ml_service_url}/api/v1/alerts",
                params={"estado": "activa", "nivel_riesgo": nivel, "page_size": "200"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, Exception):
            continue

        alertas = data.get("items", [])

        # Agrupar alertas de hoy por device_id
        device_counts: dict[str, int] = {}
        for alerta in alertas:
            created = alerta.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created)
                if created_dt >= today_start:
                    did = alerta["device_id"]
                    device_counts[did] = device_counts.get(did, 0) + 1
            except (ValueError, KeyError):
                continue

        for device_id, count in device_counts.items():
            if count < 2:
                continue

            existing = (
                db.query(Incidencia)
                .filter(
                    Incidencia.device_id == device_id,
                    Incidencia.tipo == "correctiva",
                    Incidencia.created_at >= today_start,
                )
                .first()
            )
            if existing:
                continue

            prioridad = "alta" if nivel == "alta" else "media"
            incidencia = Incidencia(
                device_id=device_id,
                tipo="correctiva",
                descripcion=(
                    f"Incidencia automatica: {count} alertas {nivel} detectadas "
                    f"para equipo {device_id} en el dia de hoy"
                ),
                prioridad=prioridad,
            )
            db.add(incidencia)
            db.commit()
            db.refresh(incidencia)
            created_incidencias.append(incidencia)

    return created_incidencias


def _next_anniversary(fecha_ingreso: date, today: date) -> date:
    """Calcular proximo aniversario de fecha_ingreso."""
    for year_offset in range(0, 5):
        try:
            anniversary = fecha_ingreso.replace(year=today.year + year_offset)
        except ValueError:
            # 29 feb en anio no bisiesto
            anniversary = date(today.year + year_offset, 3, 1)
        if anniversary >= today:
            return anniversary
    return fecha_ingreso.replace(year=today.year + 5)


def check_annual_calibrations(
    db: Session, iot_service_url: str
) -> list[Incidencia]:
    """Verificar equipos proximos a su aniversario y crear calibraciones."""
    try:
        response = httpx.get(
            f"{iot_service_url}/api/v1/iot/equipos",
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, Exception):
        return []

    equipos = data.get("items", data) if isinstance(data, dict) else data
    today = date.today()
    coordinador = _get_coordinador(db)
    created_incidencias: list[Incidencia] = []

    for equipo in equipos:
        fecha_str = equipo.get("fecha_ingreso")
        if not fecha_str:
            continue

        try:
            fecha_ingreso = date.fromisoformat(str(fecha_str))
        except (ValueError, TypeError):
            continue

        anniversary = _next_anniversary(fecha_ingreso, today)
        days_until = (anniversary - today).days

        if not (0 <= days_until <= 7):
            continue

        device_id = equipo["device_id"]

        # Idempotencia: verificar si ya existe incidencia anual reciente
        window_start = anniversary - timedelta(days=30)
        window_end = anniversary + timedelta(days=30)
        existing = (
            db.query(Incidencia)
            .filter(
                Incidencia.device_id == device_id,
                Incidencia.tipo == "calibracion",
                Incidencia.descripcion.contains("Calibracion anual"),
                Incidencia.created_at >= datetime(
                    window_start.year, window_start.month, window_start.day,
                    tzinfo=timezone.utc
                ),
                Incidencia.created_at <= datetime(
                    window_end.year, window_end.month, window_end.day,
                    23, 59, 59, tzinfo=timezone.utc
                ),
            )
            .first()
        )
        if existing:
            continue

        incidencia = Incidencia(
            device_id=device_id,
            tipo="calibracion",
            descripcion=(
                f"Calibracion anual programada para equipo {device_id}. "
                f"Aniversario: {anniversary.isoformat()}"
            ),
            prioridad="media",
            responsable_id=coordinador.id if coordinador else None,
        )
        db.add(incidencia)
        db.commit()
        db.refresh(incidencia)

        calibracion = Calibracion(
            incidencia_id=incidencia.id,
            device_id=device_id,
        )
        db.add(calibracion)
        db.commit()

        equipo_data = dict(equipo)
        equipo_data["fecha_aniversario"] = anniversary.isoformat()
        email_service.send_calibracion_notification(
            db, equipo_data, incidencia.id, motivo="anual"
        )

        created_incidencias.append(incidencia)

    return created_incidencias
