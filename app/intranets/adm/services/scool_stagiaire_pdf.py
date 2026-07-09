"""
S'Cool : PDFs Fen_ScoolStagiaire_Fiche.

3 etats WinDev generes via WeasyPrint :
  - EtatScool_DeclPres          -> build_declpres_pdf
  - EtatProdStagiareScool       -> build_prodeni_pdf
  - EtatProdStagiareScoolFibre  -> build_prodsfr_pdf

Tous 3 recuperent le logo societe 306 (GUIMMICK) cf. WinDev.
"""
from __future__ import annotations

import base64
import logging
from datetime import date as _date
from html import escape

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_stagiaire_fiche import (
    ProdEniRow, ProdSfrRow, ScoolStagiaireFiche,
)


logger = logging.getLogger(__name__)


_ID_STE_LOGO = 306


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _fmt_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _fmt_num(v, dec: int = 2) -> str:
    try:
        f = f"{float(v):,.{dec}f}"
        return f.replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return "0"


def _fmt_int(v) -> str:
    try:
        n = int(v)
        return f"{n:,}".replace(",", " ") if n else ""
    except (TypeError, ValueError):
        return ""


def _fmt_pct(v: float, dec: int = 1) -> str:
    if not v:
        return ""
    return f"{v * 100:.{dec}f}%".replace(".", ",")


def _detect_image_mime(b: bytes) -> str:
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
    try:
        import fitz  # noqa: PLC0415
    except ImportError:
        return b""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            doc.close()
            return b""
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), alpha=True)
        png = pix.tobytes("png")
        doc.close()
        return png
    except Exception:
        logger.exception("_pdf_first_page_to_png")
        return b""


def _load_logo_societe() -> str:
    """Retourne data URI du logo GUIMMICK (societe 306).
    Si PDF -> convertit en PNG via PyMuPDF.
    """
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            "SELECT logo FROM pgt_societe WHERE id_ste = ?",
            (_ID_STE_LOGO,),
        )
    except Exception:
        logger.exception("_load_logo_societe")
        return ""
    if not r:
        return ""
    raw = r.get("logo")
    if raw is None:
        return ""
    if hasattr(raw, "tobytes"):
        raw = raw.tobytes()
    raw = bytes(raw)
    mime = _detect_image_mime(raw)
    if mime == "application/pdf":
        raw = _pdf_first_page_to_png(raw)
        mime = "image/png" if raw else ""
    if not raw or not mime:
        return ""
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _load_emargements(
    id_salarie: int, date_debut: str, date_fin: str,
) -> dict[str, tuple[str, str]]:
    """Charge les emargements binaires -> {date: (matin_data_uri,
    aprem_data_uri)}."""
    out: dict[str, tuple[str, str]] = {}
    if not id_salarie or not date_debut or not date_fin:
        return out
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT date, emargement_matin, emargement_aprem
                 FROM pgt_salarie_decl_presence
                WHERE id_salarie = ?
                  AND date BETWEEN ? AND ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (id_salarie, date_debut, date_fin),
        ) or []
    except Exception:
        logger.exception("_load_emargements")
        return out
    for r in rows:
        d = str(r.get("date"))[:10]
        if not d:
            continue

        def _to_data_uri(v) -> str:
            if v is None:
                return ""
            if hasattr(v, "tobytes"):
                v = v.tobytes()
            b = bytes(v)
            m = _detect_image_mime(b)
            if not m or m == "application/pdf":
                return ""
            return f"data:{m};base64,{base64.b64encode(b).decode('ascii')}"

        out[d] = (
            _to_data_uri(r.get("emargement_matin")),
            _to_data_uri(r.get("emargement_aprem")),
        )
    return out


