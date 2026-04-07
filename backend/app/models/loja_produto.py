from sqlalchemy import Column, Integer, String, TIMESTAMP, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TipoProduto(str, enum.Enum):
    fisico = "Fisico"
    tempo = "Tempo"
    experiencia = "Experiencia"


class LojaProduto(Base):
    __tablename__ = "loja_produtos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_familia = Column(Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(1000))
    preco_pontos = Column(Integer, nullable=False)
    nivel_minimo_xp = Column(Integer, default=1)
    tipo = Column(Enum(TipoProduto), nullable=False)
    estoque = Column(Integer, default=-1)       # -1 = ilimitado
    exibir_esgotado = Column(Integer, default=1)
    ativo = Column(Integer, default=1)
    imagem_url = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    familia = relationship("Familia", back_populates="produtos")
    resgates = relationship("Resgate", back_populates="produto")
