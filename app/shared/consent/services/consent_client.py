"""Page externe de consentement client (page de fin d'appel Call).

Portage WinDev Page_ConsentClient. Le vendeur genere un lien vers
cette page pour le client, qui valide le panier + accepte/refuse
d'etre rappele par le service qualite.

URL WinDev : ...?P1=<TypeTK><IdTicket>
             ex. P1=SFR20220315123456789  ou  P1=ENI...
Portage FastAPI : le meme code est passe dans le query param `p`.

Securite : l'id_ticket est un timestamp 8 octets (impossible a deviner
par bruteforce). Pas de signature HMAC ajoutee (identique a ConfRdvPage).

⚠️ Branchement HFSQL (bascule PG prevue au WE 22-23 août 2026).
On garde les noms de tables/colonnes WinDev tel quel (casse + accents).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.core.database.connections import get_connection

logger = logging.getLogger(__name__)


# Whitelist des prefixes partenaires (evite l'injection SQL sur
# le nom de table dynamique <prefix>_produit). Basee sur les tables
# HFSQL existantes cote base adv.
ALLOWED_PART_PREFIXES = {
    "ENI", "GEP", "IAG", "OEN", "PRO", "SFR", "STR", "TLC", "VAL",
}
_PREFIX_RE = re.compile(r"^[A-Z]{3}$")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PanierLine(BaseModel):
    type: str = ""
    nom: str = ""
    montant: float | None = None
    id_panier: str = ""


class PublicConsent(BaseModel):
    type_tk: str = ""              # 'ENI' ou 'SFR'
    id_ticket: str = ""
    info_client: str = ""          # multi-ligne, prefabrique
    code_valid: str = ""
    deja_valide: bool = False      # Opt_Rappel = 1 -> plan 2 direct
    panier: list[PanierLine] = []


class ValidatePayload(BaseModel):
    opt_rappel: bool                    # True = J'accepte d'etre rappele
    opt_oppose_partenaire: bool = True  # True = Je m'oppose au partage partenaire
                                        # (semantique WinDev inversee : Opt_Partenaire=1 = opposition)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _int(v: Any) -> int:
    try:
        return int(v) if v not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


def _parse_p(p: str) -> tuple[str, int]:
    """P1 WinDev = <TypeTK 3 chars><IdTicket int>."""
    if not p or len(p) < 4:
        return "", 0
    type_tk = p[:3].upper()
    try:
        id_ticket = int(p[3:])
    except ValueError:
        id_ticket = 0
    return type_tk, id_ticket


def _bloc_info_client(row: dict) -> str:
    """Reconstruit le libelle multi-ligne du bloc info client."""
    nom = _str(row.get("NomClient"))
    nom_marital = _str(row.get("NomMaritalClient"))
    prenom = _capitalize(_str(row.get("PrenomClient")))
    adr1 = _str(row.get("ADRESSE1"))
    adr2 = _str(row.get("ADRESSE2"))
    cp = _str(row.get("CP"))
    ville = _str(row.get("VILLE"))
    mobile = _str(row.get("Mobile1"))
    mail = _str(row.get("adrMail"))

    l1 = nom
    if nom_marital:
        l1 += f" ép. {nom_marital}"
    l1 = (l1 + " " + prenom).strip()

    lignes = [l1, adr1]
    if adr2:
        lignes.append(adr2)
    lignes.append(f"{cp} {ville}".strip())
    lignes.append(f"Mobile : {mobile}")
    lignes.append(f"Courriel : {mail}")
    return "\n".join(l for l in lignes if l is not None)


# ---------------------------------------------------------------------------
# Lecture (GET)
# ---------------------------------------------------------------------------


def get_consent_public(p: str) -> Optional[PublicConsent]:
    type_tk, id_ticket = _parse_p(p)
    if not id_ticket or type_tk not in ("ENI", "SFR"):
        return None

    if type_tk == "SFR":
        return _get_sfr(id_ticket)
    return _get_eni(id_ticket)


def _get_eni(id_ticket: int) -> Optional[PublicConsent]:
    db = get_connection("ticket_bo")
    try:
        rows = db.query(
            "SELECT * FROM TK_Call WHERE IDTK_Liste = ?",
            (id_ticket,),
        )
    except Exception:
        logger.exception("_get_eni head id=%s", id_ticket)
        return None
    if not rows:
        return None
    r = rows[0]

    info = _bloc_info_client(r)
    code_valid = _str(r.get("CodeValid"))
    opt_rappel = bool(_int(r.get("Opt_Rappel")))

    panier: list[PanierLine] = []
    if not opt_rappel:
        try:
            pan_rows = db.query(
                "SELECT * FROM TK_Call_Panier WHERE IDTK_Liste = ?",
                (id_ticket,),
            ) or []
        except Exception:
            logger.exception("_get_eni panier id=%s", id_ticket)
            pan_rows = []

        # Lookup libelles partenaires (base adv)
        prefixes = {_str(pr.get("Partenaire")).upper() for pr in pan_rows}
        prefixes = {p for p in prefixes if _PREFIX_RE.match(p)}
        parts_lookup: dict[str, str] = {}
        db_adv = get_connection("adv") if prefixes else None
        if db_adv and prefixes:
            try:
                quoted = "', '".join(prefixes)
                part_rows = db_adv.query(
                    f"SELECT PréfixeBDD, Lib_Partenaire FROM Partenaire "
                    f"WHERE PréfixeBDD IN ('{quoted}')"
                ) or []
                parts_lookup = {
                    _str(pr.get("PréfixeBDD")).upper():
                        _str(pr.get("Lib_Partenaire"))
                    for pr in part_rows
                }
            except Exception:
                logger.exception("_get_eni parts lookup")

        for pr in pan_rows:
            prefix = _str(pr.get("Partenaire")).upper()
            if prefix not in ALLOWED_PART_PREFIXES:
                continue
            id_prod = _int(pr.get("IDproduit"))
            lib_prod = ""
            if id_prod and db_adv:
                try:
                    prod_rows = db_adv.query(
                        f"SELECT Lib_produit FROM {prefix}_produit "
                        f"WHERE IDproduit = ?",
                        (id_prod,),
                    ) or []
                    if prod_rows:
                        lib_prod = _str(prod_rows[0].get("Lib_produit"))
                except Exception:
                    logger.exception("_get_eni prod %s id=%s", prefix, id_prod)

            panier.append(PanierLine(
                type=parts_lookup.get(prefix, prefix),
                nom=lib_prod,
                montant=None,  # ENI = colonne Montant cachee (Wine WinDev)
                id_panier=str(_int(pr.get("IDTK_Call_Panier"))),
            ))

    return PublicConsent(
        type_tk="ENI",
        id_ticket=str(id_ticket),
        info_client=info,
        code_valid=code_valid,
        deja_valide=opt_rappel,
        panier=panier,
    )


def _get_sfr(id_ticket: int) -> Optional[PublicConsent]:
    db = get_connection("ticket_bo")
    try:
        rows = db.query(
            "SELECT * FROM TK_CallSFR WHERE IDTK_Liste = ?",
            (id_ticket,),
        )
    except Exception:
        logger.exception("_get_sfr head id=%s", id_ticket)
        return None
    if not rows:
        return None
    r = rows[0]

    info = _bloc_info_client(r)
    code_valid = _str(r.get("CodeValid"))
    opt_rappel = bool(_int(r.get("Opt_Rappel")))

    panier: list[PanierLine] = []
    if not opt_rappel:
        try:
            pan_rows = db.query(
                "SELECT * FROM TK_CallSFR_Panier "
                "WHERE IDTK_Liste = ? AND ModifELEM <> 'suppr'",
                (id_ticket,),
            ) or []
        except Exception:
            logger.exception("_get_sfr panier id=%s", id_ticket)
            pan_rows = []

        # Prefetch offres SFR (base adv)
        offre_ids = [_int(pr.get("IDOffres_SFR")) for pr in pan_rows]
        offre_ids = [o for o in offre_ids if o]
        offre_lookup: dict[int, dict] = {}
        if offre_ids:
            db_adv = get_connection("adv")
            for oid in set(offre_ids):
                try:
                    orows = db_adv.query(
                        "SELECT Lib_Offre, PrixOffre FROM SFR_OffresProvad "
                        "WHERE IDOffres_SFR = ?",
                        (oid,),
                    ) or []
                    if orows:
                        offre_lookup[oid] = orows[0]
                except Exception:
                    logger.exception("_get_sfr offre id=%s", oid)

        for pr in pan_rows:
            oid = _int(pr.get("IDOffres_SFR"))
            offre = offre_lookup.get(oid, {})
            try:
                montant = float(offre.get("PrixOffre") or 0)
            except (TypeError, ValueError):
                montant = 0.0
            # HFSQL preserve la casse WinDev "Type" (T maj) - le WinDev
            # ecrivait .TYPE en case-insensitive. Fallback sur les 3
            # casses au cas ou.
            type_val = (pr.get("Type") or pr.get("TYPE")
                        or pr.get("type") or "")
            panier.append(PanierLine(
                type=_str(type_val),
                nom=_str(offre.get("Lib_Offre")),
                montant=montant,
                id_panier=str(_int(pr.get("IDTK_CallSFR_Panier"))),
            ))

    return PublicConsent(
        type_tk="SFR",
        id_ticket=str(id_ticket),
        info_client=info,
        code_valid=code_valid,
        deja_valide=opt_rappel,
        panier=panier,
    )


# ---------------------------------------------------------------------------
# Action (POST)
# ---------------------------------------------------------------------------


def validate_consent(p: str, opt_rappel: bool,
                      opt_oppose_partenaire: bool) -> dict:
    """UPDATE Opt_Rappel + Opt_Partenaire + ModifDate.

    Note WinDev inversee : Opt_Partenaire = 1 signifie "le client
    S'OPPOSE au partage partenaire" (`newPart = pas InterrupteurPart`).

    Retour : {ok, code_valid, deja_valide, error?}.
    """
    type_tk, id_ticket = _parse_p(p)
    if not id_ticket or type_tk not in ("ENI", "SFR"):
        return {"ok": False, "error": "bad_params"}

    table = "TK_Call" if type_tk == "ENI" else "TK_CallSFR"
    db = get_connection("ticket_bo")

    # ModifDate HFSQL au format compact WinDev (YYYYMMDDHHMMSS)
    now_compact = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        db.query(
            f"UPDATE {table} SET Opt_Rappel = ?, Opt_Partenaire = ?, "
            f"ModifDate = ? WHERE IDTK_Liste = ?",
            (1 if opt_rappel else 0,
             1 if opt_oppose_partenaire else 0,
             now_compact,
             id_ticket),
        )
    except Exception as e:
        logger.exception("validate_consent update tk=%s id=%s", table, id_ticket)
        return {"ok": False, "error": str(e)}

    # Recup CodeValid pour affichage plan 2
    try:
        rows = db.query(
            f"SELECT CodeValid FROM {table} WHERE IDTK_Liste = ?",
            (id_ticket,),
        ) or []
    except Exception:
        rows = []
    code_valid = _str((rows[0] if rows else {}).get("CodeValid"))

    return {"ok": True, "code_valid": code_valid, "deja_valide": bool(opt_rappel)}
