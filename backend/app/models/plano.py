from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.database import Base


class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(50), nullable=False)
    max_filhos = Column(Integer, nullable=False)
    max_tarefas_ativas = Column(Integer, nullable=False)
    permite_foto = Column(Integer, default=0)
    permite_co_resp = Column(Integer, default=0)
    permite_relatorios = Column(Integer, default=0)
    preco_mensal = Column(DECIMAL(8, 2), nullable=False)
    preco_anual = Column(DECIMAL(8, 2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    familias = relationship("Familia", back_populates="plano")
