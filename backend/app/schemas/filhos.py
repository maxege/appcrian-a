from pydantic import BaseModel
from typing import Optional
from datetime import date


class CriarFilhoInput(BaseModel):
    nome: str
    data_nascimento: Optional[date] = None
    avatar_url: Optional[str] = None


class FilhoResponse(BaseModel):
    id: int
    id_familia: int
    nome: str
    avatar_url: Optional[str]
    nivel_atual: int
    pontos_saldo: int
    xp_total: int
    ativo: int

    class Config:
        from_attributes = True


class TransacaoPontosResponse(BaseModel):
    id: int
    valor: int
    tipo: str
    descricao: str
    criado_em: str

    class Config:
        from_attributes = True


class TransacaoXpResponse(BaseModel):
    id: int
    valor: int
    tipo: str
    descricao: str
    nivel_antes: int
    nivel_depois: int
    criado_em: str

    class Config:
        from_attributes = True


class ExtratoResponse(BaseModel):
    filho: FilhoResponse
    transacoes_pontos: list[TransacaoPontosResponse]
    transacoes_xp: list[TransacaoXpResponse]
