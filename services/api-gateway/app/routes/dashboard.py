import httpx
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def _fetch_json(url: str) -> dict | list | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


@router.get("/kpis")
async def kpis(user: dict = Depends(get_current_user)):
    # Fetch data from all services in parallel
    import asyncio

    iot_equipos, ops_incidencias, ops_calibraciones = (
        await asyncio.gather(
            _fetch_json(f"{settings.IOT_SERVICE_URL}/api/v1/iot/equipos"),
            _fetch_json(
                f"{settings.OPS_SERVICE_URL}/api/v1/incidencias?page_size=1000"
            ),
            _fetch_json(
                f"{settings.OPS_SERVICE_URL}/api/v1/calibraciones?page_size=1000"
            ),
        )
    )

    # IoT KPIs
    equipos = iot_equipos if isinstance(iot_equipos, list) else []
    total_equipos = len(equipos)
    equipos_activos = sum(1 for e in equipos if e.get("estado") == "activo")

    # Ops KPIs
    incidencias_data = ops_incidencias if isinstance(ops_incidencias, dict) else {}
    incidencias_items = incidencias_data.get("items", [])
    incidencias_abiertas = sum(
        1 for i in incidencias_items
        if i.get("estado") in ("pendiente", "en_ejecucion")
    )
    incidencias_por_tipo = {"correctiva": 0, "calibracion": 0}
    for i in incidencias_items:
        if i.get("estado") in ("pendiente", "en_ejecucion"):
            tipo = i.get("tipo", "")
            if tipo in incidencias_por_tipo:
                incidencias_por_tipo[tipo] += 1

    calibraciones_data = (
        ops_calibraciones if isinstance(ops_calibraciones, dict) else {}
    )
    calibraciones_items = calibraciones_data.get("items", [])
    calibraciones_pendientes = sum(
        1 for c in calibraciones_items if not c.get("fecha_calibracion")
    )

    return {
        "equipos": {
            "total": total_equipos,
            "activos": equipos_activos,
        },
        "incidencias": {
            "abiertas": incidencias_abiertas,
            "por_tipo": incidencias_por_tipo,
        },
        "calibraciones": {
            "pendientes": calibraciones_pendientes,
            "total": len(calibraciones_items),
        },
    }
