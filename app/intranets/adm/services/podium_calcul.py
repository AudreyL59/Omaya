"""
Proc globale WinDev Podium_Calcul.

Recalcule le podium a une date donnee : pour chaque PodiumTypePart
actif, lit la production correspondante (contrats des partenaires ou
CV cooptes) et remplit divers.pgt_podium_vendeur + pgt_podium_vendeur_part.

Cf. WinDev D:\\Claude\\WinDev\\Proc Globales\\Podium_Calcul.txt (~238 lignes).

Utilise par le Btn 'Calcul Podium' de Fen_GestionPodium (boucle sur
[du, au+7j] par pas de +1 mois).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.podium import (
    CalculPodiumParams, CalculPodiumResult,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _last_day_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def _sub_months_safe(d: date, n: int) -> date:
    """Retire n mois, clamp jour au max du mois cible."""
    y = d.year
    m = d.month - n
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    max_day = _last_day_of_month(y, m).day
    return date(y, m, min(d.day, max_day))


def _liste_orga_complet_ids(id_racine: int) -> set[int]:
    """Recupere recursivement tous les idorganigramme descendants."""
    rh = get_pg_connection("rh")
    result: set[int] = {int(id_racine)}
    to_process = [int(id_racine)]
    while to_process:
        parents = tuple(to_process)
        to_process = []
        try:
            placeholders = ",".join(["?"] * len(parents))
            rows = rh.query(
                f"""SELECT idorganigramme FROM pgt_organigramme
                     WHERE id_parent IN ({placeholders})
                       AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                parents,
            ) or []
        except Exception:
            break
        for r in rows:
            oid = int(r.get("idorganigramme") or 0)
            if oid and oid not in result:
                result.add(oid)
                to_process.append(oid)
    return result


def _load_type_etats() -> dict[int, int]:
    """Cache : id_etat -> id_type_etat pour les etats de contrat.
    Chaque partenaire a sa table {prefixe}_etat_contrat.

    Retourne {} car appele en boucle avec des prefixes differents ; on
    fera un lookup dynamique dans la fonction principale.
    """
    return {}


def _equipe_terrain(id_salarie: int, date_ref: date) -> tuple[int, int]:
    """Retourne (idorganigramme, id_type_niveau_orga) pour le
    salarie a la date donnee.
    """
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT o.idorganigramme, o.id_type_niveau_orga,
                      o.id_type_orga
                 FROM pgt_salarie_organigramme so
                 JOIN pgt_organigramme o
                      ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND (so.modif_elem IS NULL
                       OR so.modif_elem NOT LIKE '%suppr%')
                  AND (so.date_debut IS NULL OR so.date_debut <= ?)
                  AND (so.date_fin IS NULL OR so.date_fin >= ?)
                ORDER BY so.date_debut DESC NULLS LAST
                LIMIT 1""",
            (id_salarie, date_ref.isoformat(), date_ref.isoformat()),
        )
    except Exception:
        return (0, 0)
    if not r:
        return (0, 0)
    return (
        int(r.get("idorganigramme") or 0),
        int(r.get("id_type_orga") or 0),
    )


def _salarie_actif(id_salarie: int) -> bool:
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT en_activite FROM pgt_salarie_embauche
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date_debut DESC NULLS LAST
                LIMIT 1""",
            (id_salarie,),
        )
    except Exception:
        return False
    return bool(r and r.get("en_activite"))


# --------------------------------------------------------------------
# Podium_Calcul (proc principale)
# --------------------------------------------------------------------

