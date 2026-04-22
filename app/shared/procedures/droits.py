"""
Transposition de InitDroit() — chargement des droits d'accès d'un salarié.

Requête source WinDev : ReqDroitAccèsOmayaVendActifByIdsalarié (+ variantes par intranet)
Tables : salarie_droitAccès + TypeDroitAccès (Bdd_Omaya_RH)
"""

from app.core.database import HFSQLConnection


def charger_droits(
    db: HFSQLConnection,
    id_salarie: int,
    intranet: str = "vendeur",
) -> list[str]:
    """
    Charge la liste des codes de droits actifs pour un salarié.

    Selon l'intranet depuis lequel l'utilisateur se connecte, on applique
    un filtre différent sur TypeDroitAccès :
      - vendeur : FDV = 1 (uniquement les droits du périmètre Vendeur)
      - adm     : aucun filtre → tous les droits du salarié
      - autres  : FDV = 1 par défaut (à affiner quand on branchera chaque intranet)

    Retourne une liste de CodeInterne (ex: ["IntraADM", "StatsRHGr", ...]).
    """
    base_sql = """
        SELECT TypeDroitAccès.CodeInterne
        FROM TypeDroitAccès
        INNER JOIN salarie_droitAccès
            ON TypeDroitAccès.IDTypeDroitAccès = salarie_droitAccès.IDTypeDroitAccès
        WHERE salarie_droitAccès.DroitActif = 1
            AND salarie_droitAccès.ModifELEM NOT LIKE '%suppr%'
            AND salarie_droitAccès.IDSalarie = ?
    """

    if intranet == "adm":
        sql = base_sql  # pas de filtre : on veut tout
    else:
        sql = base_sql + " AND TypeDroitAccès.FDV = 1"

    rows = db.query(sql, (id_salarie,))
    return [row["CodeInterne"] for row in rows]
