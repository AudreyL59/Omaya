"""FI_SOSJU (type 17 — SOS Juridique).

Transposition de la fenêtre interne WinDev FI_SOSJU.

TK_DemandeSOS_JU (ticket_rh) : IDTK_TypeSOS_JU, IdElem (id générique
dépendant du TypeForm), RefDemande (mémo texte — Immatriculation /
Montant / référence libre), Descriptif (mémo texte).

TK_TypeSOS_JU (ticket_rh) définit le `TypeForm` qui pilote l'UI :
  - "Salarie"  : Pour = nom du salarié (IdElem = IDSalarie)
  - "Poste"    : Pour = TypePoste.Lib_Poste
  - "Societe"  : Pour = societe.RS_Interne
  - "Vehicule" : pas de "Pour", RefDemande = "Immatriculation"
  - autres     : pas de "Pour", RefDemande libre (label "Montant"
                 si IDTK_TypeSOS_JU = 1).
"""

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _types() -> list[dict]:
    try:
        db = get_pg_connection("ticket_rh")
        return [
            {
                "id": _to_int(r.get("id_tk_type_sos_ju")),
                "lib": (r.get("lib_type_sos") or "").strip(),
                "type_form": (r.get("type_form") or "").strip(),
            }
            for r in db.query(
                "SELECT id_tk_type_sos_ju, lib_type_sos, type_form "
                "FROM pgt_tk_type_sos_ju ORDER BY lib_type_sos"
            )
        ]
    except Exception:
        return []


def _postes() -> list[dict]:
    try:
        db = get_pg_connection("rh")
        return [
            {
                "id": _to_int(r.get("id_type_poste")),
                "lib": (r.get("lib_poste") or "").strip(),
            }
            for r in db.query(
                "SELECT id_type_poste, lib_poste FROM pgt_type_poste "
                "ORDER BY lib_poste"
            )
        ]
    except Exception:
        return []


def _societes() -> list[dict]:
    try:
        db = get_pg_connection("rh")
        return [
            {
                "id": _to_int(r.get("id_ste")),
                "lib": (r.get("rs_interne") or "").strip(),
            }
            for r in db.query(
                "SELECT id_ste, rs_interne FROM pgt_societe ORDER BY rs_interne"
            )
        ]
    except Exception:
        return []


def _memo(db, id_ticket: int, field: str) -> str:
    """Mémo texte (lecture isolée, PG). `db` est conservé pour
    compatibilité d'appel mais on lit toujours sur PG."""
    try:
        r = get_pg_connection("ticket_rh").query_one(
            f"SELECT id_tk_liste, {field} FROM pgt_tk_demande_sos_ju "
            f"WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def _pour_name(id_elem: int, type_form: str) -> str:
    """Libellé affiché du « Pour » selon TypeForm + IdElem."""
    if not id_elem:
        return ""
    tf = (type_form or "").strip()
    if tf == "Salarie":
        i = load_salaries_minimal({int(id_elem)}).get(int(id_elem), {})
        p = i.get("prenom", "")
        return (
            f"{i.get('nom', '')} "
            f"{p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()
    if tf == "Poste":
        try:
            r = get_pg_connection("rh").query_one(
                "SELECT id_type_poste, lib_poste FROM pgt_type_poste "
                "WHERE id_type_poste = ?",
                (int(id_elem),),
            )
            return (r.get("lib_poste") or "").strip() if r else ""
        except Exception:
            return ""
    if tf == "Societe":
        try:
            r = get_pg_connection("rh").query_one(
                "SELECT id_ste, rs_interne FROM pgt_societe WHERE id_ste = ?",
                (int(id_elem),),
            )
            return (r.get("rs_interne") or "").strip() if r else ""
        except Exception:
            return ""
    return ""


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        """SELECT id_tk_liste, id_tk_demande_sos_ju, id_tk_type_sos_ju, id_elem
        FROM pgt_tk_demande_sos_ju WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_type = _to_int(r.get("id_tk_type_sos_ju"))
    id_elem = _clean_id(_to_int(r.get("id_elem")))
    types = _types()
    type_form = ""
    for t in types:
        if t["id"] == id_type:
            type_form = t["type_form"]
            break

    return {
        "found": True,
        "id_demande": str(_clean_id(_to_int(r.get("id_tk_demande_sos_ju")))),
        "id_type": id_type,
        "types": types,
        "id_elem": str(id_elem) if id_elem else "",
        "type_form": type_form,
        "pour_name": _pour_name(id_elem, type_form),
        "ref_demande": _memo(db, id_ticket, "ref_demande"),
        "descriptif": _memo(db, id_ticket, "descriptif"),
        # Lookups pour les TypeForm Poste / Societe (combos)
        "postes": _postes(),
        "societes": _societes(),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    if str(payload.get("action") or "enregistrer") != "enregistrer":
        return {"ok": False, "error": "Action non disponible"}

    now = _now_windev()
    db = get_connection("ticket_rh")
    cur = db.query_one(
        "SELECT IDTK_Liste FROM TK_DemandeSOS_JU WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not cur:
        return {"ok": False, "error": "Demande SOS JU introuvable"}
    db.query(
        """UPDATE TK_DemandeSOS_JU SET
            IDTK_TypeSOS_JU = ?, IdElem = ?, RefDemande = ?, Descriptif = ?,
            ModifOP = ?, ModifDate = ?, ModifELEM = 'modif'
        WHERE IDTK_Liste = ?""",
        (
            _to_int(payload.get("id_type")),
            _to_int(payload.get("id_elem")),
            str(payload.get("ref_demande") or ""),
            str(payload.get("descriptif") or ""),
            int(user_id), now, int(id_ticket),
        ),
    )
    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True}
