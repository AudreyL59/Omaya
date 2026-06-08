"""
SDTC : generation du PDF EtatSTC_RecapPROD via WeasyPrint.

Transpose l'etat WinDev EtatSTC_RecapPROD :
  - Header : logo societe + titre 'SOLDE DE TOUT COMPTE - Recap PRODUCTION'
  - NOM Salarie // Raison sociale
  - 7 infos chiffrees (3 colonnes x 3 lignes) :
      Nombre Total Pts / Nombre Total Ctts / Bareme Pts
      CA Pts / CA Valeurs / CA STC
      Nombre TR
  - Sous-etat 'Solde de tout compte' (TableProduitSTC : Produit / QTE / Nb Pts / Valeur)
  - Commentaires (TEXTE3)
  - Sous-etat 'Recap PROD Globale en NB de CTTS' (TableRecapProd)
  - Sous-etat 'Recap PROD Globale en NB de PTS' (TableRecapProdPts)
  - Footer : Adresse societe + Page N/Total

Dependances : weasyprint (avec GTK3 Runtime sur Windows).
"""

from __future__ import annotations

import base64
from html import escape

from weasyprint import HTML

from app.core.database.pg import get_pg_connection


def _str(v) -> str:
    return "" if v is None else str(v)


def _fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _fmt_eur(v) -> str:
    try:
        return f"{float(v):,.2f} €".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return "0,00 €"


