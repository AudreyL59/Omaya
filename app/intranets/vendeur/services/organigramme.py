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
from datetime import date, datetime

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


def _today_windev() -> str:
    return datetime.now().strftime("%Y%m%d")


def _iso(v) -> str:
    """PG renvoie des date/datetime natifs ; on serialise en ISO 'YYYY-MM-DD'.
    Accepte aussi None/string et retourne "" pour les valeurs vides."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def _descendants(all_orgas: list[dict], root_ids: set[int]) -> set[int]:
    """Depuis une liste plate d'orgas, trouve tous les descendants récursifs."""
    result = set(root_ids)
    frontier = set(root_ids)
    while frontier:
        next_frontier = set()
        for o in all_orgas:
            parent = _to_int(o.get("id_parent"))
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
    db_rh = get_pg_connection("rh")
    today = _today_windev()

    # 1. Toutes les orgas non-supprimées
    all_orgas = db_rh.query(
        """SELECT idorganigramme, id_parent, lib_orga, id_type_niveau_orga, id_type_orga
        FROM pgt_organigramme
        WHERE modif_elem <> 'suppr'"""
    )

    acces_global = "ProdRezo" in droits

    if acces_global:
        accessible_ids = {_to_int(o.get("idorganigramme")) for o in all_orgas}
        accessible_ids.discard(0)
    else:
        # Orgas actifs du user
        user_rows = db_rh.query(
            """SELECT DISTINCT idorganigramme FROM pgt_salarie_organigramme
            WHERE id_salarie = ?
              AND modif_elem <> 'suppr'
              AND date_debut::date <= ?::date""",
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
        "SELECT id_type_niveau_orga, lib_niveau FROM pgt_type_niveau_orga"
    )
    niveaux_map = {
        _to_int(n.get("id_type_niveau_orga")): n.get("lib_niveau") or ""
        for n in niv_rows
    }

    # 3. Salariés par orga (chunks parallélisés pour amortir le coût subprocess)
    import time
    from concurrent.futures import ThreadPoolExecutor

    ids_list = list(accessible_ids)
    BATCH = 50

    def fetch_chunk(chunk: list[int]) -> list[dict]:
        ids_sql = ",".join(str(cid) for cid in chunk)
        db = get_pg_connection("rh")
        return db.query(
            f"""SELECT so.idorganigramme, s.id_salarie, s.nom, s.prenom,
                se.resp_equipe, se.resp_adjoint, se.id_type_poste,
                se.date_anciennete, se.date_debut,
                se.cj_envoye, se.formation_iag, se.en_pause, se.chauffeur
            FROM pgt_salarie s
            INNER JOIN pgt_salarie_embauche se ON s.id_salarie = se.id_salarie
            INNER JOIN pgt_salarie_organigramme so ON s.id_salarie = so.id_salarie
            WHERE so.idorganigramme IN ({ids_sql})
              AND so.modif_elem <> 'suppr'
              AND so.date_debut::date <= ?::date
              AND (so.date_fin IS NULL OR so.date_fin::date >= ?::date)
              AND se.en_activite = TRUE
              AND s.modif_elem <> 'suppr'
            ORDER BY se.resp_equipe DESC, se.resp_adjoint DESC, s.nom ASC, s.prenom ASC""",
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
    poste_ids = {_to_int(s.get("id_type_poste")) for s in salaries_rows}
    poste_ids.discard(0)
    poste_map: dict[int, dict] = {}
    if poste_ids:
        ids_poste_sql = ",".join(str(i) for i in poste_ids)
        p_rows = db_rh.query(
            f"SELECT id_type_poste, lib_poste, categorie FROM pgt_type_poste WHERE id_type_poste IN ({ids_poste_sql})"
        )
        for p in p_rows:
            poste_map[_to_int(p.get("id_type_poste"))] = {
                "lib": p.get("lib_poste") or "",
                "cat": p.get("categorie") or "",
            }

    # Mutuelles + absences en batch pour tous les salariés
    all_salarie_ids = {_to_int(s.get("id_salarie")) for s in salaries_rows}
    all_salarie_ids.discard(0)

    mutuelle_by_sal: dict[int, dict] = {}
    absence_by_sal: dict[int, dict] = {}

    if all_salarie_ids:
        ids_sal_sql = ",".join(str(i) for i in all_salarie_ids)

        mut_rows = db_rh.query(
            f"""SELECT sm.id_salarie, sm.adhesion, sm.id_mutuelle,
                sm.mutuelle_pas_adhesion, sm.mutuelle_pas_adhesion_jusquau,
                m.lib_mutuelle
            FROM pgt_salarie_mutuelle sm
            LEFT JOIN pgt_mutuelle m ON m.id_mutuelle = sm.id_mutuelle
            WHERE sm.id_salarie IN ({ids_sal_sql})"""
        )
        for m in mut_rows:
            sid = _to_int(m.get("id_salarie"))
            mutuelle_by_sal[sid] = {
                "adhesion": bool(m.get("adhesion")),
                "id": _to_int(m.get("id_mutuelle")),
                "lib": m.get("lib_mutuelle") or "",
                "pas_adhesion": bool(m.get("mutuelle_pas_adhesion")),
                "fin_date": m.get("mutuelle_pas_adhesion_jusquau") or "",
            }

        # Absences (lib depuis TypeAbsence)
        abs_rows = db_rh.query(
            f"""SELECT id_salarie, id_absence, date_debut, date_fin, id_type_absence
            FROM pgt_absence
            WHERE modif_elem NOT LIKE '%suppr%'
              AND id_salarie IN ({ids_sal_sql})
              AND date_debut::date <= ?::date
              AND (date_fin IS NULL OR date_fin::date >= ?::date)""",
            (today, today),
        )
        type_abs_ids = {_to_int(a.get("id_type_absence")) for a in abs_rows}
        type_abs_ids.discard(0)
        type_abs_map: dict[int, str] = {}
        if type_abs_ids:
            ta_sql = ",".join(str(i) for i in type_abs_ids)
            ta_rows = db_rh.query(
                f"SELECT id_type_absence, lib_absence FROM pgt_type_absence WHERE id_type_absence IN ({ta_sql})"
            )
            for t in ta_rows:
                type_abs_map[_to_int(t.get("id_type_absence"))] = t.get("lib_absence") or ""

        for a in abs_rows:
            sid = _to_int(a.get("id_salarie"))
            if sid in absence_by_sal:
                continue  # premier trouvé suffit
            id_type = _to_int(a.get("id_type_absence"))
            absence_by_sal[sid] = {
                "type_id": id_type,
                "lib": type_abs_map.get(id_type, ""),
                "date_debut": _iso(a.get("date_debut")),
                "date_fin": _iso(a.get("date_fin")),
            }

    # Dernier contrat signé par vendeur (tous partenaires confondus)
    dernier_ctt_by_sal: dict[int, str] = {}
    if all_salarie_ids:
        db_adv = get_pg_connection("adv")
        part_rows = db_adv.query(
            "SELECT prefixe_bdd FROM pgt_partenaire WHERE is_actif = TRUE AND modif_elem <> 'suppr'"
        )
        prefixes = [
            (p.get("prefixe_bdd") or "").strip()
            for p in part_rows
        ]
        prefixes = [p for p in prefixes if p]
        ids_sal_sql_quoted = ",".join(f"'{i}'" for i in all_salarie_ids)

        def fetch_contrat(prefix: str) -> list[dict]:
            db = get_pg_connection("adv")
            try:
                return db.query(
                    f"""SELECT id_salarie, MAX(date_signature) AS maxdate
                    FROM pgt_{prefix.lower()}_contrat
                    WHERE id_salarie IN ({ids_sal_sql_quoted})
                      AND date_signature IS NOT NULL
                      AND modif_elem NOT LIKE '%suppr%'
                      AND date_signature::date <= ?::date
                    GROUP BY id_salarie""",
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
                        sid = _to_int(r.get("id_salarie"))
                        # PG renvoie date natif sur max(DateSignature) -> _iso le serialise
                        d = _iso(
                            r.get("maxdate")
                            or r.get("MaxDate")
                            or r.get("max")
                        )
                        if d and d > dernier_ctt_by_sal.get(sid, "2007-01-01"):
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
        sid = _to_int(s.get("id_salarie"))
        key = (orga_id, sid)
        if key in seen:
            continue
        seen.add(key)
        info_poste = poste_map.get(_to_int(s.get("id_type_poste")), {})
        mut = mutuelle_by_sal.get(sid, {})
        absence = absence_by_sal.get(sid, {})
        date_debut = _iso(s.get("date_anciennete") or s.get("date_debut"))
        salaries_by_orga.setdefault(orga_id, []).append({
            "id_salarie": str(sid),
            "nom": s.get("nom") or "",
            "prenom": s.get("prenom") or "",
            "poste": info_poste.get("lib", ""),
            "categorie": info_poste.get("cat", ""),
            "is_resp": bool(s.get("resp_equipe")),
            "is_resp_adjoint": bool(s.get("resp_adjoint")),
            "date_debut": date_debut,
            "anciennete_jours": _jours_depuis(date_debut),
            "date_dernier_ctt": dernier_ctt_by_sal.get(sid, ""),
            "cj_envoye": bool(s.get("cj_envoye")),
            "formation_iag": bool(s.get("formation_iag")),
            "en_pause": bool(s.get("en_pause")),
            "chauffeur": bool(s.get("chauffeur")),
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
        parent_id = _to_int(o.get("id_parent"))
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
                if _to_int(o.get("id_parent")) == 0
            ]
    else:
        # Orgas avec PARENT_ID vide dans le scope
        roots = [
            _to_int(o.get("idorganigramme"))
            for o in orgas_accessible
            if _to_int(o.get("id_parent")) == 0
        ]
        # Fallback : orgas dont le parent n'est pas accessible
        if not roots:
            roots = [
                _to_int(o.get("idorganigramme"))
                for o in orgas_accessible
                if _to_int(o.get("id_parent")) not in accessible_ids
            ]

    orga_by_id = {
        _to_int(o.get("idorganigramme")): o for o in orgas_accessible
    }

    def build_node(orga_id: int) -> dict:
        o = orga_by_id[orga_id]
        id_niv = _to_int(o.get("id_type_niveau_orga"))
        children_ids = children_map.get(orga_id, [])
        return {
            "id": str(orga_id),
            "lib": o.get("lib_orga") or "",
            "lib_niveau": niveaux_map.get(id_niv, ""),
            "id_type_niveau": id_niv,
            "salaries": salaries_by_orga.get(orga_id, []),
            "children": [build_node(cid) for cid in children_ids],
        }

    return [build_node(r) for r in roots]
