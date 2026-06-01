"""FI_AttExoCash (type 25 — Attribution ExoCash).

Crédite le livret ExoCash (salarie_Livret, base rh) d'un salarié d'un
montant en EC (monnaie virtuelle interne), au titre d'une opération
(Gain Challenge / Prime / Commande Boutique EC).

Tables :
  - Tk_DemandeAttExoCash : base ticket_rh (montant + info attribution)
  - TypeOperationLivret : base rh (combo « Type Opération »)
  - ChallengeEvenement : base divers (challenge associé si Gain Challenge)
  - salarie_Livret : base rh (crédit à la validation)
  - TK_Liste : base ticket (clôture du ticket)

Fonctionnalités :
  - Saisie Montant + Info Attribution
  - Type Opération (combo TypeOperationLivret) ; si « Gain Challenge »
    (id 1) → choix d'un challenge (ChallengeEvenement)
  - Valider l'attribution : MAJ Tk_DemandeAttExoCash, crédit livret,
    SMS au demandeur (TK_Liste.OPCREA)
  - Clôturer le ticket (TK_Liste.Cloturée)

Une fois le crédit livret créé (salarie_Livret pour ce ticket), la
validation n'est plus proposée (attribution déjà effectuée).
"""

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    _windev_to_iso,
    date_only_to_iso,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

TYPE_OP_GAIN_CHALLENGE = 1  # TypeOperationLivret → affiche le choix challenge


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _fr_date(aaaammjj) -> str:
    """AAAAMMJJ (HFSQL Date) → 'JJ/MM/AAAA' (vide si absent)."""
    iso = date_only_to_iso(aaaammjj)
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _type_operations() -> list[dict]:
    """Combo « Type Opération » (TypeOperationLivret, base rh)."""
    try:
        rows = get_pg_connection("rh").query(
            "SELECT id_type_operation_livret, lib_opeation "
            "FROM pgt_type_operation_livret WHERE modif_elem NOT LIKE '%suppr%' "
            "ORDER BY lib_opeation ASC"
        )
    except Exception:
        return []
    return [
        {
            "id": _to_int(r.get("id_type_operation_livret")),
            "lib": (r.get("lib_opeation") or "").strip(),
        }
        for r in rows or []
    ]


