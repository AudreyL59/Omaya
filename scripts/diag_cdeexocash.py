"""Diag _panier_lignes pour FI_CdeExoCash : trace l'enrichissement
des lignes panier avec le catalogue ExoCashLot.

Usage : .\\venv\\Scripts\\python.exe scripts\\diag_cdeexocash.py <IDTK_Liste>
"""

import sys

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_ticket: int):
    print(f"=== TK_CdeExoCashLot WHERE IDTK_Liste = {id_ticket} ===")
    rh = get_connection("ticket_rh")
    try:
        rows = rh.query(
            """SELECT IDTK_CdeExoCashLot, IDExoCashLot, Qté, NumSuivi,
                MontantPayé, ModifElem
            FROM TK_CdeExoCashLot WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        for r in rows or []:
            print(" ", r)
        ids = [int(r.get("IDExoCashLot") or 0) for r in (rows or [])]
        print("\n  -> IDExoCashLot trouvés :", ids)
    except Exception as e:
        print("ERR:", repr(e))
        return

    if not ids:
        print("Aucun lot pour ce ticket.")
        return

    print(f"\n=== Catalogue WHERE IDExoCashLot IN ({','.join(map(str, ids))}) ===")
    div = get_connection("divers")
    try:
        rows = div.query(
            "SELECT IDExoCashLot, IDExoCashFamilleLot, Marque, LibLot, "
            "Catégorie, Montant, Stock, SurCommande, EnSolde, MontantSolde "
            "FROM ExoCashLot WHERE IDExoCashLot IN ("
            + ",".join(str(i) for i in ids) + ")"
        )
        for r in rows or []:
            print(" ", r)
    except Exception as e:
        print("ERR:", repr(e))

    print("\n=== Test _panier_lignes (fonction complète) ===")
    try:
        from app.shared.tickets.forms import cdeexocash as _mod

        print("  module file :", _mod.__file__)
        print("  has CATEG_POUR :", hasattr(_mod, "CATEG_POUR"),
              getattr(_mod, "CATEG_POUR", None))
        lignes = _mod._panier_lignes(int(id_ticket))
        for ln in lignes:
            print(" ", ln)
    except Exception as e:
        import traceback

        print("ERR _panier_lignes:", repr(e))
        traceback.print_exc()

    # Sanity check : appel direct de _lots_catalogue avec l'ID trouvé
    print("\n=== Test _lots_catalogue direct ===")
    try:
        cat = _mod._lots_catalogue(set(ids))
        print("  retour :", cat)
    except Exception as e:
        import traceback
        print("ERR _lots_catalogue:", repr(e))
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diag_cdeexocash.py <IDTK_Liste>")
        sys.exit(1)
    main(int(sys.argv[1]))
