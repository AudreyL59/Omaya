"""
Service Fen_FicheSalaires - Envoi fiches de salaire.

## Plan 1 : Decoupage PDF + matching vendeurs

1. list_societes_fdv() : combo Societe (id_type_orga=1 FDV Interne)
2. charger_pdf(pdf_bytes) : extrait les vendeurs des pages du PDF via
   pattern natif ##BULLETIN##<periode>##<num>##<NOM>##<PRENOM>##.
   Match automatique nom+prenom vs pgt_salarie.
3. rechercher_salaries(q) : recherche libre pour attribution manuelle
   des lignes rouges.

Le WinDev fait de l'OCR sur zone visuelle (1194,480,984,55) faute d'un
bon extracteur texte natif. Python + pypdf peuvent extraire le texte
brut : on cible le pattern ## qui est present en debut de chaque page
et 100% fiable.
"""

import base64
import logging
import re
import unicodedata
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.fiche_salaires import (
    ChargerPdfResult, SocieteFDV, VendeurRow,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return "-".join(x[:1].upper() + x[1:].lower() for x in p.split("-"))


def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _norm_search(s: str) -> str:
    """cf. WinDev ChaineFormate(ccSansAccent + ccMajuscule) : retire accents,
    puis majuscules + sans espaces multiples."""
    if not s:
        return ""
    # Retire caracteres mal encodes (les remplace par vide)
    s = s.replace("�", "")
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_s.upper()).strip()


# --------------------------------------------------------------------
# Combo Societes FDV Interne
# --------------------------------------------------------------------

