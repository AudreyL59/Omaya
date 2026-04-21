"""
Service Organigramme : construction de l'arbre avec salariés par orga.

Tables (Bdd_Omaya_RH) :
  - organigramme : structure hiérarchique (IdPARENT)
  - TypeNiveauOrga : libellés des niveaux
  - salarie + salarie_embauche + salarie_organigramme : salariés actifs par orga
  - TypePoste : libellé du poste (Catégorie)
"""

import base64
import struct
from datetime import datetime

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


def _today_windev() -> str:
    return datetime.now().strftime("%Y%m%d")


def _descendants(all_orgas: list[dict], root_ids: set[int]) -> set[int]:
    """Depuis une liste plate d'orgas, trouve tous les descendants récursifs."""
    result = set(root_ids)
    frontier = set(root_ids)
    while frontier:
        next_frontier = set()
        for o in all_orgas:
            parent = _to_int(o.get("IdPARENT"))
            if parent in frontier:
                oid = _to_int(o.get("idorganigramme"))
                if oid and oid not in result:
                    result.add(oid)
                    next_frontier.add(oid)
        frontier = next_frontier
    return result


def get_organigramme(
    id_salarie_user: int,
    droits: list[str],
    is_resp: bool,
) -> list[dict]:
    """
    Retourne la liste des racines de l'arbre (chaque racine est un OrgaTreeNode
    récursif avec ses enfants et salariés).
    """
    db_rh = get_connection("rh")
    today = _today_windev()

    # 1. Toutes les orgas non-supprimées
    all_orgas = db_rh.query(
        """SELECT idorganigramme, IdPARENT, Lib_ORGA, IDTypeNiveauOrga, IDTypeOrga
        FROM organigramme
        WHERE ModifELEM <> 'suppr'"""
    )

    acces_global = "ProdRezo" in droits

    if acces_global:
        accessible_ids = {_to_int(o.get("idorganigramme")) for o in all_orgas}
        accessible_ids.discard(0)
    else:
        # Orgas actifs du user
        user_rows = db_rh.query(
            """SELECT DISTINCT idorganigramme FROM salarie_organigramme
            WHERE IDSalarie = ?
              AND ModifELEM <> 'suppr'
              AND LEFT(DateDébut, 8) <= ?""",
            (id_salarie_user, today),
        )
        user_orga_ids = {_to_int(r.get("idorganigramme")) for r in user_rows}
        user_orga_ids.discard(0)

        if (is_resp or "ProdGR" in droits) and user_orga_ids:
            accessible_ids = _descendants(all_orgas, user_orga_ids)
        else:
            accessible_ids = user_orga_ids

    if not accessible_ids:
        return []

    # 2. Niveaux
    niv_rows = db_rh.query(
        "SELECT IDTypeNiveauOrga, Lib_Niveau FROM TypeNiveauOrga"
    )
    niveaux_map = {
        _to_int(n.get("IDTypeNiveauOrga")): n.get("Lib_Niveau") or ""
        for n in niv_rows
    }

    # 3. Salariés par orga (chunks parallélisés pour amortir le coût subprocess)
    import time
    from concurrent.futures import ThreadPoolExecutor

    ids_list = list(accessible_ids)
    BATCH = 50

    def fetch_chunk(chunk: list[int]) -> list[dict]:
        ids_sql = ",".join(str(cid) for cid in chunk)
        db = get_connection("rh")
        return db.query(
            f"""SELECT so.idorganigramme, s.IDSalarie, s.NOM, s.PRENOM,
                se.RespEquipe, se.RespAdjoint, se.IdTypePoste,
                se.DateAncienneté, se.DateDebut,
                se.CJ_envoyé, se.FormationIAG, se.EnPause, se.Chauffeur
            FROM salarie s
            INNER JOIN salarie_embauche se ON s.IDSalarie = se.IDSalarie
            INNER JOIN salarie_organigramme so ON s.IDSalarie = so.IDSalarie
            WHERE so.idorganigramme IN ({ids_sql})
              AND so.ModifELEM <> 'suppr'
              AND LEFT(so.DateDébut, 8) <= ?
              AND (so.DateFin = '' OR LEFT(so.DateFin, 8) >= ?)
              AND se.EnActivité = 1
              AND s.ModifELEM <> 'suppr'
            ORDER BY se.RespEquipe DESC, se.RespAdjoint DESC, s.NOM ASC, s.PRENOM ASC""",
            (today, today),
        )

    chunks = [ids_list[i : i + BATCH] for i in range(0, len(ids_list), BATCH)]
    t0 = time.time()
    salaries_rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(fetch_chunk, chunks):
            salaries_rows.extend(result)

    import logging
    logging.getLogger(__name__).warning(
        f"[ORGA] {len(accessible_ids)} orgas, {len(salaries_rows)} salariés en {time.time() - t0:.1f}s"
    )

    # Poste labels + catégorie
    poste_ids = {_to_int(s.get("IdTypePoste")) for s in salaries_rows}
    poste_ids.discard(0)
    poste_map: dict[int, dict] = {}
    if poste_ids:
        ids_poste_sql = ",".join(str(i) for i in poste_ids)
        p_rows = db_rh.query(
            f"SELECT IdTypePoste, Lib_Poste, Catégorie FROM TypePoste WHERE IdTypePoste IN ({ids_poste_sql})"
        )
        for p in p_rows:
            poste_map[_to_int(p.get("IdTypePoste"))] = {
                "lib": p.get("Lib_Poste") or "",
                "cat": p.get("Catégorie") or "",
            }

    # Mutuelles + absences en batch pour tous les salariés
    all_salarie_ids = {_to_int(s.get("IDSalarie")) for s in salaries_rows}
    all_salarie_ids.discard(0)

    mutuelle_by_sal: dict[int, dict] = {}
    absence_by_sal: dict[int, dict] = {}

    if all_salarie_ids:
        ids_sal_sql = ",".join(str(i) for i in all_salarie_ids)

        mut_rows = db_rh.query(
            f"""SELECT sm.IDSalarie, sm.Adhésion, sm.IdMutuelle,
                sm.Mutuelle_PasAdhésion, sm.Mutuelle_PasAdhésionJusquau,
                m.Lib_Mutuelle
            FROM salarie_mutuelle sm
            LEFT JOIN mutuelle m ON m.IdMutuelle = sm.IdMutuelle
            WHERE sm.IDSalarie IN ({ids_sal_sql})"""
        )
        for m in mut_rows:
            sid = _to_int(m.get("IDSalarie"))
            mutuelle_by_sal[sid] = {
                "adhesion": bool(m.get("Adhésion")),
                "id": _to_int(m.get("IdMutuelle")),
                "lib": m.get("Lib_Mutuelle") or "",
                "pas_adhesion": bool(m.get("Mutuelle_PasAdhésion")),
                "fin_date": m.get("Mutuelle_PasAdhésionJusquau") or "",
            }

        # Absences (lib depuis TypeAbsence)
        abs_rows = db_rh.query(
            f"""SELECT IDSalarie, IdAbsence, DateDEBUT, DateFIN, IDTypeAbsence
            FROM absence
            WHERE ModifELEM NOT LIKE '%suppr%'
              AND IDSalarie IN ({ids_sal_sql})
              AND LEFT(DateDEBUT, 8) <= ?
              AND (DateFIN = '' OR LEFT(DateFIN, 8) >= ?)""",
            (today, today),
        )
        type_abs_ids = {_to_int(a.get("IDTypeAbsence")) for a in abs_rows}
        type_abs_ids.discard(0)
        type_abs_map: dict[int, str] = {}
        if type_abs_ids:
            ta_sql = ",".join(str(i) for i in type_abs_ids)
            ta_rows = db_rh.query(
                f"SELECT IDTypeAbsence, Lib_Absence FROM TypeAbsence WHERE IDTypeAbsence IN ({ta_sql})"
            )
            for t in ta_rows:
                type_abs_map[_to_int(t.get("IDTypeAbsence"))] = t.get("Lib_Absence") or ""

        for a in abs_rows:
            sid = _to_int(a.get("IDSalarie"))
            if sid in absence_by_sal:
                continue  # premier trouvé suffit
            id_type = _to_int(a.get("IDTypeAbsence"))
            absence_by_sal[sid] = {
                "type_id": id_type,
                "lib": type_abs_map.get(id_type, ""),
                "date_debut": a.get("DateDEBUT") or "",
                "date_fin": a.get("DateFIN") or "",
            }

    # Dernier contrat signé par vendeur (tous partenaires confondus)
    dernier_ctt_by_sal: dict[int, str] = {}
    if all_salarie_ids:
        db_adv = get_connection("adv")
        part_rows = db_adv.query(
            "SELECT PréfixeBDD FROM Partenaire WHERE IsActif = 1 AND ModifElem <> 'suppr'"
        )
        prefixes = [
            (p.get("PréfixeBDD") or "").strip()
            for p in part_rows
        ]
        prefixes = [p for p in prefixes if p]
        ids_sal_sql_quoted = ",".join(f"'{i}'" for i in all_salarie_ids)

        def fetch_contrat(prefix: str) -> list[dict]:
            db = get_connection("adv")
            try:
                return db.query(
                    f"""SELECT IDSalarie, MAX(DateSignature) AS MaxDate
                    FROM {prefix}_contrat
                    WHERE IDSalarie IN ({ids_sal_sql_quoted})
                      AND DateSignature <> ''
                      AND ModifElem NOT LIKE '%suppr%'
                      AND LEFT(DateSignature, 8) <= ?
                    GROUP BY IDSalarie""",
                    (today,),
                )
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"[ORGA] fetch_contrat({prefix}) failed: {e}"
                )
                return []

        if prefixes:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for rows in pool.map(fetch_contrat, prefixes):
                    for r in rows:
                        sid = _to_int(r.get("IDSalarie"))
                        d = (
                            r.get("MaxDate")
                            or r.get("maxdate")
                            or r.get("MAX(DateSignature)")
                            or ""
                        )
                        d = (d or "").strip()
                        if d and d > dernier_ctt_by_sal.get(sid, "20070101"):
                            dernier_ctt_by_sal[sid] = d

    # Ancienneté en jours
    def _jours_depuis(iso_date: str) -> int:
        if not iso_date:
            return 0
        try:
            from datetime import date as _date
            if "-" in iso_date:
                y, m, d = int(iso_date[0:4]), int(iso_date[5:7]), int(iso_date[8:10])
            else:
                y, m, d = int(iso_date[0:4]), int(iso_date[4:6]), int(iso_date[6:8])
            return (_date.today() - _date(y, m, d)).days
        except Exception:
            return 0

    # Grouper salariés par orga
    salaries_by_orga: dict[int, list[dict]] = {}
    seen: set[tuple[int, int]] = set()
    for s in salaries_rows:
        orga_id = _to_int(s.get("idorganigramme"))
        sid = _to_int(s.get("IDSalarie"))
        key = (orga_id, sid)
        if key in seen:
            continue
        seen.add(key)
        info_poste = poste_map.get(_to_int(s.get("IdTypePoste")), {})
        mut = mutuelle_by_sal.get(sid, {})
        absence = absence_by_sal.get(sid, {})
        date_debut = s.get("DateAncienneté") or s.get("DateDebut") or ""
        salaries_by_orga.setdefault(orga_id, []).append({
            "id_salarie": str(sid),
            "nom": s.get("NOM") or "",
            "prenom": s.get("PRENOM") or "",
            "poste": info_poste.get("lib", ""),
            "categorie": info_poste.get("cat", ""),
            "is_resp": bool(s.get("RespEquipe")),
            "is_resp_adjoint": bool(s.get("RespAdjoint")),
            "date_debut": date_debut,
            "anciennete_jours": _jours_depuis(date_debut),
            "date_dernier_ctt": dernier_ctt_by_sal.get(sid, ""),
            "cj_envoye": bool(s.get("CJ_envoyé")),
            "formation_iag": bool(s.get("FormationIAG")),
            "en_pause": bool(s.get("EnPause")),
            "chauffeur": bool(s.get("Chauffeur")),
            "mutuelle_adhesion": mut.get("adhesion", False),
            "mutuelle_id": mut.get("id", 0),
            "mutuelle_lib": mut.get("lib", ""),
            "mutuelle_fin_date": mut.get("fin_date", "") if mut.get("pas_adhesion") else "",
            "absent": bool(absence),
            "absence_type_id": absence.get("type_id", 0),
            "absence_lib": absence.get("lib", ""),
            "absence_date_debut": absence.get("date_debut", ""),
            "absence_date_fin": absence.get("date_fin", ""),
        })

    # 4. Construction de l'arbre (uniquement sur les orgas accessibles)
    orgas_accessible = [
        o for o in all_orgas
        if _to_int(o.get("idorganigramme")) in accessible_ids
    ]

    # Map id → enfants
    children_map: dict[int, list[int]] = {}
    for o in orgas_accessible:
        oid = _to_int(o.get("idorganigramme"))
        parent_id = _to_int(o.get("IdPARENT"))
        if parent_id in accessible_ids:
            children_map.setdefault(parent_id, []).append(oid)

    # Détection des racines :
    # - ProdRezo : racine = orga avec id = 0 (méta-racine incluse dans MonOrga)
    # - Sinon : racine = orga avec PARENT_ID = 0 (ou "") dans le scope
    if acces_global:
        # Cherche l'orga d'id 0 parmi les orgas accessibles
        roots = [
            _to_int(o.get("idorganigramme"))
            for o in orgas_accessible
            if _to_int(o.get("idorganigramme")) == 0
        ]
        # Fallback si pas d'orga id=0 en base : tous les orgas avec PARENT_ID=0
        if not roots:
            roots = [
                _to_int(o.get("idorganigramme"))
                for o in orgas_accessible
                if _to_int(o.get("IdPARENT")) == 0
            ]
    else:
        # Orgas avec PARENT_ID vide dans le scope
        roots = [
            _to_int(o.get("idorganigramme"))
            for o in orgas_accessible
            if _to_int(o.get("IdPARENT")) == 0
        ]
        # Fallback : orgas dont le parent n'est pas accessible
        if not roots:
            roots = [
                _to_int(o.get("idorganigramme"))
                for o in orgas_accessible
                if _to_int(o.get("IdPARENT")) not in accessible_ids
            ]

    orga_by_id = {
        _to_int(o.get("idorganigramme")): o for o in orgas_accessible
    }

    def build_node(orga_id: int) -> dict:
        o = orga_by_id[orga_id]
        id_niv = _to_int(o.get("IDTypeNiveauOrga"))
        children_ids = children_map.get(orga_id, [])
        return {
            "id": str(orga_id),
            "lib": o.get("Lib_ORGA") or "",
            "lib_niveau": niveaux_map.get(id_niv, ""),
            "id_type_niveau": id_niv,
            "salaries": salaries_by_orga.get(orga_id, []),
            "children": [build_node(cid) for cid in children_ids],
        }

    return [build_node(r) for r in roots]
