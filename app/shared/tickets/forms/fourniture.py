"""FI_Fourniture (type 1 — Commande Fourniture).

Liste des lignes TK_DemandeFourniture du ticket (base ticket_bo) ;
édition d'une ligne existante (Qté, dateEnvoi, NumSuivi, adrLivraison).
Pas de création de ligne (le WinDev ne fait que HModifie sur la
ligne sélectionnée).
"""

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _now_windev,
    _str_id,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    maj_op_traitement_ticket,
)


def load(id_ticket: int) -> dict:
    """Lignes TK_DemandeFourniture du ticket + libellé type commande.

    adrLivraison est un mémo texte → fetch isolé par ligne (le bridge
    tronque les mémos en SELECT multi-colonnes).
    """
    db = get_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT IDTK_DemandeFourniture, IDTK_TypeCommande, Qté,
                dateEnvoi, PrioritéHaute, NumSuivi
            FROM TK_DemandeFourniture
            WHERE IDTK_Liste = ?
              AND ModifElem NOT LIKE '%suppr%'
            ORDER BY dateCrea""",
            (int(id_ticket),),
        )
    except Exception:
        rows = []

    type_ids: set[int] = set()
    base: list[dict] = []
    for r in rows:
        idl = _clean_id(_to_int(r.get("IDTK_DemandeFourniture")))
        if not idl:
            continue
        idtc = _clean_id(_to_int(r.get("IDTK_TypeCommande")))
        if idtc:
            type_ids.add(idtc)
        base.append({
            "id": str(idl),
            "id_type_commande": str(idtc) if idtc else "",
            "qte": _to_int(r.get("Qté")),
            "date_envoi": date_only_to_iso(r.get("dateEnvoi")),
            "priorite_haute": bool(r.get("PrioritéHaute")),
            "num_suivi": (r.get("NumSuivi") or "").strip(),
            "adr_livraison": "",
        })

    # Libellés type commande (TK_TypeCommande.LibTypeBS) - lecture pure PG
    type_libs: dict[int, str] = {}
    if type_ids:
        try:
            ids_t = ",".join(str(i) for i in type_ids)
            for t in get_pg_connection("ticket_bo").query(
                f"""SELECT id_tk_type_commande, lib_type_bs
                FROM pgt_tk_type_commande
                WHERE id_tk_type_commande IN ({ids_t})"""
            ):
                tid = _clean_id(_to_int(t.get("id_tk_type_commande")))
                if tid:
                    type_libs[tid] = (t.get("lib_type_bs") or "").strip()
        except Exception:
            pass

    # adrLivraison (mémo) — 1 SELECT isolé par ligne
    for ligne in base:
        ligne["lib_type_commande"] = type_libs.get(
            int(ligne["id_type_commande"]) if ligne["id_type_commande"] else 0, ""
        )
        try:
            m = db.query_one(
                "SELECT adrLivraison FROM TK_DemandeFourniture "
                "WHERE IDTK_DemandeFourniture = ?",
                (int(ligne["id"]),),
            )
            ligne["adr_livraison"] = ((m.get("adrLivraison") if m else "") or "").strip()
        except Exception:
            ligne["adr_livraison"] = ""

    return {"lignes": base}


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Modifie une ligne TK_DemandeFourniture (cf. bouton Enregistrer).

    payload : { id_ligne, qte, date_envoi (ISO|''), num_suivi, adr_livraison }
    """
    id_ligne = str(payload.get("id_ligne") or "")
    if not id_ligne.isdigit():
        return {"ok": False, "error": "Ligne invalide"}

    qte = _to_int(payload.get("qte"))
    date_envoi = iso_to_date_only(payload.get("date_envoi"))
    num_suivi = str(payload.get("num_suivi") or "").strip()
    adr_livraison = str(payload.get("adr_livraison") or "").strip()
    now = _now_windev()

    db = get_connection("ticket_bo")
    db.query(
        """UPDATE TK_DemandeFourniture
        SET Qté = ?, dateEnvoi = ?, NumSuivi = ?, adrLivraison = ?,
            ModifDate = ?, ModifELEM = 'modif', ModifOP = ?
        WHERE IDTK_DemandeFourniture = ?""",
        (qte, date_envoi, num_suivi, adr_livraison, now,
         int(user_id), int(id_ligne)),
    )
    # MajOpTraitementTicket (TK_Liste, base ticket)
    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True}
