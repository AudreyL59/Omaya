"""Exploration TK_DemandeCttCourtage : voir si des lignes existent
et quel format de clé est utilisé.

Usage : .\\venv\\Scripts\\python.exe scripts\\diag_cttcourtage2.py [IDTK_Liste optionnel]
"""

import sys

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_ticket=None):
    db = get_connection("ticket")

    print("=== Total lignes TK_DemandeCttCourtage ===")
    try:
        r = db.query_one("SELECT COUNT(*) AS n FROM TK_DemandeCttCourtage")
        print(r)
    except Exception as e:
        print("ERR:", repr(e))

    print("\n=== 5 lignes les plus récentes ===")
    try:
        rows = db.query(
            "SELECT TOP 5 IDdemandeContratWAuto, IDdemandeContratW, "
            "IDTK_Liste, IDSalarie, idDistrib "
            "FROM TK_DemandeCttCourtage "
            "ORDER BY IDdemandeContratWAuto DESC"
        )
        for r in rows or []:
            print(" ", r)
    except Exception as e:
        print("ERR:", repr(e))

    if id_ticket:
        print(f"\n=== Recherches sur IDTK_Liste = {id_ticket} (types) ===")
        for sql, params, label in [
            ("SELECT IDTK_Liste FROM TK_DemandeCttCourtage "
             "WHERE IDTK_Liste = ?", (int(id_ticket),), "int param"),
            ("SELECT IDTK_Liste FROM TK_DemandeCttCourtage "
             "WHERE IDTK_Liste = ?", (str(id_ticket),), "str param"),
            (f"SELECT IDTK_Liste FROM TK_DemandeCttCourtage "
             f"WHERE IDTK_Liste = {int(id_ticket)}", None, "inline int"),
            (f"SELECT IDTK_Liste FROM TK_DemandeCttCourtage "
             f"WHERE IDdemandeContratW = {int(id_ticket)}",
             None, "via IDdemandeContratW"),
        ]:
            try:
                r = db.query_one(sql, params) if params else db.query_one(sql)
                print(f"  [{label}] -> {r}")
            except Exception as e:
                print(f"  [{label}] ERR: {repr(e)[:120]}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
