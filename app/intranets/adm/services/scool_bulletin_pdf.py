"""
S'Cool : generation du PDF EtatBulletinScool via WeasyPrint.

Cf. WinDev Etat_ScoolBulletin (procedure MonEtat(idForm, IdStagiaire, CodeV)).
"""
from __future__ import annotations

import base64
import logging
from html import escape

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_bulletin import BulletinDetail

logger = logging.getLogger(__name__)

# Cachet + Signature + Logo depuis la societe id_ste=306 (cf. WinDev)
_ID_STE_BULLETIN = 306


def _fmt_num(v, dec: int = 2) -> str:
    try:
        return f"{float(v):,.{dec}f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return "0,00"


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _fmt_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _detect_image_mime(b: bytes) -> str:
    """Detecte le type MIME depuis les magic bytes."""
    if not b or len(b) < 8:
        return ""
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if b[:4] == b"%PDF":
        return "application/pdf"
    return ""


def _pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    """Convertit la 1ere page d'un PDF en PNG via PyMuPDF."""
    try:
        import fitz  # noqa: PLC0415
    except ImportError:
        logger.warning("PyMuPDF non installe : impossible de convertir PDF -> PNG")
        return b""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            doc.close()
            return b""
        page = doc.load_page(0)
        # Rendu haute res (150 DPI) pour la qualite
        pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=True)
        png = pix.tobytes("png")
        doc.close()
        return png
    except Exception:
        logger.exception("_pdf_first_page_to_png")
        return b""


def _compose_signature_cachet(
    cachet_bytes: bytes, signature_bytes: bytes,
) -> bytes:
    """Compose signature au-dessus du cachet dans une seule image PNG.

    WeasyPrint gere mal position:absolute + object-fit sur img. On
    fait la superposition cote serveur avec PIL.
    """
    try:
        from PIL import Image  # noqa: PLC0415
        import io as _io  # noqa: PLC0415
    except ImportError:
        logger.warning(
            "Pillow non installe : impossible de composer signature+cachet. "
            "pip install Pillow",
        )
        return b""
    # Cachet en fond
    if not cachet_bytes:
        return signature_bytes or b""
    try:
        cachet = Image.open(_io.BytesIO(cachet_bytes)).convert("RGBA")
    except Exception:
        return signature_bytes or b""
    if not signature_bytes:
        buf = _io.BytesIO()
        cachet.save(buf, format="PNG")
        return buf.getvalue()
    try:
        signature = Image.open(_io.BytesIO(signature_bytes)).convert("RGBA")
    except Exception:
        buf = _io.BytesIO()
        cachet.save(buf, format="PNG")
        return buf.getvalue()

    # Adapte la signature a la meme largeur que le cachet (max), en
    # gardant les proportions. Puis colle au centre.
    ratio_sig = signature.width / signature.height
    target_w = cachet.width
    target_h = int(target_w / ratio_sig)
    if target_h > cachet.height:
        target_h = cachet.height
        target_w = int(target_h * ratio_sig)
    signature = signature.resize(
        (target_w, target_h), Image.LANCZOS,
    )
    off_x = (cachet.width - target_w) // 2
    off_y = (cachet.height - target_h) // 2
    cachet.alpha_composite(signature, dest=(off_x, off_y))
    buf = _io.BytesIO()
    cachet.save(buf, format="PNG")
    return buf.getvalue()


def _img_b64(v) -> str:
    """Convertit bytes/memoryview en data URI base64.

    Si le contenu est un PDF, convertit la 1ere page en PNG via PyMuPDF
    (les navigateurs / WeasyPrint ne rendent pas les PDF comme <img>).
    """
    if v is None:
        return ""
    if hasattr(v, "tobytes"):
        v = v.tobytes()
    if isinstance(v, memoryview):
        v = v.tobytes()
    if not isinstance(v, (bytes, bytearray)):
        return ""
    b = bytes(v)
    mime = _detect_image_mime(b)
    if mime == "application/pdf":
        png = _pdf_first_page_to_png(b)
        if not png:
            return ""
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    if not mime:
        # Fallback : suppose PNG (comportement legacy)
        mime = "image/png"
    try:
        return f"data:{mime};base64," + base64.b64encode(b).decode("ascii")
    except Exception:
        return ""


