"""
S'Cool : generation du PDF Etat_ScoolAnalysePromo via WeasyPrint.

Transpose l'etat WinDev Etat_ScoolAnalysePromo :
  - Header : 'S'Cool - Analyse Promo - <libelle>' + date
  - Bandeau compteurs :
      * Recrutement : Presents / Retenus / JO
      * Bulletins edites : Intermediaire / Finaux
      * Resultats Promo : nb Prod / Livrable + Tx Livraison %
      * Resultats CQT Premium : Total realise / Obj Promo + Tx CQT %
  - Sous-etat 'Analyse Production' (TableEffectif) : par etape
      Periode / Date / NB Vend / nb Vend Prod / nb Fibre brut / nb Fibre
      HR / nb CQT Fibre / nb CQT HR / nb Mig Fibre / nb Mig HR /
      nb Mob Brut / nb Mob HR + ligne TOTAUX
  - Sous-etat 'Analyse Effectif' (Table_ReqStagaireFormation1) : par
      stagiaire
      NOM / PRENOM / DU / AU / En activite / Type sortie / Livrable /
      Nb Fibre brut / Nb Fibre HR / Nb CQT brut / Nb CQT HR /
      nb Mig Brut / nb Mig HR / Nb Mob Brut / NB Mob HR + ligne TOTAUX

Dependances : weasyprint (avec GTK3 Runtime sur Windows).
"""
from __future__ import annotations

import logging
from html import escape

from app.intranets.adm.schemas.scool_formation import AnalyseFormationResult

logger = logging.getLogger(__name__)


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _fmt_date(iso: str) -> str:
    if not iso or len(iso) < 10:
        return ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def _pourcent(num: int, den: int) -> str:
    if den <= 0:
        return "0,0 %"
    v = num / den * 100
    return f"{v:.1f} %".replace(".", ",")


# ---------------------------------------------------------------------
# Rendu HTML
# ---------------------------------------------------------------------

_CSS = """
@page {
  size: A4 landscape;
  margin: 12mm 10mm 15mm 10mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-size: 8pt;
    color: #666;
  }
}
* { box-sizing: border-box; }
body {
  font-family: Arial, sans-serif;
  font-size: 8pt;
  color: #17494E;
}
h1 { font-size: 14pt; margin: 0 0 4px 0; color: #17494E; }
h2 { font-size: 10pt; margin: 12px 0 4px 0; color: #17494E;
     border-bottom: 1px solid #8B7355; padding-bottom: 2px; }
.header {
  display: flex; justify-content: space-between;
  border-bottom: 2px solid #17494E; padding-bottom: 6px;
  margin-bottom: 8px;
}
.header .right { text-align: right; font-size: 8pt; color: #666; }
.compteurs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 6px; margin-bottom: 10px;
}
.compteurs .cell {
  background: #F5F5F0; border: 1px solid #E5E0D5;
  padding: 6px; border-radius: 3px;
}
.compteurs .cell .title {
  font-size: 7pt; color: #8B7355; text-transform: uppercase;
}
.compteurs .cell .value {
  font-weight: bold; color: #17494E; font-size: 9pt; margin-top: 2px;
}
.compteurs .cell .taux {
  display: inline-block; margin-left: 4px; padding: 1px 5px;
  border-radius: 3px; background: #ECF1F2; font-size: 8pt;
}
table {
  width: 100%; border-collapse: collapse; margin-top: 4px;
}
table th, table td {
  border: 1px solid #E5E0D5; padding: 3px 4px;
  text-align: right; white-space: nowrap;
}
table th {
  background: #17494E; color: white;
  font-size: 7.5pt; text-transform: uppercase;
}
table th.left, table td.left { text-align: left; }
table th.center, table td.center { text-align: center; }
tfoot td {
  font-weight: bold; background: #F5F5F0;
  border-top: 2px solid #8B7355;
}
"""


