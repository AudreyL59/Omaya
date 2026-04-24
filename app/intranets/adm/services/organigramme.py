"""
Service Organigramme ADM : accès global systématique.

Reprend get_organigramme de vendeur en forçant acces_global=True
(pas de filtrage par droits / responsabilité).
"""

from app.intranets.vendeur.services.organigramme import get_organigramme as _base_orga


def get_organigramme_adm() -> list[dict]:
    """
    ADM : accès global → on appelle la fonction vendeur en simulant ProdRezo.
    """
    # id_salarie_user=0 + droits=["ProdRezo"] déclenche acces_global=True côté
    # service vendeur, ce qui ignore la clause par droits/responsabilité.
    return _base_orga(id_salarie_user=0, droits=["ProdRezo"], is_resp=True)