def _render_html_to_pdf(html: str) -> bytes:
    """Rendu WeasyPrint (import differe : lib optionnelle sur certaines
    machines).
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint non installe : pip install weasyprint "
            "(+ GTK3 Runtime sur Windows).",
        ) from e
    return HTML(string=html).write_pdf()


# --------------------------------------------------------------------
# 1) EtatScool_DeclPres : Fiche emargement S'COOL
# --------------------------------------------------------------------

def build_declpres_pdf(fiche: ScoolStagiaireFiche) -> bytes:
    """Cf. WinDev EtatScool_DeclPres.
    Table 6 colonnes : Date | Presence | Motif abs | Periode abs |
    Emarg matin | Emarg aprem.
    """
    logo = _load_logo_societe()
    today = _date.today().strftime("%d/%m/%Y")

    # Charge les images emargement
    emarg = _load_emargements(
        int(fiche.id_salarie) if fiche.id_salarie else 0,
        fiche.date_debut, fiche.date_fin,
    )

    def _periode_label(p: int) -> str:
        if p == 1: return "Matin"
        if p == 2: return "Après-midi"
        if p == 3: return "Journée"
        return ""

    rows_html = []
    for pres in fiche.presence:
        m_uri, a_uri = emarg.get(pres.date, ("", ""))
        m_html = (
            f'<img src="{m_uri}" style="max-width:100px;max-height:40px;" />'
            if m_uri else ("✓" if pres.emarg_matin else "")
        )
        a_html = (
            f'<img src="{a_uri}" style="max-width:100px;max-height:40px;" />'
            if a_uri else ("✓" if pres.emarg_aprem else "")
        )
        pres_html = "✓" if pres.presence == 1 else (
            "½" if pres.presence == -1 else "✗"
        )
        rows_html.append(f"""
          <tr>
            <td class="c">{_fmt_date(pres.date)}</td>
            <td class="c">{pres_html}</td>
            <td>{escape(pres.motif_absence or "")}</td>
            <td class="c">{_periode_label(pres.periode)}</td>
            <td class="c">{m_html}</td>
            <td class="c">{a_html}</td>
          </tr>
        """)

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
  @page {{ size: A4 landscape; margin: 1cm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 9pt;
         color: #333; }}
  .header {{ display: flex; align-items: center; gap: 12px;
             border-bottom: 2px solid #17494E; padding-bottom: 6px;
             margin-bottom: 12px; }}
  .header img {{ height: 42px; }}
  .header h1 {{ font-size: 16pt; color: #17494E; margin: 0;
                flex: 1; text-align: center; }}
  .header .date {{ font-size: 9pt; color: #666; }}
  .title-page {{ font-size: 11pt; font-weight: bold; margin: 8px 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #17494E; color: white; padding: 4px 6px;
        text-align: left; font-weight: 600; font-size: 9pt; }}
  td {{ padding: 3px 6px; border-bottom: 1px solid #F0EDE5; font-size: 8.5pt; }}
  .c {{ text-align: center; }}
  .footer {{ margin-top: 8px; font-size: 8pt; color: #888; }}
</style></head><body>

  <div class="header">
    {f'<img src="{logo}" />' if logo else ''}
    <h1>Fiche émargement S'COOL</h1>
    <div class="date">{today}</div>
  </div>

  <div class="title-page">{escape(fiche.nom_prenom)}</div>

  <table>
    <thead><tr>
      <th class="c">Date</th>
      <th class="c">Présence</th>
      <th>Motif d'absence</th>
      <th class="c">Période d'absence</th>
      <th class="c">Émarg. matin</th>
      <th class="c">Émarg. aprem</th>
    </tr></thead>
    <tbody>{"".join(rows_html) or '<tr><td colspan="6" class="c">Aucune donnée</td></tr>'}</tbody>
  </table>

  <div class="footer">Nombre de lignes : {len(fiche.presence)}</div>

</body></html>
"""
    return _render_html_to_pdf(html)


# --------------------------------------------------------------------
# 2) EtatProdStagiareScool : bilan ENI (par semaine + graph)
# --------------------------------------------------------------------

