from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services import reporte_service
from app.services.export_csv import generate_csv
from app.services.export_pdf import generate_pdf

router = APIRouter()

ALLOWED_ROLES = {"administrador", "coordinador"}


def _check_role(x_user_rol: str | None = Header(None)):
    if x_user_rol not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="No tiene permisos para acceder a reportes",
        )


@router.get("/preview")
def preview_reporte(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    device_id: str | None = Query(None),
    tipo: str | None = Query(None),
    db: Session = Depends(get_db),
    _role: None = Depends(_check_role),
):
    rows = reporte_service.get_reporte_mantenimiento(
        db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        device_id=device_id,
        tipo=tipo,
        iot_service_url=settings.IOT_SERVICE_URL,
    )
    return {"items": rows, "total": len(rows)}


@router.get("/csv")
def export_csv(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    device_id: str | None = Query(None),
    tipo: str | None = Query(None),
    db: Session = Depends(get_db),
    _role: None = Depends(_check_role),
):
    rows = reporte_service.get_reporte_mantenimiento(
        db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        device_id=device_id,
        tipo=tipo,
        iot_service_url=settings.IOT_SERVICE_URL,
    )
    csv_content = generate_csv(rows)
    filename = f"reporte_mantenimiento_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pdf")
def export_pdf(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    device_id: str | None = Query(None),
    tipo: str | None = Query(None),
    db: Session = Depends(get_db),
    _role: None = Depends(_check_role),
):
    rows = reporte_service.get_reporte_mantenimiento(
        db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        device_id=device_id,
        tipo=tipo,
        iot_service_url=settings.IOT_SERVICE_URL,
    )
    pdf_bytes = generate_pdf(
        rows,
        fecha_inicio=str(fecha_inicio) if fecha_inicio else None,
        fecha_fin=str(fecha_fin) if fecha_fin else None,
    )
    filename = f"reporte_mantenimiento_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
