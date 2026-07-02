"""Helper commun : lookup d'un contrat par num_bs (transposition de la
procedure WinDev RequeteNumContrat).

WinDev fait un simple :
    SELECT * FROM {part}_contrat
    WHERE NumBS = '{num_bs}' AND ModifElem <> 'suppr'

En Python/PG on ajoute :
- UPPER(num_bs) = UPPER(?) : PG est case-sensitive par defaut
- modif_elem IS NULL OR NOT LIKE '%suppr%' : PG peut renvoyer NULL
- LIMIT 1 (pour la variante single) : explicite

Deux variantes :
- lookup_contrat_by_num_bs : 1 ligne (equivalent HLitPremier)
- find_contrats_by_num_bs   : liste (pour detecter doublons HNbEnr>1)
"""

from typing import Any

from app.core.database.pg import get_pg_connection

# Colonnes standard cf. WinDev RequeteNumContrat
_STANDARD_COLS = (
    "id_contrat, id_client, id_salarie, num_bs, id_produit, "
    "date_signature, id_ste, id_etat_contrat"
)


def _table_for(partenaire: str) -> str:
    """SFR -> adv.pgt_sfr_contrat, ENI -> adv.pgt_eni_contrat, etc."""
    return f"adv.pgt_{partenaire.lower()}_contrat"


def lookup_contrat_by_num_bs(
    partenaire: str,
    num_bs: str,
    extra_cols: str = "",
) -> dict[str, Any] | None:
    """Renvoie la 1ere ligne matching (cf. WinDev HLitPremier).

    Args:
        partenaire: 'SFR', 'ENI', 'OEN', 'IAG', 'PRO', 'STR', 'VAL'...
        num_bs: numero de contrat (compare en case-insensitive)
        extra_cols: colonnes supplementaires ex 'id_etat_sfr, box8, remise'

    Returns:
        dict avec les colonnes standard + extra_cols, ou None si absent.
    """
    if not num_bs:
        return None
    cols = _STANDARD_COLS
    if extra_cols:
        cols = f"{cols}, {extra_cols}"
    db = get_pg_connection("adv")
    return db.query_one(
        f"""SELECT {cols}
             FROM {_table_for(partenaire)}
            WHERE UPPER(num_bs) = UPPER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (num_bs,),
    )


def find_contrats_by_num_bs(
    partenaire: str,
    num_bs: str,
    extra_cols: str = "",
) -> list[dict[str, Any]]:
    """Renvoie toutes les lignes matching (pour detecter doublons
    HNbEnr>1 de WinDev). Utiliser pour ImportResil / ImportRun quand
    on distingue 0 / 1 / >1 resultats."""
    if not num_bs:
        return []
    cols = _STANDARD_COLS
    if extra_cols:
        cols = f"{cols}, {extra_cols}"
    db = get_pg_connection("adv")
    return db.query(
        f"""SELECT {cols}
             FROM {_table_for(partenaire)}
            WHERE UPPER(num_bs) = UPPER(?)
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (num_bs,),
    ) or []
