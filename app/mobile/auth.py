"""Endpoints d'authentification mobile (WebRest_Omayapp).

Portage iso-signature des WS WinDev :
  - VerifIdentifiant       : Omayapp_Connexion (mail + mdp -> ST_SALARIE)
  - Auth/RenewToken        : CR_renouvelleToken (id -> UUID256)
  - Auth/ChangerMotDePasse : Omayapp_ModifMDP (id + mdpOld + mdpNew -> {nIdDemande})
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body

from app.core.auth.security import (
    create_access_token, encrypt_password, verify_password,
)
from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-auth"])


# ---------------------------------------------------------------------------
#  Helpers portage WinDev
# ---------------------------------------------------------------------------

def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _str_id(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _empty_st_salarie() -> dict:
    """ST_SALARIE avec ID=0 pour signaler une auth echouee (convention
    WinDev Omayapp_Connexion : stMonSalarie.ID = 0)."""
    return {
        "ID": 0, "Nom": "", "Prenom": "", "Login": "", "Mail": "",
        "IsResp": False, "Poste": "", "Categorie": "",
        "IsPause": False, "EnActivite": False,
        "affectation": {"id": 0, "Lib": ""},
        "MesResp": [], "MonOrga": [], "DroitOmaya": [],
    }


def _info_salarie_complet(id_salarie: int) -> dict:
    """Portage Omayapp_InfoSalarié + assemblage similaire au WS WinDev
    (V1 : infos de base + droits ; MonOrga et MesResp restent vides —
    a completer en V2 via les services existants)."""
    if not id_salarie:
        return _empty_st_salarie()
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT s.id_salarie, s.nom, s.prenom, s.login,
                      sc.mail, se.resp_equipe, se.resp_adjoint,
                      se.en_activite, se.en_pause, se.id_ste,
                      se.id_type_poste,
                      tp.lib_poste, tp.categorie
                 FROM rh.pgt_salarie s
                 LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                 LEFT JOIN rh.pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
                 LEFT JOIN rh.pgt_type_poste tp ON tp.id_type_poste = se.id_type_poste
                WHERE s.id_salarie = ? LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        logger.exception("_info_salarie_complet id=%s", id_salarie)
        return _empty_st_salarie()
    if not row:
        return _empty_st_salarie()

    # Affectation principale (idorganigramme actif)
    aff_id = 0
    aff_lib = ""
    try:
        aff = db.query_one(
            """SELECT so.idorganigramme, o.lib_orga
                 FROM rh.pgt_salarie_organigramme so
                 LEFT JOIN rh.pgt_organigramme o
                        ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND COALESCE(so.aff_actif, FALSE) = TRUE
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_salarie),),
        )
        if aff:
            aff_id = int(aff.get("idorganigramme") or 0)
            aff_lib = aff.get("lib_orga") or ""
    except Exception:
        logger.exception("_info_salarie_complet: affectation id=%s", id_salarie)

    # Droits (code_interne)
    droits: list[dict] = []
    try:
        d_rows = db.query(
            """SELECT td.code_interne, td.lib_droit
                 FROM rh.pgt_salarie_droit_acces sd
                 JOIN rh.pgt_type_droit_acces td
                        ON td.id_type_droit_acces = sd.id_type_droit_acces
                WHERE sd.id_salarie = ?
                  AND COALESCE(sd.droit_actif, FALSE) = TRUE""",
            (int(id_salarie),),
        ) or []
        droits = [{"Code": d.get("code_interne") or "",
                   "Lib": d.get("lib_droit") or ""} for d in d_rows]
    except Exception:
        logger.exception("_info_salarie_complet: droits id=%s", id_salarie)

    # Exception WinDev : APPLE-VERIF Martin id 20190827110730867 -> droits vides
    if int(id_salarie) == 20190827110730867:
        droits = []

    return {
        "ID": int(row.get("id_salarie") or 0),
        "Nom": (row.get("nom") or "").strip(),
        "Prenom": _capitalise((row.get("prenom") or "").strip()),
        "Login": row.get("login") or "",
        "Mail": row.get("mail") or "",
        "IsResp": bool(row.get("resp_equipe")),
        "IsRespAdjoint": bool(row.get("resp_adjoint")),
        "IsPause": bool(row.get("en_pause")),
        "EnActivite": bool(row.get("en_activite")),
        "Poste": row.get("lib_poste") or "",
        "Categorie": row.get("categorie") or "",
        "IdSte": int(row.get("id_ste") or 0),
        "affectation": {"id": aff_id, "Lib": aff_lib},
        "DroitOmaya": droits,
        # TODO V2 : MesResp (RecupListeDaDr), MonOrga (Omayapp_InfoOrganigramme)
        "MesResp": [],
        "MonOrga": [],
    }


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@router.post("/VerifIdentifiant")
def verif_identifiant(payload: dict = Body(...)):
    """Login mobile. Portage Omayapp_Connexion.

    Payload WinDev (ST_CONNEXION) : { Mail: str, mdp: str }
    Reponse : ST_SALARIE (ID=0 si echec, sinon infos completes).

    Bonus V1 : ajoute `access_token` (JWT) dans la reponse pour
    permettre au mobile de basculer progressivement vers l'auth Bearer.
    """
    mail = (payload.get("Mail") or "").strip()
    mdp = payload.get("mdp") or ""
    if not mail or not mdp:
        return _empty_st_salarie()

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_salarie, mdp_crypte
                 FROM rh.pgt_salarie
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND LOWER(login) = LOWER(?) LIMIT 1""",
            (mail,),
        )
    except Exception:
        logger.exception("verif_identifiant: query login=%s", mail)
        return _empty_st_salarie()
    if not row:
        return _empty_st_salarie()

    mdp_crypte = row.get("mdp_crypte")
    if not mdp_crypte or not verify_password(mdp_crypte, mdp):
        return _empty_st_salarie()

    id_salarie = int(row.get("id_salarie") or 0)
    info = _info_salarie_complet(id_salarie)
    # Bonus JWT (compat future) — le mobile peut l'utiliser en Authorization: Bearer
    info["access_token"] = create_access_token({"sub": str(id_salarie)})
    info["token_type"] = "Bearer"
    # Signature HMAC pour construire le lien public de cooptation
    # (page /PageExterne/coopt?c={id}&s={SignatureCoopt}). Vide si
    # COOPT_HMAC_SECRET n'est pas configure.
    from app.shared.recrutement.services.public_coopt import sign_coopt
    info["SignatureCoopt"] = sign_coopt(id_salarie)
    return info


@router.post("/Auth/RenewToken")
def renew_token(payload: dict = Body(...)):
    """Renouvellement UUID256. Portage CR_renouvelleToken.

    Payload : { IDSalarie: int }
    Reponse : { IDSalarie: int, sToken: str }  (UUID256 = 64 hex chars,
    ou vide si le salarie n'existe pas)
    """
    try:
        id_salarie = int(payload.get("IDSalarie") or 0)
    except (TypeError, ValueError):
        id_salarie = 0
    if not id_salarie:
        return {"IDSalarie": 0, "sToken": ""}

    db_rh = get_pg_connection("rh")
    db_div = get_pg_connection("divers")

    # 1. Verif que le salarie existe
    try:
        s = db_rh.query_one(
            "SELECT id_salarie FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_salarie,),
        )
    except Exception:
        logger.exception("renew_token: check salarie")
        return {"IDSalarie": 0, "sToken": ""}
    if not s:
        return {"IDSalarie": 0, "sToken": ""}

    # 2. UUID256 = 32 octets random -> 64 chars hex (comme DonneUUID256() WinDev)
    new_uuid = secrets.token_hex(32)
    now = datetime.now()

    # 3. Upsert dans pgt_uuid_connexion
    try:
        existing = db_div.query_one(
            """SELECT id_uuid_connexion_auto
                 FROM divers.pgt_uuid_connexion
                WHERE id_salarie = ? LIMIT 1""",
            (id_salarie,),
        )
        if existing:
            db_div.query(
                """UPDATE divers.pgt_uuid_connexion
                      SET id_uuid_connexion = ?, modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_uuid_connexion_auto = ?""",
                (new_uuid, now, id_salarie,
                 int(existing.get("id_uuid_connexion_auto") or 0)),
            )
        else:
            db_div.query(
                """INSERT INTO divers.pgt_uuid_connexion
                     (id_salarie, id_uuid_connexion,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, 'new')""",
                (id_salarie, new_uuid, now, id_salarie),
            )
    except Exception:
        logger.exception("renew_token: upsert uuid id_sal=%s", id_salarie)
        return {"IDSalarie": id_salarie, "sToken": ""}

    return {"IDSalarie": id_salarie, "sToken": new_uuid}


@router.post("/Auth/ChangerMotDePasse")
def changer_mot_de_passe(payload: dict = Body(...)):
    """Changement mot de passe. Portage Omayapp_ModifMDP.

    Payload (ST_MODIFMDP) : { id: int, mdpOld: str, mdpNew: str }
    Reponse (STRéponseTK) :
      { nIdDemande: id }  si OK
      { nIdDemande: 666 } si mdpOld incorrect
      { nIdDemande: 0 }   si salarie inconnu ou echec
    """
    try:
        id_salarie = int(payload.get("id") or 0)
    except (TypeError, ValueError):
        id_salarie = 0
    mdp_old = payload.get("mdpOld") or ""
    mdp_new = payload.get("mdpNew") or ""
    if not id_salarie:
        return {"nIdDemande": 0}

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT mdp_crypte FROM rh.pgt_salarie
                WHERE id_salarie = ? LIMIT 1""",
            (id_salarie,),
        )
    except Exception:
        logger.exception("changer_mot_de_passe: query id=%s", id_salarie)
        return {"nIdDemande": 0}
    if not row:
        return {"nIdDemande": 0}

    if not verify_password(row.get("mdp_crypte"), mdp_old):
        return {"nIdDemande": 666}  # convention WinDev pour 'mauvais mdp'

    # OK -> encrypt le nouveau + update
    try:
        new_crypted = encrypt_password(mdp_new)
        import psycopg2
        now = datetime.now()
        db.query(
            """UPDATE rh.pgt_salarie
                  SET mdp_crypte = ?, modif_op = ?, modif_date = ?, modif_elem = 'modif'
                WHERE id_salarie = ?""",
            (psycopg2.Binary(new_crypted), id_salarie, now, id_salarie),
        )
        return {"nIdDemande": id_salarie}
    except Exception:
        logger.exception("changer_mot_de_passe: update id=%s", id_salarie)
        return {"nIdDemande": 0}
