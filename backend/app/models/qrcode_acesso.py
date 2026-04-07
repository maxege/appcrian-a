from sqlalchemy import Column, Integer, String, TIMESTAMP, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class QrcodeAcesso(Base):
    __tablename__ = "qrcodes_acesso"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_filho = Column(Integer, ForeignKey("filhos.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(36), unique=True, nullable=False)
    expira_em = Column(DateTime, nullable=False)
    usado = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    filho = relationship("Filho", back_populates="qrcodes")
