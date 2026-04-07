from sqlalchemy import Column, Integer, TIMESTAMP, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class StatusResgate(str, enum.Enum):
    pendente = "Pendente"
    entregue = "Entregue"
    cancelado = "Cancelado"


class Resgate(Base):
    __tablename__ = "resgates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_filho = Column(Integer, ForeignKey("filhos.id"), nullable=False)
    id_produto = Column(Integer, ForeignKey("loja_produtos.id"), nullable=False)
    preco_pontos_pago = Column(Integer, nullable=False)
    status = Column(Enum(StatusResgate), default=StatusResgate.pendente)
    id_confirmador = Column(Integer)
    data_resgate = Column(TIMESTAMP, server_default=func.now())
    data_entrega = Column(DateTime)

    filho = relationship("Filho", back_populates="resgates")
    produto = relationship("LojaProduto", back_populates="resgates")
