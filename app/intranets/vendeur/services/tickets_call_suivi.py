"""
Suivi Tickets Call (Fibre + Energie) - intranet Vendeur.

Cf. WinDev : fusion des pages Call SFR + Call ENI dans une vue unique.

Regles d'affichage :
- User avec droit 'ProdRezo' : voit tous les tickets
- Sinon : voit uniquement les tickets dont le vendeur (id_salarie du ticket)
  est rattache a un orga dans son sous-arbre (ListeOrgaComplet).

Cible : PG direct (pas HFSQL). Les tables sont synchronisees en interne
depuis OVH via SymmetricDS toutes les 5s (cf. reference_symmetricds_sync).
"""
from __future__ import annotations

import logging
from datetime import date as _date

from app.core.database.pg import get_pg_connection


logger = logging.getLogger(__name__)


# Constantes WinDev
IDTK_TYPE_DEMANDE_CALL_FIBRE = 20
IDTK_TYPE_DEMANDE_CALL_ENERGIE = 22
ID_OPE_FORMATION = 6
ID_POSTE_MASQUE_DIFF = 20

# Exclusions cf. WinDev ListeOrgaComplet : "Hors distrib Archives"
_ID_ORGA_EXCLU = 20160729152638792


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _to_int(v, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _str_id(v) -> str:
    n = _to_int(v)
    return str(n) if n else ""


def _iso(v) -> str:
    if v is None:
        return ""
    s = str(v)
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _civilite_to_prefix(civ: int) -> str:
    return {1: "M.", 2: "Mme", 3: "Mlle"}.get(civ, "")


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower() if len(s) > 1 else s.upper()


def _format_nom_client(civ: int, nom: str, nom_marital: str, prenom: str) -> str:
    parts = [_civilite_to_prefix(civ), (nom or "").upper()]
    if nom_marital:
        parts.append(f"({nom_marital.upper()})")
    parts.append(_capitalize(prenom or ""))
    return " ".join(p for p in parts if p).strip()


# --------------------------------------------------------------------
# Orga du user + descendants (cf. WinDev ListeOrgaComplet)
# --------------------------------------------------------------------

def _get_orga_courant(id_salarie: int) -> int:
    """Rattachement orga actif d'un salarie
    (dernier salarie_organigramme avec date_fin vide/future).
    """
    if not id_salarie:
        return 0
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT idorganigramme
                 FROM pgt_salarie_organigramme
                WHERE id_salarie = ?
                  AND COALESCE(aff_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                ORDER BY date_debut DESC
                LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        logger.exception("_get_orga_courant")
        return 0
    return _to_int((r or {}).get("idorganigramme"))


def _liste_orga_complet(id_orga: int) -> set[int]:
    """Cf. WinDev ListeOrgaComplet(id, suppr=Faux) : orga + descendants
    sur 5 niveaux max, exclut les supprimes et l'orga distrib archives.
    """
    if not id_orga:
        return set()
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """WITH RECURSIVE tree AS (
                   SELECT idorganigramme AS id, id_parent, 0 AS depth
                     FROM pgt_organigramme
                    WHERE idorganigramme = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                   UNION ALL
                   SELECT o.idorganigramme, o.id_parent, t.depth + 1
                     FROM pgt_organigramme o
                     JOIN tree t ON o.id_parent = t.id
                    WHERE (o.modif_elem IS NULL
                           OR o.modif_elem NOT LIKE '%suppr%')
                      AND t.depth < 5
               )
               SELECT id FROM tree""",
            (int(id_orga),),
        ) or []
    except Exception:
        logger.exception("_liste_orga_complet id_orga=%s", id_orga)
        return set()
    ids = {_to_int(r.get("id")) for r in rows}
    ids.discard(0)
    ids.discard(_ID_ORGA_EXCLU)
    return ids


def _load_affectations_actives(
    id_salaries: set[int],
) -> dict[int, dict]:
    """Retourne {id_salarie: {id_orga, lib_orga, id_orga_parent, lib_parent}}
    a partir du rattachement actif."""
    if not id_salaries:
        return {}
    rh = get_pg_connection("rh")
    ids_sql = ",".join(str(i) for i in id_salaries)
    try:
        rows = rh.query(
            f"""SELECT DISTINCT ON (so.id_salarie)
                       so.id_salarie,
                       so.idorganigramme AS id_orga,
                       o.lib_orga,
                       o.id_parent AS id_orga_parent,
                       op.lib_orga AS lib_parent
                  FROM pgt_salarie_organigramme so
                  LEFT JOIN pgt_organigramme o
                         ON o.idorganigramme = so.idorganigramme
                  LEFT JOIN pgt_organigramme op
                         ON op.idorganigramme = o.id_parent
                 WHERE so.id_salarie IN ({ids_sql})
                   AND COALESCE(so.aff_actif, FALSE) = TRUE
                   AND (so.modif_elem IS NULL
                        OR so.modif_elem NOT LIKE '%suppr%')
                 ORDER BY so.id_salarie, so.date_debut DESC""",
        ) or []
    except Exception:
        logger.exception("_load_affectations_actives")
        return {}
    return {
        _to_int(r.get("id_salarie")): {
            "id_orga": _to_int(r.get("id_orga")),
            "lib_orga": (r.get("lib_orga") or "").strip(),
            "id_orga_parent": _to_int(r.get("id_orga_parent")),
            "lib_parent": (r.get("lib_parent") or "").strip(),
        }
        for r in rows
    }


def _load_salaries(id_salaries: set[int]) -> dict[int, dict]:
    if not id_salaries:
        return {}
    rh = get_pg_connection("rh")
    ids_sql = ",".join(str(i) for i in id_salaries)
    try:
        rows = rh.query(
            f"""SELECT id_salarie, nom, prenom
                  FROM pgt_salarie
                 WHERE id_salarie IN ({ids_sql})""",
        ) or []
    except Exception:
        logger.exception("_load_salaries")
        return {}
    return {
        _to_int(r.get("id_salarie")): {
            "nom": (r.get("nom") or "").strip(),
            "prenom": _capitalize((r.get("prenom") or "").strip()),
        }
        for r in rows
    }


# --------------------------------------------------------------------
# Tickets Fibre + Energie -> vue unifiee
# --------------------------------------------------------------------

def _select_en_cours_pg(id_type_demande: int) -> list[dict]:
    """SELECT unifie : tickets en cours du jour, cf. WinDev
    list_tickets_en_cours (filtres business identiques mais on ne passe
    plus par le cache SuiviTicketCall car PG a des index perf).
    """
    db_tk = get_pg_connection("ticket")
    today_compact = _date.today().strftime("%Y%m%d")
    try:
        return db_tk.query(
            """SELECT id_tk_liste, datecrea, op_crea, id_tk_statut,
                      cloturee, modif_elem
                 FROM ticket.pgt_tk_liste
                WHERE id_tk_type_demande = ?
                  AND LEFT(datecrea, 8) = ?
                  AND COALESCE(cloturee, FALSE) = FALSE
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                  AND COALESCE(id_tk_statut, 0) NOT IN (18, 28)
                  AND (COALESCE(id_tk_statut, 0) < 14
                       OR id_tk_statut = 34)""",
            (int(id_type_demande), today_compact),
        ) or []
    except Exception:
        logger.exception("_select_en_cours_pg id_type=%s", id_type_demande)
        return []


def _select_call_sfr(ids_liste: list[int]) -> list[dict]:
    if not ids_liste:
        return []
    ids_sql = ",".join(str(i) for i in ids_liste)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, cp, ville,
                       appel_en_cours, ope_appel, ticket_diff
                  FROM ticket_bo.pgt_tk_call_sfr
                 WHERE id_tk_liste IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_call_sfr")
        return []


def _select_call_eni(ids_liste: list[int]) -> list[dict]:
    if not ids_liste:
        return []
    ids_sql = ",".join(str(i) for i in ids_liste)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, cp, ville,
                       appel_en_cours, ope_appel
                  FROM ticket_bo.pgt_tk_call
                 WHERE id_tk_liste IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_call_eni")
        return []


def _load_statuts() -> dict[int, str]:
    db_tk = get_pg_connection("ticket")
    try:
        rows = db_tk.query(
            """SELECT id_tk_statut, lib_statut
                 FROM ticket.pgt_tk_statut""",
        ) or []
    except Exception:
        return {}
    return {
        _to_int(r.get("id_tk_statut")): (r.get("lib_statut") or "").strip()
        for r in rows
    }


# --------------------------------------------------------------------
# API : point d'entree
# --------------------------------------------------------------------

def list_en_cours_suivi(
    id_user: int, user_droits: list[str], id_poste_user: int = 0,
) -> list[dict]:
    """Liste unifiee (Fibre + Energie) des tickets en cours du jour,
    filtree par orga du user si pas ProdRezo.
    """
    has_prod_rezo = "ProdRezo" in (user_droits or [])

    # Prepare liste orga autorisee si filtrage
    orga_autorises: set[int] = set()
    if not has_prod_rezo:
        id_orga_user = _get_orga_courant(id_user)
        orga_autorises = _liste_orga_complet(id_orga_user)
        if not orga_autorises:
            return []

    # 1) TK_Liste pour chaque type de demande
    tk_fibre = {
        _to_int(r.get("id_tk_liste")): r
        for r in _select_en_cours_pg(IDTK_TYPE_DEMANDE_CALL_FIBRE)
    }
    tk_eni = {
        _to_int(r.get("id_tk_liste")): r
        for r in _select_en_cours_pg(IDTK_TYPE_DEMANDE_CALL_ENERGIE)
    }

    # 2) Enrichissement TK_CallSFR / TK_Call
    call_sfr = _select_call_sfr(list(tk_fibre.keys()))
    call_eni = _select_call_eni(list(tk_eni.keys()))

    # 3) Combine
    id_salaries: set[int] = set()
    ope_ids: set[int] = set()
    combined: list[dict] = []

    def _base(row_liste: dict, row_call: dict, partenaire: str) -> dict:
        id_sal = _to_int(row_call.get("id_salarie"))
        ope = _to_int(row_call.get("ope_appel"))
        id_salaries.add(id_sal)
        if ope:
            ope_ids.add(ope)
        return {
            "id": _str_id(row_liste.get("id_tk_liste")),
            "partenaire": partenaire,
            "date_crea": _iso(row_liste.get("datecrea")),
            "id_salarie": _str_id(id_sal),
            "_id_salarie_int": id_sal,
            "civilite": _to_int(row_call.get("civilite_client")),
            "nom": row_call.get("nom_client") or "",
            "nom_marital": row_call.get("nom_marital_client") or "",
            "prenom": row_call.get("prenom_client") or "",
            "cp": (row_call.get("cp") or "").strip(),
            "ville": (row_call.get("ville") or "").strip(),
            "appel_en_cours": bool(row_call.get("appel_en_cours")),
            "ope_appel_id": ope,
            "ticket_diff": bool(row_call.get("ticket_diff")) if partenaire == "SFR" else False,
            "id_tk_statut": _to_int(row_liste.get("id_tk_statut")),
            "op_crea": _to_int(row_liste.get("op_crea")),
        }

    for r in call_sfr:
        tkl = tk_fibre.get(_to_int(r.get("id_tk_liste")))
        if not tkl:
            continue
        combined.append(_base(tkl, r, "SFR"))
    for r in call_eni:
        tkl = tk_eni.get(_to_int(r.get("id_tk_liste")))
        if not tkl:
            continue
        combined.append(_base(tkl, r, "ENI"))

    # 4) Resolve libelles + affectations
    all_ids_sal = id_salaries | ope_ids
    salaries = _load_salaries(all_ids_sal)
    affectations = _load_affectations_actives(id_salaries)
    statuts = _load_statuts()

    # 5) Filtre orga si pas ProdRezo + formatage final
    out: list[dict] = []
    from datetime import datetime, date as _dt_date
    today_2359 = datetime.combine(_dt_date.today(), datetime.max.time())
    for row in combined:
        # Filtre orga
        if not has_prod_rezo:
            aff = affectations.get(row["_id_salarie_int"])
            if not aff or aff["id_orga"] not in orga_autorises:
                continue
        # Filtre formation (OPCrea = 6)
        if row["op_crea"] == ID_OPE_FORMATION and id_user != ID_OPE_FORMATION:
            continue
        # Filtre tickets futurs
        d_iso = row["date_crea"]
        if d_iso:
            try:
                dt = datetime.strptime(d_iso[:19], "%Y-%m-%d %H:%M:%S")
                if dt > today_2359 and id_user != ID_OPE_FORMATION:
                    continue
            except ValueError:
                pass
        # Filtre TicketDiff pour idPoste=20
        if row["ticket_diff"] and id_poste_user == ID_POSTE_MASQUE_DIFF:
            continue

        sal = salaries.get(row["_id_salarie_int"], {})
        ope = salaries.get(row["ope_appel_id"], {})
        aff = affectations.get(row["_id_salarie_int"], {})
        out.append({
            "id": row["id"],
            "partenaire": row["partenaire"],
            "date_crea": row["date_crea"],
            "nom_client": _format_nom_client(
                row["civilite"], row["nom"], row["nom_marital"], row["prenom"],
            ),
            "cp": row["cp"],
            "ville": row["ville"],
            "id_salarie": row["id_salarie"],
            "nom_vendeur": (
                f"{sal.get('nom', '')} {sal.get('prenom', '')}"
            ).strip(),
            "lib_equipe": aff.get("lib_orga", ""),
            "lib_agence": aff.get("lib_parent", ""),
            "lib_statut": statuts.get(row["id_tk_statut"], ""),
            "id_tk_statut": row["id_tk_statut"],
            "appel_en_cours": row["appel_en_cours"],
            "ope_appel_nom": (
                f"{ope.get('nom', '')} {ope.get('prenom', '')}"
            ).strip() if row["ope_appel_id"] else "",
            "ticket_diff": row["ticket_diff"],
        })

    # Tri : d'abord tickets sans appel en cours, puis par date_crea desc
    out.sort(key=lambda t: (t["appel_en_cours"], t["date_crea"]), reverse=False)
    return out
