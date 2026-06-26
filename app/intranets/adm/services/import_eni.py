"""Service Fen_ImportENI (ADM Imports Bases -> Import partenaire ENI/PLENITUDE).

5 types d'import :
 1. Base Journaliere CALL  -> ImportJournalier()
 2. RUN Valides             -> importRUNValides()
 3. RUN Resils              -> importRUNResil()
 4. Salesforce              -> ImportSalesforce()
 5. Base journaliere ENI    -> ImportJournalierENI()

Pour chaque type, lecture d'un Excel + analyse + 6 tables resultats :
 - Resume importation (compteurs)
 - Contrats modifies
 - Contrats non trouves
 - Contrats RUN
 - Probleme Vendeur
 - Contrat Import Journ ENI

Les procedures metier seront codees au fur et a mesure (placeholder
pour l'instant : retourne un resume vide + erreur 'pas encore code').
"""

from __future__ import annotations

import io
from typing import Optional

from pydantic import BaseModel


class ImportEniParams(BaseModel):
    type_import: int                  # 1..5
    simulation: bool = True
    periode1_du: str = ""
    periode1_au: str = ""
    periode1_mois_paiement: str = ""  # 'MM-YYYY'
    periode2_du: str = ""
    periode2_au: str = ""
    periode2_mois_paiement: str = ""
    mois_paiement_distrib: str = ""
    maj_produit_contrat_stand: bool = True
    maj_etats_contrats_existants: bool = False


class ImportEniResume(BaseModel):
    nb_valides: int = 0
    nb_deja_statues: int = 0
    nb_doublons: int = 0
    nb_introuvables: int = 0
    nb_decommissions: int = 0
    nb_resilies: int = 0
    nb_modifications: int = 0
    nb_erreurs_mails: int = 0
    nb_erreurs_entretien: int = 0
    nb_contrats_hors_delai: int = 0
    nb_erreurs_offres: int = 0
    nb_erreurs_type_comptage: int = 0
    nb_erreurs_energie_verte: int = 0
    nb_erreurs_car: int = 0
    nb_erreurs_puiss: int = 0
    nb_erreurs_reforest: int = 0
    nb_erreurs_protection: int = 0


class ImportEniResult(BaseModel):
    ok: bool
    type_import: int
    type_label: str
    simulation: bool
    resume: ImportEniResume
    contrats_modifies: list[dict] = []
    contrats_non_trouves: list[dict] = []
    contrats_run: list[dict] = []
    pb_vendeur: list[dict] = []
    contrat_import_journ_eni: list[dict] = []
    message: str = ""


TYPE_LABELS = {
    1: "Base Journalière CALL",
    2: "RUN Valides",
    3: "RUN Résils",
    4: "Salesforce",
    5: "Base journalière ENI",
}


def run_import(p: ImportEniParams, file_bytes: bytes, op_id: int) -> ImportEniResult:
    """Dispatcher principal. Renvoie un placeholder tant que les
    procedures metier ne sont pas codees."""
    label = TYPE_LABELS.get(p.type_import, "?")
    if not file_bytes:
        return ImportEniResult(
            ok=False, type_import=p.type_import, type_label=label,
            simulation=p.simulation, resume=ImportEniResume(),
            message="Aucun fichier fourni.",
        )

    # TODO : appeler la procedure correspondante quand codee :
    # if p.type_import == 1: return _import_journalier_call(p, file_bytes, op_id)
    # if p.type_import == 2: return _import_run_valides(p, file_bytes, op_id)
    # if p.type_import == 3: return _import_run_resils(p, file_bytes, op_id)
    # if p.type_import == 4: return _import_salesforce(p, file_bytes, op_id)
    # if p.type_import == 5: return _import_journalier_eni(p, file_bytes, op_id)

    return ImportEniResult(
        ok=True, type_import=p.type_import, type_label=label,
        simulation=p.simulation, resume=ImportEniResume(),
        message=(f"Import {label} : procedure non encore codée. "
                 f"Fichier reçu ({len(file_bytes)} octets), mode "
                 f"{'simulation' if p.simulation else 'PRODUCTION'}."),
    )
