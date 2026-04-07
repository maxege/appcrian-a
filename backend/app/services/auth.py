from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Familia, FamiliaMembro, Filho

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_responsavel_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Familia:
    payload = decodificar_token(token)
    tipo = payload.get("tipo")
    id_usuario = payload.get("sub")

    if not id_usuario:
        raise HTTPException(status_code=401, detail="Token inválido")

    if tipo == "responsavel":
        usuario = db.query(Familia).filter(Familia.id == int(id_usuario)).first()
    elif tipo == "co_responsavel":
        usuario = db.query(FamiliaMembro).filter(FamiliaMembro.id == int(id_usuario)).first()
    else:
        raise HTTPException(status_code=401, detail="Tipo de usuário inválido")

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return usuario


def get_filho_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Filho:
    payload = decodificar_token(token)
    tipo = payload.get("tipo")
    id_filho = payload.get("sub")

    if tipo != "filho" or not id_filho:
        raise HTTPException(status_code=401, detail="Token de filho inválido")

    filho = db.query(Filho).filter(Filho.id == int(id_filho), Filho.ativo == 1).first()
    if not filho:
        raise HTTPException(status_code=401, detail="Filho não encontrado")

    return filho
