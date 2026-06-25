"""
SDTC - btn 'Valider la sélection et passer à l'étape suivante'.

Transposition fidèle :
1. Agrège les contrats sélectionnés (TableContrat + TableContrat1) en
   TableProduitSTC (par nom produit normalisé HACHETTE).
   - ENI : ELEC -> Valeur += 8 / GAZ -> Nb_Pts += pts
   - Autres : Nb_Pts += pts
2. Cas spécial SFR : si Col_IdTypeEtat = 8 (Raccordé/Activé) dans
   TableContrat1 -> UPDATE id_etat_contrat = 6 (Payé Raccordement),
   MAJ MoisP_Ra + nb_pts_payes_ra, ajout d'historique d'état.
3. Calcule barème global (5/20/25/30/35), commission.

Retourne {produits, nb_tot_pts, nb_tot_ctts, total_valeurs, bareme,
comm_pts_ctts, comm_tot_stc, sfr_promus} avec sfr_promus = liste des
contrats SFR auto-validés.
"""

from __future__ import annotations

from app.core.database.pg import get_pg_connection

from .bareme import BaremeResult, ProduitSTC, palier_remun
from .helpers import _int, _num, _str, normalize_nom_produit
from .histo import ajoute_histo_contrat


# Etats spéciaux (cf. WinDev)
_SFR_RACCORDE_ACTIVE = 8  # Col_IdTypeEtat
_ETAT_PAYE_RACCORDEMENT = 6
_LIB_VALIDE_PAYE = "Validé-Payé"
_LIB_PAYE_RACCORDEMENT = "Payé par employeur - Raccordement"


def valider_selection(
    *,
    contrats_traites: list[dict],
    contrats_a_traiter: list[dict],
    selected_ids_traites: set[str],
    selected_ids_a_traiter: set[str],
    mois_p_sdtc: str,
    op_id: int,
) -> dict:
    """Btn 'Valider la sélection et passer à l'étape suivante'.

    Args:
        contrats_traites: contrats de TableContrat (deja finalises)
        contrats_a_traiter: contrats de TableContrat1 (en cours)
        selected_ids_traites: ids selectionnes dans TableContrat
        selected_ids_a_traiter: ids selectionnes dans TableContrat1
        mois_p_sdtc: mois de paiement (YYYY-MM) à appliquer aux contrats
                     SFR auto-validés (cf. WinDev MoisP_SDTC)
        op_id: id_salarie de l'opérateur courant (usersCial)
    """
    produits_by_nom: dict[str, ProduitSTC] = {}
    sfr_promus: list[dict] = []

    # 1. TableContrat (contrats déjà finalisés cochés)
    for ct in contrats_traites:
        if str(ct.get("id_contrat")) not in selected_ids_traites:
            continue
        _agrege_in_produits(ct, produits_by_nom)

    # 2. TableContrat1 (contrats en cours cochés)
    for ct in contrats_a_traiter:
        if str(ct.get("id_contrat")) not in selected_ids_a_traiter:
            continue
        _agrege_in_produits(ct, produits_by_nom)

        # Cas spécial SFR Col_IdTypeEtat = 8 -> auto-validation
        partenaire = _str(ct.get("partenaire")).upper()
        if partenaire != "SFR":
            continue
        id_type_etat = _int(ct.get("id_type_etat"))
        if id_type_etat != _SFR_RACCORDE_ACTIVE:
            continue
        promu = _promote_sfr_to_paye_raccordement(
            ct, mois_p_sdtc=mois_p_sdtc, op_id=op_id
        )
        if promu:
            sfr_promus.append(promu)

    # 3. Calcul barème global
    produits = list(produits_by_nom.values())
    nb_tot_pts = sum(p.nb_pts for p in produits)
    nb_tot_ctts = sum(p.qte for p in produits)
    total_valeurs = sum(p.valeur for p in produits)

    bareme = palier_remun(nb_tot_pts)
    comm_pts_ctts = nb_tot_pts * bareme
    comm_tot_stc = comm_pts_ctts + total_valeurs

    result = BaremeResult(
        produits=produits,
        nb_tot_pts=nb_tot_pts,
        nb_tot_ctts=nb_tot_ctts,
        total_valeurs=total_valeurs,
        bareme=bareme,
        comm_pts_ctts=comm_pts_ctts,
        comm_tot_stc=comm_tot_stc,
    )
    return {
        **result.to_dict(),
        "sfr_promus": sfr_promus,
    }


def _agrege_in_produits(ct: dict, dst: dict[str, ProduitSTC]) -> None:
    """Agrégation fidèle WinDev dans TableProduitSTC."""
    nom = normalize_nom_produit(_str(ct.get("lib_produit")))
    if not nom:
        return
    p = dst.get(nom)
    if p is None:
        p = ProduitSTC(lib_produit=nom)
        dst[nom] = p

    p.qte += 1

    partenaire = _str(ct.get("partenaire")).upper()
    type_prod = _str(ct.get("type_prod")).upper()
    pts_ctt = _num(ct.get("nb_points"))

    if "ENI" in partenaire:
        if "ELEC" in type_prod:
            p.valeur += 8
        if "GAZ" in type_prod:
            p.nb_pts += pts_ctt
    else:
        p.nb_pts += pts_ctt


def _promote_sfr_to_paye_raccordement(
    ct: dict, *, mois_p_sdtc: str, op_id: int
) -> dict | None:
    """Promote un contrat SFR Col_IdTypeEtat = 8 (Raccordé/Activé) en
    état 6 (Payé par employeur - Raccordement) :

      UPDATE adv.pgt_sfr_contrat
         SET id_etat_contrat = 6,
             mois_p_ra = ?::date,
             nb_pts_payes_ra = ?,
             modif_date = NOW(),
             modif_op = ?
       WHERE id_contrat = ?

    + ajoute_histo_contrat('SFR', id, etat_old, etat_new, mois, 'Vend').
    """
    id_contrat = _int(ct.get("id_contrat"))
    if not id_contrat:
        return None
    nb_points = _num(ct.get("nb_points"))
    etat_old = _int(ct.get("id_etat_contrat"))

    # Format mois_p : YYYY-MM-01 (1er du mois)
    mois_p_date = (
        f"{mois_p_sdtc[:7]}-01"
        if (mois_p_sdtc and len(mois_p_sdtc) >= 7 and mois_p_sdtc[4] == "-")
        else None
    )

    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_sfr_contrat
              SET id_etat_contrat = ?,
                  mois_p_ra = ?::date,
                  nb_pts_payes_ra = ?,
                  modif_date = NOW(),
                  modif_op = ?
            WHERE id_contrat = ?""",
        (_ETAT_PAYE_RACCORDEMENT, mois_p_date, nb_points, int(op_id), id_contrat),
    )

    # Historique d'état (Vend = vendeur)
    try:
        ajoute_histo_contrat(
            part="SFR",
            id_contrat=id_contrat,
            etat_old=etat_old,
            etat_new=_ETAT_PAYE_RACCORDEMENT,
            mois_p=(mois_p_sdtc[:7] if mois_p_sdtc else ""),
            op_id=op_id,
            type_="Vend",
        )
    except Exception:
        # Historique non bloquant
        pass

    return {
        "id_contrat": str(id_contrat),
        "ancien_etat": etat_old,
        "nouvel_etat": _ETAT_PAYE_RACCORDEMENT,
        "lib_type_etat": _LIB_VALIDE_PAYE,
        "lib_etat": _LIB_PAYE_RACCORDEMENT,
        "mois_paiement": mois_p_sdtc[:7] if mois_p_sdtc else "",
        "nb_points": nb_points,
    }
