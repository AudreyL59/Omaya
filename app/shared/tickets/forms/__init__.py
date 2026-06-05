"""Formulaires "Détail du ticket" (fenêtres internes WinDev FI_*).

Architecture : un module par type de demande, exposant deux fonctions :

    def load(id_ticket: int) -> dict
    def save(id_ticket: int, payload: dict, user_id: int) -> dict

Le registre FORM_HANDLERS mappe IDTK_TypeDemande → module. Le router
expose des endpoints génériques /tickets/{id}/form (GET/POST) qui
dispatchent vers le bon handler selon le type du ticket.

Ordre d'implémentation = ordre du switch WinDev (Fen_TicketContenu).
"""

from . import (
    attexocash,
    avance,
    cartepro,
    cdeexocash,
    code_vendeur,
    conges,
    cttcourtage,
    cttw,
    cttw_demande,
    docdistrib,
    dpae,
    dpaedistrib,
    factdistrib,
    facturedr,
    fourniture,
    mutuelle,
    rdvtech,
    resa,
    sortie_rh,
    sosbo,
    sosju,
    ulease,
    ulease_pv,
)

# IDTK_TypeDemande → module handler
FORM_HANDLERS: dict[int, object] = {
    1: fourniture,    # Commande Fourniture
    2: cartepro,      # Carte PRO
    3: dpae,          # DPAE
    4: cttw,          # Contrat W - Signature
    9: resa,          # Réservation
    10: avance,       # Demande d'avance
    11: sosbo,        # SOS BO
    12: sortie_rh,    # Sortie RH (sans SDTC)
    13: conges,       # Congés
    17: sosju,        # SOS Juridique
    19: rdvtech,      # Retour RDV Tech FIBRE
    21: dpae,         # DPAE à venir (même formulaire)
    23: cttcourtage,  # Contrat de Courtage / Attestation
    24: cdeexocash,   # Commande ExoCash
    25: attexocash,   # Attribution ExoCash
    27: mutuelle,     # Demande Mutuelle
    28: factdistrib,  # Facturation Distrib
    29: dpaedistrib,  # Nouveau Vendeur Distrib (FI_DPAEDistrib)
    30: dpaedistrib,  # Intégration Nouveau Distrib (FI_DPAEDistrib)
    31: docdistrib,   # Réclamation Documents (FI_DocDistrib)
    33: facturedr,    # Facture BO (FI_FactureDR)
    34: ulease,       # Signature Doc ULEASE (FI_DocUlease)
    35: ulease_pv,    # PV Liv/Rest ULEASE (FI_UleasePVLivRest)
    36: sortie_rh,    # Sortie FPE / Démission (FI_SortieRH)
    37: sortie_rh,    # Sortie Licenciement / Rupture (FI_SortieRH)
    38: code_vendeur,  # Demande Code Vendeur (FI_DemandeCodeVendeur)
    39: code_vendeur,  # Désactivation Code Vendeur (FI_DemandeCodeVendeur)
    40: cttw_demande,  # Contrat W - Demande
}
