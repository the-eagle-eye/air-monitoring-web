def test_list_proveedores(client):
    resp = client.get("/api/v1/proveedores")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert all(p["estado"] == "activo" for p in data)


def test_create_proveedor(client):
    resp = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Proveedor Nuevo"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nombre"] == "Proveedor Nuevo"
    assert data["estado"] == "activo"
    assert "id" in data


def test_get_proveedor_by_id(client):
    create_resp = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Proveedor Get"},
    )
    proveedor_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/proveedores/{proveedor_id}")
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Proveedor Get"


def test_get_proveedor_not_found(client):
    resp = client.get("/api/v1/proveedores/99999")
    assert resp.status_code == 404


def test_update_proveedor(client):
    create_resp = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Proveedor Update"},
    )
    proveedor_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/proveedores/{proveedor_id}",
        json={"nombre": "Proveedor Actualizado"},
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Proveedor Actualizado"


def test_update_proveedor_not_found(client):
    resp = client.put("/api/v1/proveedores/99999", json={"nombre": "X"})
    assert resp.status_code == 404


def test_delete_proveedor(client):
    create_resp = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Proveedor Delete"},
    )
    proveedor_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/proveedores/{proveedor_id}")
    assert resp.status_code == 204

    # Should not appear in list (soft delete)
    list_resp = client.get("/api/v1/proveedores")
    names = [p["nombre"] for p in list_resp.json()]
    assert "Proveedor Delete" not in names


def test_delete_proveedor_not_found(client):
    resp = client.delete("/api/v1/proveedores/99999")
    assert resp.status_code == 404
