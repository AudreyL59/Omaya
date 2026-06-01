"""
Service Stats RH - DPAE / Sortie.

Transposition de la procedure WinDev Fen_StatRH_EntreeSortie.

Logique :
  - DPAE : salaries dont salarie_embauche.DateDebut est dans la periode
           (= nouvelle embauche sur la periode)
  - Sorties : salaries dont salarie_sortie.DateSortieDemandee est dans la periode
  - Mode "reseau" : tous (IdSte <> 4 = exclude distributeur)
  - Mode "orga" : limite aux salaries rattaches a une orga descendante
                  de id_orga (via salarie_organigramme)
  - Resume : agregation par orga (agence ou equipe) avec compteurs et durees
"""

import base64
import struct
from collections import defaultdict
from datetime import date
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


def _date_diff_days(d1: str, d2: str) -> int:
    """Nombre de jours entre d1 et d2 (format WinDev YYYYMMDD... ou ISO)."""
    def _parse(s: str) -> Optional[date]:
        if not s:
            return None
        try:
            if "-" in s:
                return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
            if len(s) >= 8 and s[:8].isdigit():
                return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            return None
        return None

    a = _parse(d1)
    b = _parse(d2)
    if not a or not b:
        return 0
    return max(0, (b - a).days)


def _descendants_orga(all_orgas: list[dict], root_ids: set[int]) -> set[int]:
    """Descendants recursifs (inclut les root_ids)."""
    result = set(root_ids)
    frontier = set(root_ids)
    while frontier:
        next_frontier: set[int] = set()
        for o in all_orgas:
            parent = _to_int(o.get("id_parent"))
            if parent in frontier:
                oid = _to_int(o.get("idorganigramme"))
                if oid and oid not in result:
                    result.add(oid)
                    next_frontier.add(oid)
        frontier = next_frontier
    return result


