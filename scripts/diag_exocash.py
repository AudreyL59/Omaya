"""Diag ExoCashLot / ExoCashFamilleLot (base divers).

Usage : .\\venv\\Scripts\\python.exe scripts\\diag_exocash.py [IDExoCashLot]
"""

import sys

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_lot=None):
    db = get_connection("divers")

    print("=== Total ExoCashLot ===")
    try:
        print(db.query_one("SELECT COUNT(*) AS n FROM ExoCashLot"))
    except Exception as e:
        print("ERR:", repr(e))

    print("\n=== SELECT minimal (clé seule, 3 lignes) ===")
    try:
        rows = db.query("SELECT TOP 3 IDExoCashLot FROM ExoCashLot")
        for r in rows or []:
            print(" ", r)
    except Exception as e:
        print("ERR:", repr(e))

    print("\n=== SELECT colonnes une par une (sur 1 ligne) ===")
    cols = [
        "IDExoCashFamilleLot", "Marque", "LibLot", "Catégorie",
        "Montant", "Stock", "SurCommande", "EnSolde", "MontantSolde",
    ]
    for c in cols:
        try:
            r = db.query_one(f"SELECT TOP 1 IDExoCashLot, {c} FROM ExoCashLot")
            v = r.get(c) if r else None
            print(f"  {c:25} -> {type(v).__name__:10} {repr(v)[:80]}")
        except Exception as e:
            print(f"  {c:25} ERR: {repr(e)[:120]}")

    print("\n=== SELECT multi-col complet (1 ligne) ===")
    try:
        r = db.query_one(
            "SELECT TOP 1 IDExoCashLot, IDExoCashFamilleLot, Marque, "
            "LibLot, Catégorie, Montant, MontantSolde, EnSolde, "
            "Stock, SurCommande FROM ExoCashLot"
        )
        print(" ", r)
    except Exception as e:
        print("ERR multi-col:", repr(e))

    print("\n=== ExoCashFamilleLot (3 lignes) ===")
    try:
        rows = db.query(
            "SELECT TOP 3 IDExoCashFamilleLot, LibFamilleLot "
            "FROM ExoCashFamilleLot"
        )
        for r in rows or []:
            print(" ", r)
    except Exception as e:
        print("ERR:", repr(e))

    if id_lot:
        print(f"\n=== Recherche IDExoCashLot = {id_lot} ===")
        try:
            r = db.query_one(
                "SELECT IDExoCashLot, IDExoCashFamilleLot, Marque, LibLot, "
                "Catégorie, Montant, Stock, SurCommande "
                "FROM ExoCashLot WHERE IDExoCashLot = ?",
                (int(id_lot),),
            )
            print(" ", r)
        except Exception as e:
            print("ERR:", repr(e))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
