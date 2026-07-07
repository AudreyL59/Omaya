"""
Schemas Fen_FicheSalaires - Envoi fiches de salaire.

2 plans :
  Plan 1 : Decoupage PDF + attribution vendeurs
  Plan 2 : Envoi + prepaie Excel + email
"""

from pydantic import BaseModel, Field


# --------------------------------------------------------------------
# Plan 1 : Charger PDF + matching
# --------------------------------------------------------------------

class SocieteFDV(BaseModel):
    """Combo Societe FDV Interne (RS_Interne des societes actives)."""
    id_ste: str
    raison_sociale: str
    rs_interne: str


class VendeurRow(BaseModel):
    """Ligne TableListeVendeur (une par vendeur trouve dans le PDF).

    Cf. WinDev :
      - Vendeur : nom brut extrait du PDF (NOM PRENOM en majuscules)
      - IdSalarie : 0 = non trouve (ligne rouge), sinon trouve
      - NomPrenom : Nom + capitalize(Prenom) - depuis pgt_salarie
      - Num_Page / Nb_Page : plage de pages du bulletin (fusion si multi)
      - Choix : True apres validation (Plan 2)
      - FichierPDF / BasePDF / TabPrepaies : noms fichiers finaux
      - Mail / GSM : contact vendeur
      - couleur : 'rouge' | 'vert' | 'orange' | ''
    """
    id_salarie: str = "0"       # str car ID 8 octets
    vendeur: str = ""           # brut PDF
    nom_prenom: str = ""        # depuis pgt_salarie
    num_page: int = 0
    nb_page: int = 1
    choix: bool = False
    fichier_pdf: str = ""       # nom fichier PDF individuel apres split
    base_pdf: str = ""          # base contrat generee par Fen_PaiesBS
    tab_prepaies: str = ""      # tableau prepaie PDF (si genere)
    mail: str = ""
    gsm: str = ""
    couleur: str = "rouge"      # rouge / vert / orange


class ChargerPdfResult(BaseModel):
    """Output apres charger PDF."""
    ok: bool
    pdf_b64: str = ""           # PDF entier en b64 (pour affichage frontend)
    nb_pages: int = 0
    vendeurs: list[VendeurRow] = Field(default_factory=list)
    message: str = ""


class RechercheSalariePayload(BaseModel):
    """Recherche manuelle salarie (ligne rouge)."""
    q: str  # recherche libre nom/prenom


# --------------------------------------------------------------------
# Valider (decoupe PDF + upload FTP + recup base)
# --------------------------------------------------------------------

class ValiderParams(BaseModel):
    """Input Btn Valider."""
    mois_paiement: str  # YYYY-MM
    pdf_b64: str        # PDF complet original en base64
    vendeurs: list[VendeurRow] = Field(default_factory=list)


class ValiderResult(BaseModel):
    ok: bool
    vendeurs: list[VendeurRow] = Field(default_factory=list)  # avec fichier_pdf / base_pdf / couleur
    nb_valides: int = 0
    nb_erreurs: int = 0
    message: str = ""


# --------------------------------------------------------------------
# Sauvegarde XLSX / Reimport XLSX (reprise etat)
# --------------------------------------------------------------------

class SauvegardeXlsxResult(BaseModel):
    ok: bool
    xlsx_b64: str = ""
    fic_name: str = ""


class ReimportXlsxResult(BaseModel):
    ok: bool
    vendeurs: list[VendeurRow] = Field(default_factory=list)
    message: str = ""


# --------------------------------------------------------------------
# Prepaie Excel (Plan 2)
# --------------------------------------------------------------------

class ParseXlsxResult(BaseModel):
    """Parse XLSX prepaie -> matrice cellules pour affichage frontend."""
    ok: bool
    nrows: int = 0
    ncols: int = 0
    cells: list[list[str]] = Field(default_factory=list)  # matrice [row][col]
    message: str = ""


class GenererPdfPrepaieParams(BaseModel):
    """Input Btn Enregistrer la selection en PDF."""
    id_salarie: str
    nom_prenom: str    # pour le nom fichier
    mois_paiement: str # YYYY-MM
    xlsx_b64: str      # XLSX complet
    plage: str         # 'A1:G17'


class GenererPdfPrepaieResult(BaseModel):
    ok: bool
    fic_name: str = ""
    couleur: str = ""    # vert / orange / rouge
    message: str = ""