def calculer_stats_entree_sortie(
    date_debut: str,   # YYYYMMDD
    date_fin: str,     # YYYYMMDD
    type_recherche: str,  # "reseau" ou "orga"
    id_orgas: Optional[list[int]] = None,
) -> dict:
    db_rh = get_pg_connection("rh")
    db_adv = get_pg_connection("adv")

    param_deb = f"{date_debut}000000"
    param_fin = f"{date_fin}235959"

    # --- Scope orga : descendants de toutes les orgas selectionnees -------
    orga_ids: Optional[set[int]] = None
    all_orgas = db_rh.query(
        """SELECT idorganigramme, id_parent, lib_orga, id_type_niveau_orga, id_ste
        FROM pgt_organigramme
        WHERE modif_elem <> 'suppr'"""
    )
    if type_recherche == "orga" and id_orgas:
        orga_ids = _descendants_orga(all_orgas, set(id_orgas))

    # --- Requete DPAE -----------------------------------------------------
    sql_dpae_base = """
        SELECT DISTINCT s.id_salarie, s.nom, s.prenom,
            sc.adresse1, sc.cp, sc.ville,
            se.date_debut, se.en_activite, se.id_ste, se.id_cvtheque,
            se.j_odirecte, se.jo_coopteur, se.coopte, se.coopteur
        FROM pgt_salarie s
        INNER JOIN pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
        LEFT JOIN pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
    """
    where_dpae = [
        "s.modif_elem <> 'suppr'",
        "se.modif_elem <> 'suppr'",
        "se.id_ste <> 4",
        "se.date_debut BETWEEN ? AND ?",
    ]
    params_dpae: list = [param_deb, param_fin]

    if orga_ids is not None:
        if not orga_ids:
            return {"dpae": [], "sorties": [], "resume": []}
        ids_sql = ",".join(str(i) for i in orga_ids)
        sql_dpae_base += f" INNER JOIN pgt_salarie_organigramme so ON so.id_salarie = s.id_salarie"
        where_dpae.append(f"so.idorganigramme IN ({ids_sql})")
        where_dpae.append(f"LEFT(so.date_debut, 8) <= ?")
        params_dpae.append(date_fin)

    sql_dpae = sql_dpae_base + " WHERE " + " AND ".join(where_dpae)
    dpae_rows = db_rh.query(sql_dpae, tuple(params_dpae))

    # --- Requete Sorties --------------------------------------------------
    sql_sortie_base = """
        SELECT DISTINCT s.id_salarie, s.nom, s.prenom,
            sc.adresse1, sc.cp, sc.ville,
            ss.date_sortie_reelle, ss.date_sortie_demandee, ss.id_type_sortie,
            se.en_activite, se.date_debut, se.id_ste
        FROM pgt_salarie s
        INNER JOIN pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
        INNER JOIN pgt_salarie_sortie ss ON ss.id_salarie = s.id_salarie
        LEFT JOIN pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
    """
    where_sortie = [
        "s.modif_elem <> 'suppr'",
        "ss.modif_elem <> 'suppr'",
        "se.id_ste <> 4",
        "se.en_activite = FALSE",
        "ss.date_sortie_demandee BETWEEN ? AND ?",
    ]
    params_sortie: list = [param_deb, param_fin]
    if orga_ids is not None and orga_ids:
        ids_sql = ",".join(str(i) for i in orga_ids)
        sql_sortie_base += " INNER JOIN pgt_salarie_organigramme so2 ON so2.id_salarie = s.id_salarie"
        where_sortie.append(f"so2.idorganigramme IN ({ids_sql})")

    sql_sortie = sql_sortie_base + " WHERE " + " AND ".join(where_sortie)
    sortie_rows = db_rh.query(sql_sortie, tuple(params_sortie))

    # --- Lookup orga de rattachement par salarie (pour le Resume) ---------
    all_salarie_ids = set()
    for r in dpae_rows:
        all_salarie_ids.add(_to_int(r.get("id_salarie")))
    for r in sortie_rows:
        all_salarie_ids.add(_to_int(r.get("id_salarie")))
    all_salarie_ids.discard(0)

    # Orgas valides pour le rattachement :
    # - si scope orga : uniquement les descendants du/des bloc(s) selectionne(s)
    # - sinon : toutes les orgas non-supprimees
    valid_orgas = orga_ids if orga_ids is not None else {
        _to_int(o.get("idorganigramme")) for o in all_orgas
    }
    valid_orgas.discard(0)

    # On prend l'orga la plus recente (date_debut max) du salarié parmi les orgas valides
    salarie_to_orga: dict[int, int] = {}
    if all_salarie_ids:
        ids_sql = ",".join(str(i) for i in all_salarie_ids)
        so_rows = db_rh.query(
            f"""SELECT id_salarie, idorganigramme, date_debut
            FROM pgt_salarie_organigramme
            WHERE id_salarie IN ({ids_sql})
              AND modif_elem <> 'suppr'
            ORDER BY id_salarie, date_debut DESC"""
        )
        for r in so_rows:
            sid = _to_int(r.get("id_salarie"))
            oid = _to_int(r.get("idorganigramme"))
            if sid and oid in valid_orgas and sid not in salarie_to_orga:
                salarie_to_orga[sid] = oid

    # --- Productifs : via ADV.{prefix}_contrat (reuse Vendeur organigramme logic) ---
    # Plus simple : on recupere juste la liste des IDSalarie ayant au moins un contrat,
    # tous partenaires confondus.
    productifs: set[int] = set()
    if all_salarie_ids:
        part_rows = db_adv.query(
            "SELECT prefixe_bdd FROM pgt_partenaire WHERE is_actif = TRUE AND modif_elem <> 'suppr'"
        )
        prefixes = [(p.get("prefixe_bdd") or "").strip() for p in part_rows]
        prefixes = [p for p in prefixes if p]
        ids_sal_sql_quoted = ",".join(f"'{i}'" for i in all_salarie_ids)

        import logging
        from concurrent.futures import ThreadPoolExecutor

        def fetch_contrat(prefix: str) -> list[int]:
            db = get_pg_connection("adv")
            try:
                rows = db.query(
                    f"""SELECT DISTINCT id_salarie
                    FROM pgt_{prefix.lower()}_contrat
                    WHERE id_salarie IN ({ids_sal_sql_quoted})
                      AND date_signature <> ''
                      AND modif_elem NOT LIKE '%suppr%'"""
                )
                return [_to_int(r.get("id_salarie")) for r in rows]
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"[ENTREE-SORTIE] fetch_contrat({prefix}) failed: {e}"
                )
                return []

        if prefixes:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for ids in pool.map(fetch_contrat, prefixes):
                    productifs.update(i for i in ids if i > 0)

    # --- Labels TypeSortieSalarie -----------------------------------------
    type_sortie_map: dict[int, str] = {}
    try:
        ts_rows = db_rh.query("SELECT id_type_sortie, lib_sortie FROM pgt_type_sortie_salarie")
        for t in ts_rows:
            type_sortie_map[_to_int(t.get("id_type_sortie"))] = t.get("lib_sortie") or ""
    except Exception:
        pass

    # --- Lookup origine DPAE via cvtheque.IDcvsource ----------------------
    # id_cvsource = 1 : cooptation (salarie) ; 2+ : CVtheque / annonceur / autre
    db_rec = get_pg_connection("recrutement")
    cvtheque_source: dict[int, int] = {}
    cvtheque_ids_dpae = {
        _to_int(r.get("id_cvtheque"))
        for r in dpae_rows
        if _to_int(r.get("id_cvtheque")) > 0
    }
    if cvtheque_ids_dpae:
        cv_sql = ",".join(str(i) for i in cvtheque_ids_dpae)
        cv_rows = db_rec.query(
            f"SELECT id_cvtheque, id_cvsource FROM pgt_cvtheque WHERE id_cvtheque IN ({cv_sql})"
        )
        for c in cv_rows:
            cvtheque_source[_to_int(c.get("id_cvtheque"))] = _to_int(c.get("id_cvsource"))

    # --- Lookup des sorties pour les DPAE inactifs ------------------------
    # Pour un DPAE dont EnActivité = 0, on veut date_sortie + fin_demandee
    sortie_by_sal: dict[int, dict] = {}
    dpae_inactif_ids = {
        _to_int(r.get("id_salarie"))
        for r in dpae_rows
        if not bool(r.get("en_activite")) and _to_int(r.get("id_salarie")) > 0
    }
    if dpae_inactif_ids:
        ids_sql = ",".join(str(i) for i in dpae_inactif_ids)
        ss_rows = db_rh.query(
            f"""SELECT id_salarie, date_sortie_reelle, date_sortie_demandee
            FROM pgt_salarie_sortie
            WHERE id_salarie IN ({ids_sql})
              AND modif_elem <> 'suppr'
            ORDER BY id_salarie, date_sortie_demandee DESC"""
        )
        for r in ss_rows:
            sid = _to_int(r.get("id_salarie"))
            if sid and sid not in sortie_by_sal:
                sortie_by_sal[sid] = {
                    "date_sortie": r.get("date_sortie_reelle") or "",
                    "fin_demandee": r.get("date_sortie_demandee") or "",
                }

    # --- Lookup societe : IdSte → RS_Interne ------------------------------
    societe_rs: dict[int, str] = {}
    try:
        ste_rows = db_rh.query("SELECT id_ste, rs_interne FROM pgt_societe")
        for s in ste_rows:
            societe_rs[_to_int(s.get("id_ste"))] = s.get("rs_interne") or ""
    except Exception:
        pass

    # --- Helper : agence + équipe d'un salarié à partir de son orga ------
    # orga_info construit ici, réutilisé plus bas dans le bloc Resume.
    orga_info: dict[int, dict] = {}
    for o in all_orgas:
        oid = _to_int(o.get("idorganigramme"))
        orga_info[oid] = {
            "lib_orga": o.get("lib_orga") or "",
            "id_parent": _to_int(o.get("id_parent")),
        }

    def _agence_equipe(id_orga: int) -> tuple[str, str]:
        info = orga_info.get(id_orga)
        if not info:
            return ("", "")
        equipe_lib = info["lib_orga"]
        parent_id = info["id_parent"]
        parent_info = orga_info.get(parent_id, {})
        agence_lib = parent_info.get("lib_orga", "")
        return (agence_lib, equipe_lib)

    # --- Construction des lignes DPAE -------------------------------------
    dpae_list: list[dict] = []
    for r in dpae_rows:
        sid = _to_int(r.get("id_salarie"))
        id_orga_sal = salarie_to_orga.get(sid, 0)
        sortie = sortie_by_sal.get(sid, {})
        id_cvtheque = _to_int(r.get("id_cvtheque"))
        id_source = cvtheque_source.get(id_cvtheque, 0)
        origine = "Cooptation" if id_source <= 1 or id_cvtheque == 0 else "CVtheque"
        id_ste = _to_int(r.get("id_ste"))
        agence_lib, equipe_lib = _agence_equipe(id_orga_sal)
        dpae_list.append({
            "id_salarie": str(sid),
            "id_ste": id_ste,
            "rs_interne": societe_rs.get(id_ste, ""),
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
            "adresse": r.get("adresse1") or "",
            "cp": r.get("cp") or "",
            "ville": r.get("ville") or "",
            "date_entree": r.get("date_debut") or "",
            "en_activite": bool(r.get("en_activite")),
            "date_sortie": sortie.get("date_sortie", ""),
            "fin_demandee": sortie.get("fin_demandee", ""),
            "origine": origine,
            "detail_origine": "",
            "id_orga": str(id_orga_sal),
            "agence": agence_lib,
            "equipe": equipe_lib,
            "prod": sid in productifs,
        })

    # --- Construction des lignes Sortie -----------------------------------
    sortie_list: list[dict] = []
    for r in sortie_rows:
        sid = _to_int(r.get("id_salarie"))
        id_orga_sal = salarie_to_orga.get(sid, 0)
        id_type = _to_int(r.get("id_type_sortie"))
        id_ste = _to_int(r.get("id_ste"))
        agence_lib, equipe_lib = _agence_equipe(id_orga_sal)
        sortie_list.append({
            "id_salarie": str(sid),
            "id_ste": id_ste,
            "rs_interne": societe_rs.get(id_ste, ""),
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
            "adresse": r.get("adresse1") or "",
            "cp": r.get("cp") or "",
            "ville": r.get("ville") or "",
            "date_entree": r.get("date_debut") or "",
            "date_sortie_reelle": r.get("date_sortie_reelle") or "",
            "fin_demandee": r.get("date_sortie_demandee") or "",
            "id_type_sortie": id_type,
            "type_sortie_lib": type_sortie_map.get(id_type, ""),
            "id_orga": str(id_orga_sal),
            "agence": agence_lib,
            "equipe": equipe_lib,
            "prod": sid in productifs,
        })

    # --- Agregation par orga (Resume) -------------------------------------
    # orga_info déjà construit plus haut. Map id -> Lib_ORGA pour le parent.
    orga_libs: dict[int, str] = {
        oid: info["lib_orga"] for oid, info in orga_info.items()
    }

    resume_agg: dict[int, dict] = defaultdict(
        lambda: {
            "nb_dpae": 0,
            "nb_sortants_non_prod": 0,
            "nb_jour_non_prod": 0,
            "nb_sortants_prod": 0,
            "nb_jour_prod": 0,
        }
    )
    # Note : id_orga est expose en string dans les lignes, mais on agrege par int ici
    # pour pouvoir lookup dans orga_info (dont les cles sont des int Python).
    for d in dpae_list:
        resume_agg[int(d["id_orga"])]["nb_dpae"] += 1
    for s in sortie_list:
        duree = _date_diff_days(s["date_entree"], s["date_sortie_reelle"] or s["fin_demandee"])
        oid = int(s["id_orga"])
        if s["prod"]:
            resume_agg[oid]["nb_sortants_prod"] += 1
            resume_agg[oid]["nb_jour_prod"] += duree
        else:
            resume_agg[oid]["nb_sortants_non_prod"] += 1
            resume_agg[oid]["nb_jour_non_prod"] += duree

    resume_list = []
    for oid, stats in resume_agg.items():
        info = orga_info.get(oid, {})
        parent_id = info.get("id_parent", 0)
        resume_list.append({
            "id_orga": str(oid),
            "lib_orga": info.get("lib_orga", f"ID {oid}" if oid else "Sans orga"),
            "id_parent": str(parent_id),
            "lib_parent": orga_libs.get(parent_id, "Reseau") if parent_id else "Reseau",
            **stats,
        })

    # Tri par lib_parent puis lib_orga
    resume_list.sort(key=lambda r: (r["lib_parent"].lower(), r["lib_orga"].lower()))

    return {
        "dpae": dpae_list,
        "sorties": sortie_list,
        "resume": resume_list,
    }