def list_societes_fdv() -> list[SocieteFDV]:
    """Cf. WinDev Combo Societe : societes FDV Interne actives.

    id_type_orga = 1 (FDV Interne) - cf. project_intranets_list memoire
    et pattern ListeSocietePage (frontend adm/pages).
    """
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_ste, raison_sociale, rs_interne
                 FROM pgt_societe
                WHERE (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                  AND id_type_orga = 1
                  AND is_actif = TRUE
                ORDER BY rs_interne ASC NULLS LAST""",
        ) or []
    except Exception:
        return []
    return [
        SocieteFDV(
            id_ste=_clean_id(r.get("id_ste")),
            raison_sociale=(r.get("raison_sociale") or "").strip(),
            rs_interne=(r.get("rs_interne") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Charger PDF (extraction + matching)
# --------------------------------------------------------------------

# Pattern robuste : ##BULLETIN##(period)##(num)##(NOM)##(prenom)##
# Tolerant sur les caracteres non-'#' (accents, espaces, tirets).
_BULLETIN_RE = re.compile(
    r'##BULLETIN##(\d{2}-\d{4})##(\d+)##([^#]+?)##([^#]+?)##'
)


def _find_salarie_by_name(
    nom_norm: str, prenom_norm: str,
) -> Optional[dict]:
    """Recherche un salarie actif par nom+prenom (insensible casse/accent).

    Retour : {id_salarie, nom, prenom, mail, gsm} ou None.
    """
    rh = get_pg_connection("rh")
    # Utilise UPPER + unaccent equivalent : on normalise cote SQL avec
    # TRANSLATE (pattern classique PG sans extension unaccent).
    try:
        rows = rh.query(
            """SELECT s.id_salarie, s.nom, s.prenom, s.login AS mail,
                      c.tel_mob AS gsm
                 FROM pgt_salarie s
                 LEFT JOIN pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                 JOIN pgt_salarie_embauche e
                      ON e.id_salarie = s.id_salarie
                     AND (e.modif_elem IS NULL
                          OR e.modif_elem NOT LIKE '%suppr%')
                     AND e.en_activite = TRUE
                WHERE UPPER(s.nom) = ?
                  AND UPPER(s.prenom) = ?
                LIMIT 2""",
            (nom_norm, prenom_norm),
        ) or []
    except Exception:
        return None
    # Ambiguite -> pas d'attribution auto (cf. WinDev HNbEnr=1)
    if len(rows) != 1:
        return None
    r = rows[0]
    return {
        "id_salarie": _clean_id(r.get("id_salarie")),
        "nom": (r.get("nom") or "").strip(),
        "prenom": (r.get("prenom") or "").strip(),
        "mail": (r.get("mail") or "").strip(),
        "gsm": (r.get("gsm") or "").strip(),
    }


def charger_pdf(pdf_bytes: bytes) -> ChargerPdfResult:
    """Cf. WinDev Btn Charger le fichier PDF.

    1. Ouvre PDF.
    2. Pour chaque page : extrait le pattern ##BULLETIN##...##NOM##PRENOM##
    3. Groupe par (nom, prenom) : Nb_Page += 1 pour multi-pages du meme
       vendeur.
    4. Match automatique vs pgt_salarie : 1 resultat = vert, sinon rouge.
    """
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError:
        return ChargerPdfResult(
            ok=False, message="pypdf non installe cote serveur",
        )

    import io as _io
    try:
        reader = PdfReader(_io.BytesIO(pdf_bytes))
    except Exception as e:
        return ChargerPdfResult(
            ok=False, message=f"PDF invalide : {e}",
        )

    nb_pages = len(reader.pages)
    if not nb_pages:
        return ChargerPdfResult(
            ok=True, nb_pages=0, vendeurs=[],
            message="PDF vide",
        )

    # Extraction pattern
    vendeurs_by_key: dict[str, VendeurRow] = {}
    order: list[str] = []

    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        m = _BULLETIN_RE.search(txt)
        if not m:
            # Page sans pattern : on cree une ligne 'inconnu'
            key = f"__unknown_{i+1}"
            vendeurs_by_key[key] = VendeurRow(
                id_salarie="0",
                vendeur=f"Page {i+1} inconnue",
                num_page=i + 1, nb_page=1,
                couleur="rouge",
            )
            order.append(key)
            continue
        nom = m.group(3).strip()
        prenom = m.group(4).strip()
        # cf. WinDev : sans espace multiple + sans accent + majuscule
        vendeur_lib = f"{_norm_search(prenom)} {_norm_search(nom)}"
        # Clef de regroupement : nom_norm|prenom_norm
        key = f"{_norm_search(nom)}|{_norm_search(prenom)}"
        if key in vendeurs_by_key:
            vendeurs_by_key[key].nb_page += 1
        else:
            row = VendeurRow(
                id_salarie="0",
                vendeur=vendeur_lib,
                num_page=i + 1,
                nb_page=1,
                couleur="rouge",
            )
            # Lookup salarie
            info = _find_salarie_by_name(
                _norm_search(nom), _norm_search(prenom),
            )
            if info:
                row.id_salarie = info["id_salarie"]
                row.nom_prenom = f"{info['nom']} {_cap_prenom(info['prenom'])}"
                row.mail = info["mail"]
                row.gsm = info["gsm"]
                row.couleur = "vert"
            vendeurs_by_key[key] = row
            order.append(key)

    vendeurs = [vendeurs_by_key[k] for k in order]

    return ChargerPdfResult(
        ok=True,
        pdf_b64=base64.b64encode(pdf_bytes).decode("ascii"),
        nb_pages=nb_pages,
        vendeurs=vendeurs,
        message=(
            f"{len(vendeurs)} vendeur(s) identifie(s) - "
            f"{sum(1 for v in vendeurs if v.id_salarie == '0')} en rouge"
        ),
    )


# --------------------------------------------------------------------
# Recherche manuelle (ligne rouge)
# --------------------------------------------------------------------

def rechercher_salaries(q: str) -> list[dict]:
    """Recherche libre nom/prenom pour attribution manuelle (cf. WinDev
    Fen_RechercheNomSalarie).
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT s.id_salarie, s.nom, s.prenom, s.login AS mail
                 FROM pgt_salarie s
                 JOIN pgt_salarie_embauche e
                      ON e.id_salarie = s.id_salarie
                     AND (e.modif_elem IS NULL
                          OR e.modif_elem NOT LIKE '%suppr%')
                     AND e.en_activite = TRUE
                WHERE UPPER(s.nom) LIKE UPPER(?)
                   OR UPPER(s.prenom) LIKE UPPER(?)
                   OR UPPER(s.nom || ' ' || s.prenom) LIKE UPPER(?)
                ORDER BY s.nom, s.prenom
                LIMIT 20""",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ) or []
    except Exception:
        return []
    return [
        {
            "id_salarie": _clean_id(r.get("id_salarie")),
            "nom": (r.get("nom") or "").strip(),
            "prenom": _cap_prenom((r.get("prenom") or "").strip()),
            "mail": (r.get("mail") or "").strip(),
        }
        for r in rows
    ]
