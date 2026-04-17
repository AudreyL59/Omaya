"""
Transposition de InitDroit() — chargement des droits d'accès d'un salarié.

Requête source WinDev : ReqDroitAccèsOmayaVendActifByIdsalarié
Tables : salarie_droitAccès + TypeDroitAccès (Bdd_Omaya_RH)
"""

from app.core.database import HFSQLConnection


def charger_droits(db: HFSQLConnection, id_salarie: int) -> list[str]:
    """
    Charge la liste des codes de droits actifs pour un salarié.

    Retourne une liste de CodeInterne (ex: ["IntraADM", "IntraCallRH", ...]).
    Equivalent de InitDroit() en WinDev.
    """
    rows = db.query(
        """
        SELECT TypeDroitAccès.CodeInterne
        FROM TypeDroitAccès
        INNER JOIN salarie_droitAccès
            ON TypeDroitAccès.IDTypeDroitAccès = salarie_droitAccès.IDTypeDroitAccès
        WHERE salarie_droitAccès.DroitActif = 1
            AND salarie_droitAccès.ModifELEM NOT LIKE '%suppr%'
            AND salarie_droitAccès.IDSalarie = ?
            AND TypeDroitAccès.FDV = 1
        """,
        (id_salarie,),
    )
    return [row["CodeInterne"] for row in rows]