def _svg_bar_chart(
    title: str, series: list[tuple[str, int, str]], height: int = 200,
) -> str:
    """SVG simple : barres verticales avec libelle + valeur.
    series = [(label, value, color), ...]
    """
    if not series:
        return ""
    max_v = max((v for _, v, _ in series if v > 0), default=1)
    if max_v <= 0:
        max_v = 1
    bar_w = 60
    gap = 20
    w = len(series) * (bar_w + gap) + 40
    h = height + 60
    parts = [f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(
        f'<text x="{w // 2}" y="15" text-anchor="middle" '
        'style="font-size:11pt;font-weight:bold;fill:#17494E;">'
        f'{escape(title)}</text>'
    )
    x = 20
    for label, val, color in series:
        bh = int((val / max_v) * height) if val > 0 else 0
        y = h - 40 - bh
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" '
            f'fill="{color}" />'
        )
        parts.append(
            f'<text x="{x + bar_w // 2}" y="{y - 4}" '
            f'text-anchor="middle" style="font-size:8pt;fill:#333;">'
            f'{val}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w // 2}" y="{h - 22}" '
            f'text-anchor="middle" style="font-size:7pt;fill:#333;">'
            f'{escape(label)}</text>'
        )
        x += bar_w + gap
    # Ligne de base
    parts.append(
        f'<line x1="10" y1="{h - 40}" x2="{w - 10}" y2="{h - 40}" '
        'stroke="#888" />'
    )
    parts.append('</svg>')
    return "".join(parts)


def _build_prod_bilan_footer(fiche: ScoolStagiaireFiche) -> tuple[dict, str]:
    """Cf. WinDev bloc 'Fin de document'. Retourne (dict des totaux, HTML)."""
    tot_h = fiche.tot_duree
    tot_h_salle = fiche.tot_salle * fiche.heure_jour_salle
    tot_h_terrain = fiche.tot_terrain * fiche.heure_jour_terrain
    nb_jours = fiche.tot_salle + fiche.tot_terrain

    absence = fiche.tot_absent
    presence = fiche.tot_present

    obj_bs = fiche.tot_obj_bs
    nb_ctt = fiche.tot_ctt
    nb_adf = fiche.tot_adf
    pct_adf = (nb_adf / nb_ctt) if nb_ctt else 0
    pct_obj = (nb_ctt / obj_bs) if obj_bs else 0

    return (
        {},
        f"""
        <div class="bilan">
          <div class="bilan-title">Bilan Formation :</div>
          <div class="bilan-row">
            <b>{_fmt_num(tot_h, 1)}</b> h dont
            <b>{_fmt_num(tot_h_salle, 1)}</b> h en salle et
            <b>{_fmt_num(tot_h_terrain, 1)}</b> h sur le terrain
          </div>
          <div class="bilan-row">Nombre de jours : <b>{_fmt_num(nb_jours, 1)}</b></div>

          <div class="bilan-h">Assiduité du stagiaire :</div>
          <div class="bilan-row">Absence : <b>{_fmt_num(absence, 1)} j</b></div>
          <div class="bilan-row">Présences : <b>{_fmt_num(presence, 1)} j</b></div>

          <div class="bilan-h">Production du stagiaire :</div>
          <div class="bilan-row">Obj BS Formation : <b>{_fmt_num(obj_bs, 1)}</b></div>
          <div class="bilan-row">NB contrats : <b>{_fmt_int(nb_ctt)}</b></div>
          <div class="bilan-row">NB contrats ADF : <b>{_fmt_int(nb_adf)}</b>
            <span class="pct">{_fmt_pct(pct_adf)}</span></div>
          <div class="bilan-row">Objectifs : <b>{_fmt_pct(pct_obj)}</b></div>
          <div class="bilan-row">Assurances : <b>{_fmt_int(fiche.tot_assu)}</b></div>
          <div class="bilan-row">Presse : <b>{_fmt_int(fiche.tot_presse)}</b></div>
          <div class="bilan-row">Cooptations : <b>{_fmt_int(fiche.tot_coopt)}</b></div>
        </div>
        """
    )


