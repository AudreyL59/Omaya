"""Generation du PDF EtatPrevRecUnique (impression d'une session de
prevision de recrutement, format paysage A4).

WeasyPrint en import lazy (lib optionnelle, cf. memoire
feedback_optional_deps_lazy.md).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


def _fmt(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    return d.strftime("%d/%m/%Y")


def _q(s: str) -> str:
    """HTML escape minimal."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_contenu_mail_etat(id_etat: int) -> str:
    """Retourne le contenu_mail (template HTML) associe a l'etat."""
    if not id_etat:
        return ""
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT contenu_mail FROM recrutement.pgt_prev_recrut_etat
            WHERE id_prev_recrut_etat = ?""",
        (int(id_etat),),
    )
    return _str(r.get("contenu_mail")) if r else ""


def build_pdf_prev_rec(id_prev: int) -> Optional[bytes]:
    """Construit le PDF de la fiche prevision. Retourne bytes ou None
    si introuvable.
    """
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT p.id_prevision_recrut,
                  p.idorganigramme, p.date_session, p.date_butoire,
                  p.id_cv_lieu_rdv, p.id_communes_france,
                  p.potentiel_accueil, p.nb_prod, p.taille_session,
                  p.coopt_smoins1, p.coopt_jmoins2,
                  p.sourcing_smoins1, p.sourcing_jmoins2,
                  p.nb_coopt_mini, p.nb_sourcing_mini,
                  p.obj_coopt, p.obj_sourcing,
                  p.commentaire,
                  o.lib_orga,
                  e.lib_etat,
                  l.lib_lieu,
                  c.nom_ville, c.code_postal
             FROM recrutement.pgt_prev_recrut p
             LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = p.idorganigramme
             LEFT JOIN recrutement.pgt_prev_recrut_etat e
                    ON e.id_prev_recrut_etat = p.id_prev_recrut_etat
             LEFT JOIN recrutement.pgt_cv_lieu_rdv l
                    ON l.id_cv_lieu_rdv = p.id_cv_lieu_rdv
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = p.id_communes_france
            WHERE p.id_prevision_recrut = ?""",
        (int(id_prev),),
    )
    if not r:
        return None

    today = date.today().strftime("%d/%m/%Y")
    equipe = _q(_str(r.get("lib_orga")))
    lieu = _q(_str(r.get("lib_lieu")))
    etat = _q(_str(r.get("lib_etat")))
    commentaire = _q(_str(r.get("commentaire")))

    # Cellules colorees rouge si sous le mini (cf PDF de reference)
    def _col(val: int, mini: int) -> str:
        return "color:#dc2626;" if val < mini else "color:#111;"

    cs1 = _int(r.get("coopt_smoins1"))
    cj2 = _int(r.get("coopt_jmoins2"))
    ss1 = _int(r.get("sourcing_smoins1"))
    sj2 = _int(r.get("sourcing_jmoins2"))
    mini_coopt = _int(r.get("nb_coopt_mini"))
    mini_src = _int(r.get("nb_sourcing_mini"))
    obj_c = _int(r.get("obj_coopt"))
    obj_s = _int(r.get("obj_sourcing"))

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><style>
@page {{ size: A4 landscape; margin: 1.5cm; @bottom-right {{ content: counter(page) "/" counter(pages); font-size: 9pt; color: #666; }} }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #111; }}
.header {{ display: flex; align-items: center; margin-bottom: 1.5em; }}
.header .logo {{ width: 60px; opacity: 0.3; font-size: 30pt; }}
.header h1 {{ flex: 1; text-align: center; font-size: 18pt; margin: 0; font-weight: bold; }}
.header .date {{ font-size: 10pt; }}
table {{ width: 100%; border-collapse: collapse; font-size: 8pt; }}
thead tr.groups th {{ background: #f3f4f6; border-bottom: 1px solid #e5e7eb; padding: 4px; font-weight: bold; }}
thead tr.cols th {{ background: #f9fafb; border-bottom: 2px solid #93c5fd; padding: 6px 4px; font-weight: normal; color: #6b7280; }}
tbody td {{ padding: 8px 4px; text-align: center; vertical-align: middle; }}
.left {{ text-align: left; }}
.right {{ text-align: right; }}
</style></head><body>

<div class="header">
  <div class="logo">&#9737;</div>
  <h1>Prévision de recrutement</h1>
  <div class="date">{today}</div>
</div>

<table>
  <thead>
    <tr class="groups">
      <th colspan="7"></th>
      <th colspan="4">Cooptation</th>
      <th colspan="4">Sourcing</th>
      <th colspan="2"></th>
    </tr>
    <tr class="cols">
      <th>Equipe</th>
      <th>Date Session</th>
      <th>Date Butoire</th>
      <th>Lieu Entretien</th>
      <th>Potentiel<br>d'Accueil</th>
      <th>NB<br>Prods</th>
      <th>Taille<br>Session</th>
      <th>S-1</th><th>J-2</th><th>Minimun</th><th>Objectif</th>
      <th>S-1</th><th>J-2 :</th><th>Minimun</th><th>Objectif</th>
      <th>Etat session</th>
      <th>Commentaire</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="left">{equipe}</td>
      <td>{_fmt(r.get('date_session'))}</td>
      <td>{_fmt(r.get('date_butoire'))}</td>
      <td class="left">{lieu}</td>
      <td>{_int(r.get('potentiel_accueil')) or ''}</td>
      <td>{_int(r.get('nb_prod')) or ''}</td>
      <td>{_int(r.get('taille_session')) or ''}</td>
      <td style="{_col(cs1, mini_coopt)}">{cs1}</td>
      <td style="{_col(cj2, mini_coopt)}">{cj2}</td>
      <td>{mini_coopt}</td>
      <td>{obj_c}</td>
      <td style="{_col(ss1, mini_src)}">{ss1}</td>
      <td style="{_col(sj2, mini_src)}">{sj2}</td>
      <td>{mini_src}</td>
      <td>{obj_s}</td>
      <td>{etat}</td>
      <td class="left">{commentaire}</td>
    </tr>
  </tbody>
</table>

</body></html>"""

    from weasyprint import HTML  # noqa: PLC0415
    return HTML(string=html).write_pdf()
