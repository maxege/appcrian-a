from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CriarTarefaInput(BaseModel):
    id_filho: int
    titulo: str
    descricao: Optional[str] = None
    pontos_recompensa: int
    xp_recompensa: int
    data_limite: datetime
    foto_obrigatoria: int = 1


class TarefaResponse(BaseModel):
    id: int
    id_filho: int
    id_criador: int
    tipo_criador: str
    titulo: str
    descricao: Optional[str]
    pontos_recompensa: int
    xp_recompensa: int
    data_limite: datetime
    data_conclusao: Optional[datetime]
    foto_obrigatoria: int
    foto_url: Optional[str]
    status: str
    motivo_rejeicao: Optional[str]
    percentual_multa_aplicado: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class EnviarFotoInput(BaseModel):
    foto_url: str  # URL já enviada ao bucket; o backend valida o formato


class RejeitarTarefaInput(BaseModel):
    motivo_rejeicao: str


class ProrrogarTarefaInput(BaseModel):
    nova_data_limite: datetime


class MultarTarefaInput(BaseModel):
    percentual_multa: Optional[float] = None  # se None, usa o padrão da família
