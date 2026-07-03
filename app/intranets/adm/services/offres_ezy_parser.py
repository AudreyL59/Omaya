"""Parser HTML pour Fen_OffresEZY onglet 'Import'.

Reproduit les 5 boutons d'import WinDev qui parsent le HTML brut des
pages Provad pour extraire les offres :
    - Import Offres SFR FIBRE       -> _parse_fibre_part
    - Import Offres SFR Mobile      -> _parse_mobile_part
    - Import Offres SFR Maison SECU -> _parse_secu
    - Import Offres SFR FIBRE Pro   -> _parse_fibre_pro
    - Import Offres SFR Mobile Pro  -> _parse_mobile_pro

Le parsing reproduit fidelement la logique ExtraitChaîne / DepuisFin
WinDev. On evite BeautifulSoup pour rester proche des marqueurs
Provad specifiques (class 'offer-label', 'whole-part', 'price-tpe',
'data-v-5798e1a9' etc.) et pour ne pas ajouter de dependance.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import TypedDict


class OffreParsed(TypedDict):
    type: str
    lib_offre: str
    debit_down: str
    debit_up: str
    prix_offre: float
    recurrence: str
    prix_pro_ttc: str
    engagement: str
    en_promo: bool
    info_promo: str
    services_inclus: str


# ---------------------------------------------------------------------
# Helpers reproduisant WinDev
# ---------------------------------------------------------------------

def _extrait(text: str, occ: int, sep: str, depuis_fin: bool = False) -> str:
    """Reproduit ExtraitChaine WinDev :
      - occ commence a 1 (occ=1 = 1er element apres split)
      - si depuis_fin : occ=1 = dernier element apres split
      - retourne '' si occ hors bornes
    """
    if not text or not sep:
        return ""
    parts = text.split(sep)
    if depuis_fin:
        idx = len(parts) - occ
    else:
        idx = occ - 1
    if 0 <= idx < len(parts):
        return parts[idx]
    return ""


def _nb_occ(text: str, sub: str) -> int:
    """ChaineOccurrence."""
    if not text or not sub:
        return 0
    return text.count(sub)


def _decode(s: str) -> str:
    """UTF8VersChaine + HTMLVersTexte : la chaine vient deja en UTF-8
    (Python str) donc on decode juste les entites HTML."""
    return html_lib.unescape(s or "").strip()


def _val_prix(prix1: str, prix2: str) -> float:
    """Val(Prix1) + Val(Prix2)/100."""
    def _val(s: str) -> float:
        m = re.search(r"[-+]?\d+", s or "")
        return float(m.group(0)) if m else 0.0
    return _val(prix1) + _val(prix2) / 100.0


# ---------------------------------------------------------------------
# Parseurs specifiques
# ---------------------------------------------------------------------

def parse_html_import(html_content: str, source: str) -> list[OffreParsed]:
    src = (source or "").lower()
    if src == "fibre":       return _parse_fibre_part(html_content)
    if src == "mobile":      return _parse_mobile_part(html_content)
    if src == "secu":        return _parse_secu(html_content)
    if src == "fibre_pro":   return _parse_fibre_pro(html_content)
    if src == "mobile_pro":  return _parse_mobile_pro(html_content)
    return []


DIV_OFFRE = 'class="offer-label"'


def _iter_blocks(contenu: str):
    """Genere les blocs par decoupe sur DIV_OFFRE (cf boucle WinDev
    pour i=1 a nbOffres : BlockOffre = ExtraitChaine(Contenu, i+1, DivOffre))."""
    nb = _nb_occ(contenu, DIV_OFFRE)
    for i in range(1, nb + 1):
        yield _extrait(contenu, i + 1, DIV_OFFRE)


def _lib_from_head(block: str) -> str:
    """Extrait lib_offre = 1er segment avant </span>, puis dernier
    apres > (utilise dans tous les 5 imports)."""
    lib = _extrait(block, 1, "</span>")
    lib = _extrait(lib, 1, ">", depuis_fin=True)
    return _decode(lib)


def _parse_debit(block: str) -> tuple[str, str, str]:
    """Extrait debit_down + debit_up. Retourne (block_reduit, down, up)."""
    b = _extrait(block, 2, "fa-arrow-down")
    down = _extrait(b, 1, "</span>")
    up = _extrait(down, 1, ">", depuis_fin=True)
    down = _extrait(down, 1, "<i")
    down = _extrait(down, 1, ">", depuis_fin=True)
    return b, _decode(down), _decode(up)


def _parse_prix_part(block: str) -> tuple[str, float]:
    """Parse le prix format 'part' (whole-part / cents-part).
    Retourne (block_apres_cents, prix)."""
    b = _extrait(block, 2, "whole-part")
    prix1 = _extrait(b, 1, "<")
    prix1 = _extrait(prix1, 1, ">", depuis_fin=True)

    b = _extrait(b, 2, "cents-part")
    prix2 = _extrait(b, 1, "<")
    prix2 = _extrait(prix2, 1, ">", depuis_fin=True)
    prix2 = _decode(prix2)
    # Milieu(Prix2, 2, 2) = caracteres a partir de la position 2, longueur 2
    prix2 = prix2[1:3] if len(prix2) >= 3 else prix2

    return b, _val_prix(prix1, prix2)


def _parse_prix_part_mobile(block: str) -> tuple[str, float]:
    """Variante Mobile : cents-part -> 2e portion apres ',' puis 2 chars."""
    b = _extrait(block, 2, "whole-part")
    prix1 = _extrait(b, 1, "<")
    prix1 = _extrait(prix1, 1, ">", depuis_fin=True)

    b = _extrait(b, 2, "cents-part")
    prix2 = _extrait(b, 2, ",")   # 2e portion apres ','
    prix2 = (prix2 or "")[:2]     # 2 premiers chars
    return b, _val_prix(prix1, prix2)


def _parse_recurrent_info_engagement_promo(block: str) -> tuple[str, str, str, str, str]:
    """Parse recurrence + infoPromo + engagement + labelPromo.
    Retourne (block_apres_services_inclus, recurrent, info_promo,
    engagement, label_promo)."""
    b = _extrait(block, 2, "recurrent")
    recurrent = _extrait(b, 1, "<")
    recurrent = _extrait(recurrent, 1, ">", depuis_fin=True)

    info_promo = ""
    if "discount" in b:
        b = _extrait(b, 2, "discount")
        info_promo = _extrait(b, 1, "<")
        info_promo = _extrait(info_promo, 1, ">", depuis_fin=True)
        info_promo = _decode(info_promo)

    b = _extrait(b, 2, "offer-eng-and-disc")
    engagement = _extrait(b, 1, "</span>")
    engagement = _extrait(engagement, 1, ">", depuis_fin=True)

    label_promo = ""
    if "promo" in b:
        b = _extrait(b, 2, "promo")
        label_promo = _extrait(b, 1, "</span>")
        label_promo = _extrait(label_promo, 1, ">", depuis_fin=True)

    b = _extrait(b, 2, "Services inclus :")
    return b, _decode(recurrent), info_promo, _decode(engagement), label_promo


def _parse_services_inclus(block_reste: str, balise: str) -> str:
    """Parcourt les <span data-v-...><span data-v-...> pour recuperer
    la liste des services inclus (RC separateur)."""
    nb = _nb_occ(block_reste, balise)
    services = []
    for j in range(1, nb + 1):
        s = _extrait(block_reste, j + 1, balise)
        s = _extrait(s, 1, "</span>")
        services.append(_decode(s))
    return "\n".join(services)


# --- Import Offres SFR FIBRE (part) ----------------------------------

def _parse_fibre_part(contenu: str) -> list[OffreParsed]:
    out: list[OffreParsed] = []
    for block in _iter_blocks(contenu):
        lib = _lib_from_head(block)
        block2, down, up = _parse_debit(block)
        block3, prix = _parse_prix_part(block2)
        block4, recurrent, info_promo, engagement, label_promo = \
            _parse_recurrent_info_engagement_promo(block3)
        services = _parse_services_inclus(
            block4,
            '<span data-v-5798e1a9=""><span data-v-5798e1a9="">',
        )
        out.append({
            "type": "FIBRE",
            "lib_offre": lib,
            "debit_down": down,
            "debit_up": up,
            "prix_offre": prix,
            "recurrence": recurrent,
            "prix_pro_ttc": "",
            "engagement": engagement,
            "en_promo": "PROMO" in (label_promo or ""),
            "info_promo": info_promo,
            "services_inclus": services,
        })
    return out


# --- Import Offres SFR Mobile (part) ---------------------------------

def _parse_mobile_part(contenu: str) -> list[OffreParsed]:
    out: list[OffreParsed] = []
    for block in _iter_blocks(contenu):
        lib = _lib_from_head(block)
        # Pas de debit pour mobile
        block2, prix = _parse_prix_part_mobile(block)
        if prix <= 0:   # cf 'si Prix > 0 alors' WinDev
            continue
        _block3, recurrent, info_promo, engagement, label_promo = \
            _parse_recurrent_info_engagement_promo(block2)
        out.append({
            "type": "MOBILE",
            "lib_offre": lib,
            "debit_down": "",
            "debit_up": "",
            "prix_offre": prix,
            "recurrence": recurrent,
            "prix_pro_ttc": "",
            "engagement": engagement,
            "en_promo": "PROMO" in (label_promo or ""),
            "info_promo": info_promo,
            "services_inclus": "",
        })
    return out


# --- Import Offres SFR Maison SECU -----------------------------------

def _parse_secu(contenu: str) -> list[OffreParsed]:
    """Cf code WinDev bouton 'Import Offres SFR Maison SECU' : meme
    parsing que Mobile part mais famille=SECU pour le matching du
    produit associe (Type reste 'MOBILE' cf bug WinDev)."""
    out: list[OffreParsed] = []
    for block in _iter_blocks(contenu):
        lib = _lib_from_head(block)
        block2, prix = _parse_prix_part_mobile(block)
        if prix <= 0:
            continue
        _block3, recurrent, info_promo, engagement, label_promo = \
            _parse_recurrent_info_engagement_promo(block2)
        out.append({
            "type": "MOBILE",     # cf code WinDev
            "lib_offre": lib,
            "debit_down": "",
            "debit_up": "",
            "prix_offre": prix,
            "recurrence": recurrent,
            "prix_pro_ttc": "",
            "engagement": engagement,
            "en_promo": "PROMO" in (label_promo or ""),
            "info_promo": info_promo,
            "services_inclus": "",
        })
    return out


# --- Import Offres SFR FIBRE Pro -------------------------------------

def _parse_prix_pro(block: str) -> tuple[str, float, str, str]:
    """Format Pro : price-tpe > whole-part-tpe (x2) + monthly-part-tpe
    + tooltip-tpe (prix TTC). Retourne (block, prix, recurrent, prix_ttc)."""
    b = _extrait(block, 2, "price-tpe")

    chaine_prix = _extrait(b, 2, "whole-part-tpe")
    prix1 = _extrait(chaine_prix, 1, "<")
    prix1 = _extrait(prix1, 1, ">", depuis_fin=True)

    b_after = _extrait(b, 3, "whole-part-tpe")
    prix2 = _extrait(b_after, 1, "<")
    prix2 = _extrait(prix2, 1, ">", depuis_fin=True)
    prix2 = _decode(prix2)
    prix2 = prix2[1:3] if len(prix2) >= 3 else prix2
    prix = _val_prix(prix1, prix2)

    b_after = _extrait(b_after, 2, "monthly-part-tpe")
    recurrent = _extrait(b_after, 1, "<")
    recurrent = _extrait(recurrent, 1, ">", depuis_fin=True)
    recurrent = _decode(recurrent).replace("€\xa0", "").replace("€ ", "")

    b_after = _extrait(b_after, 2, "tooltip-tpe tooltip-tpe-top")
    prix_ttc = _extrait(b_after, 1, "<")
    prix_ttc = _extrait(prix_ttc, 1, ">", depuis_fin=True)
    prix_ttc = _decode(prix_ttc)

    return b_after, prix, recurrent, prix_ttc


def _parse_engagement_promo_pro(block: str) -> tuple[str, str, str]:
    """Idem Part mais retourne (block, engagement, label_promo)."""
    b = _extrait(block, 2, "offer-eng-and-disc")
    engagement = _extrait(b, 1, "</span>")
    engagement = _extrait(engagement, 1, ">", depuis_fin=True)

    label_promo = ""
    if "promo" in b:
        b = _extrait(b, 2, "promo")
        label_promo = _extrait(b, 1, "</span>")
        label_promo = _extrait(label_promo, 1, ">", depuis_fin=True)

    b = _extrait(b, 2, "Services inclus :")
    return b, _decode(engagement), label_promo


def _parse_fibre_pro(contenu: str) -> list[OffreParsed]:
    out: list[OffreParsed] = []
    for block in _iter_blocks(contenu):
        lib = _lib_from_head(block)
        block2, down, up = _parse_debit(block)

        info_promo = ""
        if "discountODR" in block2:
            # cf. WinDev l.22 : BlockOffre = ExtraitChaine(BlockOffre, 2,
            # 'discountODR') tronque le bloc pour que le parsing prix
            # demarre APRES le bloc promo (evite d'attraper un prix
            # 'price-tpe' inclus dans le bloc promo).
            block2 = _extrait(block2, 2, "discountODR")
            info_promo = _extrait(block2, 1, "<")
            info_promo = _extrait(info_promo, 1, ">", depuis_fin=True)
            info_promo = _decode(info_promo)

        block3, prix, recurrent, prix_ttc = _parse_prix_pro(block2)
        _block4, engagement, label_promo = _parse_engagement_promo_pro(block3)

        # Services inclus balise Pro (data-v-16479d00)
        block_services = _extrait(_block4, 1, "")   # noop
        services = _parse_services_inclus(
            _block4,
            '<span data-v-16479d00=""><span data-v-16479d00="">',
        )
        _ = block_services

        out.append({
            "type": "FIB PRO",
            "lib_offre": lib,
            "debit_down": down,
            "debit_up": up,
            "prix_offre": prix,
            "recurrence": recurrent,
            "prix_pro_ttc": prix_ttc,
            "engagement": engagement,
            "en_promo": "ODR" in (label_promo or ""),
            "info_promo": info_promo,
            "services_inclus": services,
        })
    return out


# --- Import Offres SFR Mobile Pro ------------------------------------

def _parse_mobile_pro(contenu: str) -> list[OffreParsed]:
    out: list[OffreParsed] = []
    for block in _iter_blocks(contenu):
        lib = _lib_from_head(block)

        info_promo = ""
        if "discountODR" in block:
            # cf. WinDev l.17 (Mobile Pro) : idem Fibre Pro, tronque
            # BlockOffre pour que le parsing prix demarre APRES la promo.
            block = _extrait(block, 2, "discountODR")
            info_promo = _extrait(block, 1, "<")
            info_promo = _extrait(info_promo, 1, ">", depuis_fin=True)
            info_promo = _decode(info_promo)

        block2, prix, recurrent, prix_ttc = _parse_prix_pro(block)
        if prix <= 0:
            continue
        block3, engagement, label_promo = _parse_engagement_promo_pro(block2)
        services = _parse_services_inclus(
            block3,
            '<span data-v-16479d00=""><span data-v-16479d00="">',
        )
        out.append({
            "type": "MOB PRO",
            "lib_offre": lib,
            "debit_down": "",
            "debit_up": "",
            "prix_offre": prix,
            "recurrence": recurrent,
            "prix_pro_ttc": prix_ttc,
            "engagement": engagement,
            "en_promo": "ODR" in (label_promo or ""),
            "info_promo": info_promo,
            "services_inclus": services,
        })
    return out
