"""
Configuration du menu Intranet ADM.

L'ADM remplace l'application WinDev Windows. La home est une grille de
sections cartes (cf. project_adm_remplace_windev). Le menu est exposé
en sections + items, plus une barre d'icônes en header.

Visibilité :
  - section_droit (optionnel) : code interne TypeDroitAccès — si présent
    et non accordé, la section entière est masquée.
  - item.droit (optionnel) : idem pour chaque item.
  - Si une section ne contient aucun item visible après filtrage, elle
    est masquée côté frontend (useMenu).

Codes de droits (cf. WinDev initMenu) :
  - Sections : Menu_Prod, Menu_ImportBO, Menu_SuiviDistr, Menu_Paies,
    Menu_COMM, Menu_Salariés, Menu_Scool, Menu_Ulease, Menu_Recrut.
  - Items : SuiviProd, SuiviSFR, SuiviEnergie, GestFACT, ImpBS, ImpMasse,
    SuiviADMDistri, SuiviADMDistDoc, GestCOURTAGE, ModPaie, FichePaies,
    TabSalarie, CalcPtsEni, GenTabDivers, ExportTR, GestChallenge,
    GestExoCash, GestPodium, GestPerfExo, RegistreRH, NewDPAE, CttW,
    impFormIAG, GestMutuelle, ParamRH, FormScool, ParcAuto, CV, PrevRec,
    SaisieCV, StatRH, GestRecrut, ParamCV, Societe.
"""

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken

router = APIRouter()


def _droit(user: UserToken, code: str | None) -> bool:
    """True si le code est None (pas de check) ou présent dans user.droits."""
    return code is None or code in user.droits


# Items dont la page cible existe déjà côté frontend (Routes explicites dans App.tsx).
# Tout ce qui n'est pas dans ce set est "non codé" → grisé pour le user de
# référence (id_salarie=6), masqué pour les autres.
_CODED_ITEMS: set[str] = {"agenda_rec", "stats_rh", "organigramme", "suivi_production"}
_CODED_HEADER: set[str] = {"organigramme"}

# User de référence pour qui les items non codés restent visibles (en grisé)
_PROGRESS_USER_ID = 6


