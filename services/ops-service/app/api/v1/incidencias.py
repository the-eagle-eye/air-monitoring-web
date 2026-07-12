from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.incidencia import (
    IncidenciaCreate,
    IncidenciaUpdate,
    IncidenciaResponse,
    IncidenciaDetailResponse,
    IncidenciaListResponse,
)
from app.schemas.mantenimiento import (
    MantenimientoCreate,
    MantenimientoResponse,
    RepuestoUsado,
    AdjuntoResponse,
)
from app.models.archivo_adjunto import ArchivoAdjunto
from app.services import incidencia_service, mantenimiento_service, problema_service


class MonitorAlertRequest(BaseModel):
    device_id: str
    severidad: str  # OBSERVADO | EN_RIESGO | CRITICO


class LinkProblemaRequest(BaseModel):
    problema_id: int | None = None  # None = desvincular


router = APIRouter()


@router.get("", response_model=IncidenciaListResponse)
def list_incidencias(
    device_id: str | None = Query(None),
    tipo: str | None = Query(None),
    estado: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_user_rol: str | None = Header(None),
    x_user_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    # Tecnico can only see correctivas assigned to them
    responsable_id = None
    if x_user_rol == "tecnico" and x_user_id:
        tipo = "correctiva"
        try:
            responsable_id = int(x_user_id)
        except ValueError:
            pass

    items, total = incidencia_service.list_incidencias(
        db, device_id, tipo, estado, page, page_size,
        responsable_id=responsable_id,
    )
    return IncidenciaListResponse(
        items=[IncidenciaResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=IncidenciaResponse, status_code=201)
def create_incidencia(data: IncidenciaCreate, db: Session = Depends(get_db)):
    incidencia = incidencia_service.create_incidencia(
        db, data, settings.IOT_SERVICE_URL)
    return IncidenciaResponse.model_validate(incidencia)


def _build_mantenimiento_response(
    mto, db: Session
) -> MantenimientoResponse | None:
    if mto is None:
        return None
    repuestos = [
        RepuestoUsado.model_validate(ru.repuesto)
        for ru in (mto.repuestos_usados or [])
        if ru.repuesto
    ]
    adjuntos_db = (
        db.query(ArchivoAdjunto)
        .filter(
            ArchivoAdjunto.entidad_tipo == "mantenimiento",
            ArchivoAdjunto.entidad_id == mto.id,
        )
        .all()
    )
    adjuntos = [AdjuntoResponse.model_validate(a) for a in adjuntos_db]
    return MantenimientoResponse(
        id=mto.id,
        incidencia_id=mto.incidencia_id,
        diagnostico=mto.diagnostico,
        acciones_realizadas=mto.acciones_realizadas,
        conclusion=mto.conclusion,
        fecha_ejecucion=mto.fecha_ejecucion,
        repuestos=repuestos,
        adjuntos=adjuntos,
        created_at=mto.created_at,
    )


@router.get("/{incidencia_id}", response_model=IncidenciaDetailResponse)
def get_incidencia(incidencia_id: int, db: Session = Depends(get_db)):
    incidencia = incidencia_service.get_incidencia(db, incidencia_id)
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia no encontrada"
        )
    resp = IncidenciaResponse.model_validate(incidencia)
    mto_resp = _build_mantenimiento_response(
        incidencia.mantenimiento_correctivo, db
    )
    return IncidenciaDetailResponse(
        **resp.model_dump(),
        mantenimiento_correctivo=mto_resp,
    )


@router.put("/{incidencia_id}", response_model=IncidenciaResponse)
def update_incidencia(
    incidencia_id: int,
    data: IncidenciaUpdate,
    db: Session = Depends(get_db),
):
    try:
        incidencia = incidencia_service.update_incidencia(db, incidencia_id, data)
    except incidencia_service.InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia no encontrada"
        )
    return IncidenciaResponse.model_validate(incidencia)


@router.post("/{incidencia_id}/problema", response_model=IncidenciaResponse)
def link_problema(incidencia_id: int, data: LinkProblemaRequest,
                  db: Session = Depends(get_db)):
    """ITIL: vincula (o desvincula con problema_id=null) la incidencia a un
    Problema (causa raíz)."""
    incidencia = problema_service.link_incidencia(db, incidencia_id, data.problema_id)
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia o problema no encontrado")
    return IncidenciaResponse.model_validate(incidencia)


@router.post(
    "/{incidencia_id}/mantenimiento",
    response_model=MantenimientoResponse,
    status_code=201,
)
def submit_mantenimiento(
    incidencia_id: int,
    data: MantenimientoCreate,
    db: Session = Depends(get_db),
):
    mantenimiento = mantenimiento_service.submit_mantenimiento(
        db, incidencia_id, data
    )
    return _build_mantenimiento_response(mantenimiento, db)


@router.post("/monitor-alert")
def monitor_alert(data: MonitorAlertRequest, db: Session = Depends(get_db)):
    """Regla de consolidacion del monitor (docs/regla-consolidacion-alertas.md).

    Un unico incidente correctivo abierto por equipo (origen=monitor_salud):
    crea, escala prioridad o no hace nada segun la severidad recibida.
    C9: si el equipo esta en ventana de mantenimiento devuelve accion 'maintenance'.
    """
    incidencia, accion = incidencia_service.create_or_escalate_monitor_incidencia(
        db, data.device_id, data.severidad, settings.IOT_SERVICE_URL
    )
    if accion == "created":
        return JSONResponse(
            status_code=201,
            content={"accion": accion,
                     "incidencia": IncidenciaResponse.model_validate(
                         incidencia).model_dump(mode="json")},
        )
    if accion == "escalated":
        return JSONResponse(
            status_code=200,
            content={"accion": accion,
                     "incidencia": IncidenciaResponse.model_validate(
                         incidencia).model_dump(mode="json")},
        )
    # noop (severidad no anomala / abierto sin escalada) o maintenance (C9 silencio)
    return JSONResponse(status_code=200, content={"accion": accion})
