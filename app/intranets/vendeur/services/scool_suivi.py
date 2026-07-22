"""Service Suivi Scool (intranet Vendeur).

Portage de la Page_ScoolSuivi WinDev :
  - Liste des formations actives (filtre par formateur/promo sauf droit SuiviScool)
  - Details des stagiaires d'une formation selectionnee + prod SFR calculee
    (Fibre / CQT / Migration / Mobile — brut et HR).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)


def _str_id(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _iso_date(v: Any) -> str:
    if not v:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def liste_formations(user_id: int, droits: list[str],
                      date_min: str, actives_only: bool,
                      search: str) -> list[dict]:
    """Formations visibles par le user (formateur 1..5 ou destPromo).
    Droit `SuiviScool` -> voit toutes.

    date_min : filtre `date_fin >= date_min` (format ISO YYYY-MM-DD).
    actives_only : filtre `formation_active = TRUE`.
    search : ILIKE sur intitule + ville_formation.
    """
    db = get_pg_connection("scool")
    voit_tout = "SuiviScool" in (droits or [])

    where_extra = ""
    if not voit_tout and user_id:
        u = int(user_id)
        # LIKE %<id>% cote WinDev remplace par un OR de casts propres
        where_extra = f""" AND ({u} IN (formateur1, formateur2, formateur3,
                                        formateur4, formateur5, dest_promo))"""

    active_extra = " AND formation_active = TRUE" if actives_only else ""

    dmin = _iso_date(date_min) or date.today().isoformat()
    params: list = [dmin]
    search_extra = ""
    q = (search or "").strip()
    if q:
        search_extra = " AND (intitule ILIKE ? OR ville_formation ILIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    sql = f"""SELECT id_formation, intitule, date_debut, date_fin,
                     nb_heure_salle, nb_heure_terrain, ville_formation,
                     type_produit, categorie, formateur1, formateur2,
                     heure_jour_salle, heure_jour_terrain, formation_active
                FROM scool.pgt_formation
               WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                 AND date_fin >= ?::date
                 {active_extra}
                 {where_extra}
                 {search_extra}
               ORDER BY date_debut DESC, intitule ASC"""
    try:
        rows = db.query(sql, tuple(params)) or []
    except Exception:
        logger.exception("liste_formations")
        return []

    out = []
    for r in rows:
        out.append({
            "IDformation": _str_id(r.get("id_formation")),
            "Intitule": r.get("intitule") or "",
            "DateDebut": _iso_date(r.get("date_debut")),
            "DateFin": _iso_date(r.get("date_fin")),
            "NbHeureSalle": float(r.get("nb_heure_salle") or 0),
            "NbHeureTerrain": float(r.get("nb_heure_terrain") or 0),
            "VilleFormation": r.get("ville_formation") or "",
            "TypeProduit": r.get("type_produit") or "",
            "Categorie": r.get("categorie") or "",
            "HeureJourSalle": float(r.get("heure_jour_salle") or 0),
            "HeureJourTerrain": float(r.get("heure_jour_terrain") or 0),
            "FormationActive": bool(r.get("formation_active")),
        })
    return out


def stagiaires_formation(id_formation: int) -> list[dict]:
    """Stagiaires d'une formation + prod SFR calculee sur la periode
    (date_debut..date_fin de leur inscription)."""
    if not id_formation:
        return []
    db_scool = get_pg_connection("scool")
    db_rh = get_pg_connection("rh")

    try:
        rows = db_scool.query(
            """SELECT id_salarie, date_debut, date_fin,
                      idorganigramme, id_formation, livrable
                 FROM scool.pgt_formation_salarie
                WHERE id_formation = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (int(id_formation),),
        ) or []
    except Exception:
        logger.exception("stagiaires_formation: formation_salarie")
        return []

    sal_ids = {int(r.get("id_salarie") or 0) for r in rows if r.get("id_salarie")}
    if not sal_ids:
        return []

    # Batch : info salarie + activite + sortie
    ids_sql = ",".join(str(i) for i in sal_ids)
    infos: dict[int, dict] = {}
    try:
        info_rows = db_rh.query(
            f"""SELECT s.id_salarie, s.nom, s.prenom,
                       se.en_activite,
                       (SELECT ss.id_type_sortie
                          FROM rh.pgt_salarie_sortie ss
                         WHERE ss.id_salarie = s.id_salarie
                         ORDER BY ss.modif_date DESC LIMIT 1) AS id_type_sortie
                  FROM rh.pgt_salarie s
                  LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                 WHERE s.id_salarie IN ({ids_sql})""",
        ) or []
        for i in info_rows:
            infos[int(i.get("id_salarie") or 0)] = i
    except Exception:
        logger.exception("stagiaires_formation: infos salarie")

    # Lib du type sortie
    lib_sortie_map: dict[int, str] = {}
    sortie_ids = {int(i.get("id_type_sortie") or 0)
                   for i in infos.values()} - {0}
    if sortie_ids:
        try:
            libs = db_rh.query(
                f"""SELECT id_type_sortie, lib_sortie
                     FROM rh.pgt_type_sortie_salarie
                    WHERE id_type_sortie IN ({','.join(str(i) for i in sortie_ids)})""",
            ) or []
            for l in libs:
                lib_sortie_map[int(l.get("id_type_sortie") or 0)] = l.get("lib_sortie") or ""
        except Exception:
            logger.exception("stagiaires_formation: lib sortie")

    out = []
    for r in rows:
        sid = int(r.get("id_salarie") or 0)
        info = infos.get(sid, {})
        id_type_sortie = int(info.get("id_type_sortie") or 0)
        date_deb = _iso_date(r.get("date_debut"))
        date_fin = _iso_date(r.get("date_fin"))
        prod = _calcul_prod_sfr(sid, date_deb, date_fin)
        out.append({
            "IDStagiaire": str(sid),
            "Nom": (info.get("nom") or "").strip(),
            "Prenom": _capitalise((info.get("prenom") or "").strip()),
            "NomPrenom": (
                f"{(info.get('nom') or '').strip()} "
                f"{_capitalise((info.get('prenom') or '').strip())}"
            ).strip(),
            "DateDebut": date_deb,
            "DateFin": date_fin,
            "EnActivite": bool(info.get("en_activite")),
            "IDTypeSortie": id_type_sortie,
            "LibSortie": lib_sortie_map.get(id_type_sortie, ""),
            "Livrable": bool(r.get("livrable")),
            **prod,
        })
    out.sort(key=lambda x: (x["Nom"], x["Prenom"]))
    return out


