from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class FamiliaMembro(Base):
    __tablename__ = "familia_membros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_familia = Column(Integer, ForeignKey("familias.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    pode_criar_tarefas = Column(Integer, default=1)
    pode_aprovar = Column(Integer, default=1)
    pode_gerenciar_loja = Column(Integer, default=0)
    pode_ver_relatorios = Column(Integer, default=1)
    ativo = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())

    familia = relationship("Familia", back_populates="membros")
