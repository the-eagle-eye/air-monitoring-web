from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioResponse

router = APIRouter()


@router.get("", response_model=list[UsuarioResponse])
def list_usuarios(db: Session = Depends(get_db)):
    items = db.query(Usuario).order_by(Usuario.nombre).all()
    return [UsuarioResponse.model_validate(u) for u in items]


@router.post("", response_model=UsuarioResponse, status_code=201)
def create_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Usuario).filter(Usuario.email == data.email).first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    usuario = Usuario(**data.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UsuarioResponse.model_validate(usuario)
