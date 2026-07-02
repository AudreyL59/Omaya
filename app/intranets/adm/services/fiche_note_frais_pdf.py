"""
Impression PDF des notes de frais (transposition Btn impression WinDev).

EtatNoteFrais (1 PDF pour la periode) :
  - Header : logo societe + 'Note de frais' + date impression
  - Information du salarie : Nom Prenom / Responsable / Mois Paiement /
    Poste / Periode Frais
  - Tableau : Date | Description | Hebergement | Reception | Carburant |
    Deplacement | Telephone | Divers | TVA | TTC
  - Couleur du bandeau selon societe (cf. WinDev selon id_ste)
  - 12 lignes minimum (vides si moins de donnees)

EtatPhotoTicket :
  - Grille des photos justificatifs (max 6 par page)

Fusion : un seul PDF avec EtatNoteFrais en premier puis les photos.
"""

from __future__ import annotations

import base64
import io
import sys
import traceback
from datetime import date, datetime
from html import escape
from typing import Any

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel


_MOIS_FR = [
    "", "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre",
]


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _iso(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _fmt_fr_date(iso_s: str) -> str:
    if not iso_s or len(iso_s) < 10:
        return ""
    return f"{iso_s[8:10]}/{iso_s[5:7]}/{iso_s[0:4]}"


def _fmt_eur(n: float) -> str:
    return f"{n:.2f} €".replace(".", ",")


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def _color_societe(id_ste: int) -> tuple[str, str]:
    """Bandeau (fond, texte) WinDev selon la societe."""
    if id_ste == 2:
        return ("#FF6F00", "#000000")  # OrangeFonce
    if id_ste == 8:
        return ("#D07A00", "#000000")
    if id_ste in (9, 12):
        return ("#45A8E6", "#000000")  # Odyssee
    if id_ste == 10:
        return ("#2A2A2A", "#FFFFFF")
    if id_ste == 303:
        return ("#53DC29", "#000000")
    return ("#AAAAAA", "#000000")


def _bytes_or_none(v: Any) -> bytes | None:
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    if isinstance(v, memoryview):
        return v.tobytes()
    return None


# --- Donnees -------------------------------------------------------------

def _load_salarie_info(id_salarie: int) -> dict:
    db = get_pg_connection("rh")
    sal = db.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
        (int(id_salarie),),
    ) or {}
    emb = db.query_one(
        """SELECT id_ste, id_type_poste FROM rh.pgt_salarie_embauche
           WHERE id_salarie = ?""",
        (int(id_salarie),),
    ) or {}
    poste = ""
    if emb.get("id_type_poste"):
        r = db.query_one(
            "SELECT lib_poste FROM rh.pgt_type_poste WHERE id_type_poste = ?",
            (int(emb.get("id_type_poste")),),
        )
        if r:
            poste = _str(r.get("lib_poste"))
    societe = {}
    if emb.get("id_ste"):
        r = db.query_one(
            "SELECT id_ste, raison_sociale, guimmick FROM rh.pgt_societe "
            "WHERE id_ste = ?",
            (int(emb.get("id_ste")),),
        )
        if r:
            societe = r
    # Organigramme courant -> responsable
    orga = db.query_one(
        """SELECT o.idorganigramme
           FROM rh.pgt_salarie_organigramme so
           LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
           WHERE so.id_salarie = ?
             AND so.modif_elem NOT LIKE '%suppr%'
             AND COALESCE(so.aff_actif, FALSE) = TRUE
           ORDER BY so.date_debut DESC NULLS LAST
           LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    id_da = 0
    nom_da = ""
    if orga.get("idorganigramme"):
        da_row = db.query_one(
            """SELECT se.id_salarie, s.nom, s.prenom
               FROM rh.pgt_salarie_organigramme so
               LEFT JOIN rh.pgt_organigramme o
                 ON o.idorganigramme = so.idorganigramme
               LEFT JOIN rh.pgt_salarie_embauche se
                 ON se.id_salarie = so.id_salarie
               LEFT JOIN rh.pgt_salarie s
                 ON s.id_salarie = so.id_salarie
               WHERE (so.idorganigramme = ?
                      OR so.idorganigramme = (
                          SELECT id_parent FROM rh.pgt_organigramme
                          WHERE idorganigramme = ?))
                 AND COALESCE(so.aff_actif, FALSE) = TRUE
                 AND so.modif_elem NOT LIKE '%suppr%'
                 AND COALESCE(se.resp_equipe, FALSE) = TRUE
                 AND so.id_salarie <> ?
               ORDER BY so.date_debut DESC NULLS LAST
               LIMIT 1""",
            (
                int(orga.get("idorganigramme")),
                int(orga.get("idorganigramme")),
                int(id_salarie),
            ),
        )
        if da_row:
            id_da = _int(da_row.get("id_salarie"))
            nom_da = (
                f"{_capitalize(_str(da_row.get('prenom')))} "
                f"{_str(da_row.get('nom'))}"
            ).strip()

    return {
        "nom": _str(sal.get("nom")),
        "prenom": _str(sal.get("prenom")),
        "poste": poste,
        "id_ste": _int(emb.get("id_ste")),
        "raison_sociale": _str(societe.get("raison_sociale")),
        "logo_b64": _logo_b64(societe.get("guimmick")),
        "id_da": id_da,
        "nom_da": nom_da,
    }


def _logo_b64(blob_val: Any) -> str:
    blob = _bytes_or_none(blob_val)
    if not blob:
        return ""
    try:
        return base64.b64encode(blob).decode("ascii")
    except Exception:
        return ""


def _load_notes_with_photo(id_salarie: int, mois: int, annee: int) -> list[dict]:
    """Charge les notes + bytes photo bruts (pour la grille justificatifs)."""
    try:
        periode = date(int(annee), int(mois), 1)
    except (ValueError, TypeError):
        return []
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT nf.id_note_frais, nf.date, nf.description,
                  nf.montant_ht, nf.montant_tva, nf.montant_ttc,
                  nf.photo_ticket,
                  t.lib_type_note_frais
           FROM rh.pgt_note_frais nf
           LEFT JOIN rh.pgt_note_frais_type t
             ON t.id_note_frais_type = nf.id_note_frais_type
           WHERE nf.id_salarie = ?
             AND nf.periode_note = ?
             AND nf.modif_elem NOT LIKE '%suppr%'
           ORDER BY nf.date ASC NULLS LAST""",
        (int(id_salarie), periode),
    )
    return [
        {
            "id_note_frais": _int(r.get("id_note_frais")),
            "date_iso": _iso(r.get("date")),
            "description": _str(r.get("description")),
            "ht": _float(r.get("montant_ht")),
            "tva": _float(r.get("montant_tva")),
            "ttc": _float(r.get("montant_ttc")),
            "lib_type": _str(r.get("lib_type_note_frais")),
            "photo": _bytes_or_none(r.get("photo_ticket")),
        }
        for r in rows
    ]


