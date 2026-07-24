"""Page externe de saisie de cooptation (accessible sans login).

Le coopteur genere un lien signe depuis l'app mobile et le partage a
la personne qu'il souhaite coopter. La page publique se pre-remplit
avec les infos du coopteur (via la signature HMAC).

Signature : hmac_sha256(str(id_coopteur).encode(), COOPT_HMAC_SECRET.encode())
            -> hexa lowercase, 64 chars.

Comparaison en timing-safe (hmac.compare_digest).
"""

from __future__ import annotations

import hmac
import hashlib
from typing import Optional

from pydantic import BaseModel

from app.core.config import COOPT_HMAC_SECRET
from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


class PublicCoopteurInfo(BaseModel):
    id: str
    nom: str = ""
    prenom: str = ""


class PublicVilleItem(BaseModel):
    id: str
    cp: str = ""
    nom_ville: str = ""


def _capitalize(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def sign_coopt(id_coopteur: int) -> str:
    """Genere la signature HMAC_SHA256 pour un id coopteur donne.
    Utilise cote mobile pour construire l'URL de partage."""
    if not COOPT_HMAC_SECRET:
        return ""
    msg = str(int(id_coopteur)).encode("utf-8")
    key = COOPT_HMAC_SECRET.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_coopt_signature(id_coopteur: int, signature: str) -> bool:
    """Verifie une signature HMAC en timing-safe."""
    if not COOPT_HMAC_SECRET or not signature or not id_coopteur:
        return False
    expected = sign_coopt(id_coopteur)
    if not expected:
        return False
    try:
        return hmac.compare_digest(expected, signature.strip().lower())
    except Exception:
        return False


def get_coopteur_info(id_coopteur: int) -> tuple[Optional[PublicCoopteurInfo], bool]:
    """Retourne (info, en_activite).

    - (None, False)      : coopteur inconnu ou supprime
    - (info, False)      : coopteur existe mais salarie_embauche.en_activite = FALSE
    - (info, True)       : coopteur actif
    """
    if not id_coopteur:
        return None, False
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT s.id_salarie, s.nom, s.prenom,
                  COALESCE(se.en_activite, FALSE) AS en_activite
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
            WHERE s.id_salarie = ?
              AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')""",
        (int(id_coopteur),),
    )
    if not row:
        return None, False
    info = PublicCoopteurInfo(
        id=str(_int(row.get("id_salarie"))),
        nom=_str(row.get("nom")).upper().strip(),
        prenom=_capitalize(_str(row.get("prenom")).strip()),
    )
    return info, bool(row.get("en_activite"))


def liste_villes_by_cp(cp: str) -> list[PublicVilleItem]:
    """Autocomplete villes par code postal (5 chiffres)."""
    cp = (cp or "").strip()
    if not cp:
        return []
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_communes_france, nom_ville, code_postal
             FROM divers.pgt_communes_france
            WHERE code_postal = ?
            ORDER BY nom_ville ASC""",
        (cp,),
    ) or []
    return [
        PublicVilleItem(
            id=str(_int(r.get("id_communes_france"))),
            cp=_str(r.get("code_postal")),
            nom_ville=_str(r.get("nom_ville")),
        )
        for r in rows
    ]
