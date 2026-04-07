from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Familia, Filho
from app.models.loja_produto import LojaProduto, TipoProduto
from app.models.resgate import Resgate, StatusResgate
from app.models.transacao import TipoTransacaoPontos, RefTabelaPontos
from app.schemas.loja import (
    CriarProdutoInput, AtualizarProdutoInput, ProdutoResponse,
    RealizarResgateInput, ResgateResponse,
)
from app.services.auth import get_responsavel_atual, get_filho_atual
from app.services.nivel import creditar_pontos

router = APIRouter(prefix="/api/loja", tags=["Loja"])


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_produto_da_familia(produto_id: int, responsavel: Familia, db: Session) -> LojaProduto:
    produto = db.query(LojaProduto).filter(LojaProduto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if produto.id_familia != responsavel.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return produto


def _validar_tipo(tipo: str) -> TipoProduto:
    try:
        return TipoProduto(tipo)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Tipo inválido: {tipo}. Use Fisico, Tempo ou Experiencia")


# ─── CRUD Produtos (Responsável) ─────────────────────────────────────────────

@router.post("/produtos", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(
    dados: CriarProdutoInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    tipo = _validar_tipo(dados.tipo)
    produto = LojaProduto(
        id_familia=responsavel.id,
        nome=dados.nome,
        descricao=dados.descricao,
        preco_pontos=dados.preco_pontos,
        nivel_minimo_xp=dados.nivel_minimo_xp,
        tipo=tipo,
        estoque=dados.estoque,
        exibir_esgotado=dados.exibir_esgotado,
        imagem_url=dados.imagem_url,
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.get("/produtos", response_model=list[ProdutoResponse])
def listar_produtos(
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    return (
        db.query(LojaProduto)
        .filter(LojaProduto.id_familia == responsavel.id)
        .order_by(LojaProduto.created_at.desc())
        .all()
    )


@router.patch("/produtos/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    dados: AtualizarProdutoInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    produto = _get_produto_da_familia(produto_id, responsavel, db)

    update_data = dados.model_dump(exclude_unset=True)
    if "tipo" in update_data:
        update_data["tipo"] = _validar_tipo(update_data["tipo"])
    for campo, valor in update_data.items():
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    produto = _get_produto_da_familia(produto_id, responsavel, db)
    # Soft-delete: desativa em vez de excluir para preservar histórico de resgates
    produto.ativo = 0
    db.commit()


# ─── Loja Pública (Filho) ────────────────────────────────────────────────────

@router.get("/catalogo", response_model=list[ProdutoResponse])
def catalogo_filho(
    db: Session = Depends(get_db),
    filho: Filho = Depends(get_filho_atual),
):
    """Lista produtos ativos da família do filho, filtrando por nível mínimo."""
    return (
        db.query(LojaProduto)
        .filter(
            LojaProduto.id_familia == filho.id_familia,
            LojaProduto.ativo == 1,
            LojaProduto.nivel_minimo_xp <= filho.nivel_atual,
        )
        .order_by(LojaProduto.preco_pontos.asc())
        .all()
    )


# ─── Resgates ─────────────────────────────────────────────────────────────────

@router.post("/resgatar", response_model=ResgateResponse, status_code=status.HTTP_201_CREATED)
def resgatar_produto(
    dados: RealizarResgateInput,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    """Responsável realiza resgate em nome do filho (fluxo desktop/parental)."""
    filho = db.query(Filho).filter(
        Filho.id == dados.id_filho,
        Filho.id_familia == responsavel.id,
    ).first()
    if not filho:
        raise HTTPException(status_code=404, detail="Filho não encontrado")

    produto = db.query(LojaProduto).filter(
        LojaProduto.id == dados.id_produto,
        LojaProduto.id_familia == responsavel.id,
    ).first()
    if not produto or not produto.ativo:
        raise HTTPException(status_code=404, detail="Produto não encontrado ou inativo")

    _processar_resgate(filho, produto, responsavel.id, db)
    db.commit()
    resgate = db.query(Resgate).filter(
        Resgate.id_filho == filho.id,
        Resgate.id_produto == produto.id,
    ).order_by(Resgate.data_resgate.desc()).first()
    return resgate


@router.post("/resgatar/filho", response_model=ResgateResponse, status_code=status.HTTP_201_CREATED)
def resgatar_produto_pelo_filho(
    dados: RealizarResgateInput,
    db: Session = Depends(get_db),
    filho: Filho = Depends(get_filho_atual),
):
    """Filho realiza o próprio resgate no app infantil."""
    produto = db.query(LojaProduto).filter(
        LojaProduto.id == dados.id_produto,
        LojaProduto.id_familia == filho.id_familia,
        LojaProduto.ativo == 1,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado ou inativo")

    if filho.nivel_atual < produto.nivel_minimo_xp:
        raise HTTPException(
            status_code=403,
            detail=f"Nível insuficiente. Este produto requer nível {produto.nivel_minimo_xp}.",
        )

    _processar_resgate(filho, produto, filho.id, db)
    db.commit()
    resgate = db.query(Resgate).filter(
        Resgate.id_filho == filho.id,
        Resgate.id_produto == produto.id,
    ).order_by(Resgate.data_resgate.desc()).first()
    return resgate


def _processar_resgate(filho: Filho, produto: LojaProduto, confirmador_id: int, db: Session):
    """Valida saldo, desconta pontos, reduz estoque e cria o registro de resgate."""
    if filho.pontos_saldo < produto.preco_pontos:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente. Necessário: {produto.preco_pontos}, disponível: {filho.pontos_saldo}.",
        )

    if produto.estoque == 0:
        raise HTTPException(status_code=400, detail="Produto esgotado")

    # Debita pontos (valor negativo)
    creditar_pontos(
        filho, -produto.preco_pontos,
        TipoTransacaoPontos.compra, RefTabelaPontos.resgates,
        produto.id, f"Resgate: {produto.nome}", db,
    )

    # Reduz estoque (se não ilimitado)
    if produto.estoque > 0:
        produto.estoque -= 1

    resgate = Resgate(
        id_filho=filho.id,
        id_produto=produto.id,
        preco_pontos_pago=produto.preco_pontos,
        status=StatusResgate.pendente,
        id_confirmador=confirmador_id,
    )
    db.add(resgate)


# ─── Gerenciar Resgates (Responsável) ────────────────────────────────────────

@router.get("/resgates", response_model=list[ResgateResponse])
def listar_resgates(
    filho_id: int | None = None,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    """Lista resgates pendentes/histórico da família, opcionalmente filtrado por filho."""
    ids_filhos = [f.id for f in responsavel.filhos if f.ativo]
    query = db.query(Resgate).filter(Resgate.id_filho.in_(ids_filhos))
    if filho_id:
        query = query.filter(Resgate.id_filho == filho_id)
    return query.order_by(Resgate.data_resgate.desc()).all()


@router.patch("/resgates/{resgate_id}/entregar", response_model=ResgateResponse)
def confirmar_entrega(
    resgate_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    resgate = db.query(Resgate).filter(Resgate.id == resgate_id).first()
    if not resgate:
        raise HTTPException(status_code=404, detail="Resgate não encontrado")

    # Garante que o resgate é da família do responsável
    filho = db.query(Filho).filter(Filho.id == resgate.id_filho).first()
    if not filho or filho.id_familia != responsavel.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if resgate.status != StatusResgate.pendente:
        raise HTTPException(status_code=400, detail=f"Resgate não está pendente (status: {resgate.status})")

    resgate.status = StatusResgate.entregue
    resgate.data_entrega = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resgate)
    return resgate


@router.patch("/resgates/{resgate_id}/cancelar", response_model=ResgateResponse)
def cancelar_resgate(
    resgate_id: int,
    db: Session = Depends(get_db),
    responsavel: Familia = Depends(get_responsavel_atual),
):
    resgate = db.query(Resgate).filter(Resgate.id == resgate_id).first()
    if not resgate:
        raise HTTPException(status_code=404, detail="Resgate não encontrado")

    filho = db.query(Filho).filter(Filho.id == resgate.id_filho).first()
    if not filho or filho.id_familia != responsavel.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if resgate.status != StatusResgate.pendente:
        raise HTTPException(status_code=400, detail=f"Somente resgates pendentes podem ser cancelados")

    # Estorna pontos
    produto = db.query(LojaProduto).filter(LojaProduto.id == resgate.id_produto).first()
    creditar_pontos(
        filho, resgate.preco_pontos_pago,
        TipoTransacaoPontos.estorno, RefTabelaPontos.resgates,
        resgate.id, f"Estorno resgate: {produto.nome if produto else 'produto removido'}", db,
    )

    # Devolve ao estoque (se não ilimitado e produto ainda existe)
    if produto and produto.estoque != -1:
        produto.estoque += 1

    resgate.status = StatusResgate.cancelado
    db.commit()
    db.refresh(resgate)
    return resgate