# --- Rendu HTML ----------------------------------------------------------

_CATEGORIES = [
    ("hebergement", "Hébergement"),
    ("reception", "Réception"),
    ("carburant", "Carburant"),
    ("deplacement", "Déplacement"),
    ("telephone", "Téléphone"),
    ("divers", "Divers"),
]

# Mapping libelle WinDev -> colonne
_LIB_TO_COL = {
    "hebergement": "hebergement",
    "hébergement": "hebergement",
    "reception": "reception",
    "réception": "reception",
    "carburant": "carburant",
    "deplacement": "deplacement",
    "déplacement": "deplacement",
    "telephone": "telephone",
    "téléphone": "telephone",
}


def _ventile_ht(lib_type: str) -> str:
    return _LIB_TO_COL.get(lib_type.lower().strip(), "divers")


def _render_note_frais_html(
    salarie: dict, notes: list[dict], mois: int, annee: int
) -> str:
    bg_color, text_color = _color_societe(salarie["id_ste"])
    today = datetime.now().strftime("%d/%m/%Y")
    mois_lib = _MOIS_FR[mois] if 1 <= mois <= 12 else str(mois)
    periode_lib = f"{mois_lib} {annee}"
    nom_prenom = (
        f"{_capitalize(salarie['prenom'])} {salarie['nom']}".strip()
    )
    logo_html = ""
    if salarie.get("logo_b64"):
        logo_html = f'<img src="data:image/png;base64,{salarie["logo_b64"]}" alt="logo">'

    # Lignes + 12 minimum
    lines_html_parts = []
    tot = {k: 0.0 for k, _ in _CATEGORIES}
    tot_tva = 0.0
    tot_ttc = 0.0
    for n in notes:
        col = _ventile_ht(n["lib_type"])
        tot[col] += n["ht"]
        tot_tva += n["tva"]
        tot_ttc += n["ttc"]
        cells = []
        for k, _ in _CATEGORIES:
            v = n["ht"] if k == col else 0.0
            cells.append(_fmt_eur(v) if v else "")
        lines_html_parts.append(
            "<tr>"
            f"<td>{_fmt_fr_date(n['date_iso'])}</td>"
            f"<td>{escape(n['description'])}</td>"
            + "".join(f"<td class='num'>{c}</td>" for c in cells)
            + f"<td class='num'>{_fmt_eur(n['tva']) if n['tva'] else ''}</td>"
            f"<td class='num'>{_fmt_eur(n['ttc']) if n['ttc'] else ''}</td>"
            "</tr>"
        )

    # Pad a 12 lignes minimum
    nb_vides = max(0, 12 - len(notes))
    for _ in range(nb_vides):
        lines_html_parts.append(
            "<tr><td>&nbsp;</td><td>&nbsp;</td>"
            + "<td>&nbsp;</td>" * len(_CATEGORIES)
            + "<td>&nbsp;</td><td>&nbsp;</td></tr>"
        )

    totals_html = (
        "<tr class='totals'><td colspan='2'>= Total</td>"
        + "".join(
            f"<td class='num'>{_fmt_eur(tot[k]) if tot[k] else ''}</td>"
            for k, _ in _CATEGORIES
        )
        + f"<td class='num'>{_fmt_eur(tot_tva)}</td>"
        f"<td class='num'>{_fmt_eur(tot_ttc)}</td></tr>"
    )

    css = """
    @page {
        size: A4 landscape;
        margin: 12mm;
        @bottom-right {
            content: 'Page ' counter(page) ' / ' counter(pages);
            font-size: 8pt;
            color: #4E1D17;
        }
    }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #4E1D17; font-size: 9pt; }
    .header { display: flex; align-items: center; gap: 20px; border-bottom: 2px solid """ + bg_color + """; padding-bottom: 6mm; }
    .header .logo img { max-width: 30mm; max-height: 18mm; }
    .header h1 { margin: 0; font-size: 18pt; color: """ + bg_color + """; flex: 1; text-align: center; }
    .header .date { font-size: 10pt; color: #4E1D17; }
    .info { margin: 5mm 0; }
    .info h2 { font-size: 11pt; color: """ + bg_color + """; border-bottom: 1px solid """ + bg_color + """; padding-bottom: 1mm; margin-bottom: 3mm; }
    .info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; font-size: 9pt; }
    .info-cell .lib { font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-top: 4mm; }
    th, td { padding: 1.5mm; border: 1px solid #C4B5B0; font-size: 8pt; }
    thead th { background: """ + bg_color + """; color: """ + text_color + """; font-weight: 600; }
    td.num { text-align: right; font-family: 'Consolas', monospace; }
    tr.totals td { background: #F0E6E2; font-weight: 700; }
    """

    info_grid = (
        f"<div class='info-cell'><span class='lib'>Nom Prénom :</span> {escape(nom_prenom)}</div>"
        f"<div class='info-cell'><span class='lib'>Responsable :</span> {escape(salarie['nom_da'])}</div>"
        f"<div class='info-cell'><span class='lib'>Mois Paiement :</span> {periode_lib}</div>"
        f"<div class='info-cell'><span class='lib'>Poste :</span> {escape(salarie['poste'])}</div>"
        f"<div class='info-cell'><span class='lib'>Société :</span> {escape(salarie['raison_sociale'])}</div>"
        f"<div class='info-cell'><span class='lib'>Période Frais :</span> {periode_lib}</div>"
    )

    head_cats = "".join(f"<th>{escape(lib)}</th>" for _, lib in _CATEGORIES)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>
    <div class="header">
        <div class="logo">{logo_html}</div>
        <h1>Note de frais</h1>
        <div class="date">{today}</div>
    </div>
    <div class="info">
        <h2>Information du salarié</h2>
        <div class="info-grid">{info_grid}</div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Date</th><th>Description</th>
                {head_cats}
                <th>TVA</th><th>TTC</th>
            </tr>
        </thead>
        <tbody>
            {"".join(lines_html_parts)}
            {totals_html}
        </tbody>
    </table>
