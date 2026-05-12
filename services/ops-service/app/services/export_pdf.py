import io
from datetime import date
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


def _truncate(text: str, max_len: int = 40) -> str:
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text


def generate_pdf(
    rows: list[dict],
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.whitesmoke,
    )

    elements: list = []

    # Title
    elements.append(Paragraph(
        "Reporte de Auditoria - Mantenimientos",
        title_style,
    ))

    # Date range and generation info
    rango = ""
    if fecha_inicio and fecha_inicio != "None":
        rango += f"Desde: {fecha_inicio}"
    if fecha_fin and fecha_fin != "None":
        rango += f"  Hasta: {fecha_fin}"
    if not rango:
        rango = "Todas las fechas"
    elements.append(Paragraph(
        f"{rango}  |  Generado: {date.today().isoformat()}  |  Total registros: {len(rows)}",
        subtitle_style,
    ))

    # Summary
    if rows:
        tipos = Counter(r.get("tipo", "") for r in rows)
        estados = Counter(r.get("estado", "") for r in rows)
        summary_parts = []
        for t, c in tipos.items():
            summary_parts.append(f"{t.capitalize()}: {c}")
        summary_parts.append("|")
        for e, c in estados.items():
            summary_parts.append(f"{e.capitalize()}: {c}")
        elements.append(Paragraph(
            "Resumen: " + "  ".join(summary_parts),
            styles["Normal"],
        ))
        elements.append(Spacer(1, 8))

    # Table
    col_keys = [
        "id_incidencia", "device_id", "tipo", "estado", "prioridad",
        "responsable", "fecha_creacion", "diagnostico",
        "acciones_realizadas", "fecha_ejecucion",
        "fecha_calibracion", "proveedor", "nota_calibracion",
    ]
    col_headers = [
        "ID", "Equipo", "Tipo", "Estado", "Prioridad",
        "Responsable", "Fecha Creacion", "Diagnostico",
        "Acciones", "Fecha Ejecucion",
        "Fecha Calibracion", "Proveedor", "Nota Cal.",
    ]

    header_row = [Paragraph(h, header_cell_style) for h in col_headers]
    table_data = [header_row]

    for row in rows:
        table_row = []
        for key in col_keys:
            val = str(row.get(key, "") or "")
            val = _truncate(val, 35)
            table_row.append(Paragraph(val, cell_style))
        table_data.append(table_row)

    col_widths = [
        25, 40, 55, 55, 45,
        60, 65, 75,
        75, 65,
        65, 55, 60,
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white, colors.HexColor("#f8fafc"),
        ]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()
