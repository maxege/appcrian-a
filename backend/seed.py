"""
Seed inicial: insere os planos Free e Premium no banco.
Rodar uma única vez: docker exec family_quest_backend python seed.py
"""
from app.database import SessionLocal
from app.models import Plano


def seed():
    db = SessionLocal()
    try:
        if db.query(Plano).count() > 0:
            print("Seed já executado. Nenhuma alteração feita.")
            return

        planos = [
            Plano(
                nome="Free",
                max_filhos=1,
                max_tarefas_ativas=5,
                permite_foto=0,
                permite_co_resp=0,
                permite_relatorios=0,
                preco_mensal=0.00,
                preco_anual=0.00,
            ),
            Plano(
                nome="Premium",
                max_filhos=-1,
                max_tarefas_ativas=-1,
                permite_foto=1,
                permite_co_resp=1,
                permite_relatorios=1,
                preco_mensal=19.90,
                preco_anual=179.00,
            ),
        ]

        db.add_all(planos)
        db.commit()
        print("✅ Planos Free e Premium criados com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
