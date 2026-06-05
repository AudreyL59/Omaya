"""
Generation du PDF "Courrier FPE" (rupture de periode d'essai).

Transposition de l'etat WinDev EtatCourrierFPE. Template HTML + WeasyPrint
pour le PDF. Donnees salarie + societe lues depuis PG, images (logo,
cachet, signature, guimmick) embarquees en data URI.
"""

import base64
from datetime import date, datetime
from typing import Any

from app.core.database.pg import get_pg_connection


# --- Helpers --------------------------------------------------------------

def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _bytea_to_data_uri(blob: Any) -> str:
    """Convertit un bytea PG en data URI base64 utilisable en src d'<img>."""
    if not blob:
        return ""
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return ""
    if len(blob) < 8:
        return ""
    # Magic bytes
    ct = "image/jpeg"
    if blob[:3] == b"\xff\xd8\xff":
        ct = "image/jpeg"
    elif blob[:8] == b"\x89PNG\r\n\x1a\n":
        ct = "image/png"
    elif blob[:6] in (b"GIF87a", b"GIF89a"):
        ct = "image/gif"
    elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        ct = "image/webp"
    b64 = base64.b64encode(bytes(blob)).decode("ascii")
    return f"data:{ct};base64,{b64}"


_MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _fmt_date_fr(d: date | datetime | str | None) -> str:
    if d is None or d == "":
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d[:10], "%Y-%m-%d").date()
        except ValueError:
            return d[:10]
    if isinstance(d, datetime):
        d = d.date()
    return f"{d.day:02d} {_MOIS_FR[d.month - 1]} {d.year}"


def _add_months_minus_1day(d: date, months: int) -> date:
    """date + N mois - 1 jour (transposition WinDev datePer..Mois += 3 + Jour -=1)."""
    new_month = d.month + months
    new_year = d.year + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    # Jour bornee au dernier jour du mois cible
    import calendar
    max_day = calendar.monthrange(new_year, new_month)[1]
    new_day = min(d.day, max_day)
    # -1 jour
    target = date(new_year, new_month, new_day)
    from datetime import timedelta
    return target - timedelta(days=1)


# --- Template HTML --------------------------------------------------------

