def _create_incidencia_correctiva(client, device_id="T101"):
    resp = client.post(
        "/api/v1/incidencias",
        json={
            "device_id": device_id,
            "tipo": "correctiva",
            "descripcion": "Falla detectada en sensor",
            "prioridad": "alta",
            "responsable_id": 1,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_incidencia_calibracion(client, device_id="T101"):
    resp = client.post(
        "/api/v1/incidencias",
        json={
            "device_id": device_id,
            "tipo": "calibracion",
            "descripcion": "Calibracion programada",
            "prioridad": "media",
            "responsable_id": 1,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ---- Preview endpoint tests ----


def test_reporte_preview_empty(client):
    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "administrador"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_reporte_preview_with_data(client):
    _create_incidencia_correctiva(client)
    _create_incidencia_calibracion(client)

    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "administrador"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    tipos = {row["tipo"] for row in data["items"]}
    assert "correctiva" in tipos
    assert "calibracion" in tipos


def test_reporte_preview_includes_responsable(client):
    _create_incidencia_correctiva(client)

    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    assert data["total"] == 1
    row = data["items"][0]
    assert row["responsable"] == "Admin Test"


def test_reporte_preview_with_mantenimiento(client):
    inc = _create_incidencia_correctiva(client)
    client.post(
        f"/api/v1/incidencias/{inc['id']}/mantenimiento",
        json={
            "diagnostico": "Sensor danado",
            "acciones_realizadas": "Reemplazo de sensor",
            "conclusion": "Equipo operativo",
            "repuesto_ids": [1],
        },
    )

    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    row = data["items"][0]
    assert row["diagnostico"] == "Sensor danado"
    assert row["acciones_realizadas"] == "Reemplazo de sensor"
    assert "Sensor SO2" in row["repuestos_usados"]


# ---- Filter tests ----


def test_reporte_filter_by_tipo(client):
    _create_incidencia_correctiva(client)
    _create_incidencia_calibracion(client)

    resp = client.get(
        "/api/v1/reportes/preview?tipo=correctiva",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["tipo"] == "correctiva"


def test_reporte_filter_by_device_id(client):
    _create_incidencia_correctiva(client, device_id="T101")
    _create_incidencia_correctiva(client, device_id="T102")

    resp = client.get(
        "/api/v1/reportes/preview?device_id=T102",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["device_id"] == "T102"


def test_reporte_filter_by_date_range(client):
    _create_incidencia_correctiva(client)

    # Use a very wide range that includes today
    resp = client.get(
        "/api/v1/reportes/preview?fecha_inicio=2020-01-01&fecha_fin=2030-12-31",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    assert data["total"] >= 1

    # Use a range in the past that excludes today
    resp = client.get(
        "/api/v1/reportes/preview?fecha_inicio=2020-01-01&fecha_fin=2020-01-02",
        headers={"x-user-rol": "administrador"},
    )
    data = resp.json()
    assert data["total"] == 0


# ---- CSV export tests ----


def test_reporte_csv_returns_csv(client):
    _create_incidencia_correctiva(client)

    resp = client.get(
        "/api/v1/reportes/csv",
        headers={"x-user-rol": "administrador"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    content = resp.text
    assert "ID Incidencia" in content
    assert "T101" in content


def test_reporte_csv_empty(client):
    resp = client.get(
        "/api/v1/reportes/csv",
        headers={"x-user-rol": "coordinador"},
    )
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) == 1  # Only header row


# ---- PDF export tests ----


def test_reporte_pdf_returns_pdf(client):
    _create_incidencia_correctiva(client)

    resp = client.get(
        "/api/v1/reportes/pdf",
        headers={"x-user-rol": "administrador"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/pdf"
    assert resp.content[:5] == b"%PDF-"


def test_reporte_pdf_empty(client):
    resp = client.get(
        "/api/v1/reportes/pdf",
        headers={"x-user-rol": "coordinador"},
    )
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


# ---- Role restriction tests ----


def test_reporte_role_restriction_tecnico(client):
    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "tecnico"},
    )
    assert resp.status_code == 403


def test_reporte_role_restriction_no_role(client):
    resp = client.get("/api/v1/reportes/preview")
    assert resp.status_code == 403


def test_reporte_csv_role_restriction(client):
    resp = client.get(
        "/api/v1/reportes/csv",
        headers={"x-user-rol": "tecnico"},
    )
    assert resp.status_code == 403


def test_reporte_pdf_role_restriction(client):
    resp = client.get(
        "/api/v1/reportes/pdf",
        headers={"x-user-rol": "tecnico"},
    )
    assert resp.status_code == 403


def test_reporte_allowed_for_coordinador(client):
    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "coordinador"},
    )
    assert resp.status_code == 200


def test_reporte_allowed_for_admin(client):
    resp = client.get(
        "/api/v1/reportes/preview",
        headers={"x-user-rol": "administrador"},
    )
    assert resp.status_code == 200
