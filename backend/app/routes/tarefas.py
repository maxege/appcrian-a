from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Familia, Filho, Tarefa
from app.models.tarefa import StatusTarefa, TipoCriador
from app.models.transacao import TipoTransacaoPontos, RefTabelaPontos, TipoTransacaoXp, RefTabelaXp
from app.schemas.tarefas import (
    CriarTarefaInput, TarefaResponse,
    EnviarFotoInput, RejeitarTarefaInput,
    ProrrogarTarefaInput, MultarTarefaInput,
)
from app.services.auth import get_responsavel_atual, get_filho_atual
from app.services.nivel import creditar_pontos, creditar_xp

router = APIRouter(prefix="/api/tarefas", tags=["Tarefas"])


def _get_tarefa_da_familia(tarefa_id: int, responsavel: Familia, db: Session) -> Tarefa:
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    filho = db.query(Filho).filter(Filho.id == tarefa.id_filho).first()
    if not filho or filho.id_familia != responsavel.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return tarefa


def _verificar_limite_tarefas(filho: Filho, familia: Familia, db: Session):
    plano = familia.plano
    if plano.max_tarefas_ativas == -1:
        return
    ativas = db.query(Tarefa).filter(
        Tarefa.id_filho == filho.id,
        Tarefa.status.in_([StatusTarefa.pendente, StatusTarefa.em_analise, StatusTarefa.rejeitada]),
    ).count()
    if ativas >= plano.max_tarefas_ativas:
        raise HTTPException(
            status_code=403,
            detail=f"Plano {plano.nome} permite no máximo {plano.max_tarefas_ativas} tarefas ativas. Faça upgrade para Premium.",
        )


# ─── Criar Tarefa ────────────────────────────────────────────────────────────

