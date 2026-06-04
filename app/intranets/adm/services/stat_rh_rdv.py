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
from datetime import date, datetime

from app.core.database.pg import get_pg_connection


def _iso(v) -> str:
    """PG renvoie des date/datetime natifs ; on serialise en ISO 'YYYY-MM-DD HH:MM:SS'."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


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
    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")

    # Bornes datetime au format PostgreSQL ISO ('YYYY-MM-DD HH:MM:SS').
    # PG refuse le format compact WinDev YYYYMMDDHHMMSS sur les colonnes timestamp.
    param_deb = f"{date_debut[:4]}-{date_debut[4:6]}-{date_debut[6:8]} 00:00:00"
    param_fin = f"{date_fin[:4]}-{date_fin[4:6]}-{date_fin[6:8]} 23:59:59"

    # Choix du champ de filtre de date + du champ op_crea a utiliser
    if type_date == "planif":
        where_date = "cs.datecrea BETWEEN ? AND ?"
        op_crea_field = "cs.op_crea"
    else:
        where_date = "ae.date_debut BETWEEN ? AND ?"
        op_crea_field = "ae.op_crea"

    params: list = [param_deb, param_fin]
    where_op = ""
    if op_crea_filter is not None and op_crea_filter > 0:
        where_op = f"AND {op_crea_field} = ?"
        params.append(op_crea_filter)

    # Requete principale (uniquement tables de Bdd_Omaya_Recrutement)
    sql = f"""
    SELECT
        c.id_cvtheque AS id_cvtheque,
        c.nom AS nom,
        c.prenom AS prenom,
        c.gsm AS gsm,
        c.id_cvsource AS id_cvsource,
        c.id_elem_source AS id_elem_source,
        cs.datecrea AS datecrea,
        cs.id_cv_statut AS id_cv_statut,
        ae.id_categorie AS id_categorie,
        ae.date_debut AS date_debut,
        ae.id_prevision_recrut AS id_prevision_recrut,
        ae.id_salarie AS recruteur,
        {op_crea_field} AS op_crea,
        ac.lib_categorie AS lib_categorie,
        ac.id_cv_statut AS id_cv_statut_ag,
        src.lib_source AS lib_source
    FROM pgt_agenda_categorie ac
    INNER JOIN pgt_agenda_evenement ae
        ON ac.id_agenda_categorie = ae.id_categorie
    INNER JOIN pgt_cvsuivi cs
        ON ae.id_cv_suivi = cs.id_cv_suivi
    INNER JOIN pgt_cvtheque c
        ON cs.id_cvtheque = c.id_cvtheque
    LEFT JOIN pgt_cv_source src
        ON src.id_cvsource = c.id_cvsource
    WHERE ae.modif_elem <> 'suppr'
      AND cs.type_elem = 'RDV'
      AND cs.observation LIKE 'RDV pris%'
      AND {where_date}
      {where_op}
    """

    rows = db_rec.query(sql, tuple(params))

    # Sanity : filtrer les rows avec des ids corrompus (2^64-1 = NULL HFSQL)
    def _valid(n: int) -> bool:
        return 0 <= n < 9_000_000_000_000_000_000

    rows = [
        r for r in rows
        if _valid(_to_int(r.get("op_crea")))
        and _valid(_to_int(r.get("recruteur")))
        and _valid(_to_int(r.get("id_elem_source")))
    ]

    # Collecte des IDs pour lookups batch
    op_ids: set[int] = set()
    rec_ids: set[int] = set()
    cvtheque_ids: set[int] = set()
    coopteur_ids: set[int] = set()  # id_elem_source pour id_cvsource = 1 (salarie)
    annonceur_ids: set[int] = set()  # id_elem_source pour id_cvsource = 2 (annonceur)
    for r in rows:
        op_ids.add(_to_int(r.get("op_crea")))
        rec_ids.add(_to_int(r.get("recruteur")))
        cvtheque_ids.add(_to_int(r.get("id_cvtheque")))
        id_src = _to_int(r.get("id_cvsource"))
        id_elem = _to_int(r.get("id_elem_source"))
        if id_src == 1 and id_elem > 0:
            coopteur_ids.add(id_elem)
        elif id_src == 2 and id_elem > 0:
            annonceur_ids.add(id_elem)

    # Noms des salaries (operateurs + recruteurs + coopteurs)
    all_salarie_ids = (op_ids | rec_ids | coopteur_ids) - {0}
    salarie_names: dict[int, str] = {}
    if all_salarie_ids:
        ids_sql = ",".join(str(i) for i in all_salarie_ids)
        sal_rows = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for s in sal_rows:
            sid = _to_int(s.get("id_salarie"))
            nom = (s.get("nom") or "").strip()
            prenom = _capitalize(s.get("prenom") or "")
            salarie_names[sid] = f"{nom} {prenom}".strip()

    # Libelles annonceurs
    annonceur_lib_map: dict[int, str] = {}
    if annonceur_ids:
        ids_sql = ",".join(str(i) for i in annonceur_ids)
        try:
            a_rows = db_rec.query(
                f"SELECT id_cv_annonceur, lib_annonceur FROM pgt_cv_annonceur WHERE id_cv_annonceur IN ({ids_sql})"
            )
            for a in a_rows:
                annonceur_lib_map[_to_int(a.get("id_cv_annonceur"))] = a.get("lib_annonceur") or ""
        except Exception:
            pass

    # Embauches effectives : id_cvtheque presents dans salarie_embauche (pour JO)
    embauche_cvtheque: set[int] = set()
    if cvtheque_ids - {0}:
        cv_sql = ",".join(str(i) for i in (cvtheque_ids - {0}))
        emb_rows = db_rh.query(
            f"SELECT DISTINCT id_cvtheque FROM pgt_salarie_embauche WHERE id_cvtheque IN ({cv_sql})"
        )
        for e in emb_rows:
            embauche_cvtheque.add(_to_int(e.get("id_cvtheque")))

    # Agregation + construction des lignes
    def make_agg() -> dict:
        return {"rdv": 0, "presents": 0, "retenus": 0, "venus_jo": 0}

    op_agg: dict[int, dict] = defaultdict(make_agg)
    rec_agg: dict[int, dict] = defaultdict(make_agg)
    non_statues = 0
    rdv_list: list[dict] = []

    for r in rows:
        op_id = _to_int(r.get("op_crea"))
        rec_id = _to_int(r.get("recruteur"))
        cv_id = _to_int(r.get("id_cvtheque"))
        id_cat = _to_int(r.get("id_categorie"))
        id_stat_ag = _to_int(r.get("id_cv_statut_ag"))

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

        id_src = _to_int(r.get("id_cvsource"))
        id_elem = _to_int(r.get("id_elem_source"))
        annonceur_coopteur = ""
        if id_src == 1 and id_elem > 0:
            annonceur_coopteur = salarie_names.get(id_elem, "")
        elif id_src == 2 and id_elem > 0:
            annonceur_coopteur = annonceur_lib_map.get(id_elem, "")

        rdv_list.append({
            "id_cvtheque": str(cv_id),
            "nom": (r.get("nom") or "").strip(),
            "prenom": _capitalize(r.get("prenom") or ""),
            "gsm": r.get("gsm") or "",
            "date_crea": _iso(r.get("datecrea")),
            "date_debut": _iso(r.get("date_debut")),
            "lib_categorie": r.get("lib_categorie") or "",
            "statut_lib": r.get("lib_categorie") or "",
            "recruteur_id": str(rec_id),
            "recruteur_nom": salarie_names.get(rec_id, ""),
            "op_crea_id": str(op_id),
            "op_crea_nom": salarie_names.get(op_id, ""),
            "id_source": id_src,
            "lib_source": r.get("lib_source") or "",
            "annonceur_coopteur": annonceur_coopteur,
            "est_present": est_present,
            "est_retenu": est_retenu,
            "est_jo": est_jo,
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
