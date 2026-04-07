from sqlalchemy import Column, Integer, String, TIMESTAMP, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TipoTransacaoPontos(str, enum.Enum):
    tarefa = "Tarefa"
    compra = "Compra"
    multa = "Multa"
    ajuste_manual = "Ajuste_Manual"
    estorno = "Estorno"


class RefTabelaPontos(str, enum.Enum):
    tarefas = "tarefas"
    resgates = "resgates"
    manual = "manual"


class TransacaoPontos(Base):
    __tablename__ = "transacoes_pontos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_filho = Column(Integer, ForeignKey("filhos.id"), nullable=False)
    valor = Column(Integer, nullable=False)
    tipo = Column(Enum(TipoTransacaoPontos), nullable=False)
    ref_tabela = Column(Enum(RefTabelaPontos), nullable=False)
    ref_id = Column(Integer)
    descricao = Column(String(255), nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    filho = relationship("Filho", back_populates="transacoes_pontos")


class TipoTransacaoXp(str, enum.Enum):
    tarefa = "Tarefa"
    multa = "Multa"
    ajuste_manual = "Ajuste_Manual"


class RefTabelaXp(str, enum.Enum):
    tarefas = "tarefas"
    manual = "manual"


class TransacaoXp(Base):
    __tablename__ = "transacoes_xp"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_filho = Column(Integer, ForeignKey("filhos.id"), nullable=False)
    valor = Column(Integer, nullable=False)
    tipo = Column(Enum(TipoTransacaoXp), nullable=False)
    ref_tabela = Column(Enum(RefTabelaXp), nullable=False)
    ref_id = Column(Integer)
    descricao = Column(String(255), nullable=False)
    nivel_antes = Column(Integer, nullable=False)
    nivel_depois = Column(Integer, nullable=False)
    criado_em = Column(TIMESTAMP, server_default=func.now())

    filho = relationship("Filho", back_populates="transacoes_xp")
