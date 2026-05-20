"""Diag FI_CttCourtage : vérifie les données du ticket pour identifier
pourquoi le formulaire ne s'affiche pas.

Usage (SUR LE SERVEUR, venv) :
    .\\venv\\Scripts\\python.exe scripts\\diag_cttcourtage.py <IDTK_Liste>
"""

import sys

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_ticket: int):
    tk = get_connection("ticket").query_one(
        "SELECT IDTK_Liste, IDTK_TypeDemande, IDTK_Statut, Cloturée "
        "FROM TK_Liste WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    print("=== TK_Liste ===")
    print(tk)

    print("\n=== TK_DemandeCttCourtage (multi-col) ===")
    try:
        r = get_connection("ticket").query_one(
            """SELECT IDTK_Liste, IDdemandeContratW, IDSalarie, idDistrib,
                IDsociete_docCourtage, contratGénéré, contratValidé,
                contratSigné, contratAnnul, datesignature, TitreContrat
            FROM TK_DemandeCttCourtage WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        print(r)
    except Exception as e:
        print("ERR multi-col:", repr(e))

    print("\n=== TK_DemandeCttCourtage (clé seule) ===")
    try:
        r = get_connection("ticket").query_one(
            "SELECT IDTK_Liste FROM TK_DemandeCttCourtage "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        print(r)
    except Exception as e:
        print("ERR key-only:", repr(e))

    print("\n=== handler résolu ===")
    try:
        from app.shared.tickets.forms import FORM_HANDLERS

        id_type = (tk or {}).get("IDTK_TypeDemande")
        print("id_type =", id_type, " handler =", FORM_HANDLERS.get(id_type))
    except Exception as e:
        print("ERR handlers:", repr(e))

    print("\n=== load() ===")
    try:
        from app.shared.tickets.forms.cttcourtage import load

        out = load(int(id_ticket))
        # raccourcir si trop long
        for k, v in (out or {}).items():
            s = str(v)
            print(f"  {k}: {s[:200]}")
    except Exception as e:
        import traceback

        print("ERR load:", repr(e))
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diag_cttcourtage.py <IDTK_Liste>")
        sys.exit(1)
    main(int(sys.argv[1]))
