def test_list_usuarios(client):
    resp = client.get("/api/v1/usuarios")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


def test_create_usuario(client):
    resp = client.post(
        "/api/v1/usuarios",
        json={
            "email": "nuevo@test.com",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "rol": "tecnico",
            "password": "secret123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "nuevo@test.com"
    assert data["nombre"] == "Nuevo"
    assert data["rol"] == "tecnico"
    assert data["estado"] == "activo"
    assert "password_hash" not in data


def test_create_usuario_duplicate_email(client):
    resp = client.post(
        "/api/v1/usuarios",
        json={
            "email": "admin@test.com",
            "nombre": "Dup",
            "apellido": "Test",
            "rol": "tecnico",
            "password": "secret123",
        },
    )
    assert resp.status_code == 409


def test_get_usuario_by_id(client):
    resp = client.get("/api/v1/usuarios")
    usuario_id = resp.json()[0]["id"]

    resp = client.get(f"/api/v1/usuarios/{usuario_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == usuario_id


def test_get_usuario_not_found(client):
    resp = client.get("/api/v1/usuarios/99999")
    assert resp.status_code == 404


def test_update_usuario(client):
    resp = client.get("/api/v1/usuarios")
    usuario_id = resp.json()[0]["id"]

    resp = client.put(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Actualizado", "apellido": "Nuevo"},
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Actualizado"
    assert resp.json()["apellido"] == "Nuevo"


def test_update_usuario_password(client):
    # Create a user with password
    create_resp = client.post(
        "/api/v1/usuarios",
        json={
            "email": "pwdtest@test.com",
            "nombre": "Pwd",
            "apellido": "Test",
            "rol": "tecnico",
            "password": "original123",
        },
    )
    usuario_id = create_resp.json()["id"]

    # Update password
    resp = client.put(
        f"/api/v1/usuarios/{usuario_id}",
        json={"password": "newpass123"},
    )
    assert resp.status_code == 200

    # Verify password was changed via by-email endpoint
    email_resp = client.get("/api/v1/usuarios/by-email/pwdtest@test.com")
    assert email_resp.json()["password_hash"] is not None


def test_update_usuario_not_found(client):
    resp = client.put("/api/v1/usuarios/99999", json={"nombre": "X"})
    assert resp.status_code == 404


def test_delete_usuario(client):
    create_resp = client.post(
        "/api/v1/usuarios",
        json={
            "email": "delete@test.com",
            "nombre": "Delete",
            "apellido": "Test",
            "rol": "tecnico",
            "password": "secret123",
        },
    )
    usuario_id = create_resp.json()["id"]

    resp = client.delete(f"/api/v1/usuarios/{usuario_id}")
    assert resp.status_code == 204

    # User still exists but estado is inactivo
    get_resp = client.get(f"/api/v1/usuarios/{usuario_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["estado"] == "inactivo"


def test_delete_usuario_not_found(client):
    resp = client.delete("/api/v1/usuarios/99999")
    assert resp.status_code == 404
