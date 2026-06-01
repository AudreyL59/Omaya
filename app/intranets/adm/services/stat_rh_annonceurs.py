"""
Service Stats RH - Annonceurs.

Transposition de Fen_StatRH_Annonceurs :
- Requete principale : cvtheque ou IDcvsource = 2 et (DateSAISIE ou DateREAC dans periode)
- Filtre optionnel : IdElemSource = id annonceur specifique
- Enrichissements :
  - Statut actuel (dernier CvSuivi)
  - Statut traite (dernier CvSuivi avec IdCvStatut > 1)
  - Fiche reactivee (statut actuel <= 1 alors qu'un traitement existait)
  - RDV (via CvSuivi + AgendaEvenement + AgendaCategorie)
  - DPAE (via salarie_embauche.IDcvtheque)

Regles KPI (identiques a WinDev) :
- Present : IdCvStatutAg in (101, 102) ou >= 105
- Retenu  : IdCvStatutAg = 101 ou >= 106
- JO      : IDcvtheque present dans salarie_embauche
"""

import base64
import struct
from collections import defaultdict
from typing import Optional

from app.core.database.pg import get_pg_connection


def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _capitalize(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    return s[0].upper() + s[1:].lower()


def _to_ymd(raw: str) -> str:
    """Normalise une date en YYYYMMDD (ISO avec tirets ou WinDev)."""
    if not raw:
        return ""
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        return raw[0:4] + raw[5:7] + raw[8:10]
    if len(raw) >= 8 and raw[:8].isdigit():
        return raw[:8]
    return ""


def calculer_stats_annonceurs(
    date_debut: str,   # YYYYMMDD
    date_fin: str,     # YYYYMMDD
    id_annonceur: Optional[int] = None,
) -> dict:
    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")

    param_deb = f"{date_debut}000000"
    param_fin = f"{date_fin}235959"

    # Filtre annonceur
    if id_annonceur is not None and id_annonceur > 0:
        annonceur_sql = "= ?"
        annonceur_params: tuple = (id_annonceur,)
    else:
        annonceur_sql = "LIKE '%'"
        annonceur_params = ()

    # --- Requete principale CV annonceurs ---------------------------------
    sql_cv = f"""
        SELECT
            c.id_cvtheque, c.nom, c.prenom, c.gsm,
            c.id_communes_france, c.id_cvsource, c.id_elem_source,
            c.date_saisie, c.ope_saisie,
            c.date_reac, c.ope_reac
        FROM pgt_cvtheque c
        WHERE c.modif_elem <> 'suppr'
          AND c.id_cvsource = 2
          AND c.id_elem_source {annonceur_sql}
          AND (c.date_saisie BETWEEN ? AND ? OR c.date_reac BETWEEN ? AND ?)
    """
    params: list = [*annonceur_params, param_deb, param_fin, param_deb, param_fin]
    cv_rows = db_rec.query(sql_cv, tuple(params))

    if not cv_rows:
        return {"saisis": [], "resume": []}

    # --- Collect IDs for batch lookups ------------------------------------
    cvtheque_ids: set[int] = set()
    commune_ids: set[int] = set()
    ope_ids: set[int] = set()
    annonceur_ids: set[int] = set()

    # Sanity : un id > 9e18 = NULL HFSQL corrompu (max uint64). On exclut ces rows.
    def _valid_id(n: int) -> bool:
        return 0 < n < 9_000_000_000_000_000_000

    cv_rows = [r for r in cv_rows if _valid_id(_to_int(r.get("id_elem_source")))]
    if not cv_rows:
        return {"saisis": [], "resume": []}

    for r in cv_rows:
        cvtheque_ids.add(_to_int(r.get("id_cvtheque")))
        commune_ids.add(_to_int(r.get("id_communes_france")))
        annonceur_ids.add(_to_int(r.get("id_elem_source")))
        date_saisie_ymd = _to_ymd(r.get("date_saisie") or "")
        if date_saisie_ymd and date_debut <= date_saisie_ymd <= date_fin:
            ope_ids.add(_to_int(r.get("ope_saisie")))
        else:
            ope_ids.add(_to_int(r.get("ope_reac")))
    cvtheque_ids.discard(0)
    commune_ids.discard(0)
    ope_ids.discard(0)
    annonceur_ids.discard(0)

    # --- Batch : annonceurs (Lib_Annonceur) -------------------------------
    annonceur_lib_map: dict[int, str] = {}
    if annonceur_ids:
        ids_sql = ",".join(str(i) for i in annonceur_ids)
        a_rows = db_rec.query(
            f"SELECT id_cv_annonceur, lib_annonceur FROM pgt_cv_annonceur WHERE id_cv_annonceur IN ({ids_sql})"
        )
        for a in a_rows:
            annonceur_lib_map[_to_int(a.get("id_cv_annonceur"))] = a.get("lib_annonceur") or ""

    # --- Batch : communes -------------------------------------------------
    commune_map: dict[int, str] = {}
    if commune_ids:
        db_divers = get_pg_connection("divers")
        ids_sql = ",".join(str(i) for i in commune_ids)
        try:
            cf_rows = db_divers.query(
                f"SELECT id_communes_france, code_postal, nom_ville FROM pgt_communes_france WHERE id_communes_france IN ({ids_sql})"
            )
            for c in cf_rows:
                cid = _to_int(c.get("id_communes_france"))
                cp = c.get("code_postal") or ""
                nom = c.get("nom_ville") or ""
                commune_map[cid] = f"{cp} {nom}".strip()
        except Exception:
            pass

    # --- Batch : noms operateurs ------------------------------------------
    salarie_name_map: dict[int, str] = {}
    if ope_ids:
        ids_sql = ",".join(str(i) for i in ope_ids)
        sal_rows = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for s in sal_rows:
            sid = _to_int(s.get("id_salarie"))
            nom = (s.get("nom") or "").strip()
            prenom = _capitalize(s.get("prenom") or "")
            salarie_name_map[sid] = f"{nom} {prenom}".strip()

    # --- Batch : statuts actuels + statuts traites -----------------------
    # Dernier CvSuivi par IDcvtheque (tous statuts)
    statut_actuel_map: dict[int, tuple[int, str]] = {}
    # Dernier CvSuivi par IDcvtheque avec IdCvStatut > 1
    statut_traite_map: dict[int, tuple[int, str]] = {}
    if cvtheque_ids:
        ids_sql = ",".join(str(i) for i in cvtheque_ids)
        try:
            cs_rows = db_rec.query(
                f"""SELECT cs.id_cvtheque, cs.id_cv_statut, cs.datecrea, st.lib_statut
                FROM pgt_cvsuivi cs
                LEFT JOIN pgt_cvstatut st ON st.id_cv_statut = cs.id_cv_statut
                WHERE cs.id_cvtheque IN ({ids_sql})
                  AND cs.modif_elem NOT LIKE '%suppr%'
                ORDER BY cs.id_cvtheque, cs.datecrea DESC"""
            )
            for r in cs_rows:
                cid = _to_int(r.get("id_cvtheque"))
                id_stat = _to_int(r.get("id_cv_statut"))
                lib = r.get("lib_statut") or ""
                if cid and cid not in statut_actuel_map:
                    statut_actuel_map[cid] = (id_stat, lib)
                if cid and id_stat > 1 and cid not in statut_traite_map:
                    statut_traite_map[cid] = (id_stat, lib)
        except Exception:
            pass

    # --- Batch : RDV via AgendaEvenement ---------------------------------
    # On prend le premier RDV trouve par IDcvtheque
    rdv_map: dict[int, dict] = {}
    if cvtheque_ids:
        ids_sql = ",".join(str(i) for i in cvtheque_ids)
        try:
            rdv_rows = db_rec.query(
                f"""SELECT cs.id_cvtheque, ac.id_cv_statut AS id_cv_statut_ag, ac.lib_categorie
                FROM pgt_cvsuivi cs
                INNER JOIN pgt_agenda_evenement ae ON ae.id_cv_suivi = cs.id_cv_suivi
                INNER JOIN pgt_agenda_categorie ac ON ac.id_agenda_categorie = ae.id_categorie
                WHERE cs.id_cvtheque IN ({ids_sql})
                  AND cs.type_elem = 'RDV'
                  AND ae.modif_elem <> 'suppr'"""
            )
            for r in rdv_rows:
                cid = _to_int(r.get("id_cvtheque"))
                if cid and cid not in rdv_map:
                    rdv_map[cid] = {
                        "id_cv_statut_ag": _to_int(r.get("id_cv_statut_ag")),
                        "lib_categorie": r.get("lib_categorie") or "",
                    }
        except Exception:
            pass

    # --- Batch : embauche (DPAE) -----------------------------------------
    embauche_cvtheque: set[int] = set()
    if cvtheque_ids:
        ids_sql = ",".join(str(i) for i in cvtheque_ids)
        try:
            emb_rows = db_rh.query(
                f"SELECT DISTINCT id_cvtheque FROM pgt_salarie_embauche WHERE id_cvtheque IN ({ids_sql})"
            )
            for e in emb_rows:
                embauche_cvtheque.add(_to_int(e.get("id_cvtheque")))
        except Exception:
            pass

    # --- Aggregation + construction lignes --------------------------------
    resume_agg: dict[int, dict] = defaultdict(
        lambda: {
            "nb_cv_saisis": 0,
            "nb_cv_traites": 0,
            "nb_rdv": 0,
            "nb_presents": 0,
            "nb_retenus": 0,
            "nb_jo": 0,
        }
    )
    saisis_list: list[dict] = []

    for r in cv_rows:
        cid = _to_int(r.get("id_cvtheque"))
        id_ann = _to_int(r.get("id_elem_source"))

        # Operateur : saisie ou reactivation
        date_saisie_raw = r.get("date_saisie") or ""
        date_reac_raw = r.get("date_reac") or ""
        date_saisie_ymd = _to_ymd(date_saisie_raw)
        if (
            date_saisie_ymd
            and date_debut <= date_saisie_ymd <= date_fin
            and _to_int(r.get("ope_saisie")) > 0
        ):
            ope_id = _to_int(r.get("ope_saisie"))
            date_traitement = date_saisie_raw
            est_reac = False
        else:
            ope_id = _to_int(r.get("ope_reac"))
            date_traitement = date_reac_raw
            est_reac = True

        # Statut actuel + traite
        statut_actuel_id, statut_actuel_lib = statut_actuel_map.get(cid, (0, ""))
        statut_traite_id, statut_traite_lib = statut_traite_map.get(cid, (0, ""))

        # Fiche reac = il y a eu un traitement mais le statut actuel est redescendu <= 1
        fiche_reac = statut_traite_id > 1 and statut_actuel_id <= 1

        # RDV info
        rdv = rdv_map.get(cid, {})
        has_rdv = bool(rdv)
        id_stat_ag = rdv.get("id_cv_statut_ag", 0)
        lib_rdv = rdv.get("lib_categorie", "")
        is_present = has_rdv and (
            id_stat_ag == 101 or id_stat_ag == 102 or id_stat_ag >= 105
        )
        is_retenu = has_rdv and (id_stat_ag == 101 or id_stat_ag >= 106)
        is_jo = cid in embauche_cvtheque

        # Aggregation annonceur
        agg = resume_agg[id_ann]
        agg["nb_cv_saisis"] += 1
        if statut_traite_id > 1:
            agg["nb_cv_traites"] += 1
        if has_rdv:
            agg["nb_rdv"] += 1
        if is_present:
            agg["nb_presents"] += 1
        if is_retenu:
            agg["nb_retenus"] += 1
        if is_jo:
            agg["nb_jo"] += 1

        saisis_list.append({
            "id_cvtheque": str(cid),
            "id_annonceur": str(id_ann),
            "lib_annonceur": annonceur_lib_map.get(id_ann, ""),
            "ope_id": str(ope_id),
            "ope_nom": salarie_name_map.get(ope_id, ""),
            "date_traitement": date_traitement,
            "est_reactivation": est_reac,
            "nom_prenom": f"{(r.get('nom') or '').strip()} {_capitalize(r.get('prenom') or '')}".strip(),
            "commune": commune_map.get(_to_int(r.get("id_communes_france")), ""),
            "tel": r.get("gsm") or "",
            "statut_actuel": statut_actuel_lib,
            "id_statut_actuel": statut_actuel_id,
            "statut_rdv": lib_rdv,
            "fiche_reac": fiche_reac,
            "dpae": is_jo,
            "cv_traite": statut_traite_id > 1,
            "has_rdv": has_rdv,
            "is_present": is_present,
            "is_retenu": is_retenu,
        })

    resume_list = [
        {
            "id_annonceur": str(id_ann),
            "lib_annonceur": annonceur_lib_map.get(id_ann, f"ID {id_ann}"),
            **stats,
        }
        for id_ann, stats in resume_agg.items()
        if id_ann > 0
    ]
    resume_list.sort(key=lambda r: r["lib_annonceur"].lower())

    return {
        "saisis": saisis_list,
        "resume": resume_list,
    }
