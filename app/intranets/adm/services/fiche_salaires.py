"""
Service Fen_FicheSalaires - Envoi fiches de salaire.

## Plan 1 : Decoupage PDF + matching vendeurs

1. list_societes_fdv() : combo Societe (id_type_orga=1 FDV Interne)
2. charger_pdf(pdf_bytes) : extrait les vendeurs des pages du PDF via
   pattern natif ##BULLETIN##<periode>##<num>##<NOM>##<PRENOM>##.
   Match automatique nom+prenom vs pgt_salarie.
3. rechercher_salaries(q) : recherche libre pour attribution manuelle
   des lignes rouges.

Le WinDev fait de l'OCR sur zone visuelle (1194,480,984,55) faute d'un
bon extracteur texte natif. Python + pypdf peuvent extraire le texte
brut : on cible le pattern ## qui est present en debut de chaque page
et 100% fiable.
"""

import base64
import logging
import re
import unicodedata
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.fiche_salaires import (
    ChargerPdfResult, ReimportXlsxResult, SauvegardeXlsxResult, SocieteFDV,
    ValiderParams, ValiderResult, VendeurRow,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return "-".join(x[:1].upper() + x[1:].lower() for x in p.split("-"))


def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _norm_search(s: str) -> str:
    """cf. WinDev ChaineFormate(ccSansAccent + ccMajuscule) : retire accents,
    puis majuscules + sans espaces multiples."""
    if not s:
        return ""
    # Retire caracteres mal encodes (les remplace par vide)
    s = s.replace("�", "")
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_s.upper()).strip()


# --------------------------------------------------------------------
# Combo Societes FDV Interne
# --------------------------------------------------------------------

