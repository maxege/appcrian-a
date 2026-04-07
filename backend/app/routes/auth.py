import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Familia, Filho, Plano, Consentimento, QrcodeAcesso
from app.schemas.auth import (
    LoginResponsavelInput, TokenResponse,
    LoginFilhoInput, FilhoTokenResponse,
    CadastroFamiliaInput, FamiliaResponse,
    QrCodeResponse, ValidarQrCodeInput,
)
from app.services.auth import (
    hash_senha, verificar_senha, criar_token, get_responsavel_atual
)

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

# Controle simples de tentativas de PIN por filho (em memória — suficiente para MVP)
_tentativas_pin: dict[int, list] = {}
MAX_TENTATIVAS = 5
COOLDOWN_MINUTOS = 15


@router.post("/login", response_model=TokenResponse)
def login_responsavel(dados: LoginResponsavelInput, db: Session = Depends(get_db)):
    familia = db.query(Familia).filter(
        Familia.email_responsavel == dados.email
    ).first()

    if not familia or not verificar_senha(dados.senha, familia.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    token = criar_token({"sub": str(familia.id), "tipo": "responsavel"})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/filho/pin", response_model=FilhoTokenResponse)
def login_filho_pin(dados: LoginFilhoInput, db: Session = Depends(get_db)):
    # Verificar bloqueio por excesso de tentativas
    agora = datetime.now(timezone.utc)
    tentativas = _tentativas_pin.get(dados.id_filho, [])
    tentativas_recentes = [t for t in tentativas if (agora - t).seconds < COOLDOWN_MINUTOS * 60]

    if len(tentativas_recentes) >= MAX_TENTATIVAS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas. Aguarde {COOLDOWN_MINUTOS} minutos.",
        )

    filho = db.query(Filho).filter(
        Filho.id == dados.id_filho,
        Filho.ativo == 1,
    ).first()

    if not filho or not verificar_senha(dados.pin, filho.pin_hash):
        _tentativas_pin.setdefault(dados.id_filho, []).append(agora)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorreto",
        )

    # Login com sucesso — limpar tentativas
    _tentativas_pin.pop(dados.id_filho, None)

    token = criar_token(
        {"sub": str(filho.id), "tipo": "filho"},
        expires_delta=timedelta(hours=12),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "filho_id": filho.id,
        "nome": filho.nome,
        "nivel_atual": filho.nivel_atual,
        "pontos_saldo": filho.pontos_saldo,
        "xp_total": filho.xp_total,
    }


@router.post("/filho/qrcode", response_model=FilhoTokenResponse)
def login_filho_qrcode(dados: ValidarQrCodeInput, db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)

    qr = db.query(QrcodeAcesso).filter(
        QrcodeAcesso.token == dados.token,
        QrcodeAcesso.usado == 0,
    ).first()

    if not qr:
        raise HTTPException(status_code=400, detail="QR Code inválido ou já utilizado")

    expira_em = qr.expira_em
    if expira_em.tzinfo is None:
        expira_em = expira_em.replace(tzinfo=timezone.utc)

    if agora > expira_em:
        raise HTTPException(status_code=400, detail="QR Code expirado")

    if dados.novo_pin != dados.confirmar_pin:
        raise HTTPException(status_code=400, detail="Os PINs não coincidem")

    if len(dados.novo_pin) != 4 or not dados.novo_pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN deve ter exatamente 4 dígitos numéricos")

    filho = db.query(Filho).filter(Filho.id == qr.id_filho).first()
    if not filho:
        raise HTTPException(status_code=404, detail="Filho não encontrado")

    # Atualizar PIN e invalidar QR Code
    filho.pin_hash = hash_senha(dados.novo_pin)
    qr.usado = 1
    db.commit()
    db.refresh(filho)

    token = criar_token(
        {"sub": str(filho.id), "tipo": "filho"},
        expires_delta=timedelta(hours=12),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "filho_id": filho.id,
        "nome": filho.nome,
        "nivel_atual": filho.nivel_atual,
        "pontos_saldo": filho.pontos_saldo,
        "xp_total": filho.xp_total,
    }


@router.post("/logout")
def logout():
    # Com JWT stateless o logout é feito no cliente descartando o token.
    # Em versão futura: blacklist de tokens via Redis.
    return {"detail": "Logout realizado com sucesso"}
