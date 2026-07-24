"""Page externe de consentement client (page de fin d'appel Call).

Portage WinDev Page_ConsentClient. Le vendeur genere un lien vers
cette page pour le client, qui valide le panier + accepte/refuse
d'etre rappele par le service qualite.

URL WinDev : ...?P1=<TypeTK><IdTicket>
             ex. P1=SFR20220315123456789  ou  P1=ENI...
Portage FastAPI : le meme code est passe dans le query param `p`.

Securite : l'id_ticket est un timestamp 8 octets (impossible a deviner
par bruteforce). Pas de signature HMAC ajoutee (identique a ConfRdvPage).

Branchement PG (bascule effectuee - cf. envoi_lien_client_call /
sfr_envoi_lien_client qui ecrivent deja code_valid en PG).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)


# Whitelist des prefixes partenaires (evite l'injection SQL sur
# le nom de table dynamique pgt_<prefix>_produit). Basee sur les
# tables existantes en base adv.
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
    deja_valide: bool = False      # opt_rappel = TRUE -> plan 2 direct
    panier: list[PanierLine] = []


class ValidatePayload(BaseModel):
    opt_rappel: bool                    # True = J'accepte d'etre rappele
    opt_oppose_partenaire: bool = True  # True = Je m'oppose au partage partenaire
                                        # (semantique WinDev inversee : opt_partenaire=TRUE = opposition)


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
    nom = _str(row.get("nom_client"))
    nom_marital = _str(row.get("nom_marital_client"))
    prenom = _capitalize(_str(row.get("prenom_client")))
    adr1 = _str(row.get("adresse1"))
    adr2 = _str(row.get("adresse2"))
    cp = _str(row.get("cp"))
    ville = _str(row.get("ville"))
    mobile = _str(row.get("mobile1"))
    mail = _str(row.get("adr_mail"))

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
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT nom_client, nom_marital_client, prenom_client,
                      adresse1, adresse2, cp, ville, mobile1, adr_mail,
                      code_valid, opt_rappel
                 FROM ticket_bo.pgt_tk_call
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_ticket,),
        )
    except Exception:
        logger.exception("_get_eni head id=%s", id_ticket)
        return None
    if not row:
        return None

    info = _bloc_info_client(row)
    code_valid = _str(row.get("code_valid"))
    opt_rappel = bool(row.get("opt_rappel"))

    panier: list[PanierLine] = []
    if not opt_rappel:
        try:
            pan_rows = db.query(
                """SELECT id_tk_call_panier, partenaire, id_produit
                     FROM ticket_bo.pgt_tk_call_panier
                    WHERE id_tk_liste = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (id_ticket,),
            ) or []
        except Exception:
            logger.exception("_get_eni panier id=%s", id_ticket)
            pan_rows = []

        # Lookup libelles partenaires (base adv)
        prefixes = {_str(pr.get("partenaire")).upper() for pr in pan_rows}
        prefixes = {p for p in prefixes if _PREFIX_RE.match(p)}
        parts_lookup: dict[str, str] = {}
        db_adv = get_pg_connection("adv") if prefixes else None
        if db_adv and prefixes:
            try:
                placeholders = ",".join("?" for _ in prefixes)
                part_rows = db_adv.query(
                    f"""SELECT prefixe_bdd, lib_partenaire
                         FROM adv.pgt_partenaire
                        WHERE UPPER(prefixe_bdd) IN ({placeholders})""",
                    tuple(prefixes),
                ) or []
                parts_lookup = {
                    _str(pr.get("prefixe_bdd")).upper():
                        _str(pr.get("lib_partenaire"))
                    for pr in part_rows
                }
            except Exception:
                logger.exception("_get_eni parts lookup")

        for pr in pan_rows:
            prefix = _str(pr.get("partenaire")).upper()
            if prefix not in ALLOWED_PART_PREFIXES:
                continue
            id_prod = _int(pr.get("id_produit"))
            lib_prod = ""
            if id_prod and db_adv:
                try:
                    prod_row = db_adv.query_one(
                        f"""SELECT lib_produit
                             FROM adv.pgt_{prefix.lower()}_produit
                            WHERE id_produit = ? LIMIT 1""",
                        (id_prod,),
                    )
                    if prod_row:
                        lib_prod = _str(prod_row.get("lib_produit"))
                except Exception:
                    logger.exception("_get_eni prod %s id=%s", prefix, id_prod)

            panier.append(PanierLine(
                type=parts_lookup.get(prefix, prefix),
                nom=lib_prod,
                montant=None,  # ENI = colonne Montant cachee (WinDev)
                id_panier=str(_int(pr.get("id_tk_call_panier"))),
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
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT nom_client, nom_marital_client, prenom_client,
                      adresse1, adresse2, cp, ville, mobile1, adr_mail,
                      code_valid, opt_rappel
                 FROM ticket_bo.pgt_tk_call_sfr
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_ticket,),
        )
    except Exception:
        logger.exception("_get_sfr head id=%s", id_ticket)
        return None
    if not row:
        return None

    info = _bloc_info_client(row)
    code_valid = _str(row.get("code_valid"))
    opt_rappel = bool(row.get("opt_rappel"))

    panier: list[PanierLine] = []
    if not opt_rappel:
        try:
            pan_rows = db.query(
                """SELECT id_tk_call_sfr_panier, id_offres_sfr, type
                     FROM ticket_bo.pgt_tk_call_sfr_panier
                    WHERE id_tk_liste = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (id_ticket,),
            ) or []
        except Exception:
            logger.exception("_get_sfr panier id=%s", id_ticket)
            pan_rows = []

        # Prefetch offres SFR (base adv)
        offre_ids = {_int(pr.get("id_offres_sfr")) for pr in pan_rows}
        offre_ids = {o for o in offre_ids if o}
        offre_lookup: dict[int, dict] = {}
        if offre_ids:
            db_adv = get_pg_connection("adv")
            try:
                placeholders = ",".join("?" for _ in offre_ids)
                orows = db_adv.query(
                    f"""SELECT id_offres_sfr, lib_offre, prix_offre
                         FROM adv.pgt_sfr_offres_provad
                        WHERE id_offres_sfr IN ({placeholders})""",
                    tuple(offre_ids),
                ) or []
                offre_lookup = {
                    int(o.get("id_offres_sfr") or 0): o for o in orows
                }
            except Exception:
                logger.exception("_get_sfr offres")

        for pr in pan_rows:
            oid = _int(pr.get("id_offres_sfr"))
            offre = offre_lookup.get(oid, {})
            try:
                montant = float(offre.get("prix_offre") or 0)
            except (TypeError, ValueError):
                montant = 0.0
            panier.append(PanierLine(
                type=_str(pr.get("type")),
                nom=_str(offre.get("lib_offre")),
                montant=montant,
                id_panier=str(_int(pr.get("id_tk_call_sfr_panier"))),
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
    """UPDATE opt_rappel + opt_partenaire + modif_date.

    Note WinDev inversee : opt_partenaire = TRUE signifie "le client
    S'OPPOSE au partage partenaire" (`newPart = pas InterrupteurPart`).

    Retour : {ok, code_valid, deja_valide, error?}.
    """
    type_tk, id_ticket = _parse_p(p)
    if not id_ticket or type_tk not in ("ENI", "SFR"):
        return {"ok": False, "error": "bad_params"}

    table = ("ticket_bo.pgt_tk_call" if type_tk == "ENI"
             else "ticket_bo.pgt_tk_call_sfr")
    db = get_pg_connection("ticket_bo")
    now = datetime.now()

    try:
        db.query(
            f"""UPDATE {table}
                   SET opt_rappel = ?, opt_partenaire = ?,
                       modif_date = ?
                 WHERE id_tk_liste = ?""",
            (bool(opt_rappel),
             bool(opt_oppose_partenaire),
             now,
             id_ticket),
        )
    except Exception as e:
        logger.exception("validate_consent update tk=%s id=%s",
                          table, id_ticket)
        return {"ok": False, "error": str(e)}

    # Recup code_valid pour affichage plan 2
    try:
        row = db.query_one(
            f"SELECT code_valid FROM {table} WHERE id_tk_liste = ? LIMIT 1",
            (id_ticket,),
        )
    except Exception:
        row = None
    code_valid = _str((row or {}).get("code_valid"))

    return {"ok": True, "code_valid": code_valid, "deja_valide": bool(opt_rappel)}
