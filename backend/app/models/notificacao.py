from sqlalchemy import Column, Integer, String, TIMESTAMP, DateTime, Enum, ForeignKey, func
from app.database import Base
import enum


class TipoDestinoNotificacao(str, enum.Enum):
    responsavel = "Responsavel"
    co_responsavel = "CoResponsavel"
    filho = "Filho"


class TipoEventoNotificacao(str, enum.Enum):
    tarefa_enviada = "Tarefa_Enviada"
    tarefa_aprovada = "Tarefa_Aprovada"
    tarefa_rejeitada = "Tarefa_Rejeitada"
    tarefa_expirada = "Tarefa_Expirada"
    resgate_solicitado = "Resgate_Solicitado"
    resgate_entregue = "Resgate_Entregue"
    nivel_subiu = "Nivel_Subiu"
    item_destravado = "Item_Destravado"


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_destino = Column(Integer, nullable=False)
    tipo_destino = Column(Enum(TipoDestinoNotificacao), nullable=False)
    titulo = Column(String(150), nullable=False)
    corpo = Column(String(500), nullable=False)
    tipo_evento = Column(Enum(TipoEventoNotificacao), nullable=False)
    ref_id = Column(Integer)
    lida = Column(Integer, default=0)
    enviada_push = Column(Integer, default=0)
    criada_em = Column(TIMESTAMP, server_default=func.now())
    lida_em = Column(DateTime)
