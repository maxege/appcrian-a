from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Familia, Plano, Consentimento, Filho, QrcodeAcesso
from app.schemas.auth import CadastroFamiliaInput, FamiliaResponse, QrCodeResponse
from app.services.auth import hash_senha, get_responsavel_atual
import uuid
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/familias", tags=["Famílias"])


@router.post("", response_model=FamiliaResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_familia(dados: CadastroFamiliaInput, request: Request, db: Session = Depends(get_db)):
    if not dados.aceite_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos de uso (LGPD)")

    existente = db.query(Familia).filter(Familia.email_responsavel == dados.email_responsavel).first()
    if existente:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    # Plano Free = id 1 (seed necessário)
    plano_free = db.query(Plano).filter(Plano.nome == "Free").first()
    if not plano_free:
        raise HTTPException(status_code=500, detail="Plano Free não configurado. Execute o seed.")

    familia = Familia(
        nome_familia=dados.nome_familia,
        email_responsavel=dados.email_responsavel,
        senha_hash=hash_senha(dados.senha),
        id_plano=plano_free.id,
        trial_expira_em=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(familia)
    db.flush()

    # Gravar consentimento LGPD
    ip = dados.ip_origem or request.client.host
    consentimento = Consentimento(
        id_familia=familia.id,
        versao_termo="1.0",
        ip_origem=ip,
    )
    db.add(consentimento)
    db.commit()
    db.refresh(familia)

    return familia


@router.get("/me", response_model=FamiliaResponse)
def get_familia_atual(familia: Familia = Depends(get_responsavel_atual)):
    return familia


@router.post("/me/filhos/{id_filho}/qrcode", response_model=QrCodeResponse)
def gerar_qrcode(
    id_filho: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    filho = db.query(Filho).filter(
        Filho.id == id_filho,
        Filho.id_familia == responsavel.id,
    ).first()

    if not filho:
        raise HTTPException(status_code=404, detail="Filho não encontrado")

    # Invalidar QR Codes anteriores deste filho
    db.query(QrcodeAcesso).filter(
        QrcodeAcesso.id_filho == id_filho,
        QrcodeAcesso.usado == 0,
    ).update({"usado": 1})

    token = str(uuid.uuid4())
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=30)

    qr = QrcodeAcesso(id_filho=id_filho, token=token, expira_em=expira_em)
    db.add(qr)
    db.commit()

    return {
        "token": token,
        "expira_em": expira_em.isoformat(),
        "qrcode_url": f"familyquest://auth/qr?token={token}",
    }