def build_prodeni_pdf(fiche: ScoolStagiaireFiche) -> bytes:
    """Cf. WinDev EtatProdStagiareScool."""
    logo = _load_logo_societe()
    today = _date.today().strftime("%d/%m/%Y")

    # Groupement par semaine
    weeks: dict[str, list[ProdEniRow]] = {}
    for r in fiche.prod_eni:
        weeks.setdefault(r.sem_prod or f"Semaine {r.num_sem}", []).append(r)
    weeks_sorted = sorted(
        weeks.keys(),
        key=lambda k: int(''.join(c for c in k if c.isdigit()) or "0"),
    )

    # Construction des sections par semaine
    sections: list[str] = []
    for sem in weeks_sorted:
        rows = weeks[sem]
        st = {
            "salle": sum(r.salle for r in rows),
            "terrain": sum(r.terrain for r in rows),
            "duree": sum(r.duree for r in rows),
            "absent": sum(r.absent for r in rows),
            "present": sum(r.present for r in rows),
            "obj_bs": sum(r.objectif_bs_jour for r in rows),
            "total_ctt": sum(r.total_ctt for r in rows),
            "total_adf": sum(r.total_adf for r in rows),
            "eni_gaz": sum(r.eni_gaz for r in rows),
            "eni_dual": sum(r.eni_dual for r in rows),
            "eni_elec": sum(r.eni_elec for r in rows),
            "eni_gv": sum(r.eni_gaz_vert for r in rows),
            "eni_ev": sum(r.eni_elec_verte for r in rows),
            "eni_mail": sum(r.eni_mail for r in rows),
            "assu": sum(r.assu for r in rows),
            "presse": sum(r.presse for r in rows),
            "coopt": sum(r.cooptation for r in rows),
        }
        # Obj BS Semaine = somme obj/nb jours terrain
        rows_html = []
        for r in rows:
            rows_html.append(f"""
              <tr>
                <td class="c">{_fmt_date(r.date)}</td>
                <td class="r">{_fmt_num(r.salle, 1)}</td>
                <td class="r">{_fmt_num(r.terrain, 1)}</td>
                <td class="r">{_fmt_num(r.duree, 1)}</td>
                <td class="r">{_fmt_num(r.absent, 1)}</td>
                <td class="r">{_fmt_num(r.present, 1)}</td>
                <td class="r">{_fmt_num(r.objectif_bs_jour, 0)}</td>
                <td class="r">{_fmt_int(r.total_ctt)}</td>
                <td class="r">{_fmt_int(r.total_adf)}</td>
                <td class="r">{_fmt_pct(r.pourcent_adf)}</td>
                <td class="r">{_fmt_int(r.eni_gaz)}</td>
                <td class="r">{_fmt_int(r.eni_dual)}</td>
                <td class="r">{_fmt_pct(r.pourcent_dual)}</td>
                <td class="r">{_fmt_int(r.eni_elec)}</td>
                <td class="r">{_fmt_pct(r.pourcent_elec)}</td>
                <td class="r">{_fmt_int(r.eni_mail)}</td>
                <td class="r">{_fmt_pct(r.pourcent_mail)}</td>
                <td class="r">{_fmt_int(r.eni_gaz_vert)}</td>
                <td class="r">{_fmt_pct(r.pourcent_gv)}</td>
                <td class="r">{_fmt_int(r.eni_elec_verte)}</td>
                <td class="r">{_fmt_pct(r.pourcent_ev)}</td>
                <td class="r">{_fmt_int(r.assu)}</td>
                <td class="r">{_fmt_int(r.presse)}</td>
                <td class="r">{_fmt_pct(r.pourcent_presse)}</td>
                <td class="r">{_fmt_int(r.cooptation)}</td>
              </tr>
            """)
        sections.append(f"""
          <div class="sem-title">{escape(sem)}</div>
          <table class="prod">
            <thead>
              <tr>
                <th class="c">Date</th>
                <th class="c">Salle</th><th class="c">Terrain</th><th class="c">Durée</th>
                <th class="c">Absent</th><th class="c">Présent</th>
                <th class="c">Obj BS</th>
                <th class="c">Total Ctt</th>
                <th class="c">Ctt ADF</th><th class="c">%</th>
                <th class="c">Mono Gaz</th><th class="c">Dual</th><th class="c">%</th>
                <th class="c">Mono Elec</th><th class="c">%</th>
                <th class="c">Opt Mail</th><th class="c">%</th>
                <th class="c">En.V Gaz</th><th class="c">%</th>
                <th class="c">En.V Elec</th><th class="c">%</th>
                <th class="c">ASSU</th>
                <th class="c">PRESSE</th><th class="c">%</th>
                <th class="c">Coopt</th>
              </tr>
            </thead>
            <tbody>{"".join(rows_html)}</tbody>
            <tfoot>
              <tr class="stot">
                <td>Ss Totaux :</td>
                <td class="r">{_fmt_num(st['salle'], 1)}</td>
                <td class="r">{_fmt_num(st['terrain'], 1)}</td>
                <td class="r">{_fmt_num(st['duree'], 1)}</td>
                <td class="r">{_fmt_num(st['absent'], 1)}</td>
                <td class="r">{_fmt_num(st['present'], 1)}</td>
                <td class="r">{_fmt_num(st['obj_bs'], 0)}</td>
                <td class="r">{_fmt_int(st['total_ctt'])}</td>
                <td class="r">{_fmt_int(st['total_adf'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['eni_gaz'])}</td>
                <td class="r">{_fmt_int(st['eni_dual'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['eni_elec'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['eni_mail'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['eni_gv'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['eni_ev'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['assu'])}</td>
                <td class="r">{_fmt_int(st['presse'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['coopt'])}</td>
              </tr>
            </tfoot>
          </table>
          <div class="obj-sem">Obj BS Semaine : <b>{_fmt_num(st['obj_bs'], 1)}</b></div>
        """)

    # Axes de travail (affiches une fois en fin de tableau)
    axes_html = ""
    if fiche.axe_travail_1 or fiche.axe_travail_2:
        axes_html = f"""
        <div class="axes">
          <div><b>Axe de travail 1</b><br />{escape(fiche.axe_travail_1)}</div>
          <div><b>Axe de travail 2</b><br />{escape(fiche.axe_travail_2)}</div>
        </div>
        """

    _, bilan_html = _build_prod_bilan_footer(fiche)

    # Graph ENI - agrege sur toute la formation
    tot_ctt = (fiche.tot_ctt - fiche.tot_assu - fiche.tot_presse)
    graph = _svg_bar_chart(
        "Contrats ENI",
        [
            ("Contrats ENI", tot_ctt, "#E31E24"),
            ("Mono Gaz", sum(r.eni_gaz for r in fiche.prod_eni), "#FF9800"),
            ("Mono Elec", sum(r.eni_elec for r in fiche.prod_eni), "#4CAF50"),
            ("Dual", sum(r.eni_dual for r in fiche.prod_eni), "#00BCD4"),
            ("Mail", sum(r.eni_mail for r in fiche.prod_eni), "#8B4513"),
            ("En.V Gaz", sum(r.eni_gaz_vert for r in fiche.prod_eni), "#00838F"),
            ("En.V Elec", sum(r.eni_elec_verte for r in fiche.prod_eni), "#E91E63"),
        ],
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
  @page {{ size: A4 landscape; margin: 0.8cm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 7.5pt; color: #333; }}
  .header {{ display: flex; align-items: center; gap: 12px;
             border-bottom: 2px solid #17494E; padding-bottom: 6px;
             margin-bottom: 8px; }}
  .header img {{ height: 42px; }}
  .header h1 {{ font-size: 14pt; color: #17494E; margin: 0;
                flex: 1; text-align: center; }}
  .header .date {{ font-size: 9pt; color: #666; }}
  .title-doc {{ font-size: 10pt; font-weight: bold; text-align: center;
                margin: 2px 0 8px 0; }}
  .sem-title {{ background: #17494E; color: white; padding: 3px 6px;
                margin-top: 6px; font-weight: bold; font-size: 9pt; }}
  table.prod {{ width: 100%; border-collapse: collapse;
                table-layout: fixed; font-size: 6.5pt; }}
  table.prod th {{ background: #17494E; color: white; padding: 2px 1px;
                   font-weight: 600; font-size: 6pt; }}
  table.prod td {{ padding: 2px 1px; border-bottom: 1px solid #F0EDE5;
                   font-size: 6.5pt; }}
  table.prod tr.stot td {{ background: #F5F1E8; font-weight: bold;
                            border-top: 1px solid #17494E; }}
  .c {{ text-align: center; }}
  .r {{ text-align: right; }}
  .obj-sem {{ font-size: 8pt; color: #C00; padding: 3px; }}
  .axes {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
           margin: 8px 0; font-size: 8pt; }}
  .axes > div {{ border: 1px solid #D4C9A8; padding: 6px;
                 background: #FAFAF5; }}
  .bilan {{ float: left; width: 45%; margin-top: 6px; font-size: 8.5pt; }}
  .graph {{ float: right; width: 53%; margin-top: 6px; text-align: center; }}
  .bilan-title {{ font-weight: bold; color: #17494E; font-size: 10pt;
                  border-bottom: 1px solid #17494E; margin-bottom: 4px; }}
  .bilan-h {{ font-weight: bold; text-decoration: underline;
              margin-top: 4px; }}
  .bilan-row {{ padding: 1px 0; }}
  .pct {{ color: #888; }}
</style></head><body>

  <div class="header">
    {f'<img src="{logo}" />' if logo else ''}
    <h1>Bilan formation {escape(fiche.nom_prenom)}</h1>
    <div class="date">{today}</div>
  </div>

  <div class="title-doc">{escape(fiche.nom_prenom)}</div>

  {"".join(sections)}
  {axes_html}

  <div style="clear:both; margin-top: 10px;">
    {bilan_html}
    <div class="graph">{graph}</div>
  </div>

</body></html>
"""
    return _render_html_to_pdf(html)


# --------------------------------------------------------------------
# 3) EtatProdStagiareScoolFibre : bilan SFR
# --------------------------------------------------------------------

def build_prodsfr_pdf(fiche: ScoolStagiaireFiche) -> bytes:
    """Cf. WinDev EtatProdStagiareScoolFibre."""
    logo = _load_logo_societe()
    today = _date.today().strftime("%d/%m/%Y")

    weeks: dict[str, list[ProdSfrRow]] = {}
    for r in fiche.prod_sfr:
        weeks.setdefault(r.sem_prod or f"Semaine {r.num_sem}", []).append(r)
    weeks_sorted = sorted(
        weeks.keys(),
        key=lambda k: int(''.join(c for c in k if c.isdigit()) or "0"),
    )

    sections: list[str] = []
    for sem in weeks_sorted:
        rows = weeks[sem]
        st = {
            "salle": sum(r.salle for r in rows),
            "terrain": sum(r.terrain for r in rows),
            "duree": sum(r.duree for r in rows),
            "absent": sum(r.absent for r in rows),
            "present": sum(r.present for r in rows),
            "obj_bs": sum(r.objectif_bs_jour for r in rows),
            "total_ctt": sum(r.total_ctt for r in rows),
            "total_adf": sum(r.total_adf for r in rows),
            "power8": sum(r.power8 for r in rows),
            "premium": sum(r.premium for r in rows),
            "fibre8": sum(r.fibre8 for r in rows),
            "power": sum(r.power for r in rows),
            "migration": sum(r.migration for r in rows),
            "mobile": sum(r.mobile for r in rows),
            "assu": sum(r.assu for r in rows),
            "presse": sum(r.presse for r in rows),
            "coopt": sum(r.cooptation for r in rows),
        }
        rows_html = []
        for r in rows:
            rows_html.append(f"""
              <tr>
                <td class="c">{_fmt_date(r.date)}</td>
                <td class="r">{_fmt_num(r.salle, 1)}</td>
                <td class="r">{_fmt_num(r.terrain, 1)}</td>
                <td class="r">{_fmt_num(r.duree, 1)}</td>
                <td class="r">{_fmt_num(r.absent, 1)}</td>
                <td class="r">{_fmt_num(r.present, 1)}</td>
                <td class="r">{_fmt_num(r.objectif_bs_jour, 0)}</td>
                <td class="r">{_fmt_int(r.total_ctt)}</td>
                <td class="r">{_fmt_int(r.total_adf)}</td>
                <td class="r">{_fmt_pct(r.pourcent_adf)}</td>
                <td class="r">{_fmt_int(r.power8)}</td>
                <td class="r">{_fmt_int(r.premium)}</td>
                <td class="r">{_fmt_int(r.fibre8)}</td>
                <td class="r">{_fmt_int(r.power)}</td>
                <td class="r">{_fmt_int(r.migration)}</td>
                <td class="r">{_fmt_int(r.mobile)}</td>
                <td class="r">{_fmt_int(r.assu)}</td>
                <td class="r">{_fmt_int(r.presse)}</td>
                <td class="r">{_fmt_pct(r.pourcent_presse)}</td>
                <td class="r">{_fmt_int(r.cooptation)}</td>
              </tr>
            """)
        sections.append(f"""
          <div class="sem-title">{escape(sem)}</div>
          <table class="prod">
            <thead>
              <tr>
                <th class="c">Date</th>
                <th class="c">Salle</th><th class="c">Terrain</th><th class="c">Durée</th>
                <th class="c">Absent</th><th class="c">Présent</th>
                <th class="c">Obj BS</th>
                <th class="c">Total Ctt</th>
                <th class="c">Ctt ADF</th><th class="c">%</th>
                <th class="c">Power 8</th><th class="c">Premium</th>
                <th class="c">Fibre 8</th><th class="c">Power</th>
                <th class="c">Migration</th><th class="c">Mobile</th>
                <th class="c">ASSU</th>
                <th class="c">PRESSE</th><th class="c">%</th>
                <th class="c">Coopt</th>
              </tr>
            </thead>
            <tbody>{"".join(rows_html)}</tbody>
            <tfoot>
              <tr class="stot">
                <td>Ss Totaux :</td>
                <td class="r">{_fmt_num(st['salle'], 1)}</td>
                <td class="r">{_fmt_num(st['terrain'], 1)}</td>
                <td class="r">{_fmt_num(st['duree'], 1)}</td>
                <td class="r">{_fmt_num(st['absent'], 1)}</td>
                <td class="r">{_fmt_num(st['present'], 1)}</td>
                <td class="r">{_fmt_num(st['obj_bs'], 0)}</td>
                <td class="r">{_fmt_int(st['total_ctt'])}</td>
                <td class="r">{_fmt_int(st['total_adf'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['power8'])}</td>
                <td class="r">{_fmt_int(st['premium'])}</td>
                <td class="r">{_fmt_int(st['fibre8'])}</td>
                <td class="r">{_fmt_int(st['power'])}</td>
                <td class="r">{_fmt_int(st['migration'])}</td>
                <td class="r">{_fmt_int(st['mobile'])}</td>
                <td class="r">{_fmt_int(st['assu'])}</td>
                <td class="r">{_fmt_int(st['presse'])}</td>
                <td></td>
                <td class="r">{_fmt_int(st['coopt'])}</td>
              </tr>
            </tfoot>
          </table>
          <div class="obj-sem">Obj BS Semaine : <b>{_fmt_num(st['obj_bs'], 1)}</b></div>
        """)

    axes_html = ""
    if fiche.axe_travail_1 or fiche.axe_travail_2:
        axes_html = f"""
        <div class="axes">
          <div><b>Axe de travail 1</b><br />{escape(fiche.axe_travail_1)}</div>
          <div><b>Axe de travail 2</b><br />{escape(fiche.axe_travail_2)}</div>
        </div>
        """

    _, bilan_html = _build_prod_bilan_footer(fiche)

    graph = _svg_bar_chart(
        "Contrats SFR",
        [
            ("Power 8", sum(r.power8 for r in fiche.prod_sfr), "#E31E24"),
            ("Fibre 8", sum(r.fibre8 for r in fiche.prod_sfr), "#FF9800"),
            ("Power", sum(r.power for r in fiche.prod_sfr), "#4CAF50"),
            ("Migration", sum(r.migration for r in fiche.prod_sfr), "#00BCD4"),
            ("Mobile", sum(r.mobile for r in fiche.prod_sfr), "#8B4513"),
        ],
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
  @page {{ size: A4 landscape; margin: 0.8cm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 7.5pt; color: #333; }}
  .header {{ display: flex; align-items: center; gap: 12px;
             border-bottom: 2px solid #17494E; padding-bottom: 6px;
             margin-bottom: 8px; }}
  .header img {{ height: 42px; }}
  .header h1 {{ font-size: 14pt; color: #17494E; margin: 0;
                flex: 1; text-align: center; }}
  .header .date {{ font-size: 9pt; color: #666; }}
  .title-doc {{ font-size: 10pt; font-weight: bold; text-align: center;
                margin: 2px 0 8px 0; }}
  .sem-title {{ background: #17494E; color: white; padding: 3px 6px;
                margin-top: 6px; font-weight: bold; font-size: 9pt; }}
  table.prod {{ width: 100%; border-collapse: collapse;
                table-layout: fixed; font-size: 6.5pt; }}
  table.prod th {{ background: #17494E; color: white; padding: 2px 1px;
                   font-weight: 600; font-size: 6pt; }}
  table.prod td {{ padding: 2px 1px; border-bottom: 1px solid #F0EDE5;
                   font-size: 6.5pt; }}
  table.prod tr.stot td {{ background: #F5F1E8; font-weight: bold;
                            border-top: 1px solid #17494E; }}
  .c {{ text-align: center; }}
  .r {{ text-align: right; }}
  .obj-sem {{ font-size: 8pt; color: #C00; padding: 3px; }}
  .axes {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
           margin: 8px 0; font-size: 8pt; }}
  .axes > div {{ border: 1px solid #D4C9A8; padding: 6px;
                 background: #FAFAF5; }}
  .bilan {{ float: left; width: 45%; margin-top: 6px; font-size: 8.5pt; }}
  .graph {{ float: right; width: 53%; margin-top: 6px; text-align: center; }}
  .bilan-title {{ font-weight: bold; color: #17494E; font-size: 10pt;
                  border-bottom: 1px solid #17494E; margin-bottom: 4px; }}
  .bilan-h {{ font-weight: bold; text-decoration: underline;
              margin-top: 4px; }}
  .bilan-row {{ padding: 1px 0; }}
  .pct {{ color: #888; }}
</style></head><body>

  <div class="header">
    {f'<img src="{logo}" />' if logo else ''}
    <h1>Bilan formation {escape(fiche.nom_prenom)}</h1>
    <div class="date">{today}</div>
  </div>

  <div class="title-doc">{escape(fiche.nom_prenom)}</div>

  {"".join(sections)}
  {axes_html}

  <div style="clear:both; margin-top: 10px;">
    {bilan_html}
    <div class="graph">{graph}</div>
  </div>

</body></html>
"""
    return _render_html_to_pdf(html)
