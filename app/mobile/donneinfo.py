"""Endpoints mobile DonneInfo (WebRest_Omayapp/DonneInfo/*).

Portage iso-URL des 4 WS DonneInfo/* :
  - DonneInfo/Doc/{id}     : contenu texte d'un docCourtage
  - DonneInfo/Poste        : ST_POSTE {idPoste, libPoste}
  - DonneInfo/Salarie      : ST_SALARIE {ID, Nom, Prenom}
  - DonneInfo/Ste          : ST_SOCIETE complet
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.deps import mobile_auth
from app.shared.dialogues.services.taches_it import _rtf_to_text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-donneinfo"],
                    dependencies=[Depends(mobile_auth)])


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _bytea_to_b64(v) -> str:
    if not v:
        return ""
    if isinstance(v, memoryview):
        v = v.tobytes()
    elif isinstance(v, str):
        return v  # deja base64
    try:
        return base64.b64encode(v).decode("ascii")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
#  DonneInfo/Doc/{id}
# ---------------------------------------------------------------------------

@router.get("/DonneInfo/Doc/{id_doc}")
@router.post("/DonneInfo/Doc/{id_doc}")
def donne_info_doc(id_doc: str, _payload: Any = Body(default=None)):
    """Portage DonneContenuDoc. Retourne le texte plat d'un docCourtage.

    WinDev fait Document.VersTexte() sur le bytea. On tente :
    - Decodage UTF-8/latin-1 direct
    - Fallback parse RTF si c'est du Riched20/WinDev
    - Fallback base64 si le contenu n'est pas du texte
    Retour STRéponseTK : { nIdDemande, sInfoData: texte }
    """
    id_val = _to_int(id_doc)
    resp = {"nIdDemande": id_doc, "sInfoData": ""}
    if not id_val:
        return resp

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT contenu FROM rh.pgt_doc_courtage
                WHERE id_doc_courtage = ? LIMIT 1""",
            (id_val,),
        )
    except Exception:
        logger.exception("donne_info_doc id=%s", id_doc)
        return resp
    if not row:
        return resp

    contenu = row.get("contenu")
    if not contenu:
        return resp
    if isinstance(contenu, memoryview):
        contenu = contenu.tobytes()

    # Cas 1 : texte deja plat (UTF-8)
    if isinstance(contenu, bytes):
        # Detection RTF
        if contenu.startswith(b"{\\rtf"):
            try:
                raw = contenu.decode("latin-1", errors="replace")
                resp["sInfoData"] = _rtf_to_text(raw)
                return resp
            except Exception:
                logger.exception("donne_info_doc: rtf id=%s", id_doc)
        # Detection binaire non-texte
        try:
            resp["sInfoData"] = contenu.decode("utf-8")
            return resp
        except UnicodeDecodeError:
            try:
                resp["sInfoData"] = contenu.decode("latin-1")
                return resp
            except Exception:
                # fallback base64
                resp["sInfoData"] = _bytea_to_b64(contenu)
                return resp

    return resp


# ---------------------------------------------------------------------------
#  DonneInfo/Poste
# ---------------------------------------------------------------------------

@router.post("/DonneInfo/Poste")
def donne_info_poste(payload: dict = Body(...)):
    """Portage DonneInfoPoste. Retour : {idPoste, libPoste}."""
    id_poste = _to_int(payload.get("idPoste") or payload.get("IdSte")
                        or payload.get("id"))
    if not id_poste:
        return {"idPoste": 0, "libPoste": ""}

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_type_poste, lib_poste
                 FROM rh.pgt_type_poste
                WHERE id_type_poste = ? LIMIT 1""",
            (id_poste,),
        )
    except Exception:
        logger.exception("donne_info_poste id=%s", id_poste)
        return {"idPoste": 0, "libPoste": ""}
    if not row:
        return {"idPoste": 0, "libPoste": ""}
    return {
        "idPoste": int(row.get("id_type_poste") or 0),
        "libPoste": (row.get("lib_poste") or "").strip(),
    }


# ---------------------------------------------------------------------------
#  DonneInfo/Salarie
# ---------------------------------------------------------------------------

@router.post("/DonneInfo/Salarie")
def donne_info_salarie(payload: dict = Body(...)):
    """Portage DonneInfoSalaries. Retour ST_SALARIE minimal :
    {ID, Nom, Prenom} (l'API WinDev ne retournait que ces 3 champs)."""
    id_sa = _to_int(payload.get("IdSa") or payload.get("IDSalarie")
                     or payload.get("id"))
    if not id_sa:
        return {"ID": 0, "Nom": "", "Prenom": ""}

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_salarie, nom, prenom
                 FROM rh.pgt_salarie
                WHERE id_salarie = ? LIMIT 1""",
            (id_sa,),
        )
    except Exception:
        logger.exception("donne_info_salarie id=%s", id_sa)
        return {"ID": 0, "Nom": "", "Prenom": ""}
    if not row:
        return {"ID": 0, "Nom": "", "Prenom": ""}
    return {
        "ID": int(row.get("id_salarie") or 0),
        "Nom": (row.get("nom") or "").strip(),
        "Prenom": (row.get("prenom") or "").strip(),
    }


# ---------------------------------------------------------------------------
#  DonneInfo/Ste
# ---------------------------------------------------------------------------

@router.post("/DonneInfo/Ste")
def donne_info_ste(payload: dict = Body(...)):
    """Portage DonneInfoSte. Retour ST_SOCIETE avec images en base64."""
    id_ste = _to_int(payload.get("IdSte") or payload.get("id"))
    empty = {
        "IdSte": 0, "RS_Interne": "", "ADRESSE1": "",
        "CP": "", "VILLE": "", "SIREN": "",
        "GUIMMICK": "", "GerantSignature": "",
        "GerantParaphe": "", "CachetCial": "",
    }
    if not id_ste:
        return empty

    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_ste, rs_interne, adresse1, cp, ville, siren,
                      guimmick, gerant_signature, gerant_paraphe, cachet_cial
                 FROM rh.pgt_societe
                WHERE id_ste = ? LIMIT 1""",
            (id_ste,),
        )
    except Exception:
        logger.exception("donne_info_ste id=%s", id_ste)
        return empty
    if not row:
        return empty

    return {
        "IdSte": int(row.get("id_ste") or 0),
        "RS_Interne": (row.get("rs_interne") or "").strip(),
        "ADRESSE1": (row.get("adresse1") or "").strip(),
        "CP": (row.get("cp") or "").strip(),
        "VILLE": (row.get("ville") or "").strip(),
        "SIREN": (row.get("siren") or "").strip(),
        "GUIMMICK": _bytea_to_b64(row.get("guimmick")),
        "GerantSignature": _bytea_to_b64(row.get("gerant_signature")),
        "GerantParaphe": _bytea_to_b64(row.get("gerant_paraphe")),
        "CachetCial": _bytea_to_b64(row.get("cachet_cial")),
    }
