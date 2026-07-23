"""Endpoint mobile Podium (WebRest_Omayapp/Podium).

Portage RecupPodium WinDev - le WS le plus complexe (~500 lignes).

Retourne le classement top-3 (+ position du vendeur si hors top-3) pour
chaque PodiumType actif, sur un mois donne.

Cle metier :
  - PodiumType : les rubriques (ex: 'Prod Fibre', 'Qualite ADV', ...)
  - Configuration :
      * Qualite    : score = taux (payes / bruts) *100
      * ProdGroupe : agrege par equipe (idorganigramme) au lieu de salarie
      * Espoir     : filtre les 'anciens' via date_anciennete >= mois-2
  - Data : PodiumVendeur JOIN PodiumVendeurPart par jour
  - PodiumMois : atteste que le podium a ete calcule pour ce mois
                  (ScoreVisible controle l'affichage du score numerique)
  - IdOrgaDistrib : pour les vendeurs distributeurs, filtre l'agenda sur
                    l'orga distributeur racine ancestor de l'affectation

TODO V2 :
  - ReqEquipeTerrainBySalarieByDate : ma requete simplifiee prend
    l'affectation active a la date fin. Le WinDev avait une logique
    plus fine (avec heure de reference 9h01).
  - ReqRespOrgaActif_byOrgaIDDate : idem, prend le resp_equipe actif
    a la date fin. TODO : gerer succession de resp sur la periode.
"""

from __future__ import annotations

import base64
import calendar
import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _to_int
from app.mobile.auth import _capitalise
from app.mobile.declaratif import _orga_arbre
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-podium"],
                    dependencies=[Depends(mobile_auth)])


ID_ORGA_ARCHIVES = 20160729152638792
ID_SALARIE_EXCLU = 20200715153948361  # WinDev : exclu du calcul (fictif ?)
ID_STE_DISTRIB = 4


def _bytea_to_b64(v) -> str:
    if not v:
        return ""
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, str):
        return v
    try:
        return base64.b64encode(v).decode("ascii")
    except Exception:
        return ""


