from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Familia, Filho, TransacaoPontos, TransacaoXp
from app.schemas.filhos import (
    CriarFilhoInput, FilhoResponse, ExtratoResponse,
    TransacaoPontosResponse, TransacaoXpResponse,
)
from app.services.auth import hash_senha, get_responsavel_atual
from app.services.nivel import xp_necessario_para_nivel

router = APIRouter(prefix="/api/familias/me/filhos", tags=["Filhos"])


def _verificar_limite_filhos(familia: Familia, db: Session):
    plano = familia.plano
    if plano.max_filhos == -1:
        return  # ilimitado
    ativos = db.query(Filho).filter(
        Filho.id_familia == familia.id,
        Filho.ativo == 1,
    ).count()
    if ativos >= plano.max_filhos:
        raise HTTPException(
            status_code=403,
            detail=f"Plano {plano.nome} permite no máximo {plano.max_filhos} filho(s) ativo(s). Faça upgrade para Premium.",
        )


@router.post("", response_model=FilhoResponse, status_code=status.HTTP_201_CREATED)
def criar_filho(
    dados: CriarFilhoInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    _verificar_limite_filhos(responsavel, db)

    # PIN temporário — responsável deve gerar QR Code para o filho definir o próprio PIN
    PIN_PLACEHOLDER = "0000"
    filho = Filho(
        id_familia=responsavel.id,
        nome=dados.nome,
        pin_hash=hash_senha(PIN_PLACEHOLDER),
        avatar_url=dados.avatar_url,
        data_nascimento=dados.data_nascimento,
    )
    db.add(filho)
    db.commit()
    db.refresh(filho)
    return filho


@router.get("", response_model=list[FilhoResponse])
def listar_filhos(
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    return db.query(Filho).filter(Filho.id_familia == responsavel.id).all()


@router.get("/{id_filho}/extrato", response_model=ExtratoResponse)
def extrato_filho(
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

    pontos = (
        db.query(TransacaoPontos)
        .filter(TransacaoPontos.id_filho == id_filho)
        .order_by(TransacaoPontos.criado_em.desc())
        .limit(50)
        .all()
    )
    xp = (
        db.query(TransacaoXp)
        .filter(TransacaoXp.id_filho == id_filho)
        .order_by(TransacaoXp.criado_em.desc())
        .limit(50)
        .all()
    )

    return {
        "filho": filho,
        "transacoes_pontos": [
            {**p.__dict__, "criado_em": str(p.criado_em)} for p in pontos
        ],
        "transacoes_xp": [
            {**x.__dict__, "criado_em": str(x.criado_em)} for x in xp
        ],
    }
