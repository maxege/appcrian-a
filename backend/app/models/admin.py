from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from app.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