def _calcul_pour_date(date_ref: date, op_id: int) -> int:
    """Recalcul du podium pour une date de reference.
    Retourne le nombre de PodiumTypePart traites.
    """
    rh = get_pg_connection("rh")

    # Distributeurs (racines 4 et 14, cf. WinDev)
    orga_distribs: set[int] = set()
    for racine in (4, 14):
        orga_distribs |= _liste_orga_complet_ids(racine)

    # Liste toutes les config PodiumTypePart actives + leur PodiumType
    configs = rh.query(
        """SELECT ptp.id_podium_type_part, ptp.id_podium_type,
                  ptp.famille, ptp.sous_fam, ptp.prefixe_bdd,
                  ptp.type_prod, ptp.option_vente,
                  ptp.jour_cial_deb, ptp.jour_cial_fin,
                  pt.is_actif, pt.qualite
             FROM divers.pgt_podium_type_part ptp
             JOIN divers.pgt_podium_type pt
                  ON pt.id_podium_type = ptp.id_podium_type
            WHERE (ptp.modif_elem IS NULL
                   OR ptp.modif_elem NOT LIKE '%suppr%')
              AND pt.is_actif = TRUE
              AND (pt.modif_elem IS NULL
                   OR pt.modif_elem NOT LIKE '%suppr%')""",
    ) or []

    nb_traite = 0
    for cfg in configs:
        id_ptp = int(cfg.get("id_podium_type_part") or 0)
        id_pt = int(cfg.get("id_podium_type") or 0)
        prefixe = (cfg.get("prefixe_bdd") or "").strip()
        famille = (cfg.get("famille") or "Tous").strip()
        sous_fam = (cfg.get("sous_fam") or "Tous").strip()
        option_vente = (cfg.get("option_vente") or "").strip()
        j_deb = int(cfg.get("jour_cial_deb") or 1)
        j_fin = int(cfg.get("jour_cial_fin") or 31)
        is_qualite = bool(cfg.get("qualite"))

        # Calcul dateDeb / dateFin
        try:
            date_deb = date(
                date_ref.year, date_ref.month,
                min(j_deb, _last_day_of_month(date_ref.year, date_ref.month).day),
            )
            date_fin = date(
                date_ref.year, date_ref.month,
                min(j_fin, _last_day_of_month(date_ref.year, date_ref.month).day),
            )
        except Exception:
            continue
        if j_deb > 1:
            date_deb = _sub_months_safe(date_deb, 1)
        if is_qualite:
            date_deb = _sub_months_safe(date_deb, 2)
        # Clamp min du WinDev : 2024-01-01
        if date_deb < date(2024, 1, 1):
            date_deb = date(2024, 1, 1)

        # Recupere les contrats du prefixe correspondant
        prods = _load_prod_for_config(
            prefixe, famille, sous_fam, option_vente,
            date_deb, date_fin,
        )
        if not prods:
            continue

        # Aggregation par (id_salarie, id_equipe, date_prod, prefixe)
        agg: dict[tuple, dict] = {}
        for prod in prods:
            id_sal = int(prod.get("id_salarie") or 0)
            if not id_sal:
                continue
            if not _salarie_actif(id_sal):
                continue
            date_prod = prod.get("date_prod")
            if not date_prod:
                continue
            date_prod_d = (
                date_prod if isinstance(date_prod, date)
                else date.fromisoformat(str(date_prod)[:10])
            )
            id_eq, id_type_orga = _equipe_terrain(id_sal, date_prod_d)
            is_distrib = (
                id_type_orga == 3
                or id_eq in orga_distribs
            )
            key = (id_sal, id_ptp, date_prod_d.isoformat(), prefixe, id_eq)
            if key not in agg:
                agg[key] = {
                    "id_salarie": id_sal,
                    "id_equipe": id_eq,
                    "date_prod": date_prod_d,
                    "prefixe": prefixe,
                    "is_distrib": is_distrib,
                    "nb_brut": 0,
                    "nb_hors_rejet": 0,
                    "nb_paye": 0,
                }
            v = agg[key]
            v["nb_brut"] += 1
            id_type_etat = int(prod.get("id_type_etat") or 0)
            id_etat = int(prod.get("id_etat") or 0)
            # Regle horsRejet (cf. WinDev)
            if prefixe == "Coopt":
                # Cooptation : check dernier statut CV != 7
                if not _cv_rejete(int(prod.get("id_cvtheque") or 0)):
                    v["nb_hors_rejet"] += 1
            else:
                if id_type_etat != 3:
                    v["nb_hors_rejet"] += 1
                # Cas special SFR : Rejet BO - DEPOT DE GARANTIE = horsRejet
                if (id_type_etat == 3 and prefixe == "SFR"
                        and id_etat == 73):
                    v["nb_hors_rejet"] += 1
                if id_type_etat == 5 or id_type_etat == 8:
                    v["nb_paye"] += 1

        # MAJ divers.pgt_podium_vendeur + pgt_podium_vendeur_part
        for v in agg.values():
            _mise_a_jour_podium(id_pt, id_ptp, prefixe, v, op_id)
        nb_traite += 1

    return nb_traite


