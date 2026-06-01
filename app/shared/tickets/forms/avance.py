"""FI_Avance (type 10 — Demande d'avance sur salaire).

Transposition de la fenêtre interne WinDev FI_Avance.

TK_DemandeAvance (1 enr/ticket, clé IDTK_Liste) — base **ticket_bo** :
Bénéficiaire (salarié), Montant (monétaire), DATEPAIEMENT (« MM-AAAA »),
PreuveVirement (mémo binaire image), DemandeValidée.
salarie_avance — base **rh** (upsert par IDTK_Liste lors de la
validation : MoisSalaire, Montant, DétaiAvance, DateEffective…).

« Virement effectué » : valide la demande, extrait la preuve vers le
FTP dossier salarié, passe le ticket en statut 21 (Terminée) + histo,
crée/maj la ligne salarie_avance.
"""

import base64
import os
import tempfile

from app.core.config import FTP_GESTION_RH_PATH
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _icone_to_data_url,
    _now_windev,
    _to_int,
    ajout_histo_tk,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)


def _salaire_nom(sid: int) -> str:
    if not sid:
        return ""
    i = load_salaries_minimal({sid}).get(sid, {})
    p = i.get("prenom", "")
    return (
        f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _preuve(id_demande: int):
    """(data_url, octets) du mémo binaire PreuveVirement.

    Lecture sur PG (bytea). PG bytea revient en memoryview/bytes.
    """
    if not id_demande:
        return "", None
    try:
        db = get_pg_connection("ticket_bo")
        r = db.query_one(
            "SELECT id_tk_demande_avance, preuve_virement FROM pgt_tk_demande_avance "
            "WHERE id_tk_demande_avance = ?",
            (int(id_demande),),
        )
        v = r.get("preuve_virement") if r else None
        url = _icone_to_data_url(v)
        raw = None
        if v:
            try:
                if isinstance(v, memoryview):
                    raw = bytes(v)
                elif isinstance(v, bytes):
                    raw = v
                else:
                    raw = base64.b64decode(str(v).split(",", 1)[-1])
            except Exception:
                raw = None
        return url, raw
    except Exception:
        return "", None


def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_bo")
    r = db.query_one(
        """SELECT id_tk_liste, id_tk_demande_avance, beneficiaire, montant,
            demande_validee, date_paiement
        FROM pgt_tk_demande_avance WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_demande = _clean_id(_to_int(r.get("id_tk_demande_avance")))
    benef = _clean_id(_to_int(r.get("beneficiaire")))
    preuve_url, _ = _preuve(id_demande)

    # salarie_avance.DateEffective (base rh) -> Date du virement
    date_virement = ""
    try:
        sa = get_pg_connection("rh").query_one(
            "SELECT id_salarie_avance, date_effective FROM pgt_salarie_avance "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        date_virement = date_only_to_iso(sa.get("date_effective")) if sa else ""
    except Exception:
        date_virement = ""

    return {
        "found": True,
        "id_demande": str(id_demande) if id_demande else "",
        "benef_id": str(benef) if benef else "",
        "benef_nom": _salaire_nom(benef),
        "montant": r.get("montant") or 0,
        "mois_paiement": (r.get("date_paiement") or "").strip(),
        "date_virement": date_virement,
        "demande_validee": bool(r.get("demande_validee")),
        "preuve_url": preuve_url,
        "has_preuve": bool(preuve_url),
    }


def upload_file(id_ticket: int, filename: str, content: bytes) -> dict:
    """« Charger la preuve de virement » : attache l'image au mémo
    binaire TK_DemandeAvance.PreuveVirement (via @ATTACHMEMO@)."""
    if not content:
        return {"ok": False, "error": "Fichier vide"}
    db = get_connection("ticket_bo")
    r = db.query_one(
        "SELECT IDTK_Liste, IDTK_DemandeAvance FROM TK_DemandeAvance "
        "WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"ok": False, "error": "Demande d'avance introuvable"}
    id_demande = _clean_id(_to_int(r.get("IDTK_DemandeAvance")))
    tmp = os.path.join(tempfile.gettempdir(), f"preuve_{id_demande}.jpg")
    with open(tmp, "wb") as f:
        f.write(content)
    try:
        db.attach_memo(
            "TK_DemandeAvance", "IDTK_DemandeAvance",
            int(id_demande), "PreuveVirement", tmp,
        )
        db.query(
            "UPDATE TK_DemandeAvance SET ModifDate = ?, ModifELEM = 'modif' "
            "WHERE IDTK_DemandeAvance = ?",
            (_now_windev(), int(id_demande)),
        )
    except Exception as e:
        return {"ok": False, "error": f"Attache mémo : {e}"}
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
    return {"ok": True}


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "virement")
    if action != "virement":
        return {"ok": False, "error": "Action non disponible"}

    mois = str(payload.get("mois_paiement") or "").strip()
    if not mois:
        return {"ok": False, "error": "Le mois de paiement est obligatoire"}

    now = _now_windev()
    bo = get_connection("ticket_bo")
    r = bo.query_one(
        """SELECT IDTK_Liste, IDTK_DemandeAvance, Bénéficiaire
        FROM TK_DemandeAvance WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"ok": False, "error": "Demande d'avance introuvable"}
    id_demande = _clean_id(_to_int(r.get("IDTK_DemandeAvance")))
    benef = _clean_id(_to_int(r.get("Bénéficiaire")))
    try:
        montant = float(payload.get("montant") or 0)
    except (TypeError, ValueError):
        montant = 0.0
    date_virement = iso_to_date_only(payload.get("date_virement"))

    # 1. TK_DemandeAvance : montant, DATEPAIEMENT, DemandeValidée
    bo.query(
        """UPDATE TK_DemandeAvance SET
            Montant = ?, DATEPAIEMENT = ?, DemandeValidée = 1,
            ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
        WHERE IDTK_DemandeAvance = ?""",
        (montant, mois, now, int(user_id), int(id_demande)),
    )

    # 2. Preuve -> FTP dossier salarié (best-effort)
    _, raw = _preuve(id_demande)
    if raw:
        try:
            from .cttw_pdf import ftp_upload

            ftp_upload(
                f"{FTP_GESTION_RH_PATH}/{benef}/Fiches_Salaires",
                f"PreuveVirement_{mois}.jpg",
                raw,
            )
        except Exception:
            pass

    # 3. TK_Liste -> statut 21 (Terminée) + histo
    try:
        get_connection("ticket").query(
            """UPDATE TK_Liste SET
                IDTK_Statut = 21, modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(user_id), now, int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), 3, int(user_id))
    except Exception as e:
        return {"ok": False, "error": f"Statut ticket : {e}"}

    # 4. salarie_avance (base rh) : upsert par IDTK_Liste
    #    MoisSalaire = 1er jour du mois "MM-AAAA" -> AAAAMM01
    d = "".join(c for c in mois if c.isdigit())
    mois_salaire = ""
    if len(d) >= 6:
        if len(mois.split("-")[0]) == 2:  # "MM-AAAA"
            mm, aaaa = d[:2], d[2:6]
        else:  # "AAAA-MM"
            aaaa, mm = d[:4], d[4:6]
        mois_salaire = f"{aaaa}{mm}01"
    rh = get_connection("rh")
    try:
        ex = rh.query_one(
            "SELECT IDsalarie_avance FROM salarie_avance "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if ex:
            rh.query(
                """UPDATE salarie_avance SET
                    IDSalarie = ?, MoisSalaire = ?, Montant = ?,
                    DétaiAvance = 'Fait via ticket', DateEffective = ?,
                    IDTK_Liste = ?, ModifDate = ?, ModifOP = ?,
                    ModifELEM = 'modif'
                WHERE IDsalarie_avance = ?""",
                (
                    int(benef), mois_salaire, montant, date_virement,
                    int(id_ticket), now, int(user_id),
                    _clean_id(_to_int(ex.get("IDsalarie_avance"))),
                ),
            )
        else:
            rh.query(
                """INSERT INTO salarie_avance
                (IDsalarie_avance, IDSalarie, MoisSalaire, Montant,
                 DétaiAvance, DateEffective, DateCrea, OpCrea, IDTK_Liste,
                 ModifDate, ModifOP, ModifELEM)
                VALUES (?, ?, ?, ?, 'Fait via ticket', ?, ?, ?, ?, ?, ?,
                        'new')""",
                (
                    int(now), int(benef), mois_salaire, montant,
                    date_virement, now, int(user_id), int(id_ticket),
                    now, int(user_id),
                ),
            )
    except Exception as e:
        return {"ok": False, "error": f"salarie_avance : {e}"}

    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True, "closed": True}