def _load_infos_stagiaire(id_salarie: str) -> dict:
    if not id_salarie or id_salarie == "0":
        return {}
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT nom, prenom, date_naiss
                 FROM pgt_salarie
                WHERE id_salarie = ?""",
            (int(id_salarie),),
        )
    except Exception:
        return {}
    if not r:
        return {}
    return {
        "nom": (r.get("nom") or "").strip(),
        "prenom": (r.get("prenom") or "").strip().title(),
        "date_naiss": _fmt_date(str(r.get("date_naiss") or "")[:10]),
    }


def _load_infos_formation(id_formation: str) -> dict:
    if not id_formation or id_formation == "0":
        return {}
    db = get_pg_connection("scool")
    try:
        r = db.query_one(
            """SELECT intitule, categorie, ville_formation,
                      date_debut, date_fin
                 FROM scool.pgt_formation
                WHERE id_formation = ?""",
            (int(id_formation),),
        )
    except Exception:
        return {}
    return dict(r or {})


def _load_infos_societe() -> dict:
    """Charge cachet + signature + logo de la societe 306."""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT raison_sociale, cachet_cial, gerant_signature, logo
                 FROM pgt_societe WHERE id_ste = ?""",
            (_ID_STE_BULLETIN,),
        )
    except Exception:
        logger.exception("_load_infos_societe")
        return {}
    return dict(r or {})


def _mention_lib(id_mention: str) -> str:
    if not id_mention:
        return ""
    db = get_pg_connection("scool")
    try:
        r = db.query_one(
            """SELECT lib_mention FROM scool.pgt_bulletin_mention
                WHERE id_bulletin_mention = ?""",
            (int(id_mention),),
        )
    except Exception:
        return ""
    return (r.get("lib_mention") if r else "") or ""


_CSS = """
@page {
  size: A4 portrait;
  margin: 12mm 12mm 15mm 12mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-size: 8pt; color: #666;
  }
}
* { box-sizing: border-box; }
body {
  font-family: Arial, sans-serif; font-size: 9pt; color: #17494E;
}
h1 { font-size: 16pt; margin: 0 0 4px 0; color: #17494E; }
h2 { font-size: 10pt; margin: 12px 0 4px 0; color: #17494E;
     border-bottom: 1px solid #8B7355; padding-bottom: 2px; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 2px solid #17494E; padding-bottom: 6px; margin-bottom: 10px;
}
.header .logo { height: 60px; }
.infos {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  background: #F5F5F0; padding: 8px; border-radius: 4px;
  margin-bottom: 10px;
}
.infos .label {
  font-size: 8pt; color: #8B7355; text-transform: uppercase;
}
.infos .value { font-weight: bold; color: #17494E; }
table.notes {
  width: 100%; border-collapse: collapse; margin: 6px 0;
}
table.notes th, table.notes td {
  border: 1px solid #E5E0D5; padding: 4px 6px;
}
table.notes th {
  background: #17494E; color: white; font-size: 8pt;
}
table.notes td.center { text-align: center; }
table.notes td.right { text-align: right; }
.badge-type {
  display: inline-block; padding: 3px 10px; border-radius: 12px;
  background: #17494E; color: white; font-size: 9pt; margin-left: 6px;
}
.zone-formateur {
  border: 1px dashed #8B7355; padding: 8px; border-radius: 4px;
  margin-top: 10px; background: #FAFAF5;
}
.zone-formateur h3 {
  margin: 0 0 4px 0; font-size: 9pt; color: #8B7355;
  text-transform: uppercase;
}
.signature-cachet {
  margin-top: 20px; padding-top: 10px;
  border-top: 1px solid #E5E0D5;
  text-align: right;
}
.signature-cachet img {
  max-width: 280px; max-height: 140px;
  display: block; margin-left: auto;
}
.signature-cachet .lib {
  font-size: 8pt; color: #8B7355; margin-bottom: 4px;
}
"""