</body></html>"""


def _photo_mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def _render_justifs_html(salarie: dict, notes: list[dict], mois: int, annee: int) -> str:
    """Grille des justificatifs (3 par ligne, max 6 par page)."""
    nom_prenom = f"{_capitalize(salarie['prenom'])} {salarie['nom']}".strip()
    periode_lib = f"{_MOIS_FR[mois]} {annee}"
    items = [n for n in notes if n.get("photo")]

    cards = []
    for n in items:
        mime = _photo_mime(n["photo"])
        b64 = base64.b64encode(n["photo"]).decode("ascii")
        cards.append(
            "<div class='card'>"
            f"<div class='hdr'>{_fmt_fr_date(n['date_iso'])} · {escape(n['lib_type'])} · {_fmt_eur(n['ttc'])}</div>"
            f"<img src='data:{mime};base64,{b64}' />"
            f"<div class='desc'>{escape(n['description'])}</div>"
            "</div>"
        )

    css = """
    @page { size: A4; margin: 12mm; }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #4E1D17; font-size: 9pt; }
    h1 { font-size: 16pt; color: #4E1D17; text-align: center; margin: 0 0 4mm; }
    .sub { text-align: center; margin-bottom: 6mm; }
    .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6mm; }
    .card { border: 1px solid #C4B5B0; border-radius: 3mm; padding: 3mm; page-break-inside: avoid; }
    .hdr { font-size: 8pt; color: #4E1D17; margin-bottom: 2mm; font-weight: 600; }
    .card img { width: 100%; max-height: 90mm; object-fit: contain; border: 1px solid #EFE9E7; }
    .desc { font-size: 8pt; color: #4E1D17; margin-top: 2mm; opacity: 0.8; }
    """

    body = (
        f"<h1>Justificatifs - {periode_lib}</h1>"
        f"<div class='sub'>{escape(nom_prenom)}</div>"
    )
    if not cards:
        body += "<p style='text-align:center; opacity:0.6;'><em>Aucun justificatif photo.</em></p>"
    else:
        body += f"<div class='grid'>{''.join(cards)}</div>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{body}</body></html>"""


def build_print_pdf(id_salarie: int, mois: int, annee: int) -> bytes:
    """Genere le PDF complet (note de frais + justificatifs) et retourne les bytes."""
    salarie = _load_salarie_info(int(id_salarie))
    notes = _load_notes_with_photo(int(id_salarie), int(mois), int(annee))

    if not notes:
        raise ValueError("Pas d'information à imprimer")

    # 1) PDF principal (page paysage A4)
    html_main = _render_note_frais_html(salarie, notes, mois, annee)
    # 2) PDF justificatifs (portrait A4)
    html_just = _render_justifs_html(salarie, notes, mois, annee)

    # Import lazy : WeasyPrint requis seulement ici.
    from weasyprint import HTML  # noqa: PLC0415

    pdf_main = HTML(string=html_main).write_pdf()
    pdf_just = HTML(string=html_just).write_pdf()

    # Fusion via pypdf
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415

        writer = PdfWriter()
        for raw in (pdf_main, pdf_just):
            reader = PdfReader(io.BytesIO(raw))
            for p in reader.pages:
                writer.add_page(p)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return pdf_main + pdf_just  # fallback (probablement invalide)
