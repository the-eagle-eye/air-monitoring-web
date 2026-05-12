def test_list_repuestos(client):
    resp = client.get("/api/v1/repuestos")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    assert all(r["estado"] == "activo" for r in data)


def test_list_repuestos_filter_by_categoria(client):
    resp = client.get("/api/v1/repuestos?categoria=Sensores y Detectores")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(r["categoria"] == "Sensores y Detectores" for r in data)


def test_create_repuesto(client):
    resp = client.post(
        "/api/v1/repuestos",
        json={"nombre": "Lampara UV nueva", "categoria": "Lamparas y Optica"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Lampara UV nueva"
    assert data["categoria"] == "Lamparas y Optica"
    assert data["estado"] == "activo"
    assert "id" in data


def test_get_repuesto_by_id(client):
    # Create first
    create_resp = client.post(
        "/api/v1/repuestos",
        json={"nombre": "Repuesto Get", "categoria": "Filtros y Consumibles"},
    )
    repuesto_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/repuestos/{repuesto_id}")
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Repuesto Get"


def test_get_repuesto_not_found(client):
    resp = client.get("/api/v1/repuestos/99999")
    assert resp.status_code == 404


def test_update_repuesto(client):
    create_resp = client.post(
        "/api/v1/repuestos",
        json={"nombre": "Repuesto Update", "categoria": "Sensores y Detectores"},
    )
    repuesto_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/repuestos/{repuesto_id}",
        json={"nombre": "Repuesto Actualizado"},
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Repuesto Actualizado"
    assert resp.json()["categoria"] == "Sensores y Detectores"


def test_update_repuesto_not_found(client):
    resp = client.put("/api/v1/repuestos/99999", json={"nombre": "X"})
    assert resp.status_code == 404


def test_delete_repuesto(client):
    create_resp = client.post(
        "/api/v1/repuestos",
        json={"nombre": "Repuesto Delete", "categoria": "Filtros y Consumibles"},
    )
    repuesto_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/repuestos/{repuesto_id}")
    assert resp.status_code == 204

    # Should not appear in list (soft delete)
    list_resp = client.get("/api/v1/repuestos")
    names = [r["nombre"] for r in list_resp.json()]
    assert "Repuesto Delete" not in names


def test_delete_repuesto_not_found(client):
    resp = client.delete("/api/v1/repuestos/99999")
    assert resp.status_code == 404