def _render_html(b: BulletinDetail) -> str:
    sa = _load_infos_stagiaire(b.id_salarie)
    fo = _load_infos_formation(b.id_formation)
    so = _load_infos_societe()

    type_lib = "Bulletin définitif" if b.type_bulletin == 1 else "Bulletin intermédiaire"

    logo_b64 = _img_b64(so.get("logo"))
    # Signature superposee au cachet (composition PIL cote serveur car
    # WeasyPrint gere mal position:absolute + object-fit sur img).
    # Le cachet stocke en PDF est converti en PNG en amont, donc on
    # repasse les bytes bruts PNG a la composition.
    def _to_png_bytes(v) -> bytes:
        if v is None:
            return b""
        if hasattr(v, "tobytes"):
            v = v.tobytes()
        b = bytes(v)
        mime = _detect_image_mime(b)
        if mime == "application/pdf":
            return _pdf_first_page_to_png(b)
        return b
    cachet_png = _to_png_bytes(so.get("cachet_cial"))
    signature_png = _to_png_bytes(so.get("gerant_signature"))
    combined = _compose_signature_cachet(cachet_png, signature_png)
    signature_cachet_b64 = (
        "data:image/png;base64," + base64.b64encode(combined).decode("ascii")
        if combined else ""
    )
    mention_lib = _mention_lib(b.id_bulletin_mention)

    notes_rows = [
        ("Assiduité", b.note_assiduite, b.nb_jours_form - b.nb_jours_pres),
        ("Objectif Ctt", b.note_ctt_hr, b.nb_ctt_hr),
        ("Conquête", b.note_cqt, b.nb_cqt_hr),
        ("Premium", b.note_prem, b.nb_prem_hr),
        ("Mobile", b.note_mob, b.nb_mob_hr),
        ("Cooptation", b.note_coopt, b.nb_coopt),
        ("Objectif Décalé", b.note_obj_decale, b.objectif_decale),
        ("Attitude Théorique", b.note_app_theo, "-"),
        ("Attitude Pratique", b.note_app_pratique, "-"),
    ]

    lignes_html = "".join(
        f"""<tr>
              <td>{escape(lib)}</td>
              <td class="center">{val if isinstance(val, str) else _fmt_int(val)}</td>
              <td class="right">{_fmt_num(note)}</td>
            </tr>"""
        for lib, note, val in notes_rows
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
  <div class="header">
    <div>
      {'<img class="logo" src="' + logo_b64 + '" />' if logo_b64 else ''}
    </div>
    <div style="text-align:right">
      <h1>Bulletin de formation</h1>
      <div><span class="badge-type">{escape(type_lib)}</span></div>
    </div>
  </div>

  <div class="infos">
    <div>
      <div class="label">Stagiaire</div>
      <div class="value">{escape(sa.get('nom', ''))} {escape(sa.get('prenom', ''))}</div>
    </div>
    <div>
      <div class="label">Date de naissance</div>
      <div class="value">{escape(sa.get('date_naiss', '') or '-')}</div>
    </div>
    <div>
      <div class="label">Formation</div>
      <div class="value">{escape(fo.get('intitule', '') or '')}</div>
    </div>
    <div>
      <div class="label">Ville</div>
      <div class="value">{escape(fo.get('ville_formation', '') or '-')}</div>
    </div>
    <div>
      <div class="label">Période</div>
      <div class="value">Du {_fmt_date(b.du)} au {_fmt_date(b.au)}</div>
    </div>
    <div>
      <div class="label">Nb jours de formation</div>
      <div class="value">{_fmt_int(b.nb_jours_form)} · Présents : {_fmt_int(b.nb_jours_pres)}</div>
    </div>
  </div>

  <h2>Notes obtenues</h2>
  <table class="notes">
    <thead>
      <tr>
        <th>Item</th>
        <th>Chiffre</th>
        <th>Note</th>
      </tr>
    </thead>
    <tbody>{lignes_html}</tbody>
  </table>

  <div class="zone-formateur">
    <h3>Partie réservée aux formateurs</h3>
    <div><b>Mention :</b> {escape(mention_lib or '-')}</div>
    <div style="margin-top:6px"><b>Observation :</b><br />
      {escape(b.observation or '-')}
    </div>
    <div style="margin-top:6px"><b>Axe de travail :</b><br />
      {escape(b.axe_travail or '-')}
    </div>
  </div>

  <div class="signature-cachet">
    <div class="lib">Signature et cachet</div>
    {'<img src="' + signature_cachet_b64 + '" />' if signature_cachet_b64 else ''}
  </div>
</body></html>"""


def build_bulletin_pdf(b: BulletinDetail) -> bytes:
    try:
        from weasyprint import HTML  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint indisponible : installer weasyprint + GTK3 Runtime.",
        ) from e
    html = _render_html(b)
    return HTML(string=html).write_pdf()
