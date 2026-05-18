"""FI_CttW (type 4 — Contrat W Signature).

2 plans (cf. WinDev MaFenêtreInterne..Plan) :
  - Plan 1 : contrat non validé/signé → infos mutuelle (salarie_mutuelle,
    base rh) + Choisir le DA + aperçu du PDF non signé.
  - Plan 2 : contrat validé ET signé → affichage du PDF signé final
    (emplacement à brancher) + pages validées + actions (à venir, code
    WinDev à fournir).

TK_DemandeCttW : base ticket_rh (1 enr/ticket, clé IDTK_Liste).
salarie_mutuelle + mutuelle : base rh.
"""

from app.core.database import get_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)


def _gsm_salarie(id_salarie: int) -> str:
    """TélMob (salarie_coordonnées, base rh) nettoyé."""
    if not id_salarie:
        return ""
    try:
        db = get_connection("rh")
        r = db.query_one(
            "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
            "WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        tel = (r.get("TélMob") if r else "") or ""
        for c in (".", " ", "/", "-"):
            tel = tel.replace(c, "")
        return tel.strip()
    except Exception:
        return ""

PDF_NON_SIGNE_URL = "https://interne.omaya.fr/TempCttw/{id}-cttW.pdf"


def _salaire_nom(sid: int) -> str:
    if not sid:
        return ""
    info = load_salaries_minimal({sid}).get(sid, {})
    p = info.get("prenom", "")
    return (
        f"{info.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _load_mutuelle(id_salarie: int) -> dict:
    """Infos salarie_mutuelle (base rh) pour le Plan 1."""
    db = get_connection("rh")
    r = db.query_one(
        """SELECT IDsalarie_mutuelle, IDSalarie, Adhésion, AdhésionDate,
            Mutuelle_Dossier, IdMutuelle, Mutuelle_AttSS, Mutuelle_RIB,
            Mutuelle_DocEnvoyés, Mutuelle_RecepCertif, Mutuelle_PasAdhésion,
            Mutuelle_PasAdhésionJusquau, Mutuelle_Résilié,
            Mutuelle_RésiliéDate
        FROM salarie_mutuelle
        WHERE IDSalarie = ?""",
        (int(id_salarie),),
    )
    if not r:
        return {"mutuelle_found": False}
    return {
        "mutuelle_found": True,
        "adhesion": bool(r.get("Adhésion")),
        "adhesion_date": date_only_to_iso(r.get("AdhésionDate")),
        "mutuelle_dossier": bool(r.get("Mutuelle_Dossier")),
        "id_mutuelle": _to_int(r.get("IdMutuelle")),
        "att_ss": bool(r.get("Mutuelle_AttSS")),
        "rib": bool(r.get("Mutuelle_RIB")),
        "docs_envoyes": bool(r.get("Mutuelle_DocEnvoyés")),
        "recep_certif": bool(r.get("Mutuelle_RecepCertif")),
        "pas_adhesion": bool(r.get("Mutuelle_PasAdhésion")),
        "pas_adhesion_jusquau": date_only_to_iso(
            r.get("Mutuelle_PasAdhésionJusquau")
        ),
        "resilie": bool(r.get("Mutuelle_Résilié")),
        "resilie_date": date_only_to_iso(r.get("Mutuelle_RésiliéDate")),
    }


def _list_mutuelles() -> list[dict]:
    try:
        db = get_connection("rh")
        out = []
        for m in db.query(
            "SELECT IdMutuelle, Lib_Mutuelle FROM mutuelle WHERE IsActif = 1 "
            "ORDER BY Lib_Mutuelle"
        ):
            mid = _to_int(m.get("IdMutuelle"))
            out.append({
                "id": mid,
                "lib": (m.get("Lib_Mutuelle") or "").strip(),
            })
        return out
    except Exception:
        return []


def load(id_ticket: int) -> dict:
    db = get_connection("ticket_rh")
    r = db.query_one(
        """SELECT IDTK_Liste, IDSalarie, idDA, contratGénéré,
            contratValidé, contratSigné, contratAnnul, datesignature,
            TitreContrat, TypeCttW
        FROM TK_DemandeCttW
        WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    id_da = _clean_id(_to_int(r.get("idDA")))
    contrat_valide = bool(r.get("contratValidé"))
    contrat_signe = bool(r.get("contratSigné"))
    plan = 2 if (contrat_valide and contrat_signe) else 1

    base = {
        "found": True,
        "plan": plan,
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": _salaire_nom(id_salarie),
        "id_da": str(id_da) if id_da else "",
        "da_nom": _salaire_nom(id_da),
        "titre_contrat": (r.get("TitreContrat") or "").strip(),
        "type_cttw": (r.get("TypeCttW") or "").strip(),
        "contrat_genere": bool(r.get("contratGénéré")),
        "contrat_valide": contrat_valide,
        "contrat_signe": contrat_signe,
        "contrat_annul": bool(r.get("contratAnnul")),
        "date_signature": date_only_to_iso(r.get("datesignature")),
    }

    if plan == 1:
        base.update(_load_mutuelle(id_salarie))
        base["mutuelles"] = _list_mutuelles()
        base["pdf_non_signe_url"] = PDF_NON_SIGNE_URL.format(id=id_ticket)
    else:
        # Plan 2 : PDF signé final — emplacement à brancher (à fournir).
        base["pdf_signe_url"] = ""
        base["plan2_pending"] = True

    return base


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    """Plan 1 :
      - action 'mutuelle' : Enregistrer les infos mutuelle (salarie_mutuelle)
      - action 'da'       : Choisir le DA (TK_DemandeCttW.idDA)
    """
    action = str(payload.get("action") or "mutuelle")
    now = _now_windev()

    if action == "valider":
        # « Valider le contrat de travail pour signature »
        db = get_connection("ticket_rh")
        cur = db.query_one(
            "SELECT IDSalarie, idDA FROM TK_DemandeCttW WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Contrat introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))
        id_da = _clean_id(_to_int(cur.get("idDA")))

        db.query(
            """UPDATE TK_DemandeCttW SET
                contratValidé = 1, contratSigné = 0, contratAnnul = 0,
                datesignature = '', ContenuValidation = '',
                PhotoSalarié = '', Signature = '', paraphe = '', luApp = '',
                ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), int(id_ticket)),
        )
        # TK_Liste → statut 22 (base ticket)
        get_connection("ticket").query(
            """UPDATE TK_Liste
            SET IDTK_Statut = 22, ModifDate = ?, ModifElem = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(id_ticket)),
        )
        # SMS au DA (best-effort, comme le WinDev)
        sms_result = ""
        gsm_da = _gsm_salarie(id_da)
        if gsm_da:
            txt = (
                f"Le contrat de travail pour {_salaire_nom(id_salarie)} "
                "est disponible à la signature sur ton appli OMAYA."
            )
            try:
                sms_result = envoi_sms(txt, gsm_da, "", "OMAYA-Info")
            except Exception as e:
                sms_result = f"SMS non envoyé : {e}"
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "sms_result": sms_result}

    if action == "da":
        id_da = str(payload.get("id_da") or "")
        if not id_da.isdigit():
            return {"ok": False, "error": "DA invalide"}
        db = get_connection("ticket_rh")
        db.query(
            """UPDATE TK_DemandeCttW
            SET idDA = ?, ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(id_da), now, int(user_id), int(id_ticket)),
        )
        return {"ok": True}

    # action mutuelle
    id_salarie = str(payload.get("id_salarie") or "")
    if not id_salarie.isdigit():
        return {"ok": False, "error": "Salarié inconnu"}

    def b(k):
        return 1 if payload.get(k) else 0

    db = get_connection("rh")
    exists = db.query_one(
        "SELECT IDsalarie_mutuelle FROM salarie_mutuelle WHERE IDSalarie = ?",
        (int(id_salarie),),
    )
    if not exists:
        return {"ok": False, "error": "Fiche mutuelle introuvable"}

    db.query(
        """UPDATE salarie_mutuelle SET
            Adhésion = ?, AdhésionDate = ?, Mutuelle_Dossier = ?,
            IdMutuelle = ?, Mutuelle_AttSS = ?, Mutuelle_RIB = ?,
            Mutuelle_DocEnvoyés = ?, Mutuelle_RecepCertif = ?,
            Mutuelle_PasAdhésion = ?, Mutuelle_PasAdhésionJusquau = ?,
            Mutuelle_Résilié = ?, Mutuelle_RésiliéDate = ?,
            ModifDate = ?, ModifOp = ?, ModifElem = 'modif'
        WHERE IDSalarie = ?""",
        (
            b("adhesion"), iso_to_date_only(payload.get("adhesion_date")),
            b("mutuelle_dossier"), _to_int(payload.get("id_mutuelle")),
            b("att_ss"), b("rib"), b("docs_envoyes"), b("recep_certif"),
            b("pas_adhesion"),
            iso_to_date_only(payload.get("pas_adhesion_jusquau")),
            b("resilie"), iso_to_date_only(payload.get("resilie_date")),
            now, int(user_id), int(id_salarie),
        ),
    )
    return {"ok": True}
