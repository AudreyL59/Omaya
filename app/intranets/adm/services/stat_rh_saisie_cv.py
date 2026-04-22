"""
Service Stats RH - Saisie et Traitement CV.

Transposition des requetes WinDev maReqCVSaisis / maReqCVTraite.

Mode "service" (reseau complet) : origine = 1, operateur = tous
Mode "personne" : origine = *, operateur = id_salarie

Tables :
- cvtheque, CvSuivi, CvSource, CvStatut dans Bdd_Omaya_Recrutement
- CommunesFrance dans Bdd_Omaya_Divers
- salarie dans Bdd_Omaya_RH (pour nom operateur)
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
    """Normalise une date en YYYYMMDD (accepte ISO '2026-04-20...' ou WinDev '20260420...')."""
    if not raw:
        return ""
    # Format ISO avec tirets : 2026-04-20[T...]
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        return raw[0:4] + raw[5:7] + raw[8:10]
    # Format WinDev YYYYMMDD(HHMMSS)
    if len(raw) >= 8 and raw[:8].isdigit():
        return raw[:8]
    return ""


def calculer_stats_saisie_cv(
    date_debut: str,      # YYYYMMDD
    date_fin: str,        # YYYYMMDD
    type_recherche: str,  # "service" ou "personne"
    id_ope_filter: Optional[int] = None,
) -> dict:
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")

    param_deb = f"{date_debut}000000"
    param_fin = f"{date_fin}235959"

    # Filtres selon mode
    if type_recherche == "service":
        # Service complet : Origine = 1 (CVtheque interne), operateur = % (tous)
        origine_param = "1"
        op_filter_sql = "LIKE '%'"
        op_filter_params: tuple = ()
    else:
        # Une personne : Origine = % (toutes), operateur specifique
        origine_param = "%"
        if id_ope_filter is not None and id_ope_filter > 0:
            op_filter_sql = "= ?"
            op_filter_params = (id_ope_filter,)
        else:
            op_filter_sql = "LIKE '%'"
            op_filter_params = ()

    # --- Req CV Saisis (saisie OU reactivation dans la periode) -----------
    # Note : c.Origine est stocke comme chaine cote HFSQL ; on compare toujours avec LIKE + string param.
    sql_cv_saisis = f"""
        SELECT
            c.IDcvtheque, c.Nom, c.Prenom, c.GSM,
            c.IDCommunesFrance, c.IDcvsource, c.IdElemSource,
            c.DateSAISIE, c.Opé_SAISIE,
            c.DateREAC, c.Opé_REAC,
            c.Origine,
            s.Lib_Source
        FROM cvtheque c
        LEFT JOIN CvSource s ON s.IDcvsource = c.IDcvsource
        WHERE c.ModifElem <> 'suppr'
          AND c.Origine LIKE ?
          AND (
                (c.DateSAISIE BETWEEN ? AND ? AND c.Opé_SAISIE {op_filter_sql})
             OR (c.DateREAC   BETWEEN ? AND ? AND c.Opé_REAC   {op_filter_sql})
          )
    """
    params_saisis: list = [
        origine_param,
        param_deb, param_fin, *op_filter_params,
        param_deb, param_fin, *op_filter_params,
    ]
    saisis_rows = db_rec.query(sql_cv_saisis, tuple(params_saisis))

    # --- Req CV Traite (CvSuivi avec IdCvStatut 2..99) --------------------
    sql_cv_traite = f"""
        SELECT
            c.IDcvtheque, c.Nom, c.Prenom, c.GSM,
            c.IDCommunesFrance, c.IDcvsource, c.IdElemSource,
            c.DateSAISIE,
            cs.IdCvStatut, cs.OPCrea, cs.Datecrea,
            st.LibStatut,
            s.Lib_Source
        FROM cvtheque c
        INNER JOIN CvSuivi cs ON cs.IDcvtheque = c.IDcvtheque
        LEFT JOIN CvStatut st ON st.IdCvStatut = cs.IdCvStatut
        LEFT JOIN CvSource s ON s.IDcvsource = c.IDcvsource
        WHERE cs.Datecrea BETWEEN ? AND ?
          AND cs.IdCvStatut BETWEEN 2 AND 99
          AND cs.OPCrea {op_filter_sql}
          AND c.ModifElem <> 'suppr'
    """
    params_traite: list = [param_deb, param_fin, *op_filter_params]
    traite_rows = db_rec.query(sql_cv_traite, tuple(params_traite))

    # --- Lookup CommunesFrance (pour les deux listes) ---------------------
    commune_ids = set()
    for r in saisis_rows:
        commune_ids.add(_to_int(r.get("IDCommunesFrance")))
    for r in traite_rows:
        commune_ids.add(_to_int(r.get("IDCommunesFrance")))
    commune_ids.discard(0)

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

    # --- Lookup statut actuel de chaque cvtheque (dernier CvSuivi) --------
    # Pour la colonne "Statut actuel" des onglets
    cvtheque_ids = {_to_int(r.get("IDcvtheque")) for r in saisis_rows}
    cvtheque_ids |= {_to_int(r.get("IDcvtheque")) for r in traite_rows}
    cvtheque_ids.discard(0)

    statut_actuel_map: dict[int, str] = {}
    if cvtheque_ids:
        ids_sql = ",".join(str(i) for i in cvtheque_ids)
        try:
            latest_rows = db_rec.query(
                f"""SELECT cs.IDcvtheque, cs.IdCvStatut, st.LibStatut, cs.Datecrea
                FROM CvSuivi cs
                LEFT JOIN CvStatut st ON st.IdCvStatut = cs.IdCvStatut
                WHERE cs.IDcvtheque IN ({ids_sql})
                  AND cs.ModifElem NOT LIKE '%suppr%'
                ORDER BY cs.IDcvtheque, cs.Datecrea DESC"""
            )
            for r in latest_rows:
                cid = _to_int(r.get("IDcvtheque"))
                if cid and cid not in statut_actuel_map:
                    statut_actuel_map[cid] = r.get("LibStatut") or ""
        except Exception:
            pass

    # --- Lookup operateurs (noms + annonceurs pour source=1 / 2) ---------
    ope_ids = set()
    for r in saisis_rows:
        # Saisie ou reac : on prend la saisie si dans periode, sinon reac
        date_saisie_ymd = _to_ymd(r.get("DateSAISIE") or "")
        if date_saisie_ymd and date_debut <= date_saisie_ymd <= date_fin:
            ope_ids.add(_to_int(r.get("Opé_SAISIE")))
        else:
            ope_ids.add(_to_int(r.get("Opé_REAC")))
    for r in traite_rows:
        ope_ids.add(_to_int(r.get("OPCrea")))
    ope_ids.discard(0)

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

    # Annonceurs/coopteurs pour les CV saisis
    annonceur_lib_map: dict[int, str] = {}
    annonceur_ids = {
        _to_int(r.get("IdElemSource"))
        for r in saisis_rows
        if _to_int(r.get("IDcvsource")) == 2 and _to_int(r.get("IdElemSource")) > 0
    }
    if annonceur_ids:
        ids_sql = ",".join(str(i) for i in annonceur_ids)
        try:
            a_rows = db_rec.query(
                f"SELECT IDCvAnnonceur, Lib_Annonceur FROM CvAnnonceur WHERE IDCvAnnonceur IN ({ids_sql})"
            )
            for a in a_rows:
                annonceur_lib_map[_to_int(a.get("IDCvAnnonceur"))] = a.get("Lib_Annonceur") or ""
        except Exception:
            pass
    # Coopteurs (salaries) pour source=1 : deja dans salarie_name_map si l'id est dans ope_ids,
    # sinon on complete
    coopt_salarie_ids = {
        _to_int(r.get("IdElemSource"))
        for r in saisis_rows
        if _to_int(r.get("IDcvsource")) == 1 and _to_int(r.get("IdElemSource")) > 0
    } - set(salarie_name_map.keys())
    if coopt_salarie_ids:
        ids_sql = ",".join(str(i) for i in coopt_salarie_ids)
        sal_rows = db_rh.query(
            f"SELECT IDSalarie, Nom, Prenom FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for s in sal_rows:
            sid = _to_int(s.get("IDSalarie"))
            nom = (s.get("Nom") or "").strip()
            prenom = _capitalize(s.get("Prenom") or "")
            salarie_name_map[sid] = f"{nom} {prenom}".strip()

    # --- Construction des lignes + agregation resume ----------------------
    resume_agg: dict[int, dict] = defaultdict(lambda: {"nb_cv_saisis": 0, "nb_cv_traites": 0})

    saisis_list: list[dict] = []
    for r in saisis_rows:
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

        resume_agg[ope_id]["nb_cv_saisis"] += 1

        id_source = _to_int(r.get("IDcvsource"))
        id_elem = _to_int(r.get("IdElemSource"))
        annonceur = ""
        if id_source == 1 and id_elem > 0:
            annonceur = salarie_name_map.get(id_elem, "")
        elif id_source == 2 and id_elem > 0:
            annonceur = annonceur_lib_map.get(id_elem, "")

        cid = _to_int(r.get("IDcvtheque"))
        saisis_list.append({
            "id_cvtheque": str(cid),
            "ope_id": str(ope_id),
            "ope_nom": salarie_name_map.get(ope_id, ""),
            "date_traitement": date_traitement,
            "est_reactivation": est_reac,
            "nom_prenom": f"{(r.get('Nom') or '').strip()} {_capitalize(r.get('Prenom') or '')}".strip(),
            "commune": commune_map.get(_to_int(r.get("IDCommunesFrance")), ""),
            "tel": r.get("GSM") or "",
            "statut_actuel": statut_actuel_map.get(cid, ""),
            "id_source": id_source,
            "lib_source": r.get("Lib_Source") or "",
            "annonceur_coopteur": annonceur,
        })

    traite_list: list[dict] = []
    for r in traite_rows:
        ope_id = _to_int(r.get("OPCrea"))
        resume_agg[ope_id]["nb_cv_traites"] += 1
        cid = _to_int(r.get("IDcvtheque"))

        id_source = _to_int(r.get("IDcvsource"))
        id_elem = _to_int(r.get("IdElemSource"))
        annonceur = ""
        if id_source == 1 and id_elem > 0:
            annonceur = salarie_name_map.get(id_elem, "")
        elif id_source == 2 and id_elem > 0:
            annonceur = annonceur_lib_map.get(id_elem, "")

        traite_list.append({
            "id_cvtheque": str(cid),
            "ope_id": str(ope_id),
            "ope_nom": salarie_name_map.get(ope_id, ""),
            "date_traitement": r.get("Datecrea") or "",
            "nom_prenom": f"{(r.get('Nom') or '').strip()} {_capitalize(r.get('Prenom') or '')}".strip(),
            "commune": commune_map.get(_to_int(r.get("IDCommunesFrance")), ""),
            "tel": r.get("GSM") or "",
            "statut_actuel": r.get("LibStatut") or statut_actuel_map.get(cid, ""),
            "id_cv_statut": _to_int(r.get("IdCvStatut")),
            "date_saisie": r.get("DateSAISIE") or "",
            "id_source": id_source,
            "lib_source": r.get("Lib_Source") or "",
            "annonceur_coopteur": annonceur,
        })

    resume_list = [
        {
            "id_ope": str(ope_id),
            "nom": salarie_name_map.get(ope_id, f"ID {ope_id}"),
            "nb_cv_saisis": stats["nb_cv_saisis"],
            "nb_cv_traites": stats["nb_cv_traites"],
        }
        for ope_id, stats in resume_agg.items()
        if ope_id > 0
    ]
    resume_list.sort(key=lambda r: r["nom"].lower())

    return {
        "saisis": saisis_list,
        "traites": traite_list,
        "resume": resume_list,
    }