@router.post("", response_model=TarefaResponse, status_code=status.HTTP_201_CREATED)
def criar_tarefa(
    dados: CriarTarefaInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    filho = db.query(Filho).filter(
        Filho.id == dados.id_filho,
        Filho.id_familia == responsavel.id,
    ).first()
    if not filho:
        raise HTTPException(status_code=404, detail="Filho não encontrado")

    _verificar_limite_tarefas(filho, responsavel, db)

    # Plano Free não permite foto obrigatória
    foto_obrigatoria = dados.foto_obrigatoria
    if not responsavel.plano.permite_foto:
        foto_obrigatoria = 0

    tarefa = Tarefa(
        id_filho=filho.id,
        id_criador=responsavel.id,
        tipo_criador=TipoCriador.responsavel,
        titulo=dados.titulo,
        descricao=dados.descricao,
        pontos_recompensa=dados.pontos_recompensa,
        xp_recompensa=dados.xp_recompensa,
        data_limite=dados.data_limite,
        foto_obrigatoria=foto_obrigatoria,
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Listar Tarefas ──────────────────────────────────────────────────────────

@router.get("", response_model=list[TarefaResponse])
def listar_tarefas(
    filho_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    filho = db.query(Filho).filter(
        Filho.id == filho_id,
        Filho.id_familia == responsavel.id,
    ).first()
    if not filho:
        raise HTTPException(status_code=404, detail="Filho não encontrado")

    return db.query(Tarefa).filter(Tarefa.id_filho == filho_id).order_by(Tarefa.created_at.desc()).all()


# ─── Filho: Enviar Foto ───────────────────────────────────────────────────────

@router.patch("/{tarefa_id}/enviar-foto", response_model=TarefaResponse)
def enviar_foto(
    tarefa_id: int,
    dados: EnviarFotoInput,
    db: Session = Depends(get_db),
    filho: Filho = Depends(get_filho_atual),
):
    tarefa = db.query(Tarefa).filter(
        Tarefa.id == tarefa_id,
        Tarefa.id_filho == filho.id,
    ).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    if tarefa.status not in [StatusTarefa.pendente, StatusTarefa.rejeitada]:
        raise HTTPException(status_code=400, detail=f"Não é possível enviar foto com status '{tarefa.status}'")

    tarefa.foto_url = dados.foto_url
    tarefa.status = StatusTarefa.em_analise
    tarefa.data_envio_foto = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Responsável: Aprovar ─────────────────────────────────────────────────────

@router.patch("/{tarefa_id}/aprovar", response_model=TarefaResponse)
def aprovar_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tarefa = _get_tarefa_da_familia(tarefa_id, responsavel, db)

    if tarefa.status != StatusTarefa.em_analise:
        raise HTTPException(status_code=400, detail="Somente tarefas Em_Analise podem ser aprovadas")

    filho = db.query(Filho).filter(Filho.id == tarefa.id_filho).first()

    tarefa.status = StatusTarefa.concluida
    tarefa.data_conclusao = datetime.now(timezone.utc)

    creditar_pontos(
        filho, tarefa.pontos_recompensa,
        TipoTransacaoPontos.tarefa, RefTabelaPontos.tarefas,
        tarefa.id, f"Tarefa concluída: {tarefa.titulo}", db,
    )
    creditar_xp(
        filho, tarefa.xp_recompensa,
        TipoTransacaoXp.tarefa, RefTabelaXp.tarefas,
        tarefa.id, f"XP por tarefa: {tarefa.titulo}", db,
    )

    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Responsável: Rejeitar ────────────────────────────────────────────────────

@router.patch("/{tarefa_id}/rejeitar", response_model=TarefaResponse)
def rejeitar_tarefa(
    tarefa_id: int,
    dados: RejeitarTarefaInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tarefa = _get_tarefa_da_familia(tarefa_id, responsavel, db)

    if tarefa.status != StatusTarefa.em_analise:
        raise HTTPException(status_code=400, detail="Somente tarefas Em_Analise podem ser rejeitadas")

    tarefa.status = StatusTarefa.rejeitada
    tarefa.motivo_rejeicao = dados.motivo_rejeicao
    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Responsável: Prorrogar ───────────────────────────────────────────────────

@router.patch("/{tarefa_id}/prorrogar", response_model=TarefaResponse)
def prorrogar_tarefa(
    tarefa_id: int,
    dados: ProrrogarTarefaInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tarefa = _get_tarefa_da_familia(tarefa_id, responsavel, db)

    if tarefa.status not in [StatusTarefa.pendente, StatusTarefa.rejeitada, StatusTarefa.expirada]:
        raise HTTPException(status_code=400, detail="Tarefa não pode ser prorrogada no status atual")

    tarefa.data_limite = dados.nova_data_limite
    tarefa.status = StatusTarefa.pendente
    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Responsável: Multar ──────────────────────────────────────────────────────

@router.patch("/{tarefa_id}/multar", response_model=TarefaResponse)
def multar_tarefa(
    tarefa_id: int,
    dados: MultarTarefaInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tarefa = _get_tarefa_da_familia(tarefa_id, responsavel, db)

    if tarefa.status == StatusTarefa.em_analise:
        raise HTTPException(status_code=400, detail="Tarefa em análise não pode ser multada")

    percentual = dados.percentual_multa if dados.percentual_multa is not None else float(responsavel.percentual_multa_padrao)
    pontos_com_desconto = int(tarefa.pontos_recompensa * (1 - percentual / 100))

    filho = db.query(Filho).filter(Filho.id == tarefa.id_filho).first()

    tarefa.status = StatusTarefa.concluida
    tarefa.data_conclusao = datetime.now(timezone.utc)
    tarefa.percentual_multa_aplicado = percentual

    creditar_pontos(
        filho, pontos_com_desconto,
        TipoTransacaoPontos.multa, RefTabelaPontos.tarefas,
        tarefa.id, f"Tarefa com multa ({percentual}%): {tarefa.titulo}", db,
    )
    creditar_xp(
        filho, -5,
        TipoTransacaoXp.multa, RefTabelaXp.tarefas,
        tarefa.id, f"Multa por atraso: {tarefa.titulo}", db,
    )

    db.commit()
    db.refresh(tarefa)
    return tarefa


# ─── Responsável: Cancelar ────────────────────────────────────────────────────

@router.patch("/{tarefa_id}/cancelar", response_model=TarefaResponse)
def cancelar_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tarefa = _get_tarefa_da_familia(tarefa_id, responsavel, db)

    if tarefa.status == StatusTarefa.concluida:
        raise HTTPException(status_code=400, detail="Tarefa já concluída não pode ser cancelada")

    filho = db.query(Filho).filter(Filho.id == tarefa.id_filho).first()

    tarefa.status = StatusTarefa.cancelada

    creditar_xp(
        filho, -20,
        TipoTransacaoXp.multa, RefTabelaXp.tarefas,
        tarefa.id, f"Cancelamento de tarefa: {tarefa.titulo}", db,
    )

    db.commit()
    db.refresh(tarefa)
    return tarefa
