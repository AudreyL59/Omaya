"""Service Fen_ImportIAG (ADM Imports Bases -> Import partenaire IAG).

2 types d'import (vs 4 pour ENI) :
 1. Base Journalière -> importJournalier()
 2. RUN              -> importValide() ou importResil() selon le nom
    du fichier ('ANNUL' dedans -> resil, sinon valide).

Multi-fichier : sFichier WinDev contient plusieurs noms separes par RC,
le frontend peut en uploader plusieurs d'un coup.

Specificite IAG : c'est une assurance, donc pas de gaz/elec/CAR/puissance
(simplifie vs ENI). Juste num_bs, id_produit, id_etat_contrat,
date_signature, id_salarie, id_client.

Les procedures metier seront codees au fur et a mesure (placeholder
pour l'instant).
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ImportIagParams(BaseModel):
    type_import: int                # 1 = Base Journ, 2 = RUN
    simulation: bool = True
    format_vendeur: str = "prenom_nom"   # 'prenom_nom' ou 'nom_prenom'
    periode1_du: str = ""
    periode1_au: str = ""
    periode1_mois_paiement: str = ""
    periode2_du: str = ""
    periode2_au: str = ""
    periode2_mois_paiement: str = ""
    mois_paiement_distrib: str = ""


class ImportIagResume(BaseModel):
    nb_fichiers: int = 0
    nb_ajoutes: int = 0
    nb_valides: int = 0
    nb_resilies: int = 0
    nb_deja_saisis: int = 0           # type 1 : "deja saisi"
    nb_deja_statues: int = 0          # type 2 : "deja statue"
    nb_introuvables: int = 0
    nb_doublons: int = 0
    nb_pb_vendeur: int = 0
    nb_erreurs: int = 0


class ImportIagResult(BaseModel):
    ok: bool
    type_import: int
    type_label: str
    simulation: bool
    resume: ImportIagResume
    fichiers_traites: list[str] = []
    contrats_ajoutes: list[dict] = []
    contrats_modifies: list[dict] = []         # 'deja saisis' / 'deja statues'
    contrats_non_trouves: list[dict] = []
    contrats_run: list[dict] = []
    pb_vendeur: list[dict] = []                # = onglet 'Erreurs' si type 2
    message: str = ""
    xlsx_b64: str = ""
    xlsx_name: str = ""
    mail_envoye: bool = False


TYPE_LABELS = {
    1: "Base Journalière",
    2: "RUN",
}


def run_import_iag(
    p: ImportIagParams, files: list[tuple[str, bytes]], op_id: int,
) -> ImportIagResult:
    """Dispatcher principal. `files` est une liste de tuples
    (nom_fichier, contenu_bytes)."""
    label = TYPE_LABELS.get(p.type_import, "?")
    if not files:
        return ImportIagResult(
            ok=False, type_import=p.type_import, type_label=label,
            simulation=p.simulation, resume=ImportIagResume(),
            message="Aucun fichier fourni.",
        )

    resume = ImportIagResume(nb_fichiers=len(files))
    ajoutes: list[dict] = []
    modifies: list[dict] = []
    non_trouves: list[dict] = []
    runs: list[dict] = []
    pb_vendeur: list[dict] = []
    fichiers_traites: list[str] = []

    for fname, content in files:
        fichiers_traites.append(fname)
        # TODO : appeler la procedure metier quand codee :
        # if p.type_import == 1:
        #     _import_journalier_iag(p, fname, content, op_id, resume, ...)
        # else:
        #     if 'ANNUL' in fname.upper():
        #         _import_resil_iag(...)
        #     else:
        #         _import_valide_iag(...)
        pass

    return ImportIagResult(
        ok=True, type_import=p.type_import, type_label=label,
        simulation=p.simulation, resume=resume,
        fichiers_traites=fichiers_traites,
        contrats_ajoutes=ajoutes,
        contrats_modifies=modifies,
        contrats_non_trouves=non_trouves,
        contrats_run=runs,
        pb_vendeur=pb_vendeur,
        message=(
            f"{len(files)} fichier(s) reçu(s). Logique métier non encore codée "
            f"(squelette en place). Mode "
            f"{'simulation' if p.simulation else 'PRODUCTION'}."
        ),
    )
