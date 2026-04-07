from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Produtos ────────────────────────────────────────────────────────────────

class CriarProdutoInput(BaseModel):
    nome: str = Field(..., max_length=100)
    descricao: Optional[str] = Field(None, max_length=1000)
    preco_pontos: int = Field(..., gt=0)
    nivel_minimo_xp: int = Field(1, ge=1)
    tipo: str  # Fisico | Tempo | Experiencia
    estoque: int = Field(-1, ge=-1)  # -1 = ilimitado
    exibir_esgotado: int = Field(1, ge=0, le=1)
    imagem_url: Optional[str] = None


class AtualizarProdutoInput(BaseModel):
    nome: Optional[str] = Field(None, max_length=100)
    descricao: Optional[str] = Field(None, max_length=1000)
    preco_pontos: Optional[int] = Field(None, gt=0)
    nivel_minimo_xp: Optional[int] = Field(None, ge=1)
    tipo: Optional[str] = None
    estoque: Optional[int] = Field(None, ge=-1)
    exibir_esgotado: Optional[int] = Field(None, ge=0, le=1)
    ativo: Optional[int] = Field(None, ge=0, le=1)
    imagem_url: Optional[str] = None


class ProdutoResponse(BaseModel):
    id: int
    id_familia: int
    nome: str
    descricao: Optional[str]
    preco_pontos: int
    nivel_minimo_xp: int
    tipo: str
    estoque: int
    exibir_esgotado: int
    ativo: int
    imagem_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Resgates ─────────────────────────────────────────────────────────────────

class RealizarResgateInput(BaseModel):
    id_produto: int
    id_filho: int


class ResgateResponse(BaseModel):
    id: int
    id_filho: int
    id_produto: int
    preco_pontos_pago: int
    status: str
    data_resgate: datetime
    data_entrega: Optional[datetime]

    class Config:
        from_attributes = True
