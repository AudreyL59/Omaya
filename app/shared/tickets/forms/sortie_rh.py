"""FI_SortieRH (types 12 / 36 / 37) - Tickets de sortie RH.

- Type 12 : Sortie RH simple (sans SDTC)
- Type 36 : Sortie FPE / Démission (Service BO)
- Type 37 : Sortie Licenciement / Rupture / Dém présumée (Service JU)

Transposition de la fenêtre interne WinDev FI_SortieRH (Fen_TicketContenu).
Tables PG :
- ticket.pgt_tk_liste : pour récupérer id_tk_type_demande + clôture
- ticket_rh.pgt_tk_demande_sortie_rh : pour type_sortie + info_cplt + doc_sortie
- rh.pgt_salarie / pgt_type_sortie_salarie : pour le nom + libellé du type
- adv.pgt_<prefixe>_contrat : pour calculer la date du dernier contrat
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any

from app.core.config import DOCS_URL
from app.core.database.pg import get_pg_connection

from ..service import maj_op_traitement_ticket


# --- Helpers --------------------------------------------------------------

def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


def _iso_date(v: Any) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 else ""


def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _date_dernier_ctt(id_salarie: int) -> str:
    """Retourne la date ISO du dernier contrat signé du vendeur, tous
    partenaires confondus (équivalent DateDernierCttVendeur WinDev).

    Vide si aucun contrat trouvé.
    """
    if not id_salarie:
        return ""
    db_adv = get_pg_connection("adv")
    try:
        rows = db_adv.query(
            """SELECT prefixe_bdd FROM pgt_partenaire
            WHERE is_actif = TRUE AND modif_elem <> 'suppr'"""
        )
    except Exception:
        return ""
    prefixes = [(p.get("prefixe_bdd") or "").strip() for p in rows]
    prefixes = [p for p in prefixes if p]
    if not prefixes:
        return ""

    today_str = datetime.now().strftime("%Y-%m-%d")

    def fetch_one(prefix: str) -> str:
        try:
            db = get_pg_connection("adv")
            r = db.query_one(
                f"""SELECT MAX(date_signature) AS m
                FROM pgt_{prefix.lower()}_contrat
                WHERE id_salarie = ?
                  AND date_signature IS NOT NULL
                  AND modif_elem NOT LIKE '%suppr%'
                  AND date_signature::date <= ?::date""",
                (id_salarie, today_str),
            )
            return _iso_date(r.get("m")) if r else ""
        except Exception:
            return ""

    max_date = ""
    with ThreadPoolExecutor(max_workers=8) as pool:
        for d in pool.map(fetch_one, prefixes):
            if d and d > max_date:
                max_date = d
    return max_date


# --- load / save ---------------------------------------------------------

def load(id_ticket: int) -> dict:
    """Charge les infos affichées dans le ticket sortie RH."""
    db_ticket = get_pg_connection("ticket")
    db_tkrh = get_pg_connection("ticket_rh")
    db_rh = get_pg_connection("rh")

    # 1) TK_Liste pour récupérer id_tk_type_demande (12, 36, 37)
    tk = db_ticket.query_one(
        """SELECT id_tk_type_demande
        FROM pgt_tk_liste WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not tk:
        return {"found": False}
    id_type_demande = _int(tk.get("id_tk_type_demande"))

    # 2) TK_DemandeSortieRH
    dem = db_tkrh.query_one(
        """SELECT id_salarie, type_sortie, info_cplt, doc_sortie
        FROM pgt_tk_demande_sortie_rh
        WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not dem:
        return {"found": False}

    id_salarie = _int(dem.get("id_salarie"))
    type_sortie = _int(dem.get("type_sortie"))

    # 3) Infos salarié
    nom = prenom = ""
    if id_salarie:
        s = db_rh.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
            (id_salarie,),
        )
        if s:
            nom = _str(s.get("nom"))
            prenom = _str(s.get("prenom"))

    # 4) Libellé du type de sortie courant
    lib_sortie = ""
    if type_sortie:
        ts = db_rh.query_one(
            "SELECT lib_sortie FROM pgt_type_sortie_salarie WHERE id_type_sortie = ?",
            (type_sortie,),
        )
        lib_sortie = _str(ts.get("lib_sortie")) if ts else ""

    # 5) Options pour la combo
    options = db_rh.query(
        """SELECT id_type_sortie, lib_sortie FROM pgt_type_sortie_salarie
        WHERE modif_elem NOT LIKE '%suppr%' ORDER BY lib_sortie"""
    )

    # 6) Date du dernier contrat
    date_dernier_ctt = _date_dernier_ctt(id_salarie)

    # 7) URL doc sortie si DocSortie = TRUE
    doc_url = ""
    if dem.get("doc_sortie"):
        # WinDev : lienDoc + "gestionRH/" + IDSalarie + "/" + idTicket + "_DocSortie.pdf"
        base = (DOCS_URL or "").rstrip("/")
        doc_url = f"{base}/gestionRH/{id_salarie}/{id_ticket}_DocSortie.pdf"

    return {
        "found": True,
        "id_ticket": str(id_ticket),
        "id_salarie": str(id_salarie),
        "id_type_demande": id_type_demande,
        # SDTC visible sauf pour type 12 (Sortie RH simple cf. WinDev)
        "show_sdtc": id_type_demande != 12,
        "lib_nom": f"{nom} {_capitalize(prenom)}".strip(),
        "nom": nom,
        "prenom": prenom,
        "type_sortie": type_sortie,
        "lib_sortie": lib_sortie,
        "type_sortie_options": [
            {
                "id": _int(t.get("id_type_sortie")),
                "label": _str(t.get("lib_sortie")),
            }
            for t in options
        ],
        "info_cplt": _str(dem.get("info_cplt")),
        "doc_sortie": bool(dem.get("doc_sortie")),
        "doc_url": doc_url,
        "date_dernier_ctt": date_dernier_ctt,
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Actions du ticket sortie RH (action = enregistrer | close | mark_doc_seen)."""
    action = str(payload.get("action") or "")
    db_ticket = get_pg_connection("ticket")
    db_tkrh = get_pg_connection("ticket_rh")

    # --- Enregistrer : UPDATE TK_DemandeSortieRH (type_sortie + info_cplt) ---
    if action == "enregistrer":
        type_sortie = _int(payload.get("type_sortie"))
        info_cplt = str(payload.get("info_cplt") or "")
        try:
            db_tkrh.query(
                """UPDATE pgt_tk_demande_sortie_rh SET
                    type_sortie = ?, info_cplt = ?,
                    modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
                (str(type_sortie), info_cplt, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"enregistrer : {e}"}
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    # --- Clôturer le ticket : UPDATE TK_Liste.Cloturee = TRUE ---
    if action == "close":
        try:
            db_ticket.query(
                """UPDATE pgt_tk_liste SET
                    cloturee = TRUE,
                    date_cloture = NOW(),
                    modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
                (int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"close : {e}"}
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    # --- Le bouton "Voir le document de sortie" tracke juste la consultation ---
    if action == "mark_doc_seen":
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    return {"ok": False, "error": f"Action inconnue : {action}"}
