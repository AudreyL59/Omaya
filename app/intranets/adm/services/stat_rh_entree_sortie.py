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
            parent = _to_int(o.get("IdPARENT"))
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
    db_rh = get_connection("rh")
    db_adv = get_connection("adv")

    param_deb = f"{date_debut}000000"
    param_fin = f"{date_fin}235959"

    # --- Scope orga : descendants de toutes les orgas selectionnees -------
    orga_ids: Optional[set[int]] = None
    all_orgas = db_rh.query(
        """SELECT idorganigramme, IdPARENT, Lib_ORGA, IDTypeNiveauOrga, IdSte
        FROM organigramme
        WHERE ModifELEM <> 'suppr'"""
    )
    if type_recherche == "orga" and id_orgas:
        orga_ids = _descendants_orga(all_orgas, set(id_orgas))

    # --- Requete DPAE -----------------------------------------------------
    sql_dpae_base = """
        SELECT DISTINCT s.IDSalarie, s.Nom, s.Prenom,
            sc.ADRESSE1, sc.CP, sc.VILLE,
            se.DateDebut, se.EnActivité, se.IdSte, se.IDcvtheque,
            se.JOdirecte, se.JOCoopteur, se.Coopté, se.Coopteur
        FROM salarie s
        INNER JOIN salarie_embauche se ON se.IDSalarie = s.IDSalarie
        LEFT JOIN salarie_coordonnées sc ON sc.IDSalarie = s.IDSalarie
    """
    where_dpae = [
        "s.ModifELEM <> 'suppr'",
        "se.ModifELEM <> 'suppr'",
        "se.IdSte <> 4",
        "se.DateDebut BETWEEN ? AND ?",
    ]
    params_dpae: list = [param_deb, param_fin]

    if orga_ids is not None:
        if not orga_ids:
            return {"dpae": [], "sorties": [], "resume": []}
        ids_sql = ",".join(str(i) for i in orga_ids)
        sql_dpae_base += f" INNER JOIN salarie_organigramme so ON so.IDSalarie = s.IDSalarie"
        where_dpae.append(f"so.idorganigramme IN ({ids_sql})")
        where_dpae.append(f"LEFT(so.DateDébut, 8) <= ?")
        params_dpae.append(date_fin)

    sql_dpae = sql_dpae_base + " WHERE " + " AND ".join(where_dpae)
    dpae_rows = db_rh.query(sql_dpae, tuple(params_dpae))

    # --- Requete Sorties --------------------------------------------------
    sql_sortie_base = """
        SELECT DISTINCT s.IDSalarie, s.Nom, s.Prenom,
            sc.ADRESSE1, sc.CP, sc.VILLE,
            ss.DateSortieRéelle, ss.DateSortieDemandée, ss.IDTypeSortie,
            se.EnActivité, se.DateDebut, se.IdSte
        FROM salarie s
        INNER JOIN salarie_embauche se ON se.IDSalarie = s.IDSalarie
        INNER JOIN salarie_sortie ss ON ss.IDSalarie = s.IDSalarie
        LEFT JOIN salarie_coordonnées sc ON sc.IDSalarie = s.IDSalarie
    """
    where_sortie = [
        "s.ModifELEM <> 'suppr'",
        "ss.ModifELEM <> 'suppr'",
        "se.IdSte <> 4",
        "se.EnActivité = 0",
        "ss.DateSortieDemandée BETWEEN ? AND ?",
    ]
    params_sortie: list = [param_deb, param_fin]
    if orga_ids is not None and orga_ids:
        ids_sql = ",".join(str(i) for i in orga_ids)
        sql_sortie_base += " INNER JOIN salarie_organigramme so2 ON so2.IDSalarie = s.IDSalarie"
        where_sortie.append(f"so2.idorganigramme IN ({ids_sql})")

    sql_sortie = sql_sortie_base + " WHERE " + " AND ".join(where_sortie)
    sortie_rows = db_rh.query(sql_sortie, tuple(params_sortie))

    # --- Lookup orga de rattachement par salarie (pour le Resume) ---------
    all_salarie_ids = set()
    for r in dpae_rows:
        all_salarie_ids.add(_to_int(r.get("IDSalarie")))
    for r in sortie_rows:
        all_salarie_ids.add(_to_int(r.get("IDSalarie")))
    all_salarie_ids.discard(0)

    # Orgas valides pour le rattachement :
    # - si scope orga : uniquement les descendants du/des bloc(s) selectionne(s)
    # - sinon : toutes les orgas non-supprimees
    valid_orgas = orga_ids if orga_ids is not None else {
        _to_int(o.get("idorganigramme")) for o in all_orgas
    }
    valid_orgas.discard(0)

    # On prend l'orga la plus recente (DateDébut max) du salarié parmi les orgas valides
    salarie_to_orga: dict[int, int] = {}
    if all_salarie_ids:
        ids_sql = ",".join(str(i) for i in all_salarie_ids)
        so_rows = db_rh.query(
            f"""SELECT IDSalarie, idorganigramme, DateDébut
            FROM salarie_organigramme
            WHERE IDSalarie IN ({ids_sql})
              AND ModifELEM <> 'suppr'
            ORDER BY IDSalarie, DateDébut DESC"""
        )
        for r in so_rows:
            sid = _to_int(r.get("IDSalarie"))
            oid = _to_int(r.get("idorganigramme"))
            if sid and oid in valid_orgas and sid not in salarie_to_orga:
                salarie_to_orga[sid] = oid

    # --- Productifs : via ADV.{prefix}_contrat (reuse Vendeur organigramme logic) ---
    # Plus simple : on recupere juste la liste des IDSalarie ayant au moins un contrat,
    # tous partenaires confondus.
    productifs: set[int] = set()
    if all_salarie_ids:
        part_rows = db_adv.query(
            "SELECT PréfixeBDD FROM Partenaire WHERE IsActif = 1 AND ModifElem <> 'suppr'"
        )
        prefixes = [(p.get("PréfixeBDD") or "").strip() for p in part_rows]
        prefixes = [p for p in prefixes if p]
        ids_sal_sql_quoted = ",".join(f"'{i}'" for i in all_salarie_ids)

        import logging
        from concurrent.futures import ThreadPoolExecutor

        def fetch_contrat(prefix: str) -> list[int]:
            db = get_connection("adv")
            try:
                rows = db.query(
                    f"""SELECT DISTINCT IDSalarie
                    FROM {prefix}_contrat
                    WHERE IDSalarie IN ({ids_sal_sql_quoted})
                      AND DateSignature <> ''
                      AND ModifElem NOT LIKE '%suppr%'"""
                )
                return [_to_int(r.get("IDSalarie")) for r in rows]
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
        ts_rows = db_rh.query("SELECT IDTypeSortie, Lib_Sortie FROM TypeSortieSalarie")
        for t in ts_rows:
            type_sortie_map[_to_int(t.get("IDTypeSortie"))] = t.get("Lib_Sortie") or ""
    except Exception:
        pass

    # --- Lookup des sorties pour les DPAE inactifs ------------------------
    # Pour un DPAE dont EnActivité = 0, on veut date_sortie + fin_demandee
    sortie_by_sal: dict[int, dict] = {}
    dpae_inactif_ids = {
        _to_int(r.get("IDSalarie"))
        for r in dpae_rows
        if not bool(r.get("EnActivité")) and _to_int(r.get("IDSalarie")) > 0
    }
    if dpae_inactif_ids:
        ids_sql = ",".join(str(i) for i in dpae_inactif_ids)
        ss_rows = db_rh.query(
            f"""SELECT IDSalarie, DateSortieRéelle, DateSortieDemandée
            FROM salarie_sortie
            WHERE IDSalarie IN ({ids_sql})
              AND ModifELEM <> 'suppr'
            ORDER BY IDSalarie, DateSortieDemandée DESC"""
        )
        for r in ss_rows:
            sid = _to_int(r.get("IDSalarie"))
            if sid and sid not in sortie_by_sal:
                sortie_by_sal[sid] = {
                    "date_sortie": r.get("DateSortieRéelle") or "",
                    "fin_demandee": r.get("DateSortieDemandée") or "",
                }

    # --- Construction des lignes DPAE -------------------------------------
    dpae_list: list[dict] = []
    for r in dpae_rows:
        sid = _to_int(r.get("IDSalarie"))
        id_orga_sal = salarie_to_orga.get(sid, 0)
        sortie = sortie_by_sal.get(sid, {})
        dpae_list.append({
            "id_salarie": str(sid),
            "id_ste": _to_int(r.get("IdSte")),
            "nom": (r.get("Nom") or "").strip(),
            "prenom": (r.get("Prenom") or "").strip(),
            "adresse": r.get("ADRESSE1") or "",
            "cp": r.get("CP") or "",
            "ville": r.get("VILLE") or "",
            "date_entree": r.get("DateDebut") or "",
            "en_activite": bool(r.get("EnActivité")),
            "date_sortie": sortie.get("date_sortie", ""),
            "fin_demandee": sortie.get("fin_demandee", ""),
            "origine": "",
            "detail_origine": "",
            "id_orga": str(id_orga_sal),
            "prod": sid in productifs,
        })

    # --- Construction des lignes Sortie -----------------------------------
    sortie_list: list[dict] = []
    for r in sortie_rows:
        sid = _to_int(r.get("IDSalarie"))
        id_orga_sal = salarie_to_orga.get(sid, 0)
        id_type = _to_int(r.get("IDTypeSortie"))
        sortie_list.append({
            "id_salarie": str(sid),
            "id_ste": _to_int(r.get("IdSte")),
            "nom": (r.get("Nom") or "").strip(),
            "prenom": (r.get("Prenom") or "").strip(),
            "adresse": r.get("ADRESSE1") or "",
            "cp": r.get("CP") or "",
            "ville": r.get("VILLE") or "",
            "date_entree": r.get("DateDebut") or "",
            "date_sortie_reelle": r.get("DateSortieRéelle") or "",
            "fin_demandee": r.get("DateSortieDemandée") or "",
            "id_type_sortie": id_type,
            "type_sortie_lib": type_sortie_map.get(id_type, ""),
            "id_orga": str(id_orga_sal),
            "prod": sid in productifs,
        })

    # --- Agregation par orga (Resume) -------------------------------------
    # Libelles orga + parent
    orga_info: dict[int, dict] = {}
    for o in all_orgas:
        oid = _to_int(o.get("idorganigramme"))
        orga_info[oid] = {
            "lib_orga": o.get("Lib_ORGA") or "",
            "id_parent": _to_int(o.get("IdPARENT")),
        }
    # Map id -> Lib_ORGA (pour retrouver le nom du parent)
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
