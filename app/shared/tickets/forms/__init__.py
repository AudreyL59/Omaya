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
    avance,
    cartepro,
    conges,
    cttcourtage,
    cttw,
    cttw_demande,
    dpae,
    fourniture,
    rdvtech,
    resa,
    sosbo,
    sosju,
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
    13: conges,       # Congés
    17: sosju,        # SOS Juridique
    19: rdvtech,      # Retour RDV Tech FIBRE
    21: dpae,         # DPAE à venir (même formulaire)
    23: cttcourtage,  # Contrat de Courtage / Attestation
    40: cttw_demande,  # Contrat W - Demande
}
