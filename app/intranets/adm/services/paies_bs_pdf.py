"""
Generation du PDF EtatBaseSalaire (Fen_PaiesBS - GenerationBase).

Cf. WinDev :
  procedure GenerationBase()
    // Peuple BaseContrat
    // iImprimeEtat(EtatBaseSalaire, VendeurNom, IdSte, MoisFmt,
    //              nbCtt, testEni, testSFR)
    // Upload FTP gestionRH/{id_sal}/Fiches_Salaires/{name}.pdf
    // Ouvre Fen_ApercuFichier

L'etat WinDev EtatBaseSalaire :
  - Logo societe (guimmick) en haut a gauche
  - Titre 'Base Contrat <vendeur>' au centre
  - Date impression 'JJ/MM/AAAA' a droite
  - Entete page 'Salaire de <mois>'
  - Colonnes : Signe le | Num BS | NomProduit | Etat | MoisPaiement
    | CAR (si ENI) | Date Racc/Activ (si SFR) | Type Vente (si SFR)
    | Portabilite | Prise saisie | Note
  - Pied de page : 'Nombre de lignes : XXX'
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import date, datetime
from html import escape
from typing import Any, Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.paies_bs import (
    GenerationBaseParams, GenerationBaseResult, GenerationBaseRow,
)

logger = logging.getLogger(__name__)


_MOIS_FR = [
    "", "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre",
]


def _mois_label(mois_iso: str) -> str:
    """'2026-06' -> 'Juin 2026'."""
    if len(mois_iso) != 7:
        return mois_iso
    y = mois_iso[:4]
    m = int(mois_iso[5:7])
    return f"{_MOIS_FR[m] if 1 <= m <= 12 else ''} {y}"


def _fr_date(iso: str) -> str:
    """'YYYY-MM-DD' -> 'DD/MM/YYYY'."""
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def _sanitize_name(s: str) -> str:
    """Nom de fichier safe : sans espace/accent, alphanum + _ + -."""
    import unicodedata
    if not s:
        return "vendeur"
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_s = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_s).strip("_")
    return ascii_s or "vendeur"


def _bytes_or_none(v: Any) -> Optional[bytes]:
    if v is None:
        return None
    if isinstance(v, memoryview):
        return v.tobytes()
    if isinstance(v, bytes):
        return v
    if isinstance(v, str):
        try:
            return base64.b64decode(v)
        except Exception:
            return None
    return None


def _logo_b64(blob: Any) -> str:
    b = _bytes_or_none(blob)
    if not b:
        return ""
    try:
        return base64.b64encode(b).decode("ascii")
    except Exception:
        return ""


def _load_vendeur_and_societe(id_salarie: int) -> dict:
    """Charge nom vendeur + id_ste + logo societe (guimmick)."""
    rh = get_pg_connection("rh")
    sal = rh.query_one(
        "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
        (int(id_salarie),),
    ) or {}
    emb = rh.query_one(
        """SELECT id_ste FROM pgt_salarie_embauche
            WHERE id_salarie = ?
              AND (modif_elem IS NULL
                   OR modif_elem NOT LIKE '%suppr%')
            ORDER BY date_debut DESC NULLS LAST
            LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    id_ste = int(emb.get("id_ste") or 0)
    ste = {}
    logo_b64 = ""
    if id_ste:
        ste = rh.query_one(
            "SELECT raison_sociale, guimmick FROM pgt_societe "
            "WHERE id_ste = ?",
            (id_ste,),
        ) or {}
        logo_b64 = _logo_b64(ste.get("guimmick"))
    prenom = (sal.get("prenom") or "").strip()
    prenom_cap = "-".join(
        x[:1].upper() + x[1:].lower() for x in prenom.split("-")
    )
    return {
        "vendeur_nom": (
            f"{(sal.get('nom') or '').strip()} {prenom_cap}"
        ).strip(),
        "id_ste": id_ste,
        "raison_sociale": (ste.get("raison_sociale") or "").strip(),
        "logo_b64": logo_b64,
    }


def _render_html(
    p: GenerationBaseParams, info: dict, date_impression: str,
) -> str:
    """Cf. WinDev EtatBaseSalaire template."""
    logo_html = (
        f'<img src="data:image/png;base64,{info["logo_b64"]}" '
        f'style="max-height:60px;max-width:120px;">'
        if info.get("logo_b64") else ""
    )
    titre = f"Base Contrat {info.get('vendeur_nom') or ''}"
    mois_lib = _mois_label(p.mois_paiement)

    # Entete tableau : colonnes conditionnelles CAR / DateRacc / TypeVente
    entete = ["Signé le", "Num BS", "Nom Produit", "État", "Mois Paiement"]
    if p.has_eni:
        entete.append("CAR")
    if p.has_sfr:
        entete.append("Date Racc/Activ")
        entete.append("Type Vente")
    entete.extend(["Portabilité", "Prise saisie", "Note", "NB Pts"])

    # Lignes
    rows: list[str] = []
    for c in p.contrats:
        cells = [
            _fr_date(c.signe_le),
            escape(c.num_bs or "-"),
            escape(c.nom_produit or "-"),
            escape(c.etat or "-"),
            _fr_date(c.mois_paiement),
        ]
        if p.has_eni:
            cells.append(escape(str(c.car or "")))
        if p.has_sfr:
            cells.append(_fr_date(c.date_racc_activ))
            cells.append(escape(c.type_vente or ""))
        cells.extend([
            "Oui" if c.portabilite else "",
            "Oui" if c.prise_saisie else "",
            f"{c.note:.1f}".replace(".", ",") if c.note else "",
            f"{c.nb_pts:.2f}".replace(".", ",") if c.nb_pts else "0,00",
        ])
        rows.append(
            "<tr>"
            + "".join(f"<td>{v}</td>" for v in cells)
            + "</tr>"
        )

    # Si aucune ligne : placeholder (cf. WinDev '-')
    if not rows:
        placeholder_cells = ["-"] * len(entete)
        placeholder_cells[-1] = "0"
        rows.append(
            "<tr>"
            + "".join(f"<td>{v}</td>" for v in placeholder_cells)
            + "</tr>"
        )

    n_lignes = len(p.contrats)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{escape(titre)}</title>