_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
@page { size: A4; margin: 1.5cm 2cm; }
body { font-family: Arial, sans-serif; font-size: 11pt; color: #000; line-height: 1.5; }
.header { text-align: center; margin-bottom: 25px; }
.header img { max-height: 80px; }
.destinataire { text-align: right; margin-bottom: 25px; line-height: 1.4; }
.objet { text-decoration: underline; margin: 20px 0 8px 0; font-weight: bold; }
.date-lieu { text-align: center; margin: 20px 0; }
.titre { margin: 18px 0 14px 0; }
.corps { text-align: justify; }
.corps p { margin: 10px 0; }
ul { margin: 8px 0 8px 30px; }
ul li { margin: 4px 0; }
.signature-block { margin-top: 50px; text-align: right; }
.signature-images img { max-height: 70px; margin-left: 12px; vertical-align: middle; }
.footer { position: fixed; bottom: 0.5cm; left: 0; right: 0; text-align: center; }
.footer img { max-height: 55px; }
</style>
</head>
<body>

<div class="header">{{LOGO}}</div>

<div class="destinataire">
{{NOM_COMPLET}}<br/>
{{ADRESSE1}}{{ADRESSE2_BR}}<br/>
{{CP_VILLE}}
</div>

<div class="objet">Objet : Notification de la rupture de la période d'essai du contrat de travail.</div>
<div>Lettre recommandée avec accusé de réception + envoi simple</div>

<div class="date-lieu">{{STE_VILLE}}, le {{DATEDUJOUR}}</div>

<div class="titre">{{TITRE}},</div>

<div class="corps">
<p>Votre contrat de travail qui a été conclu le {{DATEDEBUT}} comporte une période d'essai de trois mois. Celle-ci a débuté le {{DATEDEBUT}} et se termine le {{FINPERESSAI}}.</p>

<p>Cette période d'essai n'étant pas achevée et pas concluante pour notre part, nous vous notifions par la présente, notre intention de la rompre.</p>

<p>La rupture de la période d'essai étant soumise aux règles de droit commun relatives au délai de prévenance, à savoir (articles L. 1221-25 et L. 1221-26 du Code du travail) :</p>

<ul>
<li>24 heures en deçà de huit jours de présence.</li>
<li>48 heures entre huit jours et un mois de présence.</li>
<li>deux semaines après un mois de présence.</li>
<li>un mois après trois mois de présence.</li>
</ul>

<p>Vous cesserez donc de faire partie de nos effectifs à l'issu du délai de prévenance <u>de {{DELAIPREV}}</u> qui débutera à la date d'envoi du présent courrier.</p>

<p>Vous pouvez toutefois demander <u>par écrit</u> à être dispensé de votre délai de prévenance.</p>

<p>Nous vous prions d'agréer, {{TITRE}}, l'expression de nos salutations distinguées.</p>
</div>

<div class="signature-block">
<div>La direction.</div>
<div class="signature-images">{{CACHET}}{{SIGNATURE}}</div>
</div>

<div class="footer">{{GUIMMICK}}</div>

</body>
</html>
"""


# --- Generation -----------------------------------------------------------

def generate_courrier_fpe(id_salarie: int, delai_prev: str) -> tuple[bytes, str]:
    """Genere le PDF du courrier de rupture de periode d'essai.

    Retourne (bytes du PDF, nom de fichier suggere).
    Leve ValueError si donnees manquantes (salarie/date d'embauche).
    """
    db_rh = get_pg_connection("rh")

    row = db_rh.query_one(
        """SELECT
            s.id_salarie, s.nom, s.prenom, s.sexe,
            sc.adresse1, sc.adresse2, sc.cp, sc.ville,
            se.date_debut, se.id_ste
        FROM rh.pgt_salarie s
        LEFT JOIN rh.pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
        LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
        WHERE s.id_salarie = ?""",
        (id_salarie,),
    )
    if not row:
        raise ValueError(f"Salarié {id_salarie} introuvable")

    sexe = _str(row.get("sexe")).upper()
    titre = "Monsieur" if sexe == "H" else "Madame"
    nom_complet = f"{titre} {_str(row.get('nom'))} {_str(row.get('prenom'))}".strip()
    adresse1 = _str(row.get("adresse1"))
    adresse2 = _str(row.get("adresse2"))
    cp_ville = f"{_str(row.get('cp'))} {_str(row.get('ville'))}".strip()

    date_debut = row.get("date_debut")
    if not date_debut:
        raise ValueError("Date d'embauche manquante pour le salarié")
    if isinstance(date_debut, str):
        date_debut = datetime.strptime(date_debut[:10], "%Y-%m-%d").date()
    if isinstance(date_debut, datetime):
        date_debut = date_debut.date()

    fin_per_essai = _add_months_minus_1day(date_debut, 3)
    today = date.today()

    # Societe
    soc = db_rh.query_one(
        """SELECT raison_sociale, adresse1 AS adr, cp, ville, siret,
            logo, guimmick, cachet_cial, gerant_signature
        FROM rh.pgt_societe
        WHERE id_ste = ?""",
        (row.get("id_ste"),),
    )
    soc_ville = ""
    logo_uri = guimmick_uri = cachet_uri = signature_uri = ""
    if soc:
        soc_ville = _str(soc.get("ville"))
        logo_uri = _bytea_to_data_uri(soc.get("logo"))
        guimmick_uri = _bytea_to_data_uri(soc.get("guimmick"))
        cachet_uri = _bytea_to_data_uri(soc.get("cachet_cial"))
        signature_uri = _bytea_to_data_uri(soc.get("gerant_signature"))

    def _img(uri: str, max_h: int = 80) -> str:
        return f'<img src="{uri}" style="max-height: {max_h}px;"/>' if uri else ""

    html = _TEMPLATE
    html = html.replace("{{LOGO}}", _img(logo_uri, 80))
    html = html.replace("{{NOM_COMPLET}}", nom_complet)
    html = html.replace("{{ADRESSE1}}", adresse1)
    html = html.replace("{{ADRESSE2_BR}}", f"<br/>{adresse2}" if adresse2 else "")
    html = html.replace("{{CP_VILLE}}", cp_ville)
    html = html.replace("{{STE_VILLE}}", soc_ville)
    html = html.replace("{{DATEDUJOUR}}", _fmt_date_fr(today))
    html = html.replace("{{TITRE}}", titre)
    html = html.replace("{{DATEDEBUT}}", _fmt_date_fr(date_debut))
    html = html.replace("{{FINPERESSAI}}", _fmt_date_fr(fin_per_essai))
    html = html.replace("{{DELAIPREV}}", _str(delai_prev))
    html = html.replace("{{CACHET}}", _img(cachet_uri, 70))
    html = html.replace("{{SIGNATURE}}", _img(signature_uri, 70))
    html = html.replace("{{GUIMMICK}}", _img(guimmick_uri, 55))

    # Conversion HTML -> PDF via WeasyPrint
    from weasyprint import HTML  # type: ignore
    pdf_bytes = HTML(string=html).write_pdf()

    # Nom de fichier
    safe = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in f"{_str(row.get('nom'))}_{_str(row.get('prenom'))}"
    ).strip()
    filename = f"Courrier_FPE_{safe or id_salarie}_{today.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename
