import csv
import io

from app.services.reporte_service import COLUMNS

HEADERS_ES = {
    "id_incidencia": "ID Incidencia",
    "device_id": "Equipo (ID)",
    "equipo_nombre": "Nombre Equipo",
    "ubicacion": "Ubicacion",
    "modelo": "Modelo",
    "marca": "Marca",
    "tipo": "Tipo",
    "estado": "Estado",
    "prioridad": "Prioridad",
    "descripcion": "Descripcion",
    "responsable": "Responsable",
    "fecha_creacion": "Fecha Creacion",
    "fecha_actualizacion": "Fecha Actualizacion",
    "diagnostico": "Diagnostico",
    "acciones_realizadas": "Acciones Realizadas",
    "conclusion": "Conclusion",
    "fecha_ejecucion": "Fecha Ejecucion",
    "repuestos_usados": "Repuestos Usados",
    "fecha_calibracion": "Fecha Calibracion",
    "proveedor": "Proveedor",
    "certificado_url": "Certificado URL",
    "nota_calibracion": "Nota Calibracion",
}


def generate_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    header_row = [HEADERS_ES.get(col, col) for col in COLUMNS]
    writer = csv.writer(output)
    writer.writerow(header_row)

    for row in rows:
        writer.writerow([row.get(col, "") for col in COLUMNS])

    return output.getvalue()
