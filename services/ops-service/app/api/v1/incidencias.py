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
from app.services import incidencia_service, mantenimiento_service


class AlertTriggerRequest(BaseModel):
    device_id: str
    nivel_riesgo: str = "alta"

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
    incidencia = incidencia_service.create_incidencia(db, data)
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
    incidencia = incidencia_service.update_incidencia(db, incidencia_id, data)
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia no encontrada"
        )
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


@router.post("/evaluar", response_model=list[IncidenciaResponse])
def evaluar_alertas(db: Session = Depends(get_db)):
    created = incidencia_service.evaluate_alerts(db, settings.ML_SERVICE_URL)
    return [IncidenciaResponse.model_validate(i) for i in created]


@router.post("/alert-trigger", response_model=IncidenciaResponse, status_code=201)
def alert_trigger(data: AlertTriggerRequest, db: Session = Depends(get_db)):
    """Crear incidencia correctiva automatica cuando ml-service detecta alerta alta o media."""
    incidencia = incidencia_service.create_alert_triggered_incidencia(
        db, data.device_id, settings.IOT_SERVICE_URL, nivel_riesgo=data.nivel_riesgo
    )
    if incidencia is None:
        return JSONResponse(
            status_code=200,
            content={"detail": "Incidencia correctiva ya existe para hoy"},
        )
    return IncidenciaResponse.model_validate(incidencia)
