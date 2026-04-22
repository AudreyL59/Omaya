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

from app.core.database import get_connection


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
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")

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
            c.IDcvtheque, c.Nom, c.Prenom, c.GSM,
            c.IDCommunesFrance, c.IDcvsource, c.IdElemSource,
            c.DateSAISIE, c.Opé_SAISIE,
            c.DateREAC, c.Opé_REAC
        FROM cvtheque c
        WHERE c.ModifElem <> 'suppr'
          AND c.IDcvsource = 2
          AND c.IdElemSource {annonceur_sql}
          AND (c.DateSAISIE BETWEEN ? AND ? OR c.DateREAC BETWEEN ? AND ?)
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

    cv_rows = [r for r in cv_rows if _valid_id(_to_int(r.get("IdElemSource")))]
    if not cv_rows:
        return {"saisis": [], "resume": []}

    for r in cv_rows:
        cvtheque_ids.add(_to_int(r.get("IDcvtheque")))
        commune_ids.add(_to_int(r.get("IDCommunesFrance")))
        annonceur_ids.add(_to_int(r.get("IdElemSource")))
        date_saisie_ymd = _to_ymd(r.get("DateSAISIE") or "")
        if date_saisie_ymd and date_debut <= date_saisie_ymd <= date_fin:
            ope_ids.add(_to_int(r.get("Opé_SAISIE")))
        else:
            ope_ids.add(_to_int(r.get("Opé_REAC")))
    cvtheque_ids.discard(0)
    commune_ids.discard(0)
    ope_ids.discard(0)
    annonceur_ids.discard(0)

    # --- Batch : annonceurs (Lib_Annonceur) -------------------------------
    annonceur_lib_map: dict[int, str] = {}
    if annonceur_ids:
        ids_sql = ",".join(str(i) for i in annonceur_ids)
        a_rows = db_rec.query(
            f"SELECT IDCvAnnonceur, Lib_Annonceur FROM CvAnnonceur WHERE IDCvAnnonceur IN ({ids_sql})"
        )
        for a in a_rows:
            annonceur_lib_map[_to_int(a.get("IDCvAnnonceur"))] = a.get("Lib_Annonceur") or ""

    # --- Batch : communes -------------------------------------------------
    commune_map: dict[int, str] = {}
    if commune_ids:
        db_divers = get_connection("divers")
        ids_sql = ",".join(str(i) for i in commune_ids)
        try:
            cf_rows = db_divers.query(
                f"SELECT IDCommunesFrance, CodePostal, NomVille FROM CommunesFrance WHERE IDCommunesFrance IN ({ids_sql})"
            )
            for c in cf_rows:
                cid = _to_int(c.get("IDCommunesFrance"))
                cp = c.get("CodePostal") or ""
                nom = c.get("NomVille") or ""
                commune_map[cid] = f"{cp} {nom}".strip()
        except Exception:
            pass

    # --- Batch : noms operateurs ------------------------------------------
    salarie_name_map: dict[int, str] = {}
    if ope_ids:
        ids_sql = ",".join(str(i) for i in ope_ids)
        sal_rows = db_rh.query(
            f"SELECT IDSalarie, Nom, Prenom FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for s in sal_rows:
            sid = _to_int(s.get("IDSalarie"))
            nom = (s.get("Nom") or "").strip()
            prenom = _capitalize(s.get("Prenom") or "")
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
                f"""SELECT cs.IDcvtheque, cs.IdCvStatut, cs.Datecrea, st.LibStatut
                FROM CvSuivi cs
                LEFT JOIN CvStatut st ON st.IdCvStatut = cs.IdCvStatut
                WHERE cs.IDcvtheque IN ({ids_sql})
                  AND cs.ModifElem NOT LIKE '%suppr%'
                ORDER BY cs.IDcvtheque, cs.Datecrea DESC"""
            )
            for r in cs_rows:
                cid = _to_int(r.get("IDcvtheque"))
                id_stat = _to_int(r.get("IdCvStatut"))
                lib = r.get("LibStatut") or ""
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
                f"""SELECT cs.IDcvtheque, ac.IdCvStatut AS IdCvStatutAg, ac.Lib_Catégorie
                FROM CvSuivi cs
                INNER JOIN AgendaEvénement ae ON ae.IDCvSuivi = cs.IDCvSuivi
                INNER JOIN AgendaCatégorie ac ON ac.IDAgendaCatégorie = ae.IDCatégorie
                WHERE cs.IDcvtheque IN ({ids_sql})
                  AND cs.TypeElem = 'RDV'
                  AND ae.ModifElem <> 'suppr'"""
            )
            for r in rdv_rows:
                cid = _to_int(r.get("IDcvtheque"))
                if cid and cid not in rdv_map:
                    rdv_map[cid] = {
                        "id_cv_statut_ag": _to_int(r.get("IdCvStatutAg")),
                        "lib_categorie": r.get("Lib_Catégorie") or "",
                    }
        except Exception:
            pass

    # --- Batch : embauche (DPAE) -----------------------------------------
    embauche_cvtheque: set[int] = set()
    if cvtheque_ids:
        ids_sql = ",".join(str(i) for i in cvtheque_ids)
        try:
            emb_rows = db_rh.query(
                f"SELECT DISTINCT IDcvtheque FROM salarie_embauche WHERE IDcvtheque IN ({ids_sql})"
            )
            for e in emb_rows:
                embauche_cvtheque.add(_to_int(e.get("IDcvtheque")))
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
        cid = _to_int(r.get("IDcvtheque"))
        id_ann = _to_int(r.get("IdElemSource"))

        # Operateur : saisie ou reactivation
        date_saisie_raw = r.get("DateSAISIE") or ""
        date_reac_raw = r.get("DateREAC") or ""
        date_saisie_ymd = _to_ymd(date_saisie_raw)
        if (
            date_saisie_ymd
            and date_debut <= date_saisie_ymd <= date_fin
            and _to_int(r.get("Opé_SAISIE")) > 0
        ):
            ope_id = _to_int(r.get("Opé_SAISIE"))
            date_traitement = date_saisie_raw
            est_reac = False
        else:
            ope_id = _to_int(r.get("Opé_REAC"))
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
            "nom_prenom": f"{(r.get('Nom') or '').strip()} {_capitalize(r.get('Prenom') or '')}".strip(),
            "commune": commune_map.get(_to_int(r.get("IDCommunesFrance")), ""),
            "tel": r.get("GSM") or "",
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
