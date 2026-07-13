from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
    UsuarioWithHash,
)

router = APIRouter()

_NOT_FOUND = "Usuario no encontrado"
_NOT_FOUND_RESPONSE = {404: {"description": _NOT_FOUND}}
_EMAIL_TAKEN_RESPONSE = {409: {"description": "Email ya registrado"}}


def _hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


@router.get("", response_model=list[UsuarioResponse])
def list_usuarios(db: Session = Depends(get_db)):
    items = db.query(Usuario).order_by(Usuario.nombre).all()
    return [UsuarioResponse.model_validate(u) for u in items]


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=201,
    responses=_EMAIL_TAKEN_RESPONSE,
)
def create_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Usuario).filter(Usuario.email == data.email).first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    fields = data.model_dump(exclude={"password"})
    fields["password_hash"] = _hash_password(data.password)
    usuario = Usuario(**fields)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)


@router.put(
    "/{usuario_id}",
    response_model=UsuarioResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def update_usuario(
    usuario_id: int, data: UsuarioUpdate, db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    updates = data.model_dump(exclude_unset=True)
    if "password" in updates:
        password = updates.pop("password")
        if password:
            updates["password_hash"] = _hash_password(password)
    for key, value in updates.items():
        setattr(usuario, key, value)
    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)


@router.delete(
    "/{usuario_id}", status_code=204, responses=_NOT_FOUND_RESPONSE
)
def delete_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    usuario.estado = "inactivo"
    db.commit()


@router.get(
    "/by-email/{email}",
    response_model=UsuarioWithHash,
    responses=_NOT_FOUND_RESPONSE,
)
def get_usuario_by_email(email: str, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return UsuarioWithHash.model_validate(usuario)


@router.get(
    "/{usuario_id}",
    response_model=UsuarioResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return UsuarioResponse.model_validate(usuario)
