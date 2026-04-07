from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class StatusTarefa(str, enum.Enum):
    pendente = "Pendente"
    em_analise = "Em_Analise"
    concluida = "Concluida"
    rejeitada = "Rejeitada"
    expirada = "Expirada"
    cancelada = "Cancelada"


class TipoCriador(str, enum.Enum):
    responsavel = "Responsavel"
    co_responsavel = "CoResponsavel"


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_filho = Column(Integer, ForeignKey("filhos.id"), nullable=False)
    id_criador = Column(Integer, nullable=False)
    tipo_criador = Column(Enum(TipoCriador), nullable=False)
    titulo = Column(String(150), nullable=False)
    descricao = Column(String(1000))
    pontos_recompensa = Column(Integer, nullable=False)
    xp_recompensa = Column(Integer, nullable=False)
    data_limite = Column(DateTime, nullable=False)
    data_envio_foto = Column(DateTime)
    data_conclusao = Column(DateTime)
    foto_obrigatoria = Column(Integer, default=1)
    foto_url = Column(String(255))
    status = Column(Enum(StatusTarefa), default=StatusTarefa.pendente)
    motivo_rejeicao = Column(String(500))
    percentual_multa_aplicado = Column(DECIMAL(5, 2))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    filho = relationship("Filho", back_populates="tarefas")
