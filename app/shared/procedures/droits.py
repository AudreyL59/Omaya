"""
Transposition de InitDroit() — chargement des droits d'accès d'un salarié.

Requête source WinDev : ReqDroitAccèsOmayaVendActifByIdsalarié (+ variantes par intranet)
Tables : pgt_salarie_droit_acces + pgt_type_droit_acces (schema rh).
"""

from app.core.database.pg import PGConnection


def charger_droits(
    db: PGConnection,
    id_salarie: int,
    intranet: str = "vendeur",
) -> list[str]:
    """
    Charge la liste des codes de droits actifs pour un salarié.

    Selon l'intranet depuis lequel l'utilisateur se connecte, on applique
    un filtre différent sur pgt_type_droit_acces :
      - vendeur : fdv = TRUE (uniquement les droits du périmètre Vendeur)
      - adm     : aucun filtre → tous les droits du salarié
      - autres  : fdv = TRUE par défaut (à affiner quand on branchera chaque intranet)

    Retourne une liste de code_interne (ex: ["IntraADM", "StatsRHGr", ...]).
    """
    base_sql = """
        SELECT t.code_interne
        FROM pgt_type_droit_acces t
        INNER JOIN pgt_salarie_droit_acces sd
            ON t.id_type_droit_acces = sd.id_type_droit_acces
        WHERE sd.droit_actif = TRUE
            AND sd.modif_elem NOT LIKE '%suppr%'
            AND sd.id_salarie = ?
    """

    if intranet == "adm":
        sql = base_sql  # pas de filtre : on veut tout
    else:
        sql = base_sql + " AND t.fdv = TRUE"

    rows = db.query(sql, (id_salarie,))
    return [row["code_interne"] for row in rows]


def charger_droits_hfsql(db, id_salarie: int, intranet: str = "vendeur") -> list[str]:
    """Variante HFSQL de charger_droits (intranets servis en HFSQL, ex.
    intracall Fibre/Energie). Tables : salarie_droitAccès + TypeDroitAccès
    (Bdd_Omaya_RH). Mêmes règles de filtre que la version PG.
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
        sql = base_sql
    else:
        sql = base_sql + " AND TypeDroitAccès.FDV = 1"

    rows = db.query(sql, (id_salarie,))
    return [row["CodeInterne"] for row in rows]