<style>
@page {{
  size: A4 landscape;
  margin: 12mm 10mm 15mm 10mm;
  @bottom-right {{
    content: counter(page) "/" counter(pages);
    font-size: 8pt; color: #888;
  }}
}}
body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 9pt; color: #222; }}
header {{
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 2px solid #17494E; padding-bottom: 6px; margin-bottom: 8px;
}}
header .logo {{ min-width: 120px; }}
header h1 {{ font-size: 16pt; color: #17494E; text-align: center; margin: 0; }}
header .date {{ min-width: 120px; text-align: right; font-size: 9pt; }}
.titre-page {{ font-size: 12pt; font-weight: bold; color: #4E1D17; margin: 6px 0; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
thead th {{
  background: #17494E; color: white; padding: 4px 6px; font-size: 8pt;
  text-align: left; text-transform: uppercase; letter-spacing: 0.02em;
}}
tbody td {{
  padding: 3px 6px; border-bottom: 1px solid #E5DDDC;
  font-size: 8pt; vertical-align: top;
}}
tbody tr:nth-child(even) td {{ background: #F5F5F0; }}
footer {{
  margin-top: 10px; font-size: 8pt; color: #444;
  border-top: 1px solid #E5DDDC; padding-top: 4px;
}}
</style>
</head>
<body>
<header>
  <div class="logo">{logo_html}</div>
  <h1>{escape(titre)}</h1>
  <div class="date">{escape(date_impression)}</div>
</header>
<div class="titre-page">Salaire de {escape(mois_lib)}</div>
<table>
  <thead>
    <tr>{''.join(f'<th>{escape(x)}</th>' for x in entete)}</tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
<footer>Nombre de lignes : {n_lignes}</footer>
</body>
</html>
"""


def generer_base_pdf(
    p: GenerationBaseParams, op_id: int,
) -> GenerationBaseResult:
    """Genere le PDF EtatBaseSalaire + upload FTP + retourne URL.

    Cf. WinDev GenerationBase() :
    1. Peuple BaseContrat (deja fait cote input p.contrats)
    2. iImprimeEtat(EtatBaseSalaire, ...) -> PDF
    3. Upload FTP gestionRH/{id_sal}/Fiches_Salaires/
    4. Retour URL pour Fen_ApercuFichier
    """
    if not p.id_salarie:
        return GenerationBaseResult(ok=False, message="Salarie manquant")
    if len(p.mois_paiement) != 7:
        return GenerationBaseResult(
            ok=False, message="Format mois_paiement invalide (YYYY-MM)",
        )

    info = _load_vendeur_and_societe(p.id_salarie)
    if not info["vendeur_nom"]:
        return GenerationBaseResult(
            ok=False, message="Salarie introuvable",
        )

    # Nom fichier : {vendeur}_{mois}_base.pdf (cf. WinDev)
    fic_name = (
        f"{_sanitize_name(info['vendeur_nom'])}"
        f"_{p.mois_paiement}_base.pdf"
    )
    date_impression = datetime.now().strftime("%d/%m/%Y")
    html = _render_html(p, info, date_impression)

    # Genere le PDF (lazy import WeasyPrint : lib optionnelle)
    try:
        from weasyprint import HTML  # noqa: PLC0415
        pdf_bytes = HTML(string=html).write_pdf()
    except Exception as e:
        logger.exception("WeasyPrint KO")
        return GenerationBaseResult(
            ok=False,
            message=f"Erreur generation PDF : {e}. "
                    "WeasyPrint installe ? Cf. reference_weasyprint_windows_gtk.",
        )

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # Upload FTP (cf. WinDev EnvoiFichier gestionRH/{id_sal}/Fiches_Salaires/)
    ftp_uploaded = False
    url = ""
    try:
        from app.core.config import FTP_GESTION_RH_PATH
        from app.shared.tickets.forms.cttw_pdf import ftp_upload

        ftp_upload(
            f"{FTP_GESTION_RH_PATH.rstrip('/')}/{p.id_salarie}/Fiches_Salaires",
            fic_name, pdf_bytes,
        )
        ftp_uploaded = True
        # URL publique : gestionRH/{id_sal}/Fiches_Salaires/{fic}
        # (cf. WinDev lienDoc + 'gestionRH/...')
        url = (
            f"/gestionRH/{p.id_salarie}/Fiches_Salaires/{fic_name}"
        )
    except Exception as e:
        logger.exception("Upload FTP KO")
        # Best-effort : on retourne le PDF meme si FTP down
        return GenerationBaseResult(
            ok=True,
            fic_name=fic_name,
            pdf_b64=pdf_b64,
            ftp_uploaded=False,
            message=f"PDF genere mais upload FTP KO : {e}",
        )

    return GenerationBaseResult(
        ok=True,
        fic_name=fic_name,
        pdf_b64=pdf_b64,
        ftp_uploaded=ftp_uploaded,
        url=url,
        message="PDF genere et uploade sur FTP",
    )
