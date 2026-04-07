from sqlalchemy.orm import Session
from app.models import Filho, TransacaoPontos, TransacaoXp
from app.models.transacao import (
    TipoTransacaoPontos, RefTabelaPontos,
    TipoTransacaoXp, RefTabelaXp,
)

NIVEL_MAXIMO = 50


def xp_necessario_para_nivel(nivel: int) -> int:
    """Fórmula cumulativa: XP_total = N * (N-1) / 2 * 200"""
    return nivel * (nivel - 1) // 2 * 200


def verificar_e_atualizar_nivel(filho: Filho, db: Session) -> list[int]:
    """Verifica se o filho subiu de nível. Retorna lista de novos níveis atingidos."""
    novos_niveis = []
    while filho.nivel_atual < NIVEL_MAXIMO:
        proximo = filho.nivel_atual + 1
        if filho.xp_total >= xp_necessario_para_nivel(proximo):
            filho.nivel_atual = proximo
            novos_niveis.append(proximo)
        else:
            break
    return novos_niveis


def creditar_pontos(
    filho: Filho,
    valor: int,
    tipo: TipoTransacaoPontos,
    ref_tabela: RefTabelaPontos,
    ref_id: int,
    descricao: str,
    db: Session,
) -> None:
    filho.pontos_saldo = max(0, filho.pontos_saldo + valor)
    db.add(filho)
    transacao = TransacaoPontos(
        id_filho=filho.id,
        valor=valor,
        tipo=tipo,
        ref_tabela=ref_tabela,
        ref_id=ref_id,
        descricao=descricao,
    )
    db.add(transacao)


def creditar_xp(
    filho: Filho,
    valor: int,
    tipo: TipoTransacaoXp,
    ref_tabela: RefTabelaXp,
    ref_id: int,
    descricao: str,
    db: Session,
) -> list[int]:
    nivel_antes = filho.nivel_atual
    filho.xp_total = max(0, filho.xp_total + valor)

    novos_niveis = verificar_e_atualizar_nivel(filho, db)

    db.add(filho)
    transacao = TransacaoXp(
        id_filho=filho.id,
        valor=valor,
        tipo=tipo,
        ref_tabela=ref_tabela,
        ref_id=ref_id,
        descricao=descricao,
        nivel_antes=nivel_antes,
        nivel_depois=filho.nivel_atual,
    )
    db.add(transacao)
    return novos_niveis