def _load_societe(id_ste: int) -> dict:
    if not id_ste:
        return {}
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT raison_sociale, adresse1, cp, ville, siret, logo
           FROM rh.pgt_societe WHERE id_ste = ?""",
        (int(id_ste),),
    )
    if not row:
        return {}
    logo_b64 = ""
    blob = row.get("logo")
    if blob and isinstance(blob, (bytes, bytearray, memoryview)):
        try:
            logo_b64 = base64.b64encode(bytes(blob)).decode("ascii")
        except Exception:
            logo_b64 = ""
    return {
        "raison_sociale": _str(row.get("raison_sociale")),
        "adresse1": _str(row.get("adresse1")),
        "cp": _str(row.get("cp")),
        "ville": _str(row.get("ville")),
        "siret": _str(row.get("siret")),
        "logo_b64": logo_b64,
    }


# --- Agregations type WinDev ---------------------------------------------

_PRESS_NAMES = {"TELE 7 JOUR", "ELLE", "PARIS MATCH"}

_TYPE_KEYS = [
    ("temporaire", "Temporaire", ["TEMPORAIRE"]),
    ("attente_ope", "En Attente Opé", ["EN ATTENTE OP"]),
    ("rejets", "Rejets", ["REJET", "ANOMALIE"]),
    ("resiliation", "Résiliation", ["RESILIATION", "RÉSILIATION"]),
    ("valide_paye", "Validé-payé", ["VALID"]),
    ("decommission", "Décommission", ["DECOMMISSION", "DÉCOMMISSION"]),
]


def _normalize_nom_produit(lib_produit: str) -> str:
    nom = (lib_produit or "").split("(", 1)[0].strip()
    if nom.upper() in _PRESS_NAMES:
        return "HACHETTE"
    return nom


def _match_type_etat(lib: str) -> str | None:
    up = (lib or "").upper()
    for key, _label, patterns in _TYPE_KEYS:
        for p in patterns:
            if p in up:
                return key
    return None


def _build_table_produit_stc(contrats: list[dict]) -> list[dict]:
    """Reproduit TableProduitSTC : par produit -> QTE, Nb_Pts, Valeur."""
    by_nom: dict[str, dict] = {}
    for c in contrats:
        nom = _normalize_nom_produit(_str(c.get("lib_produit")))
        if not nom:
            continue
        row = by_nom.setdefault(nom, {"lib_produit": nom, "qte": 0, "nb_pts": 0.0, "valeur": 0.0})
        row["qte"] += 1
        partenaire = _str(c.get("partenaire")).upper()
        type_prod = _str(c.get("type_prod")).upper()
        try:
            pts = float(c.get("nb_points") or 0)
        except (TypeError, ValueError):
            pts = 0
        if "ENI" in partenaire:
            if "ELEC" in type_prod:
                row["valeur"] += 8
            if "GAZ" in type_prod:
                row["nb_pts"] += pts
        else:
            row["nb_pts"] += pts
    return sorted(by_nom.values(), key=lambda r: r["lib_produit"])


def _build_recap_prod(contrats: list[dict], by_pts: bool = False) -> list[dict]:
    """Reproduit TableRecapProd / TableRecapProdPts : par produit, par Type_Etat."""
    by_nom: dict[str, dict] = {}
    for c in contrats:
        nom = _normalize_nom_produit(_str(c.get("lib_produit")))
        if not nom:
            continue
        row = by_nom.setdefault(
            nom,
            {"lib_produit": nom, **{k: 0 for k, _, _ in _TYPE_KEYS}},
        )
        k = _match_type_etat(_str(c.get("type_etat_lib")))
        if not k:
            continue
        try:
            inc = float(c.get("nb_points") or 0) if by_pts else 1
        except (TypeError, ValueError):
            inc = 0
        row[k] += inc
    return sorted(by_nom.values(), key=lambda r: r["lib_produit"])


# --- Rendu HTML / WeasyPrint ---------------------------------------------

_CSS = """
@page {
    size: A4;
    margin: 18mm 14mm 22mm 14mm;
    @bottom-left {
        content: var(--societe-footer, '');
        font-size: 8pt;
        color: #4E1D17;
    }
    @bottom-right {
        content: 'Page ' counter(page) ' / ' counter(pages);
        font-size: 8pt;
        color: #4E1D17;
    }
}
* { box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #4E1D17;
    font-size: 10pt;
    margin: 0;
}
.header {
    display: flex;
    align-items: center;
    border-bottom: 2px solid #17494E;
    padding-bottom: 6mm;
    margin-bottom: 6mm;
}
.header .logo { width: 32mm; }
.header .logo img { max-width: 32mm; max-height: 20mm; }
.header .titre {
    flex: 1;
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    color: #17494E;
}
.titre-salarie {
    text-align: center;
    font-size: 12pt;
    font-weight: bold;
    margin-bottom: 4mm;
}
.infos-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2mm 6mm;
    margin: 4mm 0 6mm 0;
}
.info-cell {
    display: flex;
    justify-content: space-between;
    padding: 1.5mm 3mm;
    border-bottom: 1px solid #EFE9E7;
}
.info-cell .lib { font-weight: 600; }
.info-cell .val { font-family: 'Consolas', monospace; }
.sub-state { margin: 5mm 0; }
.sub-state h2 {
    background: #17494E;
    color: white;
    font-size: 11pt;
    padding: 2mm 4mm;
    margin: 0;
    text-align: center;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
}
th, td {
    padding: 1.5mm 3mm;
    border-bottom: 1px solid #EFE9E7;
    text-align: right;
}
th:first-child, td:first-child { text-align: left; }
thead th {
    background: #EFE9E7;
    color: #4E1D17;
    font-weight: 600;
}
tfoot td {
    background: #F7F4F3;
    font-weight: 600;
    border-top: 2px solid #17494E;
    border-bottom: none;
}
.commentaires {
    margin: 5mm 0;
    padding: 4mm;
    border: 1px solid #EFE9E7;
    background: #FBF9F8;
    min-height: 20mm;
    white-space: pre-wrap;
}
.commentaires .lib {
    font-weight: 600;
    margin-bottom: 2mm;
    color: #17494E;
}
"""


def _render_info_cell(lib: str, val: str) -> str:
    return f'<div class="info-cell"><span class="lib">{escape(lib)} :</span><span class="val">{escape(val)}</span></div>'


def _render_recap_table(title: str, rows: list[dict]) -> str:
    head_cells = "".join(
        f"<th>{escape(label)}</th>" for _, label, _ in _TYPE_KEYS
    )
    body = ""
    totals = {k: 0 for k, _, _ in _TYPE_KEYS}
    for r in rows:
        cells = ""
        for k, _, _ in _TYPE_KEYS:
            v = r.get(k, 0) or 0
            cells += f"<td>{_fmt_int(v) if isinstance(v, int) or float(v).is_integer() else f'{v:.2f}'}</td>"
            totals[k] += v
        body += f"<tr><td>{escape(r['lib_produit'])}</td>{cells}</tr>"
    foot_cells = ""
    for k, _, _ in _TYPE_KEYS:
        v = totals[k]
        foot_cells += f"<td>= {_fmt_int(v) if isinstance(v, int) or float(v).is_integer() else f'{v:.2f}'}</td>"
    return f"""
    <section class="sub-state">
      <h2>{escape(title)}</h2>
      <table>
        <thead><tr><th>Produit</th>{head_cells}</tr></thead>
        <tbody>{body}</tbody>
        <tfoot><tr><td></td>{foot_cells}</tr></tfoot>
      </table>
    </section>
    """


def _render_prod_stc_table(rows: list[dict]) -> str:
    body = ""
    tot_qte = tot_pts = tot_val = 0
    for r in rows:
        body += (
            f"<tr><td>{escape(r['lib_produit'])}</td>"
            f"<td>{_fmt_int(r['qte'])}</td>"
            f"<td>{_fmt_int(r['nb_pts'])}</td>"
            f"<td>{_fmt_eur(r['valeur'])}</td></tr>"
        )
        tot_qte += r["qte"]
        tot_pts += r["nb_pts"]
        tot_val += r["valeur"]
    return f"""
    <section class="sub-state">
      <h2>Solde de tout compte</h2>
      <table>
        <thead><tr><th>Produit</th><th>QTE</th><th>Nb Pts</th><th>Valeur</th></tr></thead>
        <tbody>{body}</tbody>
        <tfoot><tr>
          <td></td>
          <td>= {_fmt_int(tot_qte)}</td>
          <td>= {_fmt_int(tot_pts)}</td>
          <td>= {_fmt_eur(tot_val)}</td>
        </tr></tfoot>
      </table>
    </section>
    """


def build_pdf(
    *,
    salarie: dict,
    bareme: dict,
    contrats_consideres: list[dict],
    nb_tr: int = 0,
    commentaires: str = "",
) -> bytes:
    """Genere le PDF EtatSTC_RecapPROD.

    Arguments :
      salarie  : dict (issu de svc.load -> .salarie) -- attendu : lib_nom, id_ste
      bareme   : dict (issu de compute_bareme.to_dict)
      contrats_consideres : liste des contrats deja traites coches + selection SDTC
      nb_tr    : nombre de TR (saisie operateur)
      commentaires : TEXTE3 (saisie operateur)
    """
    societe = _load_societe(int(salarie.get("id_ste") or 0))
    lib_nom = _str(salarie.get("lib_nom"))
    rs = societe.get("raison_sociale") or _str(salarie.get("lib_societe"))

    titre_page = f"{lib_nom} // {rs}".strip(" /")

    # Header
    logo_html = ""
    if societe.get("logo_b64"):
        logo_html = (
            f'<img src="data:image/png;base64,{societe["logo_b64"]}" alt="logo">'
        )
    header = f"""
    <div class="header">
      <div class="logo">{logo_html}</div>
      <div class="titre">SOLDE DE TOUT COMPTE<br><span style="font-size:10pt;font-weight:normal;">Récap PRODUCTION</span></div>
      <div style="width:32mm;"></div>
    </div>
    <div class="titre-salarie">{escape(titre_page)}</div>
    """

    # 7 infos
    info_cells = [
        _render_info_cell("Nombre Total de pts", _fmt_int(bareme.get("nb_tot_pts", 0))),
        _render_info_cell("Nombre Total de Ctts", _fmt_int(bareme.get("nb_tot_ctts", 0))),
        _render_info_cell("Barême des Pts", _fmt_eur(bareme.get("bareme", 0))),
        _render_info_cell("CA des Pts", _fmt_eur(bareme.get("comm_pts_ctts", 0))),
        _render_info_cell("CA des valeurs", _fmt_eur(bareme.get("total_valeurs", 0))),
        _render_info_cell("CA du STC", _fmt_eur(bareme.get("comm_tot_stc", 0))),
        _render_info_cell("Nombre de TR", _fmt_int(nb_tr)),
    ]
    infos_html = f'<div class="infos-grid">{"".join(info_cells)}</div>'

    # Sous-etats
    prod_stc = _build_table_produit_stc(contrats_consideres)
    recap_nb = _build_recap_prod(contrats_consideres, by_pts=False)
    recap_pts = _build_recap_prod(contrats_consideres, by_pts=True)

    prod_stc_html = _render_prod_stc_table(prod_stc)
    recap_nb_html = _render_recap_table("Récap PROD Globale en NB de CTTS", recap_nb)
    recap_pts_html = _render_recap_table("Récap PROD Globale en NB de PTS", recap_pts)

    commentaires_html = ""
    if commentaires.strip():
        commentaires_html = (
            f'<div class="commentaires"><div class="lib">Commentaires :</div>{escape(commentaires)}</div>'
        )

    # Footer dynamique : ne peut pas utiliser var(--...) dans WeasyPrint
    # pour le contenu de @bottom-left, donc on injecte directement dans le CSS.
    footer_text = ""
    if societe.get("raison_sociale"):
        bits = [societe["raison_sociale"]]
        if societe.get("adresse1"):
            bits.append(societe["adresse1"])
        if societe.get("cp") or societe.get("ville"):
            bits.append(f'{societe.get("cp", "")} {societe.get("ville", "")}'.strip())
        if societe.get("siret"):
            bits.append(f'Siret : {societe["siret"]}')
        footer_text = " - ".join(bits)

    css_with_footer = _CSS.replace(
        "var(--societe-footer, '')",
        f'"{footer_text}"' if footer_text else '""',
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css_with_footer}</style></head>
<body>
{header}
{infos_html}
{prod_stc_html}
{commentaires_html}
{recap_nb_html}
{recap_pts_html}
</body></html>"""

    return HTML(string=html).write_pdf()
