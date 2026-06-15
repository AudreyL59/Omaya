"""
Etats d'impression de la fiche salarie ADM.

Transposition des etats WinDev :
  - Etat_PochetteSalarie  : page principale avec photo + identite + societe
                            + contrat + responsable + coordonnees + urgence
  - EtatAbsencesSalarie   : liste groupee par AnneeConge + Type d'absence

Le bouton 'Imprimer' (clic principal) genere uniquement la Pochette.
Le menu deroulant 'Pochette + Absences' fusionne les 2 (cf. WinDev :
PDFFusionne via le clic flèche).

PDF via WeasyPrint (HTML/CSS), fusion via pypdf. Photos encodees en
data URL base64 pour eviter l'I/O disque.
"""

from __future__ import annotations

import base64
import io
import sys
import traceback
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _fr_date(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _capitalize_first(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def _civilite(civ: int) -> str:
    return {1: "Mr", 2: "Mme"}.get(int(civ or 0), "Mr")


def _esc(v: Any) -> str:
    s = _str(v)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _detect_mime(b: bytes) -> str:
    """Detecte le format reel d'une image par signature magique.

    PG renvoie souvent du JPEG (photos salarie) ou du PNG (gimmick).
    WinDev pouvait stocker du BMP brut. On detecte pour eviter le mime
    type incorrect (refus de WeasyPrint)."""
    if len(b) >= 8 and b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(b) >= 3 and b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(b) >= 6 and (b[:6] == b"GIF87a" or b[:6] == b"GIF89a"):
        return "image/gif"
    if len(b) >= 2 and b[:2] == b"BM":
        return "image/bmp"
    if len(b) >= 4 and b[:4] == b"RIFF" and len(b) >= 12 and b[8:12] == b"WEBP":
        return "image/webp"
    # Fallback : laisse WeasyPrint detecter via l'entete (souvent OK
    # avec octet-stream)
    return "image/png"


def _img_data_url(b: Any, mime: str | None = None) -> str:
    """Convertit un bytea PG en data URL (string vide si pas de donnee).

    Si mime est None, detecte le format reel via signature magique."""
    if b is None:
        return ""
    if isinstance(b, memoryview):
        b = bytes(b)
    if not isinstance(b, (bytes, bytearray)) or not b:
        return ""
    raw = bytes(b)
    actual_mime = mime or _detect_mime(raw)
    try:
        return f"data:{actual_mime};base64,{base64.b64encode(raw).decode('ascii')}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Chargement des donnees
# ---------------------------------------------------------------------------


def _load_pochette_data(id_salarie: int) -> dict:
    """Charge tout ce qu'il faut pour la Pochette (1 grosse requete +
    quelques resolutions par cle)."""
    db = get_pg_connection("rh")

    sal = db.query_one(
        """SELECT s.id_salarie, s.civilite, s.nom, s.prenom, s.sexe,
                  s.nationalite, s.date_naiss, s.lieu_naiss, s.dep_naiss,
                  s.num_ss, s.cpam, s.num_cin, s.travailleur_handi,
                  s.photo,
                  c.adresse1, c.adresse2, c.cp, c.ville,
                  c.tel_fixe, c.tel_mob, c.mail,
                  c.urg_nom, c.urg_lien, c.urg_tel,
                  e.date_debut, e.date_anciennete, e.date_fin_per_essai,
                  e.id_type_poste, e.id_type_ctt, e.id_type_horaire,
                  e.id_ste,
                  ss.date_sortie_demandee, ss.date_sortie_reelle,
                  ss.id_type_sortie
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_coordonnees c ON c.id_salarie = s.id_salarie
             LEFT JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
             LEFT JOIN rh.pgt_salarie_sortie ss ON ss.id_salarie = s.id_salarie
            WHERE s.id_salarie = ?
            LIMIT 1""",
        (int(id_salarie),),
    ) or {}

    # Resolutions libelles + societe + organigramme + responsable
    id_ste = _int(sal.get("id_ste"))
    soc = (
        db.query_one(
            """SELECT rs_interne, raison_sociale, guimmick
                 FROM rh.pgt_societe WHERE id_ste = ? LIMIT 1""",
            (id_ste,),
        )
        if id_ste
        else {}
    ) or {}

    lib_poste = ""
    if sal.get("id_type_poste"):
        r = db.query_one(
            """SELECT lib_poste FROM rh.pgt_type_poste
                WHERE id_type_poste = ? LIMIT 1""",
            (int(sal["id_type_poste"]),),
        )
        lib_poste = _str((r or {}).get("lib_poste"))

    lib_ctt = ""
    if sal.get("id_type_ctt"):
        r = db.query_one(
            """SELECT intitule FROM rh.pgt_type_ctt_travail
                WHERE id_type_ctt = ? LIMIT 1""",
            (int(sal["id_type_ctt"]),),
        )
        lib_ctt = _str((r or {}).get("intitule"))

    lib_horaire = ""
    if sal.get("id_type_horaire"):
        r = db.query_one(
            """SELECT lib_horaire FROM rh.pgt_type_horaire_travail
                WHERE id_type_horaire = ? LIMIT 1""",
            (int(sal["id_type_horaire"]),),
        )
        lib_horaire = _str((r or {}).get("lib_horaire"))

    lib_sortie = ""
    if sal.get("id_type_sortie"):
        r = db.query_one(
            """SELECT lib_sortie FROM rh.pgt_type_sortie_salarie
                WHERE id_type_sortie = ? LIMIT 1""",
            (int(sal["id_type_sortie"]),),
        )
        lib_sortie = _str((r or {}).get("lib_sortie"))

    # Equipe + responsable (1er DA/DR rattache au meme orga ou parent)
    lib_equipe = ""
    lib_resp = ""
    orga_row = db.query_one(
        """SELECT o.idorganigramme, o.lib_orga, o.id_parent
             FROM rh.pgt_salarie_organigramme so
             LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
            WHERE so.id_salarie = ?
              AND COALESCE(so.aff_actif, FALSE) = TRUE
              AND so.modif_elem NOT LIKE '%suppr%'
            ORDER BY so.date_debut DESC NULLS LAST
            LIMIT 1""",
        (int(id_salarie),),
    )
    if orga_row:
        lib_orga = _str(orga_row.get("lib_orga"))
        parent_row = None
        if orga_row.get("id_parent"):
            parent_row = db.query_one(
                """SELECT lib_orga FROM rh.pgt_organigramme
                    WHERE idorganigramme = ? LIMIT 1""",
                (int(orga_row["id_parent"]),),
            )
        lib_parent = _str((parent_row or {}).get("lib_orga"))
        lib_equipe = f"{lib_parent} => {lib_orga}" if lib_parent else lib_orga

        # Responsable : 1er DA/DR (resp_equipe=true) sur cet orga ou parent
        id_da_row = db.query_one(
            """SELECT s2.nom, s2.prenom
                 FROM rh.pgt_salarie_organigramme so2
                 INNER JOIN rh.pgt_salarie_embauche se2
                   ON se2.id_salarie = so2.id_salarie
                 INNER JOIN rh.pgt_salarie s2 ON s2.id_salarie = so2.id_salarie
                WHERE (so2.idorganigramme = ?
                       OR so2.idorganigramme = ?)
                  AND COALESCE(so2.aff_actif, FALSE) = TRUE
                  AND so2.modif_elem NOT LIKE '%suppr%'
                  AND COALESCE(se2.resp_equipe, FALSE) = TRUE
                  AND so2.id_salarie <> ?
                ORDER BY so2.date_debut DESC NULLS LAST
                LIMIT 1""",
            (
                int(orga_row.get("idorganigramme") or 0),
                int(orga_row.get("id_parent") or 0),
                int(id_salarie),
            ),
        )
        if id_da_row:
            lib_resp = (
                _str(id_da_row.get("nom"))
                + " "
                + _capitalize_first(_str(id_da_row.get("prenom")))
            ).strip()

    return {
        "sal": sal,
        "soc": soc,
        "lib_poste": lib_poste,
        "lib_ctt": lib_ctt,
        "lib_horaire": lib_horaire,
        "lib_sortie": lib_sortie,
        "lib_equipe": lib_equipe,
        "lib_resp": lib_resp,
    }


def _load_absences_data(id_salarie: int) -> dict:
    """Liste les absences groupees par AnneeConge puis Type d'absence.

    Reprend la requete WinDev (TypeAbsence JOIN absence + tri DESC/ASC/DESC).
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT a.id_type_absence, a.id_absence,
                  a.date_debut, a.date_fin,
                  a.nbj, a.nbj_ouvres, a.nb_samedi,
                  a.periode AS annee_conge,
                  ta.lib_absence
             FROM rh.pgt_absence a
             INNER JOIN rh.pgt_type_absence ta
               ON ta.id_type_absence = a.id_type_absence
            WHERE a.id_salarie = ?
              AND (a.modif_elem IS NULL OR a.modif_elem NOT LIKE '%suppr%')
            ORDER BY a.periode DESC NULLS LAST,
                     a.id_type_absence ASC,
                     a.date_debut DESC""",
        (int(id_salarie),),
    )

    # Groupement : Periode -> Type -> lignes + totaux
    groups: list[dict] = []
    cur_per: dict | None = None
    cur_typ: dict | None = None
    for r in rows or []:
        per = _str(r.get("annee_conge")) or "—"
        typ_id = int(r.get("id_type_absence") or 0)
        if cur_per is None or cur_per["periode"] != per:
            cur_per = {
                "periode": per,
                "types": [],
                "tot_nbj": 0,
                "tot_nbj_ouvres": 0,
                "tot_nb_samedi": 0,
            }
            groups.append(cur_per)
            cur_typ = None
        if cur_typ is None or cur_typ["id"] != typ_id:
            cur_typ = {
                "id": typ_id,
                "lib": _str(r.get("lib_absence")),
                "rows": [],
                "tot_nbj": 0,
                "tot_nbj_ouvres": 0,
                "tot_nb_samedi": 0,
            }
            cur_per["types"].append(cur_typ)
        nbj = int(r.get("nbj") or 0)
        nbjo = int(r.get("nbj_ouvres") or 0)
        nbs = int(r.get("nb_samedi") or 0)
        cur_typ["rows"].append({
            "date_debut": _fr_date(r.get("date_debut")),
            "date_fin": _fr_date(r.get("date_fin")),
            "nbj": nbj,
            "nbj_ouvres": nbjo,
            "nb_samedi": nbs,
        })
        cur_typ["tot_nbj"] += nbj
        cur_typ["tot_nbj_ouvres"] += nbjo
        cur_typ["tot_nb_samedi"] += nbs
        cur_per["tot_nbj"] += nbj
        cur_per["tot_nbj_ouvres"] += nbjo
        cur_per["tot_nb_samedi"] += nbs

    return {"groups": groups, "total_rows": len(rows or [])}


# ---------------------------------------------------------------------------
# Rendu HTML
# ---------------------------------------------------------------------------


CSS_COMMON = """
@page { size: A4 portrait; margin: 15mm 12mm 15mm 12mm; }
* { box-sizing: border-box; }
body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10pt;
  color: #1e293b;
  margin: 0;
}
h1 { font-size: 18pt; margin: 0 0 10mm 0; text-align: center; color: #17494E; }
h2 { font-size: 12pt; margin: 6mm 0 2mm 0; color: #17494E; }
.bloc { border: 1px solid #cbd5e1; border-radius: 4px; padding: 3mm; margin-bottom: 3mm; }
.row { display: flex; gap: 6mm; }
.col { flex: 1; }
.label { color: #64748b; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.5px; }
.value { font-weight: 600; font-size: 10pt; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 2mm 3mm; font-size: 9pt; text-align: left; }
th { background: #EFE9E7; color: #4E1D17; }
tr.total td { font-weight: 700; background: #F7EEEB; }
tr.grand-total td { font-weight: 700; background: #E5DDDC; }
img.photo { width: 28mm; height: 35mm; object-fit: cover; border: 1px solid #cbd5e1; }
img.gimmick { max-width: 50mm; max-height: 20mm; object-fit: contain; }
"""


def _render_pochette_html(d: dict) -> str:
    sal = d["sal"]
    soc = d["soc"]
    titre = (
        f"{_civilite(sal.get('civilite'))} "
        f"{_esc(sal.get('nom'))} "
        f"{_esc(_capitalize_first(_str(sal.get('prenom'))))}"
    )
    photo_url = _img_data_url(sal.get("photo"))
    gimmick_url = _img_data_url(soc.get("guimmick"))

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><style>{CSS_COMMON}</style></head>
<body>

<div style="display:flex; align-items:center; gap:5mm; margin-bottom: 6mm;">
  <div style="flex:0 0 28mm;">
    {'<img class="photo" src="' + photo_url + '"/>' if photo_url else ''}
  </div>
  <div style="flex:1; text-align:center;">
    <h1>{titre}</h1>
    <div class="value">{_esc(soc.get('rs_interne') or soc.get('raison_sociale'))}</div>
  </div>
  <div style="flex:0 0 50mm; text-align:right;">
    {'<img class="gimmick" src="' + gimmick_url + '"/>' if gimmick_url else ''}
  </div>
</div>

<div class="bloc">
  <h2>Identité</h2>
  <div class="row">
    <div class="col"><div class="label">Sexe (H/F)</div><div class="value">{_esc(sal.get('sexe'))}</div></div>
    <div class="col"><div class="label">Nationalité</div><div class="value">{_esc(sal.get('nationalite'))}</div></div>
    <div class="col"><div class="label">Travailleur handicapé</div><div class="value">{'Oui' if sal.get('travailleur_handi') else 'Non'}</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col"><div class="label">Né(e) le</div><div class="value">{_fr_date(sal.get('date_naiss'))}</div></div>
    <div class="col"><div class="label">à</div><div class="value">{_esc(sal.get('lieu_naiss'))} ({_int(sal.get('dep_naiss')) or ''})</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col"><div class="label">N° Sécu Soc.</div><div class="value">{_esc(sal.get('num_ss'))}</div></div>
    <div class="col"><div class="label">CPAM</div><div class="value">{_esc(sal.get('cpam'))}</div></div>
    <div class="col"><div class="label">N° CIN</div><div class="value">{_esc(sal.get('num_cin'))}</div></div>
  </div>
</div>

<div class="bloc">
  <h2>Emploi</h2>
  <div class="row">
    <div class="col"><div class="label">Poste</div><div class="value">{_esc(d['lib_poste'])}</div></div>
    <div class="col"><div class="label">Type Ctt</div><div class="value">{_esc(d['lib_ctt'])}</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col"><div class="label">Responsable</div><div class="value">{_esc(d['lib_resp'])}</div></div>
    <div class="col"><div class="label">Horaire</div><div class="value">{_esc(d['lib_horaire'])}</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col" style="flex:2;"><div class="label">Équipe</div><div class="value">{_esc(d['lib_equipe'])}</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col"><div class="label">Date Début</div><div class="value">{_fr_date(sal.get('date_debut'))}</div></div>
    <div class="col"><div class="label">Fin période d'essai</div><div class="value">{_fr_date(sal.get('date_fin_per_essai'))}</div></div>
    <div class="col"><div class="label">Date Ancienneté</div><div class="value">{_fr_date(sal.get('date_anciennete'))}</div></div>
  </div>
  <div class="row" style="margin-top:2mm;">
    <div class="col"><div class="label">Date Sortie Demandée</div><div class="value">{_fr_date(sal.get('date_sortie_demandee'))}</div></div>
    <div class="col"><div class="label">Date Sortie Réelle</div><div class="value">{_fr_date(sal.get('date_sortie_reelle'))}</div></div>
    <div class="col"><div class="label">Type de sortie</div><div class="value">{_esc(d['lib_sortie'])}</div></div>
  </div>
</div>

<div class="row">
  <div class="col bloc">
    <h2>Coordonnées postales &amp; téléphoniques</h2>
    <div class="label">Adresse</div>
    <div class="value">{_esc(sal.get('adresse1'))}</div>
    <div class="value">{_esc(sal.get('adresse2'))}</div>
    <div class="value">{_esc(sal.get('cp'))} {_esc(sal.get('ville'))}</div>
    <div class="row" style="margin-top:3mm;">
      <div class="col"><div class="label">Tél fixe</div><div class="value">{_esc(sal.get('tel_fixe'))}</div></div>
      <div class="col"><div class="label">Tél mobile</div><div class="value">{_esc(sal.get('tel_mob'))}</div></div>
    </div>
    <div class="label" style="margin-top:2mm;">Courriel</div>
    <div class="value">{_esc(sal.get('mail'))}</div>
  </div>

  <div class="col bloc">
    <h2>Personne à contacter en cas d'urgence</h2>
    <div class="row">
      <div class="col"><div class="label">Nom du contact</div><div class="value">{_esc(sal.get('urg_nom'))}</div></div>
      <div class="col"><div class="label">Lien de parenté</div><div class="value">{_esc(sal.get('urg_lien'))}</div></div>
    </div>
    <div class="row" style="margin-top:2mm;">
      <div class="col"><div class="label">Tél du contact</div><div class="value">{_esc(sal.get('urg_tel'))}</div></div>
    </div>
  </div>
</div>

<div style="margin-top: 6mm; text-align: right; font-size: 8pt; color: #94a3b8;">
  Édité le {datetime.now().strftime('%d/%m/%Y')}
</div>
</body></html>"""


def _render_absences_html(id_salarie: int, d: dict) -> str:
    # Recupere le nom dans la 1ere ligne dispo ou via une requete
    pochette = _load_pochette_data(id_salarie)
    sal = pochette["sal"]
    titre = (
        f"{_esc(sal.get('nom'))} {_esc(_capitalize_first(_str(sal.get('prenom'))))}"
    )

    rows_html = []
    for g in d["groups"]:
        rows_html.append(
            f'<tr style="background:#F0E6E2;"><td colspan="5"><strong>Période {g["periode"]}</strong></td></tr>'
        )
        for t in g["types"]:
            rows_html.append(
                f'<tr style="background:#FBF6F4;"><td colspan="5">— <em>{_esc(t["lib"])}</em></td></tr>'
            )
            for r in t["rows"]:
                rows_html.append(
                    f"<tr>"
                    f"<td>{_esc(r['date_debut'])}</td>"
                    f"<td>{_esc(r['date_fin'])}</td>"
                    f"<td style='text-align:right'>{r['nbj']}</td>"
                    f"<td style='text-align:right'>{r['nbj_ouvres']}</td>"
                    f"<td style='text-align:right'>{r['nb_samedi']}</td>"
                    f"</tr>"
                )
            rows_html.append(
                f"<tr class='total'>"
                f"<td colspan='2'>Total {_esc(t['lib'])}</td>"
                f"<td style='text-align:right'>{t['tot_nbj']}</td>"
                f"<td style='text-align:right'>{t['tot_nbj_ouvres']}</td>"
                f"<td style='text-align:right'>{t['tot_nb_samedi']}</td>"
                f"</tr>"
            )
        rows_html.append(
            f"<tr class='grand-total'>"
            f"<td colspan='2'>Total période {g['periode']}</td>"
            f"<td style='text-align:right'>{g['tot_nbj']}</td>"
            f"<td style='text-align:right'>{g['tot_nbj_ouvres']}</td>"
            f"<td style='text-align:right'>{g['tot_nb_samedi']}</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><style>{CSS_COMMON}</style></head>
<body>
<h1>Liste des absences</h1>
<h2 style="text-align:center;">{titre}</h2>

<table>
  <thead>
    <tr>
      <th>Du</th>
      <th>Au</th>
      <th style="text-align:right">Nb Jours</th>
      <th style="text-align:right">Nb Jours ouvrés<br/><span style="font-weight:normal;font-size:7pt;">(hors samedi)</span></th>
      <th style="text-align:right">Nb Samedi</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows_html) or '<tr><td colspan="5" style="text-align:center; font-style:italic; color:#94a3b8;">Aucune absence enregistrée.</td></tr>'}
  </tbody>
</table>

<div style="margin-top: 4mm; font-size: 9pt;">
  Nombre de lignes : <strong>{d['total_rows']}</strong>
</div>

<div style="margin-top: 6mm; text-align: right; font-size: 8pt; color: #94a3b8;">
  Édité le {datetime.now().strftime('%d/%m/%Y')}
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Generation PDF (lazy import WeasyPrint)
# ---------------------------------------------------------------------------


def generate_pochette_pdf(id_salarie: int) -> bytes:
    data = _load_pochette_data(id_salarie)
    html = _render_pochette_html(data)
    from weasyprint import HTML  # noqa: PLC0415
    return HTML(string=html).write_pdf()


def generate_absences_pdf(id_salarie: int) -> bytes:
    data = _load_absences_data(id_salarie)
    html = _render_absences_html(id_salarie, data)
    from weasyprint import HTML  # noqa: PLC0415
    return HTML(string=html).write_pdf()


def generate_pochette_complete_pdf(id_salarie: int) -> bytes:
    """Pochette + Absences fusionnees (cf. WinDev PDFFusionne)."""
    pdf_p = generate_pochette_pdf(id_salarie)
    pdf_a = generate_absences_pdf(id_salarie)
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        writer = PdfWriter()
        for raw in (pdf_p, pdf_a):
            reader = PdfReader(io.BytesIO(raw))
            for p in reader.pages:
                writer.add_page(p)
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return pdf_p  # fallback : juste la pochette


def filename_for(id_salarie: int, suffix: str = "") -> str:
    """Nom de fichier suggere pour le PDF."""
    db = get_pg_connection("rh")
    row = db.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
        (int(id_salarie),),
    ) or {}
    nom = _str(row.get("nom")).replace(" ", "_") or str(id_salarie)
    prenom = _capitalize_first(_str(row.get("prenom"))).replace(" ", "_")
    base = f"Pochette_{nom}_{prenom}" if prenom else f"Pochette_{nom}"
    return f"{base}{suffix}.pdf"
