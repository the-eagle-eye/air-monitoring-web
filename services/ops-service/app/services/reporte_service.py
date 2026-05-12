import logging
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session, joinedload

from app.models.incidencia import Incidencia
from app.models.mantenimiento import MantenimientoCorrectivo, MantenimientoRepuesto
from app.models.calibracion import Calibracion
from app.models.usuario import Usuario
from app.models.proveedor_calibracion import ProveedorCalibracion
from app.models.repuesto import Repuesto

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


def get_reporte_mantenimiento(
    db: Session,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    device_id: str | None = None,
    tipo: str | None = None,
    iot_service_url: str = "",
) -> list[dict]:
    query = (
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

    query = query.order_by(Incidencia.created_at.desc())
    incidencias = query.all()

    # Enrich with equipment data
    equipos_map: dict[str, dict] = {}
    if iot_service_url:
        equipos_map = _fetch_equipos_map(iot_service_url)

    rows: list[dict] = []
    for inc in incidencias:
        equipo = equipos_map.get(inc.device_id, {})
        mant = inc.mantenimiento_correctivo
        cal = inc.calibracion
        resp_nombre = ""
        if inc.responsable:
            resp_nombre = f"{inc.responsable.nombre} {inc.responsable.apellido}"

        repuestos_str = ""
        if mant and mant.repuestos_usados:
            repuestos_str = ", ".join(
                mr.repuesto.nombre for mr in mant.repuestos_usados if mr.repuesto
            )

        proveedor_nombre = ""
        if cal and cal.proveedor:
            proveedor_nombre = cal.proveedor.nombre

        row = {
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
            "responsable": resp_nombre,
            "fecha_creacion": (
                inc.created_at.isoformat() if inc.created_at else ""
            ),
            "fecha_actualizacion": (
                inc.updated_at.isoformat() if inc.updated_at else ""
            ),
            "diagnostico": mant.diagnostico if mant else "",
            "acciones_realizadas": mant.acciones_realizadas if mant else "",
            "conclusion": mant.conclusion if mant else "",
            "fecha_ejecucion": (
                mant.fecha_ejecucion.isoformat()
                if mant and mant.fecha_ejecucion
                else ""
            ),
            "repuestos_usados": repuestos_str,
            "fecha_calibracion": (
                cal.fecha_calibracion.isoformat()
                if cal and cal.fecha_calibracion
                else ""
            ),
            "proveedor": proveedor_nombre,
            "certificado_url": cal.certificado_url if cal else "",
            "nota_calibracion": cal.nota if cal else "",
        }
        rows.append(row)

    return rows
