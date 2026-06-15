"""
Transposition de la procedure globale `ajouteHistoContrat(Part, idcontrat,
EtatOld, EtatNew, MoisP, Type='')` WinDev.

Insere une ligne d'historique d'etat dans la bonne table par partenaire :
  - ENI / IAG / TLC / VAL / STR : pgt_<part>_histo_etat_ctt
  - SFR : pgt_sfr_histo_etat_ctt (Type='Vend') ou pgt_sfr_histo_etat_ctt_sfr (autre)
  - OEN : pgt_oen_histo_etat_ctt (Type='Vend') ou pgt_oen_histo_etat_ctt_oen (autre)

Toutes les tables partagent la meme structure (id_histo_auto + id_histo +
id_contrat + op_saisie + date + old_etat + new_etat + date_paiement +
ModifOP + ModifDate + ModifElem).
"""

from __future__ import annotations

from app.core.database.pg import get_pg_connection

from .helpers import _int, new_id


# Partenaires gerees + variantes selon Type
# Cle = (partenaire_majuscule, type_majuscule)
# Valeur = nom_table (suffixe apres pgt_)
_TABLE_BY_PART_TYPE: dict[tuple[str, str], str] = {
    # ENI / IAG / TLC / VAL / STR : 1 seule table
    ("ENI", ""): "eni_histo_etat_ctt",
    ("IAG", ""): "iag_histo_etat_ctt",
    ("TLC", ""): "tlc_histo_etat_ctt",
    ("VAL", ""): "val_histo_etat_ctt",
    ("STR", ""): "str_histo_etat_ctt",
    # SFR : 2 tables selon Type
    ("SFR", "VEND"): "sfr_histo_etat_ctt",
    ("SFR", ""): "sfr_histo_etat_ctt_sfr",
    # OEN : 2 tables selon Type
    ("OEN", "VEND"): "oen_histo_etat_ctt",
    ("OEN", ""): "oen_histo_etat_ctt_oen",
}


def ajoute_histo_contrat(
    part: str,
    id_contrat: int | str,
    etat_old: int,
    etat_new: int,
    mois_p: str,
    op_id: int,
    type_: str = "",
) -> dict:
    """Insert d'historique d'etat dans la bonne table par partenaire.

    Args:
        part: partenaire (ENI/IAG/TLC/VAL/STR/SFR/OEN)
        id_contrat: contrat concerne
        etat_old: ancien id_etat
        etat_new: nouvel id_etat
        mois_p: mois de paiement format 'YYYYMM' ou 'YYYY-MM' (varchar(7))
        op_id: id_salarie de l'operateur (usersCial)
        type_: '' (defaut) ou 'Vend' (SFR/OEN seulement)

    Retourne {ok, table, id_histo}.
    """
    part_up = (part or "").upper().strip()
    type_up = (type_ or "").upper().strip()

    # SFR/OEN : si Type non-Vend (ou autre) -> table _sfr/_oen
    if part_up in ("SFR", "OEN"):
        key = (part_up, "VEND") if type_up == "VEND" else (part_up, "")
    else:
        key = (part_up, "")

    suffix = _TABLE_BY_PART_TYPE.get(key)
    if suffix is None:
        # Partenaire inconnu : on ignore silencieusement (cf. WinDev :
        # le selon ne gere que les partenaires connus).
        return {"ok": False, "error": f"Partenaire non gere : {part_up}"}

    table = f"adv.pgt_{suffix}"
    id_histo = new_id()

    db = get_pg_connection("adv")
    db.execute(
        f"""INSERT INTO {table}
              (id_histo_auto, id_histo, id_contrat, op_saisie,
               date, old_etat, new_etat, date_paiement,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?,
                   NOW(), ?, ?, ?,
                   ?, NOW(), 'new')""",
        (
            id_histo, id_histo,
            _int(id_contrat), _int(op_id),
            _int(etat_old), _int(etat_new), str(mois_p or "")[:7],
            _int(op_id),
        ),
    )
    return {"ok": True, "table": table, "id_histo": str(id_histo)}
