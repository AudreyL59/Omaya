"""
Service Stats RH - Prise de RDV.

Transposition des procedures WinDev TraiterRDV_DatePlanif / TraiterRDV_DateRDV.

Logique metier :
  - Present : IdCvStatutAg in (101, 102) ou >= 105
  - Retenu  : IdCvStatutAg = 101 ou >= 106  (sous-ensemble de Present)
  - Venu en JO : IDCategorie = 8 (JO) OU presence dans salarie_embauche (embauche effective)
  - Non statue : IDCategorie in (1, 11)
"""

import base64
import struct
from collections import defaultdict

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


def calculer_stats_rdv(
    date_debut: str,       # YYYYMMDD
    date_fin: str,         # YYYYMMDD
    type_date: str,        # "planif" ou "rdv"
    op_crea_filter: int | None,  # None = service complet ; sinon ID du salarie
) -> dict:
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")

    # Bornes datetime format WinDev YYYYMMDDHHMMSS
    param_deb = f"{date_debut}000000"
    param_fin = f"{date_fin}235959"

    # Choix du champ de filtre de date + du champ OPCrea a utiliser
    if type_date == "planif":
        where_date = "CvSuivi.Datecrea BETWEEN ? AND ?"
        op_crea_field = "CvSuivi.OPCrea"
    else:
        where_date = "AgendaEvénement.DateDébut BETWEEN ? AND ?"
        op_crea_field = "AgendaEvénement.OPCrea"

    params: list = [param_deb, param_fin]
    where_op = ""
    if op_crea_filter is not None and op_crea_filter > 0:
        where_op = f"AND {op_crea_field} = ?"
        params.append(op_crea_filter)

    # Requete principale (uniquement tables de Bdd_Omaya_Recrutement)
    sql = f"""
    SELECT
        cvtheque.IDcvtheque AS IDcvtheque,
        cvtheque.Nom AS Nom,
        cvtheque.Prenom AS Prenom,
        cvtheque.GSM AS GSM,
        cvtheque.IDcvsource AS IDcvsource,
        cvtheque.IdElemSource AS IdElemSource,
        CvSuivi.Datecrea AS Datecrea,
        CvSuivi.IdCvStatut AS IdCvStatut,
        AgendaEvénement.IDCatégorie AS IDCategorie,
        AgendaEvénement.DateDébut AS DateDebut,
        AgendaEvénement.IDprevisionRecrut AS IDprevisionRecrut,
        AgendaEvénement.IDSalarie AS Recruteur,
        {op_crea_field} AS OPCrea,
        AgendaCatégorie.Lib_Catégorie AS Lib_Categorie,
        AgendaCatégorie.IdCvStatut AS IdCvStatutAg
    FROM AgendaCatégorie
    INNER JOIN AgendaEvénement
        ON AgendaCatégorie.IDAgendaCatégorie = AgendaEvénement.IDCatégorie
    INNER JOIN CvSuivi
        ON AgendaEvénement.IDCvSuivi = CvSuivi.IDCvSuivi
    INNER JOIN cvtheque
        ON CvSuivi.IDcvtheque = cvtheque.IDcvtheque
    WHERE AgendaEvénement.ModifElem <> 'suppr'
      AND CvSuivi.TypeElem = 'RDV'
      AND CvSuivi.Observation LIKE 'RDV pris%'
      AND {where_date}
      {where_op}
    """

    rows = db_rec.query(sql, tuple(params))

    # Collecte des IDs pour lookups batch
    op_ids: set[int] = set()
    rec_ids: set[int] = set()
    cvtheque_ids: set[int] = set()
    for r in rows:
        op_ids.add(_to_int(r.get("OPCrea")))
        rec_ids.add(_to_int(r.get("Recruteur")))
        cvtheque_ids.add(_to_int(r.get("IDcvtheque")))

    # Noms des salaries (operateurs + recruteurs)
    all_salarie_ids = (op_ids | rec_ids) - {0}
    salarie_names: dict[int, str] = {}
    if all_salarie_ids:
        ids_sql = ",".join(str(i) for i in all_salarie_ids)
        sal_rows = db_rh.query(
            f"SELECT IDSalarie, Nom, Prenom FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for s in sal_rows:
            sid = _to_int(s.get("IDSalarie"))
            nom = (s.get("Nom") or "").strip()
            prenom = _capitalize(s.get("Prenom") or "")
            salarie_names[sid] = f"{nom} {prenom}".strip()

    # Embauches effectives : IDcvtheque presents dans salarie_embauche (pour JO)
    embauche_cvtheque: set[int] = set()
    if cvtheque_ids - {0}:
        cv_sql = ",".join(str(i) for i in (cvtheque_ids - {0}))
        emb_rows = db_rh.query(
            f"SELECT DISTINCT IDcvtheque FROM salarie_embauche WHERE IDcvtheque IN ({cv_sql})"
        )
        for e in emb_rows:
            embauche_cvtheque.add(_to_int(e.get("IDcvtheque")))

    # Agregation + construction des lignes
    def make_agg() -> dict:
        return {"rdv": 0, "presents": 0, "retenus": 0, "venus_jo": 0}

    op_agg: dict[int, dict] = defaultdict(make_agg)
    rec_agg: dict[int, dict] = defaultdict(make_agg)
    non_statues = 0
    rdv_list: list[dict] = []

    for r in rows:
        op_id = _to_int(r.get("OPCrea"))
        rec_id = _to_int(r.get("Recruteur"))
        cv_id = _to_int(r.get("IDcvtheque"))
        id_cat = _to_int(r.get("IDCategorie"))
        id_stat_ag = _to_int(r.get("IdCvStatutAg"))

        op_agg[op_id]["rdv"] += 1
        rec_agg[rec_id]["rdv"] += 1

        est_present = id_stat_ag == 101 or id_stat_ag == 102 or id_stat_ag >= 105
        est_retenu = id_stat_ag == 101 or id_stat_ag >= 106

        if est_present:
            op_agg[op_id]["presents"] += 1
            rec_agg[rec_id]["presents"] += 1
        if est_retenu:
            op_agg[op_id]["retenus"] += 1
            rec_agg[rec_id]["retenus"] += 1

        if id_cat == 1 or id_cat == 11:
            non_statues += 1

        # JO : IDCategorie = 8 OU candidat embauche
        est_jo = id_cat == 8 or cv_id in embauche_cvtheque
        if est_jo:
            op_agg[op_id]["venus_jo"] += 1
            rec_agg[rec_id]["venus_jo"] += 1

        rdv_list.append({
            "id_cvtheque": str(cv_id),
            "nom": (r.get("Nom") or "").strip(),
            "prenom": _capitalize(r.get("Prenom") or ""),
            "gsm": r.get("GSM") or "",
            "date_crea": r.get("Datecrea") or "",
            "date_debut": r.get("DateDebut") or "",
            "lib_categorie": r.get("Lib_Categorie") or "",
            "statut_lib": r.get("Lib_Categorie") or "",
            "recruteur_nom": salarie_names.get(rec_id, ""),
            "op_crea_nom": salarie_names.get(op_id, ""),
        })

    operateurs = [
        {"id": str(op_id), "nom": salarie_names.get(op_id, f"ID {op_id}"), **stats}
        for op_id, stats in op_agg.items()
    ]
    recruteurs = [
        {"id": str(rec_id), "nom": salarie_names.get(rec_id, f"ID {rec_id}"), **stats}
        for rec_id, stats in rec_agg.items()
    ]

    return {
        "rdv": rdv_list,
        "operateurs": sorted(operateurs, key=lambda x: x["nom"].lower()),
        "recruteurs": sorted(recruteurs, key=lambda x: x["nom"].lower()),
        "non_statues": non_statues,
    }
