"""Module Tickets partagé entre les intranets Vendeur et ADM.

L'affichage est filtré par droit utilisateur :
  - intranet ADM     : filtre sur TK_TypeDemande.DroitAccès
  - intranet Vendeur : filtre sur TK_TypeDemande.DroitAccèsVend

Les routers Vendeur et ADM montent le router shared en passant la clé du
champ droit à utiliser pour le filtrage.
"""