def _last_day_of_month(d: date) -> date:
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def _shift_months(d: date, delta: int) -> date:
    """Decale d de delta mois (peut etre negatif)."""
    m = d.month - 1 + delta
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def _get_vendeur_info(id_vend: int) -> dict:
    """Recup {id, id_orga, is_distrib} - version simplifiee pour Podium.
    is_distrib : True si l'orga du vendeur descend d'une racine avec
    id_ste=4 (societes distributrices)."""
    db = get_pg_connection("rh")
    try:
        aff = db.query_one(
            """SELECT so.idorganigramme
                 FROM rh.pgt_salarie_organigramme so
                WHERE so.id_salarie = ?
                  AND COALESCE(so.aff_actif, FALSE) = TRUE
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_vend),),
        )
    except Exception:
        logger.exception("_get_vendeur_info id=%s", id_vend)
        return {"id": int(id_vend), "id_orga": 0, "is_distrib": False}
    id_orga = _to_int((aff or {}).get("idorganigramme"))
    is_distrib = _id_orga_distrib(id_orga) > 0 if id_orga else False
    return {"id": int(id_vend), "id_orga": id_orga,
            "is_distrib": is_distrib}


def _id_orga_distrib(id_orga_vend: int) -> int:
    """Retourne l'id de l'orga distributeur racine (fille directe de
    societe distrib IdSte=4) qui contient id_orga_vend. Ou 0 si non
    trouve."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT orga1.idorganigramme
                 FROM rh.pgt_organigramme orga1
                 JOIN rh.pgt_organigramme orga_parent
                        ON orga1.id_parent = orga_parent.idorganigramme
                WHERE orga_parent.id_parent = 0
                  AND orga_parent.idorganigramme <> ?
                  AND orga_parent.id_ste = ?
                  AND (orga1.modif_elem IS NULL OR orga1.modif_elem <> 'suppr')
                ORDER BY orga1.lib_orga""",
            (ID_ORGA_ARCHIVES, ID_STE_DISTRIB),
        ) or []
    except Exception:
        logger.exception("_id_orga_distrib")
        return 0
    for r in rows:
        distrib_id = int(r.get("idorganigramme") or 0)
        arbre = _orga_arbre(distrib_id)
        if any(o["id"] == id_orga_vend for o in arbre):
            return distrib_id
    return 0


def _equipe_terrain_salarie(id_sal: int, at_date: date) -> tuple[int, str]:
    """ReqEquipeTerrainBySalarieByDate simplifie : retourne l'affectation
    active du salarie a la date donnee."""
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT so.idorganigramme, o.lib_orga
                 FROM rh.pgt_salarie_organigramme so
                 LEFT JOIN rh.pgt_organigramme o
                        ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND so.date_debut::date <= ?
                  AND (so.date_fin IS NULL OR so.date_fin::date >= ?
                       OR so.date_fin::date < '1901-01-01')
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_sal), at_date, at_date),
        )
    except Exception:
        return 0, ""
    if not row:
        return 0, ""
    return _to_int(row.get("idorganigramme")), (row.get("lib_orga") or "").strip()


def _resp_orga_actif(id_orga: int, date_deb: date, date_fin: date
                       ) -> tuple[int, str, str]:
    """ReqRespOrgaActif_byOrgaIDDate simplifie : premier resp d'equipe
    actif sur l'orga."""
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT s.id_salarie, s.nom, s.prenom
                 FROM rh.pgt_salarie s
                 JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                 JOIN rh.pgt_salarie_organigramme so
                        ON so.id_salarie = s.id_salarie
                WHERE so.idorganigramme = ?
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                  AND so.date_debut::date <= ?
                  AND (so.date_fin IS NULL OR so.date_fin::date >= ?
                       OR so.date_fin::date < '1901-01-01')
                  AND COALESCE(se.en_activite, FALSE) = TRUE
                  AND COALESCE(se.resp_equipe, FALSE) = TRUE
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY se.resp_equipe DESC, se.resp_adjoint DESC,
                          s.nom, s.prenom
                LIMIT 1""",
            (int(id_orga), date_fin, date_deb),
        )
    except Exception:
        return 0, "", ""
    if not row:
        return 0, "", ""
    return (_to_int(row.get("id_salarie")),
            (row.get("nom") or "").strip(),
            (row.get("prenom") or "").strip())


def _photo_salarie_b64(id_sal: int) -> str:
    """Photo salarie en b64. Fallback GUIMMICK societe si vide."""
    if not id_sal:
        return ""
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            "SELECT photo FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (int(id_sal),),
        )
    except Exception:
        return ""
    if row and row.get("photo"):
        return _bytea_to_b64(row.get("photo"))
    # Fallback : GUIMMICK societe
    try:
        st = db.query_one(
            """SELECT s.guimmick
                 FROM rh.pgt_societe s
                 JOIN rh.pgt_salarie_embauche se ON se.id_ste = s.id_ste
                WHERE se.id_salarie = ? LIMIT 1""",
            (int(id_sal),),
        )
        if st and st.get("guimmick"):
            return _bytea_to_b64(st.get("guimmick"))
    except Exception:
        pass
    return ""


@router.post("/Podium")
def podium(payload: dict = Body(...),
           id_auth: int = Depends(mobile_auth)):
    """Portage RecupPodium.

    Payload : { idVend, MoisP, AnnéeP } (fallback idVend = user auth).
    Retour : [ST_Podium] avec classement top-3 par PodiumType actif.
    """
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie")
                       or id_auth)
    mois = _to_int(payload.get("MoisP"))
    annee_s = str(payload.get("AnnéeP") or payload.get("AnneeP") or "").strip()
    if not id_vend or not mois or not annee_s:
        return []

    v_info = _get_vendeur_info(id_vend)
    id_orga_vend = v_info["id_orga"]
    is_distrib = v_info["is_distrib"]

    id_orga_distrib = 0
    if is_distrib:
        id_orga_distrib = _id_orga_distrib(id_orga_vend)
    if not id_orga_distrib:
        id_orga_distrib = id_orga_vend

    db = get_pg_connection("divers")

    # 1. Liste des PodiumType actifs
    try:
        types = db.query(
            """SELECT id_podium_type, lib_podium_type, lib_court,
                      prod_groupe, qualite, espoir
                 FROM divers.pgt_podium_type
                WHERE COALESCE(is_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY ordre_affichage ASC NULLS LAST""",
        ) or []
    except Exception:
        logger.exception("podium types")
        return []

    result: list[dict] = []

    for t in types:
        id_type = _to_int(t.get("id_podium_type"))
        test_quali = bool(t.get("qualite"))
        test_prod_gr = bool(t.get("prod_groupe"))
        test_espoir = bool(t.get("espoir"))

        # 2. Verif PodiumMois existe
        try:
            pm = db.query_one(
                """SELECT id_podium_mois, score_visible, mois, annee
                     FROM divers.pgt_podium_mois
                    WHERE annee = ? AND mois = ? AND id_podium_type = ?
                    LIMIT 1""",
                (annee_s, mois, id_type),
            )
        except Exception:
            logger.exception("podium mois t=%s", id_type)
            pm = None
        if not pm:
            continue

        score_visible = bool(pm.get("score_visible"))
        test_coopt = False

        # 3. Partitions du type
        try:
            parts = db.query(
                """SELECT id_podium_type_part, jour_cial_deb, jour_cial_fin,
                          type_prod, prefixe_bdd
                     FROM divers.pgt_podium_type_part
                    WHERE id_podium_type = ?
                      AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
                (id_type,),
            ) or []
        except Exception:
            logger.exception("podium parts t=%s", id_type)
            parts = []

        # Agrege {key: {IdEquipe/idSalarié, NomVend, LibEquipe, brut, paye,
        #              nbCtt, supp, EnActivite, Taux}}
        table: dict[tuple, dict] = {}

        for p in parts:
            if (p.get("prefixe_bdd") or "").lower() == "coopt":
                test_coopt = True

            jc_deb = _to_int(p.get("jour_cial_deb")) or 1
            jc_fin = _to_int(p.get("jour_cial_fin"))
            id_type_part = _to_int(p.get("id_podium_type_part"))
            type_prod = (p.get("type_prod") or "").strip()

            # Calcul dateDeb/dateFin
            if jc_deb == 1:
                date_deb = date(int(annee_s.split("-")[-1] or annee_s[:4]), mois, 1)
                date_fin = _last_day_of_month(date_deb)
            else:
                y = int(annee_s.split("-")[-1] or annee_s[:4])
                date_deb = _shift_months(date(y, mois, jc_deb), -1)
                date_fin = date(y, mois, jc_fin) if jc_fin else _last_day_of_month(date(y, mois, 1))

            # OrgaDistrib pour filtrage distrib
            orga_distrib_ids: set[int] = set()
            if is_distrib:
                orga_distrib_ids = {o["id"] for o in _orga_arbre(id_orga_distrib)}

            # Condition Espoir
            espoir_sql = ""
            espoir_params: tuple = ()
            if test_espoir:
                d_esp = _shift_months(date_deb, -2)
                espoir_sql = " AND se.date_anciennete >= ?"
                espoir_params = (d_esp,)

            # Requete PodiumVendeur + Part
            if test_prod_gr:
                sql = f"""SELECT DISTINCT pv.id_equipe AS id_equipe,
                                 SUM(pvp.qte_brut) AS qte_brut,
                                 SUM(pvp.qte_hors_rejet) AS qte_hors_rejet,
                                 SUM(pvp.qte_paye) AS qte_paye
                            FROM divers.pgt_podium_vendeur pv
                            JOIN divers.pgt_podium_vendeur_part pvp
                                   ON pvp.id_podium_vendeur = pv.id_podium_vendeur
                            JOIN rh.pgt_salarie s ON s.id_salarie = pv.id_salarie
                            JOIN rh.pgt_salarie_embauche se
                                   ON se.id_salarie = s.id_salarie
                           WHERE (pvp.modif_elem IS NULL OR pvp.modif_elem <> 'suppr')
                             AND (pv.modif_elem IS NULL OR pv.modif_elem <> 'suppr')
                             AND pv.date_jour BETWEEN ? AND ?
                             AND pv.id_podium_type = ?
                             AND COALESCE(pv.distributeur, FALSE) = ?
                             AND pvp.id_podium_type_part = ?
                             AND pv.id_salarie <> ?
                             {espoir_sql}
                           GROUP BY pv.id_equipe"""
            else:
                sql = f"""SELECT DISTINCT s.nom, s.prenom,
                                 SUM(pvp.qte_brut) AS qte_brut,
                                 SUM(pvp.qte_hors_rejet) AS qte_hors_rejet,
                                 SUM(pvp.qte_paye) AS qte_paye,
                                 s.id_salarie AS id_salarie,
                                 se.en_activite, se.resp_equipe,
                                 se.date_anciennete, se.en_pause
                            FROM divers.pgt_podium_vendeur pv
                            JOIN divers.pgt_podium_vendeur_part pvp
                                   ON pvp.id_podium_vendeur = pv.id_podium_vendeur
                            JOIN rh.pgt_salarie s ON s.id_salarie = pv.id_salarie
                            JOIN rh.pgt_salarie_embauche se
                                   ON se.id_salarie = s.id_salarie
                           WHERE (pvp.modif_elem IS NULL OR pvp.modif_elem <> 'suppr')
                             AND (pv.modif_elem IS NULL OR pv.modif_elem <> 'suppr')
                             AND pv.date_jour BETWEEN ? AND ?
                             AND pv.id_podium_type = ?
                             AND COALESCE(pv.distributeur, FALSE) = ?
                             AND pvp.id_podium_type_part = ?
                             AND pv.id_salarie <> ?
                             {espoir_sql}
                           GROUP BY s.nom, s.prenom, s.id_salarie,
                                    se.en_activite, se.resp_equipe,
                                    se.date_anciennete, se.en_pause"""

            params = (date_deb, date_fin, id_type, is_distrib, id_type_part,
                      ID_SALARIE_EXCLU) + espoir_params
            try:
                rows = db.query(sql, params) or []
            except Exception:
                logger.exception("podium query part=%s", id_type_part)
                rows = []

            for r in rows:
                if test_prod_gr:
                    id_eq = _to_int(r.get("id_equipe"))
                    # Filtre distrib
                    if is_distrib and id_eq not in orga_distrib_ids:
                        continue
                    key = ("eq", id_eq)
                    if key not in table:
                        # Recup resp d'equipe
                        id_resp, nom_r, prenom_r = _resp_orga_actif(
                            id_eq, date_deb, date_fin)
                        # Lib_ORGA
                        lib_orga = ""
                        supp = False
                        try:
                            dbrh = get_pg_connection("rh")
                            o = dbrh.query_one(
                                """SELECT lib_orga, modif_elem
                                     FROM rh.pgt_organigramme
                                    WHERE idorganigramme = ? LIMIT 1""",
                                (id_eq,),
                            )
                            if o:
                                lib_orga = (o.get("lib_orga") or "").strip()
                                supp = (o.get("modif_elem") or "") == "suppr"
                        except Exception:
                            pass
                        table[key] = {
                            "IdEquipe": id_eq,
                            "idSalarie": id_resp,
                            "NomVend": f"{nom_r} {_capitalise(prenom_r)}".strip(),
                            "LibEquipe": lib_orga,
                            "brut": 0, "paye": 0, "nbCtt": 0,
                            "supp": supp, "EnActivite": True,
                            "Taux": 0.0,
                        }
                else:
                    id_sal = _to_int(r.get("id_salarie"))
                    # Filtre distrib via equipe terrain
                    if is_distrib:
                        id_eq_t, _ = _equipe_terrain_salarie(id_sal, date_fin)
                        if id_eq_t not in orga_distrib_ids:
                            continue
                    key = ("sal", id_sal)
                    if key not in table:
                        id_eq_t, lib_eq_t = _equipe_terrain_salarie(id_sal, date_fin)
                        table[key] = {
                            "IdEquipe": id_eq_t,
                            "idSalarie": id_sal,
                            "NomVend": (f"{(r.get('nom') or '').strip()} "
                                         f"{_capitalise((r.get('prenom') or '').strip())}").strip(),
                            "LibEquipe": lib_eq_t,
                            "brut": 0, "paye": 0, "nbCtt": 0,
                            "supp": False, "EnActivite": True,
                            "Taux": 0.0,
                        }
                    en_act = bool(r.get("en_activite"))
                    table[key]["EnActivite"] = en_act and not bool(r.get("en_pause"))

                entry = table[key]
                if test_quali:
                    entry["brut"] += _to_int(r.get("qte_brut"))
                    entry["paye"] += _to_int(r.get("qte_paye"))
                else:
                    if type_prod == "Brut":
                        entry["nbCtt"] += _to_int(r.get("qte_brut"))
                    elif type_prod == "HorsRejet":
                        entry["nbCtt"] += _to_int(r.get("qte_hors_rejet"))
                    else:
                        entry["nbCtt"] += _to_int(r.get("qte_paye"))

        # Calcul Taux Qualite (min 20 brut)
        if test_quali:
            for e in table.values():
                if e["brut"] > 20:
                    e["Taux"] = e["paye"] / e["brut"]

        # Tri : Taux desc (Quali) ou nbCtt desc
        sort_key = "Taux" if test_quali else "nbCtt"
        entries = sorted(table.values(), key=lambda x: x[sort_key], reverse=True)

        st_podium = {
            "ID": id_type,
            "LibPodium": (t.get("lib_podium_type") or "").strip(),
            "LibCourt": (t.get("lib_court") or "").strip(),
            "Pod_Mois": _to_int(pm.get("mois")),
            "Pod_Annee": str(pm.get("annee") or ""),
            "ScoreVisible": score_visible,
            "PodCoopt": test_coopt,
            "PodQuali": test_quali,
            "classement": [],
        }

        # Top-3 (skip supp/inactifs et si Quali skip taux=0)
        test_pos = False
        pos_reel = 0
        n_max = 3
        i = 0
        while pos_reel < n_max and i < len(entries):
            e = entries[i]
            i += 1
            if e["supp"] or not e["EnActivite"]:
                n_max += 1
                continue
            if test_quali and e["Taux"] <= 0:
                n_max += 1
                continue
            pos_reel += 1
            score = round(e["Taux"] * 100) if test_quali else e["nbCtt"]
            vend = {
                "pos": pos_reel,
                "ID": str(e["idSalarie"]),
                "Nom": e["NomVend"],
                "Equipe": e["LibEquipe"],
                "Photo": _photo_salarie_b64(e["idSalarie"]),
                "Score": score,
            }
            st_podium["classement"].append(vend)
            if test_prod_gr:
                if e["IdEquipe"] == id_orga_vend:
                    test_pos = True
            else:
                if e["idSalarie"] == id_vend:
                    test_pos = True

        # Si le vendeur n'est pas dans le top, ajoute sa ligne "Vous"/"Votre equipe"
        if not test_pos:
            ind_pos = 0
            pos = 0
            for e in entries:
                if e["supp"] or not e["EnActivite"]:
                    continue
                if test_quali and e["Taux"] <= 0:
                    continue
                pos += 1
                match = (e["IdEquipe"] == id_orga_vend) if test_prod_gr \
                        else (e["idSalarie"] == id_vend)
                if match:
                    ind_pos = pos
                    break

            score_me = 0
            if ind_pos > 0:
                for e in entries:
                    if e["supp"] or not e["EnActivite"]:
                        continue
                    if test_quali and e["Taux"] <= 0:
                        continue
                    match = (e["IdEquipe"] == id_orga_vend) if test_prod_gr \
                            else (e["idSalarie"] == id_vend)
                    if match:
                        score_me = round(e["Taux"] * 100) if test_quali \
                                    else e["nbCtt"]
                        break

            st_podium["classement"].append({
                "pos": ind_pos,
                "ID": str(id_vend),
                "Nom": "Votre équipe" if test_prod_gr else "Vous",
                "Equipe": "",
                "Photo": _photo_salarie_b64(id_vend),
                "Score": score_me,
            })

        result.append(st_podium)

    return result
