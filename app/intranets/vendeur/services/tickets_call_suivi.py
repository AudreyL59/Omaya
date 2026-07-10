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
STATUTS_TRAITES = (14, 15, 16, 17, 19)   # 18 et 28 exclus

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


def _parse_dt(v):
    """Retourne un datetime a partir d'un compact WinDev ou d'un datetime PG."""
    from datetime import datetime as _dt
    if v is None:
        return None
    if hasattr(v, "year"):
        return v
    s = str(v).strip()
    if not s or s.startswith("0000") or s.startswith("1900"):
        return None
    for fmt in ("%Y%m%d%H%M%S%f", "%Y%m%d%H%M%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return _dt.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


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


# --------------------------------------------------------------------
# Tickets traites (avec panier + colonnes specifiques Fibre/Energie)
# --------------------------------------------------------------------

def _load_offres_sfr_ref() -> dict[int, str]:
    """Referentiel SFR_OffresProvad : {id_offres_sfr: lib_offre}."""
    adv = get_pg_connection("adv")
    try:
        rows = adv.query(
            """SELECT id_offres_sfr, lib_offre
                 FROM adv.pgt_sfr_offres_provad""",
        ) or []
    except Exception:
        return {}
    return {
        _to_int(r.get("id_offres_sfr")): (r.get("lib_offre") or "").strip()
        for r in rows
    }


def _select_traites_pg(
    id_type_demande: int, jour_compact: str,
) -> list[dict]:
    """Tickets clotures/traites du jour cf. WinDev list_tickets_traites."""
    statuts_sql = ",".join(str(s) for s in STATUTS_TRAITES)
    db_tk = get_pg_connection("ticket")
    try:
        return db_tk.query(
            f"""SELECT id_tk_liste, datecrea, id_tk_statut
                  FROM ticket.pgt_tk_liste
                 WHERE id_tk_type_demande = ?
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')
                   AND id_tk_statut IN ({statuts_sql})
                   AND LEFT(datecrea, 8) = ?
                 ORDER BY datecrea ASC""",
            (int(id_type_demande), jour_compact),
        ) or []
    except Exception:
        logger.exception("_select_traites_pg id_type=%s", id_type_demande)
        return []


def _select_call_sfr_traites(ids_liste: list[int]) -> list[dict]:
    if not ids_liste:
        return []
    ids_sql = ",".join(str(i) for i in ids_liste)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_call_sfr, id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, cp, ville, ref_appel
                  FROM ticket_bo.pgt_tk_call_sfr
                 WHERE id_tk_liste IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_call_sfr_traites")
        return []


def _select_call_eni_traites(ids_liste: list[int]) -> list[dict]:
    if not ids_liste:
        return []
    ids_sql = ",".join(str(i) for i in ids_liste)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_call, id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, cp, ville, ref_appel
                  FROM ticket_bo.pgt_tk_call
                 WHERE id_tk_liste IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_call_eni_traites")
        return []


def _select_panier_sfr(id_calls: list[int]) -> list[dict]:
    if not id_calls:
        return []
    ids_sql = ",".join(str(i) for i in id_calls)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_call_sfr, id_offres_sfr, type, type_vente,
                       num, num_date_saisie, statut_prod
                  FROM ticket_bo.pgt_tk_call_sfr_panier
                 WHERE id_tk_call_sfr IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_panier_sfr")
        return []


def _select_panier_eni(id_calls: list[int]) -> list[dict]:
    if not id_calls:
        return []
    ids_sql = ",".join(str(i) for i in id_calls)
    db_bo = get_pg_connection("ticket_bo")
    try:
        return db_bo.query(
            f"""SELECT id_tk_call, id_produit, num_bs, num_date_saisie,
                       statut_prod, partenaire
                  FROM ticket_bo.pgt_tk_call_panier
                 WHERE id_tk_call IN ({ids_sql})
                   AND (modif_elem IS NULL
                        OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        logger.exception("_select_panier_eni")
        return []


def list_traites_suivi(
    id_user: int, user_droits: list[str], jour: str | None = None,
) -> list[dict]:
    """Liste unifiee (Fibre + Energie) des tickets traites, filtree par
    orga du user si pas ProdRezo.

    jour : format 'YYYY-MM-DD' ou 'YYYYMMDD' ou None (= today).
    """
    has_prod_rezo = "ProdRezo" in (user_droits or [])
    orga_autorises: set[int] = set()
    if not has_prod_rezo:
        id_orga_user = _get_orga_courant(id_user)
        orga_autorises = _liste_orga_complet(id_orga_user)
        if not orga_autorises:
            return []

    if jour:
        jour_compact = jour.replace("-", "")
    else:
        jour_compact = _date.today().strftime("%Y%m%d")

    # 1) TK_Liste par type
    liste_fibre = _select_traites_pg(
        IDTK_TYPE_DEMANDE_CALL_FIBRE, jour_compact,
    )
    liste_eni = _select_traites_pg(
        IDTK_TYPE_DEMANDE_CALL_ENERGIE, jour_compact,
    )
    if not liste_fibre and not liste_eni:
        return []

    by_id_fibre = {_to_int(r.get("id_tk_liste")): r for r in liste_fibre}
    by_id_eni = {_to_int(r.get("id_tk_liste")): r for r in liste_eni}
    statuts = _load_statuts()

    # 2) TK_CallSFR + TK_Call
    call_sfr = _select_call_sfr_traites(list(by_id_fibre.keys()))
    call_eni = _select_call_eni_traites(list(by_id_eni.keys()))

    id_calls_sfr = [_to_int(r.get("id_tk_call_sfr")) for r in call_sfr]
    id_calls_eni = [_to_int(r.get("id_tk_call")) for r in call_eni]
    id_salaries: set[int] = {
        _to_int(r.get("id_salarie")) for r in call_sfr + call_eni
    } - {0}

    # 3) Paniers
    panier_sfr_by_call: dict[int, list[dict]] = {}
    for p in _select_panier_sfr(id_calls_sfr):
        panier_sfr_by_call.setdefault(
            _to_int(p.get("id_tk_call_sfr")), [],
        ).append(p)

    panier_eni_by_call: dict[int, list[dict]] = {}
    for p in _select_panier_eni(id_calls_eni):
        panier_eni_by_call.setdefault(
            _to_int(p.get("id_tk_call")), [],
        ).append(p)

    # 4) Lookups salaries + affectations + refs offres SFR
    salaries = _load_salaries(id_salaries)
    affectations = _load_affectations_actives(id_salaries)
    offre_libs = _load_offres_sfr_ref() if call_sfr else {}

    # 5) Construction Fibre
    out: list[dict] = []
    for r in call_sfr:
        id_tk = _to_int(r.get("id_tk_liste"))
        tk = by_id_fibre.get(id_tk)
        if not tk:
            continue
        id_sal = _to_int(r.get("id_salarie"))
        # Filtre orga si applicable
        if not has_prod_rezo:
            aff = affectations.get(id_sal)
            if not aff or aff["id_orga"] not in orga_autorises:
                continue

        id_call = _to_int(r.get("id_tk_call_sfr"))
        panier = panier_sfr_by_call.get(id_call, [])

        nb_fibre_valide = 0
        nb_mobile_valide = 0
        offres_fibre_txt = ""
        lib_statut = statuts.get(_to_int(tk.get("id_tk_statut")), "")
        delai_depasse = False

        for off in panier:
            statut_prod = _to_int(off.get("statut_prod"))
            typ = (off.get("type") or "").strip()
            num = (off.get("num") or "").strip()
            type_vente = _to_int(off.get("type_vente"))
            if statut_prod in (1, 3):
                if typ == "FIBRE":
                    nb_fibre_valide += 1
                    lib_offre = offre_libs.get(
                        _to_int(off.get("id_offres_sfr")), "",
                    )
                    suffix = " - CQ" if type_vente in (1, 2) else " - Mig"
                    offres_fibre_txt += f"\n{lib_offre}{suffix}"
                    if num:
                        lib_statut = "Tk Call - Num BS SFR renseigné"
                elif typ == "MOBILE":
                    nb_mobile_valide += 1
            # Delai prise num >= 1h apres creation
            dt_saisie = _parse_dt(off.get("num_date_saisie"))
            if dt_saisie:
                dt_crea = _parse_dt(tk.get("datecrea"))
                if dt_crea and (dt_saisie - dt_crea).total_seconds() >= 3600:
                    delai_depasse = True

        sal = salaries.get(id_sal, {})
        aff = affectations.get(id_sal, {})
        out.append({
            "id": _str_id(id_tk),
            "partenaire": "SFR",
            "date_crea": _iso(tk.get("datecrea")),
            "nom_client": _format_nom_client(
                _to_int(r.get("civilite_client")),
                r.get("nom_client") or "",
                r.get("nom_marital_client") or "",
                r.get("prenom_client") or "",
            ),
            "cp": (r.get("cp") or "").strip(),
            "ville": (r.get("ville") or "").strip(),
            "nom_vendeur": (
                f"{sal.get('nom', '')} {sal.get('prenom', '')}"
            ).strip(),
            "agence": aff.get("lib_orga", "") or aff.get("lib_parent", ""),
            "lib_statut": lib_statut,
            "ref_appel": (r.get("ref_appel") or "").strip(),
            "nb_offres": len(panier),
            "nb_fibre_valide": nb_fibre_valide,
            "nb_mobile_valide": nb_mobile_valide,
            "col_offres_fibre": offres_fibre_txt.strip(),
            "nb_offres_valides": 0,        # Fibre : non utilise
            "nb_num_bs": 0,                # Fibre : non utilise
            "nb_brut_par_partenaire": {},  # Fibre : non utilise
            "vendeur_distrib": False,      # simplification : pas calcule ici
            "premier_contrat": False,      # non calcule dans le suivi Vendeur
            "delai_depasse": delai_depasse,
        })

    # 6) Construction Energie
    for r in call_eni:
        id_tk = _to_int(r.get("id_tk_liste"))
        tk = by_id_eni.get(id_tk)
        if not tk:
            continue
        id_sal = _to_int(r.get("id_salarie"))
        if not has_prod_rezo:
            aff = affectations.get(id_sal)
            if not aff or aff["id_orga"] not in orga_autorises:
                continue

        id_call = _to_int(r.get("id_tk_call"))
        panier = panier_eni_by_call.get(id_call, [])

        nb_offres_valides = 0
        nb_num_bs = 0
        nb_brut_par_partenaire: dict[str, int] = {}
        lib_statut = statuts.get(_to_int(tk.get("id_tk_statut")), "")
        delai_depasse = False

        for off in panier:
            prefix = (off.get("partenaire") or "").strip()
            if prefix:
                nb_brut_par_partenaire[prefix] = (
                    nb_brut_par_partenaire.get(prefix, 0) + 1
                )
            statut_prod = _to_int(off.get("statut_prod"))
            num_bs = (off.get("num_bs") or "").strip()
            if statut_prod in (1, 3):
                nb_offres_valides += 1
                if num_bs:
                    nb_num_bs += 1
                    lib_statut = "Tk Call - Num BS renseigné"
            dt_saisie = _parse_dt(off.get("num_date_saisie"))
            if dt_saisie:
                dt_crea = _parse_dt(tk.get("datecrea"))
                if dt_crea and (dt_saisie - dt_crea).total_seconds() >= 3600:
                    delai_depasse = True

        sal = salaries.get(id_sal, {})
        aff = affectations.get(id_sal, {})
        # Partenaire dominant : celui qui a le plus d'offres brut
        partenaire_dominant = "ENI"
        if nb_brut_par_partenaire:
            partenaire_dominant = max(
                nb_brut_par_partenaire, key=nb_brut_par_partenaire.get,
            )
        out.append({
            "id": _str_id(id_tk),
            "partenaire": partenaire_dominant,
            "date_crea": _iso(tk.get("datecrea")),
            "nom_client": _format_nom_client(
                _to_int(r.get("civilite_client")),
                r.get("nom_client") or "",
                r.get("nom_marital_client") or "",
                r.get("prenom_client") or "",
            ),
            "cp": (r.get("cp") or "").strip(),
            "ville": (r.get("ville") or "").strip(),
            "nom_vendeur": (
                f"{sal.get('nom', '')} {sal.get('prenom', '')}"
            ).strip(),
            "agence": aff.get("lib_orga", "") or aff.get("lib_parent", ""),
            "lib_statut": lib_statut,
            "ref_appel": (r.get("ref_appel") or "").strip(),
            "nb_offres": len(panier),
            "nb_fibre_valide": 0,        # Energie : non utilise
            "nb_mobile_valide": 0,       # Energie : non utilise
            "col_offres_fibre": "",      # Energie : non utilise
            "nb_offres_valides": nb_offres_valides,
            "nb_num_bs": nb_num_bs,
            "nb_brut_par_partenaire": nb_brut_par_partenaire,
            "vendeur_distrib": False,
            "premier_contrat": False,
            "delai_depasse": delai_depasse,
        })

    # Tri : date desc
    out.sort(key=lambda t: t["date_crea"], reverse=True)
    return out
