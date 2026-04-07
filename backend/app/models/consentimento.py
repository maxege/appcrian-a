from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Consentimento(Base):
    __tablename__ = "consentimentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_familia = Column(Integer, ForeignKey("familias.id"), nullable=False)
    versao_termo = Column(String(20), nullable=False)
    ip_origem = Column(String(45), nullable=False)
    aceito_em = Column(TIMESTAMP, server_default=func.now())

    familia = relationship("Familia", back_populates="consentimentos")