def _challenges() -> list[dict]:
    """Liste des challenges (ChallengeEvenement, base divers) pour le
    select. Libellé enrichi 'Libellé, du JJ/MM/AAAA au JJ/MM/AAAA'."""
    try:
        rows = get_pg_connection("divers").query(
            "SELECT id_challenge_evenement, libelle, date_debut, date_fin "
            "FROM pgt_challenge_evenement WHERE modif_elem NOT LIKE '%suppr%' "
            "ORDER BY date_debut DESC"
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        idc = _clean_id(_to_int(r.get("id_challenge_evenement")))
        if not idc:
            continue
        lib = (r.get("libelle") or "").strip()
        d1 = _fr_date(r.get("date_debut"))
        d2 = _fr_date(r.get("date_fin"))
        label = lib
        if d1 and d2:
            label = f"{lib}, du {d1} au {d2}"
        out.append({"id": str(idc), "label": label})
    return out


def _challenge_label(id_challenge: int) -> str:
    if not id_challenge:
        return ""
    try:
        r = get_pg_connection("divers").query_one(
            "SELECT id_challenge_evenement, libelle, date_debut, date_fin "
            "FROM pgt_challenge_evenement WHERE id_challenge_evenement = ?",
            (int(id_challenge),),
        )
    except Exception:
        return ""
    if not r:
        return ""
    lib = (r.get("libelle") or "").strip()
    d1 = _fr_date(r.get("date_debut"))
    d2 = _fr_date(r.get("date_fin"))
    return f"{lib}, du {d1} au {d2}" if (d1 and d2) else lib


def _livret_existant(id_ticket: int, use_hf: bool = False) -> dict | None:
    """salarie_Livret déjà créé pour ce ticket → attribution effectuée.

    use_hf=True : utilise HFSQL (pour les checks pre-UPDATE, evite le lag
    de la sync). use_hf=False (default) : PG (lecture d'affichage).
    """
    try:
        db = get_connection("rh") if use_hf else get_pg_connection("rh")
        if use_hf:
            return db.query_one(
                "SELECT IDsalarie_Livret, IDTypeOperationLivret, IDChallenge, "
                "DateOpération FROM salarie_Livret WHERE IDTK_Liste = ?",
                (int(id_ticket),),
            )
        return db.query_one(
            "SELECT id_salarie_livret, id_type_operation_livret, id_challenge, "
            "date_operation FROM pgt_salarie_livret WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
    except Exception:
        return None


def _info_attribution(id_ticket: int) -> str:
    """Mémo texte InfoAttribution (lecture isolée)."""
    try:
        r = get_pg_connection("ticket_rh").query_one(
            "SELECT id_tk_liste, info_attribution FROM pgt_tk_demande_att_exo_cash "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        return ((r.get("info_attribution") if r else "") or "").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_rh")
    r = db.query_one(
        "SELECT id_tk_liste, id_tk_demande_att_exo_cash, id_salarie, montant_ec "
        "FROM pgt_tk_demande_att_exo_cash WHERE id_tk_liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_att = _clean_id(_to_int(r.get("id_tk_demande_att_exo_cash")))
    id_salarie = _clean_id(_to_int(r.get("id_salarie")))

    salarie_nom = ""
    if id_salarie:
        i = load_salaries_minimal({id_salarie}).get(id_salarie, {})
        p = (i.get("prenom") or "")
        salarie_nom = (
            f"{i.get('nom', '')} "
            f"{p[:1].upper() + p[1:].lower() if p else ''}"
        ).strip()

    livret = _livret_existant(id_ticket)
    attribuee = bool(livret)
    type_operation = _to_int(livret.get("id_type_operation_livret")) if livret else 0
    id_challenge = _clean_id(_to_int(livret.get("id_challenge"))) if livret else 0
    date_attribution = _windev_to_iso(livret.get("date_operation")) if livret else ""

    return {
        "found": True,
        "id_att": str(id_att) if id_att else "",
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": salarie_nom,
        "montant": float(r.get("montant_ec") or 0),
        "info_attribution": _info_attribution(id_ticket),
        "type_operation": type_operation,
        "id_challenge": str(id_challenge) if id_challenge else "",
        "challenge_label": _challenge_label(id_challenge),
        "attribuee": attribuee,
        "date_attribution": date_attribution,
        "type_operations": _type_operations(),
        "challenges": _challenges(),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()

    # --- validation de l'attribution (crédit livret) ---
    if action == "valider":
        # SELECT pre-UPDATE -> garde sur HFSQL pour eviter le lag PG
        if _livret_existant(id_ticket, use_hf=True):
            return {"ok": False, "error": "Attribution déjà effectuée"}

        rh_tk = get_connection("ticket_rh")
        cur = rh_tk.query_one(
            "SELECT IDTk_DemandeAttExoCash, IDSalarie FROM Tk_DemandeAttExoCash "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Demande introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        montant = float(payload.get("montant") or 0)
        if montant <= 0:
            return {"ok": False, "error": "Montant EC invalide"}
        info = str(payload.get("info_attribution") or "")
        type_op = _to_int(payload.get("type_operation"))
        id_challenge = _to_int(payload.get("id_challenge"))

        # 1. ÉcranVersFichier : MAJ Tk_DemandeAttExoCash (montant + info)
        try:
            rh_tk.query(
                """UPDATE Tk_DemandeAttExoCash SET MontantEC = ?,
                    InfoAttribution = ?, ModifDate = ?, ModifOp = ?,
                    ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (montant, info, now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"MAJ demande : {e}"}

        # 2. salarie_Livret : crédit (base rh)
        try:
            get_connection("rh").query(
                """INSERT INTO salarie_Livret
                (IDsalarie_Livret, IDSalarie, IDTypeOperationLivret,
                 IDChallenge, IDTK_Liste, MontantCrédit, MontantDébit,
                 DateOpération, Operateur, ModifDate, ModifOp, ModifElem)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'new')""",
                (
                    int(now), int(id_salarie), int(type_op),
                    int(id_challenge), int(id_ticket), float(montant),
                    now, int(user_id), now, int(user_id),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"salarie_Livret : {e}"}

        # 3. SMS au demandeur (TK_Liste.OPCREA)
        sms_result = ""
        try:
            tk = get_connection("ticket").query_one(
                "SELECT IDTK_Liste, OPCREA FROM TK_Liste WHERE IDTK_Liste = ?",
                (int(id_ticket),),
            )
            op_crea = _clean_id(_to_int(tk.get("OPCREA"))) if tk else 0
            infos = load_salaries_minimal({op_crea, id_salarie, int(user_id)})
            benef = infos.get(id_salarie, {})
            bp = (benef.get("prenom") or "")
            benef_nom = (
                f"{bp[:1].upper() + bp[1:].lower() if bp else ''} "
                f"{benef.get('nom', '')}"
            ).strip()
            up = (infos.get(int(user_id), {}).get("prenom") or "")
            op_prenom = up[:1].upper() + up[1:].lower() if up else ""
            montant_txt = (
                str(int(montant)) if float(montant).is_integer()
                else f"{montant:.2f}"
            )
            texte = (
                f"L'exo cash de {montant_txt}EC pour {benef_nom} "
                f"vient d'être validé par {op_prenom}."
            )
            c = get_connection("rh").query_one(
                "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
                "WHERE IDSalarie = ?",
                (int(op_crea),),
            )
            gsm = ((c.get("TélMob") if c else "") or "")
            for ch in (".", " ", "/", "-"):
                gsm = gsm.replace(ch, "")
            if gsm:
                sms_result = envoi_sms(texte, gsm, "", "AttExoCash")
        except Exception as e:
            sms_result = f"SMS non envoyé : {e}"

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {
            "ok": True,
            "sms_result": sms_result,
            "date_attribution": _windev_to_iso(now),
        }

    # --- clôture du ticket ---
    if action == "cloturer":
        try:
            get_connection("ticket").query(
                """UPDATE TK_Liste SET Cloturée = 1, ModifOp = ?,
                    ModifDate = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (int(user_id), now, int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"clôture : {e}"}
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    return {"ok": False, "error": "Action non disponible"}