def _cv_rejete(id_cvtheque: int) -> bool:
    """Retourne True si le dernier statut CV est 7 (rejete)."""
    if not id_cvtheque:
        return False
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT id_cv_statut FROM recrutement.pgt_cv_statut_histo
                WHERE id_cvtheque = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date_statut DESC NULLS LAST
                LIMIT 1""",
            (id_cvtheque,),
        )
    except Exception:
        return False
    return bool(r and int(r.get("id_cv_statut") or 0) == 7)


def _load_prod_for_config(
    prefixe: str, famille: str, sous_fam: str, option_vente: str,
    date_deb: date, date_fin: date,
) -> list[dict]:
    """Charge les 'productions' selon le PréfixeBDD.

    - 'Coopt' : cvtheque (schema recrutement)
    - Autres : {prefixe_bdd}_contrat / _produit / _etat_contrat (schema adv)

    Retourne des lignes normalisees :
    {id_salarie, date_prod, id_type_etat, id_etat, [id_cvtheque]}
    """
    if not prefixe:
        return []

    if prefixe == "Coopt":
        rh = get_pg_connection("rh")
        try:
            rows = rh.query(
                """SELECT idcvtheque AS id_cvtheque,
                          id_element_source AS id_salarie,
                          date_saisie AS date_prod
                     FROM recrutement.pgt_cvtheque
                    WHERE (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                      AND id_cv_source = 1
                      AND date_saisie::date BETWEEN ? AND ?""",
                (date_deb.isoformat(), date_fin.isoformat()),
            ) or []
        except Exception:
            logger.exception("_load_prod Coopt")
            return []
        result = []
        for r in rows:
            result.append({
                "id_cvtheque": r.get("id_cvtheque"),
                "id_salarie": r.get("id_salarie"),
                "date_prod": r.get("date_prod"),
                "id_type_etat": 0,
                "id_etat": 0,
            })
        return result

    # Autres partenaires : contrats
    schema = "adv"
    prefixe_lower = prefixe.lower()
    tbl_ctt = f"pgt_{prefixe_lower}_contrat"
    tbl_prod = f"pgt_{prefixe_lower}_produit"
    tbl_etat = f"pgt_{prefixe_lower}_etat_contrat"

    where_option = ""
    if famille and famille.lower() != "tous":
        where_option += f" AND prod.famille = '{famille}'"
    if sous_fam and sous_fam.lower() != "tous":
        where_option += f" AND prod.sous_fam = '{sous_fam}'"
    if option_vente:
        has_cq = "CQ-" in option_vente
        has_mig = "MIG-" in option_vente
        if has_cq and not has_mig:
            where_option += " AND ct.type_vente <= 2"
        elif has_mig and not has_cq:
            where_option += " AND ct.type_vente > 2"
        # (les deux ou aucun : pas de filtre)

    sql = f"""
        SELECT DISTINCT ct.id_contrat, ct.num_bs,
               ct.id_salarie,
               ct.date_signature AS date_prod,
               et.id_type_etat, et.id_etat
          FROM {schema}.{tbl_ctt} ct
          JOIN {schema}.{tbl_prod} prod ON prod.id_produit = ct.id_produit
          JOIN {schema}.{tbl_etat} et ON et.id_etat = ct.id_etat_contrat
         WHERE ct.num_bs NOT LIKE 'TK%'
           AND (ct.modif_elem IS NULL
                OR ct.modif_elem NOT LIKE '%suppr%')
           AND ct.date_signature::date BETWEEN ? AND ?
           {where_option}"""

    rh = get_pg_connection("rh")
    try:
        rows = rh.query(sql, (date_deb.isoformat(), date_fin.isoformat())) or []
    except Exception:
        logger.exception("_load_prod prefixe=%s", prefixe)
        return []
    return list(rows)


def _mise_a_jour_podium(
    id_pt: int, id_ptp: int, prefixe: str, v: dict, op_id: int,
) -> None:
    """Cf. WinDev MiseàJourPodium.

    - Cherche ou cree une ligne divers.pgt_podium_vendeur pour
      (id_salarie, id_podium_type, date_jour, distributeur, id_equipe)
    - Puis met a jour divers.pgt_podium_vendeur_part pour id_podium_type_part
      avec les compteurs nb_brut / nb_hors_rejet / nb_paye.
    """
    db = get_pg_connection("rh")
    id_sal = int(v["id_salarie"])
    id_eq = int(v["id_equipe"])
    date_prod = v["date_prod"]
    is_distrib = bool(v["is_distrib"])

    # Cherche PodiumVendeur existant
    try:
        r = db.query_one(
            """SELECT id_podium_vendeur FROM divers.pgt_podium_vendeur
                WHERE id_salarie = ? AND id_podium_type = ?
                  AND date_jour = ? AND distributeur = ?
                  AND id_equipe = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_sal, id_pt, date_prod.isoformat(), is_distrib, id_eq),
        )
    except Exception:
        return

    if r:
        id_pv = int(r.get("id_podium_vendeur") or 0)
    else:
        try:
            r2 = db.query_one(
                """INSERT INTO divers.pgt_podium_vendeur
                      (id_podium_type, date_jour, id_salarie, id_equipe,
                       distributeur, modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, NOW(), ?, 'new')
                   RETURNING id_podium_vendeur""",
                (id_pt, date_prod.isoformat(), id_sal, id_eq,
                 is_distrib, int(op_id)),
            )
            id_pv = int(r2.get("id_podium_vendeur") or 0) if r2 else 0
        except Exception:
            logger.exception("insert PodiumVendeur")
            return

    if not id_pv:
        return

    # Cherche PodiumVendeurPart pour (id_pv, id_ptp)
    try:
        rp = db.query_one(
            """SELECT id_podium_vendeur_part
                 FROM divers.pgt_podium_vendeur_part
                WHERE id_podium_vendeur = ? AND id_podium_type_part = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_pv, id_ptp),
        )
    except Exception:
        return

    if rp:
        db.execute(
            """UPDATE divers.pgt_podium_vendeur_part
                  SET qte_brut = ?, qte_hors_rejet = ?, qte_paye = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_podium_vendeur_part = ?""",
            (
                int(v["nb_brut"]), int(v["nb_hors_rejet"]),
                int(v["nb_paye"]), int(op_id),
                int(rp.get("id_podium_vendeur_part") or 0),
            ),
        )
    else:
        db.execute(
            """INSERT INTO divers.pgt_podium_vendeur_part
                  (id_podium_type_part, id_podium_vendeur, prefixe_bdd,
                   qte_brut, qte_hors_rejet, qte_paye,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (
                id_ptp, id_pv, prefixe,
                int(v["nb_brut"]), int(v["nb_hors_rejet"]),
                int(v["nb_paye"]), int(op_id),
            ),
        )


# --------------------------------------------------------------------
# Btn Calcul Podium (boucle sur [du, au+7j] par pas de 1 mois)
# --------------------------------------------------------------------

def calcul_podium(
    p: CalculPodiumParams, op_id: int,
) -> CalculPodiumResult:
    """Cf. WinDev 'Btn Calcul Podium' : boucle sur [du, au+7j] par pas
    de 1 mois, appelle Podium_Calcul pour chaque date_ref.
    """
    try:
        date_du = date.fromisoformat(p.du[:10])
        date_au = date.fromisoformat(p.au[:10]) + timedelta(days=7)
    except Exception:
        return CalculPodiumResult(
            ok=False, message="Dates invalides",
        )

    date_ref = date_du
    nb = 0
    total_parts = 0
    while date_ref < date_au:
        try:
            total_parts += _calcul_pour_date(date_ref, op_id)
        except Exception:
            logger.exception("calcul_podium date_ref=%s", date_ref)
        # +1 mois
        date_ref = _sub_months_safe(date_ref, -1)
        nb += 1

    return CalculPodiumResult(
        ok=True,
        nb_iterations=nb,
        message=f"{nb} iteration(s), {total_parts} config(s) traitees",
    )
