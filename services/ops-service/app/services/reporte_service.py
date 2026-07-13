import logging
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session, joinedload

from app.models.incidencia import Incidencia
from app.models.mantenimiento import MantenimientoCorrectivo, MantenimientoRepuesto
from app.models.calibracion import Calibracion

logger = logging.getLogger(__name__)

COLUMNS = [
    "id_incidencia",
    "device_id",
    "equipo_nombre",
    "ubicacion",
    "modelo",
    "marca",
    "tipo",
    "estado",
    "prioridad",
    "descripcion",
    "responsable",
    "fecha_creacion",
    "fecha_actualizacion",
    "diagnostico",
    "acciones_realizadas",
    "conclusion",
    "fecha_ejecucion",
    "repuestos_usados",
    "fecha_calibracion",
    "proveedor",
    "certificado_url",
    "nota_calibracion",
]


def _fetch_equipos_map(iot_service_url: str) -> dict[str, dict]:
    """Fetch all equipos from iot-service and return a lookup by device_id."""
    try:
        resp = httpx.get(
            f"{iot_service_url}/api/v1/iot/equipos",
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        equipos = data.get("items", data) if isinstance(data, dict) else data
        return {e["device_id"]: e for e in equipos}
    except Exception:
        logger.warning("No se pudo obtener equipos de iot-service")
        return {}


def _base_query(db: Session):
    return (
        db.query(Incidencia)
        .outerjoin(Incidencia.mantenimiento_correctivo)
        .outerjoin(Incidencia.calibracion)
        .outerjoin(Incidencia.responsable)
        .options(
            joinedload(Incidencia.mantenimiento_correctivo)
            .joinedload(MantenimientoCorrectivo.repuestos_usados)
            .joinedload(MantenimientoRepuesto.repuesto),
            joinedload(Incidencia.calibracion)
            .joinedload(Calibracion.proveedor),
            joinedload(Incidencia.responsable),
        )
    )


def _apply_filters(
    query,
    fecha_inicio: date | None,
    fecha_fin: date | None,
    device_id: str | None,
    tipo: str | None,
):
    if fecha_inicio:
        start_dt = datetime(
            fecha_inicio.year, fecha_inicio.month, fecha_inicio.day,
            tzinfo=timezone.utc,
        )
        query = query.filter(Incidencia.created_at >= start_dt)
    if fecha_fin:
        end_dt = datetime(
            fecha_fin.year, fecha_fin.month, fecha_fin.day,
            23, 59, 59, tzinfo=timezone.utc,
        )
        query = query.filter(Incidencia.created_at <= end_dt)
    if device_id:
        query = query.filter(Incidencia.device_id == device_id)
    if tipo:
        query = query.filter(Incidencia.tipo == tipo)
    return query


def _responsable_nombre(inc: Incidencia) -> str:
    if not inc.responsable:
        return ""
    return f"{inc.responsable.nombre} {inc.responsable.apellido}"


def _repuestos_str(mant: MantenimientoCorrectivo | None) -> str:
    if not mant or not mant.repuestos_usados:
        return ""
    return ", ".join(
        mr.repuesto.nombre for mr in mant.repuestos_usados if mr.repuesto
    )


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _incidencia_to_row(inc: Incidencia, equipo: dict) -> dict:
    mant = inc.mantenimiento_correctivo
    cal = inc.calibracion
    return {
        "id_incidencia": inc.id,
        "device_id": inc.device_id,
        "equipo_nombre": equipo.get("nombre", ""),
        "ubicacion": equipo.get("ubicacion", ""),
        "modelo": equipo.get("modelo", ""),
        "marca": equipo.get("marca", ""),
        "tipo": inc.tipo,
        "estado": inc.estado,
        "prioridad": inc.prioridad,
        "descripcion": inc.descripcion or "",
        "responsable": _responsable_nombre(inc),
        "fecha_creacion": _iso(inc.created_at),
        "fecha_actualizacion": _iso(inc.updated_at),
        "diagnostico": mant.diagnostico if mant else "",
        "acciones_realizadas": mant.acciones_realizadas if mant else "",
        "conclusion": mant.conclusion if mant else "",
        "fecha_ejecucion": _iso(mant.fecha_ejecucion) if mant else "",
        "repuestos_usados": _repuestos_str(mant),
        "fecha_calibracion": _iso(cal.fecha_calibracion) if cal else "",
        "proveedor": cal.proveedor.nombre if cal and cal.proveedor else "",
        "certificado_url": cal.certificado_url if cal else "",
        "nota_calibracion": cal.nota if cal else "",
    }


def get_reporte_mantenimiento(
    db: Session,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    device_id: str | None = None,
    tipo: str | None = None,
    iot_service_url: str = "",
) -> list[dict]:
    query = _apply_filters(
        _base_query(db), fecha_inicio, fecha_fin, device_id, tipo
    ).order_by(Incidencia.created_at.desc())
    incidencias = query.all()

    equipos_map = _fetch_equipos_map(iot_service_url) if iot_service_url else {}
    return [
        _incidencia_to_row(inc, equipos_map.get(inc.device_id, {}))
        for inc in incidencias
    ]
