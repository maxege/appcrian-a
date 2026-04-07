from pydantic import BaseModel, EmailStr
from typing import Optional


# --- Login Responsável ---
class LoginResponsavelInput(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Login Filho ---
class LoginFilhoInput(BaseModel):
    id_filho: int
    pin: str


class FilhoTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    filho_id: int
    nome: str
    nivel_atual: int
    pontos_saldo: int
    xp_total: int


# --- Cadastro de Família ---
class CadastroFamiliaInput(BaseModel):
    nome_familia: str
    email_responsavel: EmailStr
    senha: str
    aceite_termos: bool  # LGPD — obrigatório
    ip_origem: Optional[str] = None  # preenchido pelo backend


class FamiliaResponse(BaseModel):
    id: int
    nome_familia: str
    email_responsavel: str
    id_plano: int

    class Config:
        from_attributes = True


# --- QR Code ---
class QrCodeResponse(BaseModel):
    token: str
    expira_em: str
    qrcode_url: str  # deep link para o app


class ValidarQrCodeInput(BaseModel):
    token: str
    novo_pin: str
    confirmar_pin: str