def _calcul_prod_sfr(id_salarie: int, date_deb: str, date_fin: str) -> dict:
    """Compte les contrats SFR du stagiaire sur la periode de formation.

    Retourne les champs : NbFibreBrut, NbFibreHR, NbCQTBrut, NbCQTHR,
    NbMigBrut, NbMigHR, NbMobBrut, NbMobHR.

    Regles (portage WinDev CalculProdSFR) :
    - Contrats non supprimes, id_type_etat != 9
    - Famille = FIBRE :
        * NbFibreBrut += nb (toujours), NbFibreHR += nb si etat != 3
        * TypeVente 1 ou 2 -> NbCQTBrut (toujours), NbCQTHR si etat != 3
        * TypeVente autre -> NbMigBrut / NbMigHR (idem)
    - Famille autre :
        * NbMobBrut / NbMobHR (idem)
    """
    default = {
        "NbFibreBrut": 0, "NbFibreHR": 0,
        "NbCQTBrut": 0, "NbCQTHR": 0,
        "NbMigBrut": 0, "NbMigHR": 0,
        "NbMobBrut": 0, "NbMobHR": 0,
    }
    if not id_salarie or not date_deb or not date_fin:
        return default
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT p.famille, e.id_type_etat, c.type_vente,
                      COUNT(c.id_contrat) AS nbctt
                 FROM adv.pgt_sfr_contrat c
                 INNER JOIN adv.pgt_sfr_etat_contrat e
                        ON e.id_etat = c.id_etat_contrat
                 INNER JOIN adv.pgt_sfr_produit p
                        ON p.id_produit = c.id_produit
                WHERE (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
                  AND c.id_salarie = ?
                  AND c.date_signature::date BETWEEN ?::date AND ?::date
                  AND e.id_type_etat <> 9
                GROUP BY p.famille, e.id_type_etat, c.type_vente""",
            (int(id_salarie), date_deb, date_fin),
        ) or []
    except Exception:
        logger.exception("_calcul_prod_sfr id_sal=%s", id_salarie)
        return default

    r = dict(default)
    for row in rows:
        famille = (row.get("famille") or "").upper().strip()
        id_type_etat = int(row.get("id_type_etat") or 0)
        type_vente = int(row.get("type_vente") or 0)
        nb = int(row.get("nbctt") or 0)
        etat_ok = id_type_etat != 3  # cote HR : exclut aussi etat = 3
        if famille == "FIBRE":
            r["NbFibreBrut"] += nb
            if etat_ok:
                r["NbFibreHR"] += nb
            if type_vente in (1, 2):
                r["NbCQTBrut"] += nb
                if etat_ok:
                    r["NbCQTHR"] += nb
            else:
                r["NbMigBrut"] += nb
                if etat_ok:
                    r["NbMigHR"] += nb
        else:
            r["NbMobBrut"] += nb
            if etat_ok:
                r["NbMobHR"] += nb
    return r