def _render_html(a: AnalyseFormationResult) -> str:
    tx_liv = _pourcent(a.total_livrable, a.jo)
    tx_cqt = _pourcent(a.total_cqt, a.obj_cqt)

    # Table Effectif : totaux
    tot_e = {
        "nb_vend": 0, "nb_vend_prod": 0,
        "nb_ctt_brut": 0, "nb_ctt_hr": 0,
        "nb_cqt": 0, "nb_cqt_hr": 0,
        "nb_mig": 0, "nb_mig_hr": 0,
        "nb_mob_brut": 0, "nb_mob_hr": 0,
    }
    for e in a.effectif:
        for k in tot_e:
            tot_e[k] += getattr(e, k, 0)

    # Table Stagiaires : totaux
    tot_s = {
        "nb_fibre_brut": 0, "nb_fibre_hr": 0,
        "nb_cqt_brut": 0, "nb_cqt_hr": 0,
        "nb_mig_brut": 0, "nb_mig_hr": 0,
        "nb_mob_brut": 0, "nb_mob_hr": 0,
    }
    nb_livrables_stag = 0
    for s in a.stagiaires:
        for k in tot_s:
            tot_s[k] += getattr(s, k, 0)
        if s.livrable:
            nb_livrables_stag += 1

    # Header
    html_header = f"""
    <div class="header">
      <div>
        <h1>S'Cool - Analyse Promo - {escape(a.intitule)}</h1>
        <div>Promo du <b>{_fmt_date(a.du)}</b> au <b>{_fmt_date(a.au)}</b>
             &nbsp;·&nbsp; nb Jours Terrain : <b>{a.nb_jours_terrain}</b>
             {"&nbsp;·&nbsp;<b style='color:#166534'>Formation Clôturée</b>" if a.formation_cloturee else ""}
        </div>
      </div>
    </div>"""

    # Compteurs
    html_compteurs = f"""
    <div class="compteurs">
      <div class="cell">
        <div class="title">Recrutement</div>
        <div class="value">
          {_fmt_int(a.presents)} présents · {_fmt_int(a.retenus)} retenus
          · {_fmt_int(a.jo)} JO
        </div>
      </div>
      <div class="cell">
        <div class="title">Bulletins édités</div>
        <div class="value">
          {_fmt_int(a.intermediaires)} intermédiaires
          · {_fmt_int(a.finaux)} finaux
        </div>
      </div>
      <div class="cell">
        <div class="title">Résultats Promo</div>
        <div class="value">
          {_fmt_int(a.total_prod)} nb Prod
          · {_fmt_int(a.total_livrable)} livrable
          <span class="taux">Tx Livr. {tx_liv}</span>
        </div>
      </div>
      <div class="cell">
        <div class="title">Résultats CQT Premium</div>
        <div class="value">
          {_fmt_int(a.total_cqt)} / {_fmt_int(a.obj_cqt)}
          <span class="taux">Tx CQT {tx_cqt}</span>
        </div>
      </div>
    </div>"""

    # Table Effectif
    lignes_e = "".join(
        f"""<tr>
          <td class="left">{escape(e.periode)}</td>
          <td>{_fmt_date(e.date)}</td>
          <td>{_fmt_int(e.nb_vend)}</td>
          <td>{_fmt_int(e.nb_vend_prod)}</td>
          <td>{_fmt_int(e.nb_ctt_brut)}</td>
          <td>{_fmt_int(e.nb_ctt_hr)}</td>
          <td>{_fmt_int(e.nb_cqt)}</td>
          <td>{_fmt_int(e.nb_cqt_hr)}</td>
          <td>{_fmt_int(e.nb_mig)}</td>
          <td>{_fmt_int(e.nb_mig_hr)}</td>
          <td>{_fmt_int(e.nb_mob_brut)}</td>
          <td>{_fmt_int(e.nb_mob_hr)}</td>
        </tr>"""
        for e in a.effectif
    )
    tfoot_e = f"""<tr>
        <td class="left" colspan="2">TOTAUX :</td>
        <td>{_fmt_int(tot_e['nb_vend'])}</td>
        <td>{_fmt_int(tot_e['nb_vend_prod'])}</td>
        <td>{_fmt_int(tot_e['nb_ctt_brut'])}</td>
        <td>{_fmt_int(tot_e['nb_ctt_hr'])}</td>
        <td>{_fmt_int(tot_e['nb_cqt'])}</td>
        <td>{_fmt_int(tot_e['nb_cqt_hr'])}</td>
        <td>{_fmt_int(tot_e['nb_mig'])}</td>
        <td>{_fmt_int(tot_e['nb_mig_hr'])}</td>
        <td>{_fmt_int(tot_e['nb_mob_brut'])}</td>
        <td>{_fmt_int(tot_e['nb_mob_hr'])}</td>
      </tr>"""

    html_effectif = f"""
    <h2>Analyse Production</h2>
    <table>
      <thead>
        <tr>
          <th class="left">Période</th>
          <th>Date</th>
          <th>NB Vend</th>
          <th>nb Vend Prod</th>
          <th>nb Fibre brut</th>
          <th>nb Fibre HR*</th>
          <th>nb CQT Fibre</th>
          <th>nb CQT HR*</th>
          <th>nb Mig Fibre</th>
          <th>nb Mig HR*</th>
          <th>nb Mob Brut</th>
          <th>nb Mob HR*</th>
        </tr>
      </thead>
      <tbody>{lignes_e}</tbody>
      <tfoot>{tfoot_e}</tfoot>
    </table>"""

    # Table Stagiaires
    lignes_s = "".join(
        f"""<tr>
          <td class="left">{escape(s.nom)}</td>
          <td class="left">{escape(s.prenom)}</td>
          <td>{_fmt_date(s.du)}</td>
          <td>{_fmt_date(s.au)}</td>
          <td class="center">{'X' if s.en_activite else ''}</td>
          <td class="left">{escape(s.type_sortie or '')}</td>
          <td class="center">{'X' if s.livrable else ''}</td>
          <td>{_fmt_int(s.nb_fibre_brut)}</td>
          <td>{_fmt_int(s.nb_fibre_hr)}</td>
          <td>{_fmt_int(s.nb_cqt_brut)}</td>
          <td>{_fmt_int(s.nb_cqt_hr)}</td>
          <td>{_fmt_int(s.nb_mig_brut)}</td>
          <td>{_fmt_int(s.nb_mig_hr)}</td>
          <td>{_fmt_int(s.nb_mob_brut)}</td>
          <td>{_fmt_int(s.nb_mob_hr)}</td>
        </tr>"""
        for s in a.stagiaires
    )
    tfoot_s = f"""<tr>
        <td class="left" colspan="6">TOTAUX :</td>
        <td class="center">{_fmt_int(nb_livrables_stag)}</td>
        <td>{_fmt_int(tot_s['nb_fibre_brut'])}</td>
        <td>{_fmt_int(tot_s['nb_fibre_hr'])}</td>
        <td>{_fmt_int(tot_s['nb_cqt_brut'])}</td>
        <td>{_fmt_int(tot_s['nb_cqt_hr'])}</td>
        <td>{_fmt_int(tot_s['nb_mig_brut'])}</td>
        <td>{_fmt_int(tot_s['nb_mig_hr'])}</td>
        <td>{_fmt_int(tot_s['nb_mob_brut'])}</td>
        <td>{_fmt_int(tot_s['nb_mob_hr'])}</td>
      </tr>"""

    html_stagiaires = f"""
    <h2>Analyse Effectif</h2>
    <table>
      <thead>
        <tr>
          <th class="left">NOM</th>
          <th class="left">PRÉNOM</th>
          <th>DU</th>
          <th>AU</th>
          <th>En activité</th>
          <th class="left">Type de sortie</th>
          <th>Livrable</th>
          <th>Nb Fibre brut</th>
          <th>Nb Fibre HR*</th>
          <th>Nb CQT brut</th>
          <th>Nb CQT HR*</th>
          <th>nb Mig Brut</th>
          <th>nb Mig HR*</th>
          <th>Nb Mob Brut</th>
          <th>NB Mob HR*</th>
        </tr>
      </thead>
      <tbody>{lignes_s}</tbody>
      <tfoot>{tfoot_s}</tfoot>
    </table>
    <p style="font-size:7pt; color:#B91C1C; font-style:italic; margin-top:4px;">
      * HR : Hors Rejet
    </p>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
{html_header}
{html_compteurs}
{html_effectif}
{html_stagiaires}
</body></html>"""


def build_analyse_pdf(a: AnalyseFormationResult) -> bytes:
    """Genere le PDF de l'analyse d'une formation.

    Args:
        a : resultat d'analyse (schemas.AnalyseFormationResult).

    Returns:
        bytes du PDF.

    Raises:
        RuntimeError : si WeasyPrint n'est pas installe.
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint indisponible : "
            "installer weasyprint + GTK3 Runtime.",
        ) from e

    html = _render_html(a)
    return HTML(string=html).write_pdf()