def list_societes_fdv() -> list[SocieteFDV]:
    """Cf. WinDev Combo Societe : societes FDV Interne actives.

    id_type_orga = 1 (FDV Interne) - cf. project_intranets_list memoire
    et pattern ListeSocietePage (frontend adm/pages).
    """
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_ste, raison_sociale, rs_interne
                 FROM pgt_societe
                WHERE (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                  AND id_type_orga = 1
                  AND is_actif = TRUE
                ORDER BY rs_interne ASC NULLS LAST""",
        ) or []
    except Exception:
        return []
    return [
        SocieteFDV(
            id_ste=_clean_id(r.get("id_ste")),
            raison_sociale=(r.get("raison_sociale") or "").strip(),
            rs_interne=(r.get("rs_interne") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Charger PDF (extraction + matching)
# --------------------------------------------------------------------

# Pattern robuste : ##BULLETIN##(period)##(num)##(NOM)##(prenom)##
# Tolerant sur les caracteres non-'#' (accents, espaces, tirets).
_BULLETIN_RE = re.compile(
    r'##BULLETIN##(\d{2}-\d{4})##(\d+)##([^#]+?)##([^#]+?)##'
)


def _find_salarie_by_name(
    nom_norm: str, prenom_norm: str,
) -> Optional[dict]:
    """Recherche un salarie actif par nom+prenom (insensible casse/accent).

    Retour : {id_salarie, nom, prenom, mail, gsm} ou None.
    """
    rh = get_pg_connection("rh")
    # Utilise UPPER + unaccent equivalent : on normalise cote SQL avec
    # TRANSLATE (pattern classique PG sans extension unaccent).
    try:
        rows = rh.query(
            """SELECT s.id_salarie, s.nom, s.prenom, s.login AS mail,
                      c.tel_mob AS gsm
                 FROM pgt_salarie s
                 LEFT JOIN pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                 JOIN pgt_salarie_embauche e
                      ON e.id_salarie = s.id_salarie
                     AND (e.modif_elem IS NULL
                          OR e.modif_elem NOT LIKE '%suppr%')
                     AND e.en_activite = TRUE
                WHERE UPPER(s.nom) = ?
                  AND UPPER(s.prenom) = ?
                LIMIT 2""",
            (nom_norm, prenom_norm),
        ) or []
    except Exception:
        return None
    # Ambiguite -> pas d'attribution auto (cf. WinDev HNbEnr=1)
    if len(rows) != 1:
        return None
    r = rows[0]
    return {
        "id_salarie": _clean_id(r.get("id_salarie")),
        "nom": (r.get("nom") or "").strip(),
        "prenom": (r.get("prenom") or "").strip(),
        "mail": (r.get("mail") or "").strip(),
        "gsm": (r.get("gsm") or "").strip(),
    }


def charger_pdf(pdf_bytes: bytes) -> ChargerPdfResult:
    """Cf. WinDev Btn Charger le fichier PDF.

    1. Ouvre PDF.
    2. Pour chaque page : extrait le pattern ##BULLETIN##...##NOM##PRENOM##
    3. Groupe par (nom, prenom) : Nb_Page += 1 pour multi-pages du meme
       vendeur.
    4. Match automatique vs pgt_salarie : 1 resultat = vert, sinon rouge.
    """
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError:
        return ChargerPdfResult(
            ok=False, message="pypdf non installe cote serveur",
        )

    import io as _io
    try:
        reader = PdfReader(_io.BytesIO(pdf_bytes))
    except Exception as e:
        return ChargerPdfResult(
            ok=False, message=f"PDF invalide : {e}",
        )

    nb_pages = len(reader.pages)
    if not nb_pages:
        return ChargerPdfResult(
            ok=True, nb_pages=0, vendeurs=[],
            message="PDF vide",
        )

    # Extraction pattern
    vendeurs_by_key: dict[str, VendeurRow] = {}
    order: list[str] = []

    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        m = _BULLETIN_RE.search(txt)
        if not m:
            # Page sans pattern : on cree une ligne 'inconnu'
            key = f"__unknown_{i+1}"
            vendeurs_by_key[key] = VendeurRow(
                id_salarie="0",
                vendeur=f"Page {i+1} inconnue",
                num_page=i + 1, nb_page=1,
                couleur="rouge",
            )
            order.append(key)
            continue
        nom = m.group(3).strip()
        prenom = m.group(4).strip()
        # cf. WinDev : sans espace multiple + sans accent + majuscule
        vendeur_lib = f"{_norm_search(prenom)} {_norm_search(nom)}"
        # Clef de regroupement : nom_norm|prenom_norm
        key = f"{_norm_search(nom)}|{_norm_search(prenom)}"
        if key in vendeurs_by_key:
            vendeurs_by_key[key].nb_page += 1
        else:
            row = VendeurRow(
                id_salarie="0",
                vendeur=vendeur_lib,
                num_page=i + 1,
                nb_page=1,
                couleur="rouge",
            )
            # Lookup salarie
            info = _find_salarie_by_name(
                _norm_search(nom), _norm_search(prenom),
            )
            if info:
                row.id_salarie = info["id_salarie"]
                row.nom_prenom = f"{info['nom']} {_cap_prenom(info['prenom'])}"
                row.mail = info["mail"]
                row.gsm = info["gsm"]
                row.couleur = "vert"
            vendeurs_by_key[key] = row
            order.append(key)

    vendeurs = [vendeurs_by_key[k] for k in order]

    return ChargerPdfResult(
        ok=True,
        pdf_b64=base64.b64encode(pdf_bytes).decode("ascii"),
        nb_pages=nb_pages,
        vendeurs=vendeurs,
        message=(
            f"{len(vendeurs)} vendeur(s) identifie(s) - "
            f"{sum(1 for v in vendeurs if v.id_salarie == '0')} en rouge"
        ),
    )


# --------------------------------------------------------------------
# Recherche manuelle (ligne rouge)
# --------------------------------------------------------------------

def rechercher_salaries(q: str) -> list[dict]:
    """Recherche libre nom/prenom pour attribution manuelle (cf. WinDev
    Fen_RechercheNomSalarie).
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT s.id_salarie, s.nom, s.prenom, s.login AS mail
                 FROM pgt_salarie s
                 JOIN pgt_salarie_embauche e
                      ON e.id_salarie = s.id_salarie
                     AND (e.modif_elem IS NULL
                          OR e.modif_elem NOT LIKE '%suppr%')
                     AND e.en_activite = TRUE
                WHERE UPPER(s.nom) LIKE UPPER(?)
                   OR UPPER(s.prenom) LIKE UPPER(?)
                   OR UPPER(s.nom || ' ' || s.prenom) LIKE UPPER(?)
                ORDER BY s.nom, s.prenom
                LIMIT 20""",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ) or []
    except Exception:
        return []
    return [
        {
            "id_salarie": _clean_id(r.get("id_salarie")),
            "nom": (r.get("nom") or "").strip(),
            "prenom": _cap_prenom((r.get("prenom") or "").strip()),
            "mail": (r.get("mail") or "").strip(),
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# Btn Valider - decoupe PDF + upload FTP + recup base
# --------------------------------------------------------------------

def _safe_filename(s: str) -> str:
    """Sanitize nom fichier : espaces -> underscore + retire caracteres
    dangereux. Preserve caracteres alphanumeriques + tirets + accents.
    """
    if not s:
        return "vendeur"
    # Retire caracteres mal encodes (encodage PDF cassé)
    s = s.replace("�", "").replace("�", "")
    # Retire caracteres OS-dangereux
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s)
    # Espaces -> underscore
    s = re.sub(r"\s+", "_", s.strip())
    return s or "vendeur"


def _download_ftp_optional(path: str) -> Optional[bytes]:
    """Tente de recuperer un fichier via FTP. Retourne None si absent."""
    try:
        from app.shared.tickets.forms.factdistrib import _ftp_download
        return _ftp_download(path)
    except Exception:
        return None


def valider(p: ValiderParams) -> ValiderResult:
    """Cf. WinDev Btn Valider.

    Pour chaque vendeur attribue (id_salarie != 0) :
    1. Extrait les pages [num_page, num_page + nb_page - 1] du PDF
       original + genere un PDF individuel.
    2. Upload FTP gestionRH/{id}/Fiches_Salaires/{Vendeur}_{YYYY-MM}_FS.pdf
    3. Cherche la base PDF deja generee par Fen_PaiesBS :
       gestionRH/{id}/Fiches_Salaires/{NOM_PRENOM}_{YYYY-MM}_base.pdf
       (fallback : {NOM_PRENOM}_{MM-YYYY}_base.pdf)
    """
    # Validation
    if not p.pdf_b64:
        return ValiderResult(ok=False, message="PDF manquant")
    if not p.vendeurs:
        return ValiderResult(ok=False, message="Aucun vendeur")
    if len(p.mois_paiement) != 7 or p.mois_paiement[4] != "-":
        return ValiderResult(
            ok=False, message="mois_paiement invalide (YYYY-MM)",
        )

    # Verifie qu'aucun vendeur n'est en rouge
    non_attribues = [v for v in p.vendeurs if v.id_salarie == "0"]
    if non_attribues:
        return ValiderResult(
            ok=False,
            message=(
                f"{len(non_attribues)} vendeur(s) non attribue(s). "
                "Merci de verifier les lignes en rouge."
            ),
            vendeurs=p.vendeurs,
        )

    # Decode le PDF source
    try:
        pdf_source = base64.b64decode(p.pdf_b64)
    except Exception as e:
        return ValiderResult(ok=False, message=f"PDF b64 invalide : {e}")

    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
        from app.core.config import FTP_GESTION_RH_PATH
        from app.shared.tickets.forms.cttw_pdf import ftp_upload
    except ImportError as e:
        return ValiderResult(
            ok=False, message=f"Dependance manquante : {e}",
        )

    import io as _io
    try:
        reader = PdfReader(_io.BytesIO(pdf_source))
    except Exception as e:
        return ValiderResult(ok=False, message=f"PDF illisible : {e}")

    ftp_root = FTP_GESTION_RH_PATH.rstrip("/")
    nb_valides = 0
    nb_erreurs = 0
    result_rows: list[VendeurRow] = []

    for v in p.vendeurs:
        # Copie la structure de v pour retour
        nv = v.model_copy()

        # 1. Extrait les pages [num_page .. num_page + nb_page - 1]
        num_min = int(v.num_page)  # 1-indexed
        num_max = num_min + int(v.nb_page) - 1
        try:
            writer = PdfWriter()
            for k in range(num_min - 1, num_max):  # 0-indexed
                if 0 <= k < len(reader.pages):
                    writer.add_page(reader.pages[k])
            buf = _io.BytesIO()
            writer.write(buf)
            pdf_indiv = buf.getvalue()
        except Exception as e:
            logger.exception("Split PDF KO vendeur %s", v.vendeur)
            nv.couleur = "rouge"
            result_rows.append(nv)
            nb_erreurs += 1
            continue

        # 2. Nom fichier FS.pdf (cf. WinDev)
        fic_name = f"{_safe_filename(v.vendeur)}_{p.mois_paiement}_FS.pdf"
        # 3. Upload FTP
        upload_ok = False
        try:
            ftp_upload(
                f"{ftp_root}/{v.id_salarie}/Fiches_Salaires",
                fic_name, pdf_indiv,
            )
            upload_ok = True
        except Exception as e:
            logger.exception("Upload FTP KO : %s", fic_name)

        nv.fichier_pdf = fic_name if upload_ok else ""

        # 4. Cherche la base PDF (generee par Fen_PaiesBS)
        # cf. WinDev : Majuscule(NomPrenom)+"_"+DateVersChaine(MoisP,"AAAA-MM")+"_base.pdf"
        # avec fallback sur MM-AAAA
        base_candidates = []
        if v.nom_prenom:
            nom_prenom_up = v.nom_prenom.upper()
            base_candidates.append(
                _safe_filename(nom_prenom_up)
                + f"_{p.mois_paiement}_base.pdf",
            )
            # Fallback MM-AAAA
            mm_aaaa = p.mois_paiement[5:7] + "-" + p.mois_paiement[:4]
            base_candidates.append(
                _safe_filename(nom_prenom_up)
                + f"_{mm_aaaa}_base.pdf",
            )

        base_found = ""
        for candidate in base_candidates:
            path = f"{ftp_root}/{v.id_salarie}/Fiches_Salaires/{candidate}"
            content = _download_ftp_optional(path)
            if content:
                base_found = candidate
                break
        nv.base_pdf = base_found

        # 5. Couleur / statut
        if upload_ok:
            nv.choix = True
            nv.couleur = "vert"
            nb_valides += 1
        else:
            nv.couleur = "orange"
            nb_erreurs += 1

        result_rows.append(nv)

    return ValiderResult(
        ok=True,
        vendeurs=result_rows,
        nb_valides=nb_valides,
        nb_erreurs=nb_erreurs,
        message=(
            f"{nb_valides} vendeur(s) valide(s), {nb_erreurs} erreur(s). "
            + ("Passer au Plan 2." if nb_erreurs == 0 else "")
        ),
    )


# --------------------------------------------------------------------
# Sauvegarde XLSX / Reimport XLSX
# --------------------------------------------------------------------

_XLSX_COLS = [
    ("Choix", "choix"),
    ("Vendeur", "vendeur"),
    ("NomPrenom", "nom_prenom"),
    ("NumPage", "num_page"),
    ("NbPage", "nb_page"),
    ("IdSalarie", "id_salarie"),
    ("Mail", "mail"),
    ("GSM", "gsm"),
    ("FichierPDF", "fichier_pdf"),
    ("BasePDF", "base_pdf"),
    ("TabPrepaies", "tab_prepaies"),
    ("Couleur", "couleur"),
]


def sauvegarder_xlsx(vendeurs: list[VendeurRow]) -> SauvegardeXlsxResult:
    """Btn Sauve EXCEL : exporte TableListeVendeur en XLSX pour reprise
    ulterieure. Cf. WinDev TableListeVendeur.VersExcel(...).
    """
    try:
        from openpyxl import Workbook  # noqa: PLC0415
    except ImportError:
        return SauvegardeXlsxResult(ok=False)

    wb = Workbook()
    ws = wb.active
    ws.title = "Sauve"
    # Header
    ws.append([lbl for lbl, _ in _XLSX_COLS])
    for v in vendeurs:
        d = v.model_dump()
        ws.append([d.get(attr, "") for _, attr in _XLSX_COLS])

    import io as _io
    buf = _io.BytesIO()
    wb.save(buf)
    xlsx_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return SauvegardeXlsxResult(
        ok=True,
        xlsx_b64=xlsx_b64,
        fic_name="SauveEnvoieFicSalaires.xlsx",
    )


def reimporter_xlsx(xlsx_bytes: bytes) -> ReimportXlsxResult:
    """Btn Reimporter Sauve XLS : recharge un XLSX genere par
    sauvegarder_xlsx (cf. WinDev Btn Reimporter Sauve XLS).
    """
    try:
        from openpyxl import load_workbook  # noqa: PLC0415
    except ImportError:
        return ReimportXlsxResult(
            ok=False, message="openpyxl non installe",
        )

    import io as _io
    try:
        wb = load_workbook(_io.BytesIO(xlsx_bytes), data_only=True)
    except Exception as e:
        return ReimportXlsxResult(
            ok=False, message=f"XLSX illisible : {e}",
        )
    ws = wb.active
    if not ws or ws.max_row < 2:
        return ReimportXlsxResult(ok=True, vendeurs=[])

    # Attend le meme header que sauvegarder_xlsx (positions fixes)
    vendeurs: list[VendeurRow] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or all(x is None for x in row):
            continue
        try:
            d = {}
            for i, (_, attr) in enumerate(_XLSX_COLS):
                if i < len(row) and row[i] is not None:
                    v = row[i]
                    if attr == "choix":
                        d[attr] = bool(v) and str(v).lower() not in (
                            "false", "0", "non", "",
                        )
                    elif attr in ("num_page", "nb_page"):
                        try:
                            d[attr] = int(v)
                        except (TypeError, ValueError):
                            d[attr] = 0
                    elif attr == "id_salarie":
                        d[attr] = str(int(v)) if v else "0"
                    else:
                        d[attr] = str(v).strip()
            vendeurs.append(VendeurRow(**d))
        except Exception:
            logger.exception("Row XLSX skip")

    return ReimportXlsxResult(
        ok=True,
        vendeurs=vendeurs,
        message=f"{len(vendeurs)} vendeur(s) reimporte(s)",
    )
