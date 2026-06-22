"""
Service Fen_FicheVehicule - Btn header Imprimer fiche.

Genere un PDF "Pochette vehicule" (Etat WinDev EtatPochette_Vehicule) :
logo marque + titre + immat + CV fiscaux + forfait KM + type possession
+ date debut/fin + KM de depart + commentaire (RTF).

Cf. WinDev EtatPochette_Vehicule (req sur vehicule_Fiche + vehicule_Marque).
"""

from __future__ import annotations

import base64
import re
from datetime import date, datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.intranets.adm.services.ctt_travail import generer_pdf_publiposte


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _date_fr(v: Any) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
    return s


def _img_b64(v: Any, default_mime: str = "image/png") -> str:
    if v is None:
        return ""
    if isinstance(v, memoryview):
        v = bytes(v)
    if not isinstance(v, (bytes, bytearray)):
        return ""
    sig = bytes(v[:8])
    if sig.startswith(b"\x89PNG"):
        mime = "image/png"
    elif sig.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif sig[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    else:
        mime = default_mime
    return f"data:{mime};base64,{base64.b64encode(bytes(v)).decode('ascii')}"


def _rtf_to_html(rtf: str) -> str:
    """Extraction naive RTF -> HTML (paragraphes + sauts de ligne).
    Suffisant pour un commentaire vehicule (pas de format avance)."""
    if not rtf:
        return ""
    s = rtf
    if not s.startswith("{\\rtf"):
        return _html_escape(s)
    # Retire les groupes de declaration (font/color tables, info, etc.)
    for tag in (
        r"\{\\fonttbl[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
        r"\{\\colortbl[^{}]*\}",
        r"\{\\\*\\generator[^{}]*\}",
        r"\{\\info[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
        r"\{\\stylesheet[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
        r"\{\\\*\\[a-z]+[^{}]*\}",
    ):
        s = re.sub(tag, "", s, flags=re.IGNORECASE)
    # Decode les caracteres echappes \'XX (cp1252)
    def _hex(m: "re.Match[str]") -> str:
        try:
            return bytes.fromhex(m.group(1)).decode("cp1252", errors="replace")
        except Exception:
            return ""
    s = re.sub(r"\\'([0-9a-fA-F]{2})", _hex, s)
    # Newlines
    s = s.replace("\\par", "\n").replace("\\line", "\n")
    # Retire les commandes restantes \xxx[N]
    s = re.sub(r"\\[a-zA-Z]+-?\d*\s?", "", s)
    # Retire les accolades restantes et l'eventuel \* en debut
    s = re.sub(r"[{}]", "", s)
    s = s.replace("\\*", "")
    # Trim + escape HTML + nl2br
    txt = _html_escape(s.strip())
    return txt.replace("\n", "<br/>")


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _load_vehicule(id_vehicule: int) -> dict | None:
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT vf.id_vehicule, vf.id_vehicule_marque, vf.modele,
                  vf.immat, vf.forfait_km, vf.achat_loc, vf.date_deb,
                  vf.date_fin, vf.k_mdepart, vf.km_actuel, vf.date_releve,
                  vf.chevaux_fiscaux, vf.info_vehicule, vf.id_ste_proprio,
                  vm.nom AS marque_nom, vm.logo AS marque_logo
             FROM ulease.pgt_vehicule_fiche vf
       INNER JOIN ulease.pgt_vehicule_marque vm
               ON vm.id_vehicule_marque = vf.id_vehicule_marque
            WHERE vf.id_vehicule = ? LIMIT 1""",
        (int(id_vehicule),),
    )
    return r


def generate_pochette_pdf(id_vehicule: int) -> tuple[bytes, str] | None:
    """Genere le PDF Pochette + nom de fichier.

    Returns (pdf_bytes, filename) ou None si vehicule introuvable.
    Filename = <DateHeureSys>_Fiche_<IMMAT>.pdf (cf. WinDev)."""
    veh = _load_vehicule(id_vehicule)
    if not veh:
        return None

    marque_nom = _str(veh.get("marque_nom"))
    modele = _str(veh.get("modele"))
    immat = _str(veh.get("immat"))
    cv = _int(veh.get("chevaux_fiscaux"))
    forfait_km = _int(veh.get("forfait_km"))
    achat_loc = _str(veh.get("achat_loc"))
    date_deb = _date_fr(veh.get("date_deb"))
    date_fin = _date_fr(veh.get("date_fin"))
    km_depart = _int(veh.get("k_mdepart"))
    commentaire_html = _rtf_to_html(_str(veh.get("info_vehicule")))
    marque_logo_b64 = _img_b64(veh.get("marque_logo"))

    titre = f"{marque_nom} {modele}".strip()
    immat_filename = re.sub(r"[^A-Za-z0-9_-]", "", immat) or "Vehicule"
    filename = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}_Fiche_{immat_filename}.pdf"
    )

    logo_block = (
        f'<img src="{marque_logo_b64}" '
        f'style="max-height:35mm;max-width:50mm;object-fit:contain;"/>'
        if marque_logo_b64
        else ""
    )

    def _row(lib: str, val: str) -> str:
        return (
            f'<tr><td style="padding:4px 8px;text-align:right;'
            f'font-weight:bold;width:55mm;color:#17494E;">{lib} :</td>'
            f'<td style="padding:4px 8px;">{val or "&nbsp;"}</td></tr>'
        )

    date_block = ""
    if date_deb or date_fin:
        date_block = (
            f'{date_deb}'
            f'{("  -  Au  " + date_fin) if date_fin else ""}'
        )

    body_html = f"""
<table style="width:100%;margin-bottom:10mm;border-collapse:collapse;">
  <tr>
    <td style="width:55mm;text-align:center;vertical-align:middle;">
      {logo_block}
    </td>
    <td style="vertical-align:middle;">
      <h1 style="margin:0;font-size:22pt;color:#17494E;">Fiche VEHICULE</h1>
      <div style="font-size:14pt;color:#4E1D17;margin-top:4mm;">
        {_html_escape(titre)}
      </div>
    </td>
  </tr>
</table>

<table style="margin:0 auto;border-collapse:collapse;font-size:11pt;">
  {_row("Immatriculation", _html_escape(immat))}
  {_row("Nombre de CV fiscaux", str(cv) if cv else "")}
  {_row("FORFAIT KM", f"{forfait_km:,}".replace(",", " ") if forfait_km else "")}
  {_row("Type de possession", _html_escape(achat_loc))}
  {_row("Date d'achat / Loc", date_block)}
  {_row("KM de Départ", f"{km_depart:,}".replace(",", " ") if km_depart else "")}
</table>

<div style="margin-top:15mm;">
  <div style="font-weight:bold;color:#17494E;margin-bottom:3mm;">
    Commentaire :
  </div>
  <div style="border:1px solid #ccc;padding:5mm;min-height:60mm;">
    {commentaire_html}
  </div>
</div>
"""

    pdf = generer_pdf_publiposte(
        body_html,
        id_ste=_int(veh.get("id_ste_proprio")),
    )
    if not pdf:
        return None
    return pdf, filename
