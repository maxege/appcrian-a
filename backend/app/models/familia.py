from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Familia(Base):
    __tablename__ = "familias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_familia = Column(String(100), nullable=False)
    email_responsavel = Column(String(150), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    id_plano = Column(Integer, ForeignKey("planos.id"), nullable=False)
    modo_progressao = Column(Integer, default=1)  # 1=Autonomia, 0=Manual
    percentual_multa_padrao = Column(DECIMAL(5, 2), default=20.00)
    gateway_customer_id = Column(String(100))
    trial_expira_em = Column(DateTime)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    plano = relationship("Plano", back_populates="familias")
    membros = relationship("FamiliaMembro", back_populates="familia", cascade="all, delete-orphan")
    filhos = relationship("Filho", back_populates="familia", cascade="all, delete-orphan")
    consentimentos = relationship("Consentimento", back_populates="familia")
    produtos = relationship("LojaProduto", back_populates="familia", cascade="all, delete-orphan")
