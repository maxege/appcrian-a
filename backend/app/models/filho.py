from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Filho(Base):
    __tablename__ = "filhos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_familia = Column(Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    pin_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255))
    data_nascimento = Column(Date)
    pontos_saldo = Column(Integer, default=0)
    xp_total = Column(Integer, default=0)
    nivel_atual = Column(Integer, default=1)
    ativo = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    familia = relationship("Familia", back_populates="filhos")
    qrcodes = relationship("QrcodeAcesso", back_populates="filho", cascade="all, delete-orphan")
    tarefas = relationship("Tarefa", back_populates="filho")
    resgates = relationship("Resgate", back_populates="filho")
    transacoes_pontos = relationship("TransacaoPontos", back_populates="filho")
    transacoes_xp = relationship("TransacaoXp", back_populates="filho")