@router.get("/menu")
def get_menu(user: UserToken = Depends(get_current_user)):
    """Retourne header_actions + sections avec items, filtrés selon les droits."""

    # Barre d'icônes en header (boutons WinDev BTN_Orga / BTN_Scanner / BTN_ExoNews / BTN_Entité)
    header_actions_raw = [
        {"key": "search",       "label": "Recherche",     "route": "/recherche",     "icon": "search",   "droit": None},
        {"key": "organigramme", "label": "Organigramme",  "route": "/organigramme",  "icon": "network",  "droit": "Menu_Salariés"},
        {"key": "scanner",      "label": "Scanner",       "route": "/scanner",       "icon": "scan",     "droit": "Menu_Salariés"},
        {"key": "exo_news",     "label": "Exo News",      "route": "/exo-news",      "icon": "newspaper","droit": "Menu_COMM"},
        {"key": "societes",     "label": "Sociétés",      "route": "/societes",      "icon": "building", "droit": "Societe"},
        {"key": "notifications","label": "Notifications", "route": "/notifications", "icon": "bell",     "droit": None, "badge": 0},
    ]
    is_progress_user = user.id_salarie == _PROGRESS_USER_ID

    header_actions = []
    for a in header_actions_raw:
        if not _droit(user, a["droit"]):
            continue
        is_coded = a["key"] in _CODED_HEADER
        if not is_progress_user and not is_coded:
            continue
        item = {k: v for k, v in a.items() if k != "droit"}
        item["visible"] = True
        item["coded"] = is_coded
        header_actions.append(item)

    sections_raw = [
        {
            "key": "prod_contrat",
            "label": "Prod et Contrat",
            "section_droit": "Menu_Prod",
            "items": [
                {"key": "suivi_production",  "label": "Suivi Production",         "route": "/production",      "icon": "line-chart","droit": "SuiviProd"},
                {"key": "suivi_sfr",         "label": "Suivi SFR",                "route": "/suivi-sfr",       "icon": "antenna",   "droit": "SuiviSFR"},
                {"key": "suivi_energie",     "label": "Suivi Énergie",            "route": "/suivi-energie",   "icon": "zap",       "droit": "SuiviEnergie"},
                {"key": "rech_ville",        "label": "Rechercher / Ajouter une ville","route":"/villes",     "icon": "map-pin",   "droit": "Menu_Prod"},
            ],
        },
        {
            "key": "facture",
            "label": "Facture",
            "section_droit": "GestFACT",
            "items": [
                {"key": "suivi_factures",    "label": "Suivi des factures",       "route": "/factures",        "icon": "receipt",   "droit": "GestFACT"},
            ],
        },
        {
            "key": "imports",
            "label": "Imports Bases",
            "section_droit": "Menu_ImportBO",
            "items": [
                {"key": "import_contrats",   "label": "Import contrats",          "route": "/imports/contrats","icon": "file-down","droit": "ImpBS"},
                {"key": "import_masse",      "label": "Import en masse",          "route": "/imports/masse",   "icon": "upload",   "droit": "ImpMasse"},
                {"key": "import_colonnes",   "label": "Ajout de colonnes",        "route": "/imports/colonnes","icon": "columns",  "droit": "ImpBS"},
                {"key": "import_notations",  "label": "Import notations",         "route": "/imports/notations","icon": "star",    "droit": "ImpBS"},
            ],
        },
        {
            "key": "qualite",
            "label": "Qualité",
            "section_droit": None,  # pas de check WinDev fourni
            "items": [
                {"key": "tableau_bord",      "label": "Tableau de bord",          "route": "/qualite",         "icon": "layout-dashboard","droit": None},
            ],
        },
        {
            "key": "suivi_distrib",
            "label": "Suivi Distrib",
            "section_droit": "Menu_SuiviDistr",
            "items": [
                {"key": "suivi_distributeurs","label": "Suivi des distributeurs", "route": "/distributeurs",   "icon": "truck",    "droit": "SuiviADMDistri"},
                {"key": "suivi_docs_distrib","label": "Suivi Docs Distributeurs", "route": "/distributeurs/documents","icon":"files","droit": "SuiviADMDistDoc"},
                {"key": "ctt_courtage",      "label": "Liste des Contrats de Courtage","route":"/contrats-courtage","icon":"file-text","droit": "GestCOURTAGE"},
            ],
        },
        {
            "key": "paies",
            "label": "Paies",
            "section_droit": "Menu_Paies",
            "items": [
                {"key": "module_paies",      "label": "Module paies",             "route": "/paies",                "icon": "wallet",    "droit": "ModPaie"},
                {"key": "fiches_salaire",    "label": "Envoi fiches de salaire",  "route": "/paies/fiches",         "icon": "send",      "droit": "FichePaies"},
                {"key": "tableau_salarie",   "label": "Tableau salarié",          "route": "/paies/tableau-salarie","icon": "table",     "droit": "TabSalarie"},
                {"key": "calcul_points",     "label": "Calcul points Contrats",   "route": "/paies/points",         "icon": "calculator","droit": "CalcPtsEni"},
                {"key": "tableaux_divers",   "label": "Génération tableaux divers","route": "/paies/tableaux-divers","icon": "table-2",   "droit": "GenTabDivers"},
                {"key": "export_tr",         "label": "Export Commande de TR",    "route": "/paies/export-tr",      "icon": "download",  "droit": "ExportTR"},
            ],
        },
        {
            "key": "comm",
            "label": "Comm",
            "section_droit": "Menu_COMM",
            "items": [
                {"key": "challenges",        "label": "Gestion des challenges",   "route": "/comm/challenges","icon":"trophy",        "droit": "GestChallenge"},
                {"key": "exo_cash",          "label": "Gestion Exo Cash",         "route": "/comm/exo-cash",  "icon":"banknote",      "droit": "GestExoCash"},
                {"key": "podiums",           "label": "Gestion des Podiums",      "route": "/comm/podiums",   "icon":"medal",         "droit": "GestPodium"},
                {"key": "sms_perf",          "label": "Gestion SMS Perf-Exo",     "route": "/comm/sms-perf",  "icon":"message-square","droit": "GestPerfExo"},
            ],
        },
        {
            "key": "scool",
            "label": "S'Cool",
            "section_droit": "Menu_Scool",
            "items": [
                {"key": "formations_liste",  "label": "Liste des formations",     "route": "/scool/formations","icon":"book-open","droit": "FormScool"},
                {"key": "planning_scool",    "label": "Planning S'Cool",          "route": "/scool/planning",  "icon":"calendar","droit": "FormScool"},
            ],
        },
        {
            "key": "salaries",
            "label": "Salariés",
            "section_droit": "Menu_Salariés",
            "items": [
                {"key": "registre_rh",       "label": "Registre RH",              "route": "/salaries/registre",       "icon":"book",           "droit": "RegistreRH"},
                {"key": "dpae",              "label": "Nouvelle DPAE",            "route": "/salaries/dpae",           "icon":"user-plus",      "droit": "NewDPAE"},
                {"key": "ctt_travail",       "label": "Liste des contrats de travail","route":"/salaries/contrats",   "icon":"file-signature", "droit": "CttW"},
                {"key": "formations_iag",    "label": "Suivi des formations IAG", "route": "/salaries/formations-iag", "icon":"graduation-cap", "droit": "impFormIAG"},
                {"key": "mutuelle",          "label": "Adhésion mutuelle entreprise","route":"/salaries/mutuelle",    "icon":"heart-pulse",    "droit": "GestMutuelle"},
                {"key": "params_rh",         "label": "Paramètres RH",            "route": "/salaries/parametres",     "icon":"settings",       "droit": "ParamRH"},
            ],
        },
        {
            "key": "ulease",
            "label": "Ulease",
            "section_droit": "Menu_Ulease",
            "items": [
                {"key": "parc_auto",         "label": "Suivi du Parc Auto",       "route": "/ulease/parc-auto","icon":"car",       "droit": "ParcAuto"},
                {"key": "ulease_docs",       "label": "Liste des documents ULEASE","route":"/ulease/documents","icon":"file-text", "droit": "ParcAuto"},
                {"key": "ulease_recherche",  "label": "Recherche Véhicule / Conducteur","route":"/ulease/recherche","icon":"search","droit": "ParcAuto"},
            ],
        },
        {
            "key": "recrutement",
            "label": "Recrutement",
            "section_droit": "Menu_Recrut",
            "items": [
                {"key": "recherche_cv",      "label": "Recherche CV",             "route": "/recrutement/recherche-cv","icon":"file-search",  "droit": "CV"},
                {"key": "recherche_cv_kw",   "label": "Recherche CV par mots clés","route":"/recrutement/recherche-cv-kw","icon":"search-code","droit": "CV"},
                {"key": "prevision_rec",     "label": "Prévision de recrutement", "route": "/recrutement/prevision",   "icon":"trending-up",  "droit": "PrevRec"},
                {"key": "agenda_rec",        "label": "Agenda de recrutement",    "route": "/agenda-recrutement",      "icon":"calendar-check","droit": "Menu_Recrut"},
                {"key": "saisie_cv",         "label": "Saisie de CV",             "route": "/recrutement/saisie-cv",   "icon":"file-plus",    "droit": "SaisieCV"},
                {"key": "cv_presaisis",      "label": "CV Pré-saisis",            "route": "/recrutement/cv-presaisis","icon":"files",        "droit": "SaisieCV"},
                {"key": "stats_rh",          "label": "Stats RH",                 "route": "/stat-rh",                 "icon":"bar-chart-3",  "droit": "StatRH"},
                {"key": "lieu_rdv",          "label": "Lieu de RDV",              "route": "/recrutement/lieu-rdv",    "icon":"map-pin",      "droit": "PrevRec"},
                {"key": "villes_favori",     "label": "Villes en favori",         "route": "/recrutement/villes",      "icon":"map",          "droit": "PrevRec"},
                {"key": "gestion_recruteurs","label": "Gestion des recruteurs",   "route": "/recrutement/recruteurs",  "icon":"users",        "droit": "GestRecrut"},
                {"key": "params_cvtheque",   "label": "Paramètre CVthèque",       "route": "/recrutement/parametres",  "icon":"settings",     "droit": "ParamCV"},
            ],
        },
    ]

    sections = []
    for s in sections_raw:
        if not _droit(user, s["section_droit"]):
            continue
        items_visible = []
        for it in s["items"]:
            if not _droit(user, it["droit"]):
                continue
            is_coded = it["key"] in _CODED_ITEMS
            if not is_progress_user and not is_coded:
                continue
            item = {k: v for k, v in it.items() if k != "droit"}
            item["visible"] = True
            item["coded"] = is_coded
            items_visible.append(item)
        if not items_visible:
            continue
        sections.append({
            "key": s["key"],
            "label": s["label"],
            "items": items_visible,
        })

    return {
        "menu_visible": True,
        "header_actions": header_actions,
        "sections": sections,
    }
