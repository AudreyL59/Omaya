"""Diagnostic du format de la rubrique HFSQL 'Heure' (TK_DemandeResa).

Usage (SUR LE SERVEUR, venv) :
    .\\venv\\Scripts\\python.exe scripts\\diag_resa_heure.py <IDTK_Liste>
"""

import sys

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_ticket: int):
    db = get_connection("ticket_bo")
    r = db.query_one(
        """SELECT IDTK_Liste, Jour_Dep, Heure_Dep, Heure_Arr,
            JourR_Dep, HeureR_Dep, HeureR_Arr
        FROM TK_DemandeResa WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        print("Aucune réservation pour", id_ticket)
        return
    for k, v in r.items():
        print(f"{k!r:20} type={type(v).__name__:8} repr={v!r}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diag_resa_heure.py <IDTK_Liste>")
        sys.exit(1)
    main(int(sys.argv[1]))
