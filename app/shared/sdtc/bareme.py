"""
SDTC : calcul du bareme + commissions a partir des contrats selectionnes.

Transposition du bloc WinDev "Btn Valider la selection et passer a l'etape
suivante" de Fen_SDTC. Pour chaque contrat selectionne :

    nomProd = ExtraitChaine(Lib_Produit, 1, "(")
    si nomProd in {"TELE 7 JOUR", "ELLE", "PARIS MATCH"}:
        nomProd = "HACHETTE"

    TableProduitSTC[nomProd].QTE += 1

    si Partenaire contient "ENI":
        si TypeProd contient "ELEC": Valeur += 8
        si TypeProd contient "GAZ" : Nb_Pts += NB_Points
    sinon:
        Nb_Pts += NB_Points

Puis :
    NB_Tot_Pts    = somme(Nb_Pts)
    NB_Tot_Ctts   = somme(QTE)
    Total_Valeurs = somme(Valeur)

Bareme (paliers ENI / SFR) :
    < 21 pts  -> 5
    < 41 pts  -> 20
    < 61 pts  -> 25
    < 81 pts  -> 30
    >= 81 pts -> 35

COmm_Pts_Ctts = NB_Tot_Pts * Bareme
Comm_Tot_STC  = COmm_Pts_Ctts + Total_Valeurs
"""

from __future__ import annotations

from dataclasses import dataclass, field

_PRESS_NAMES = {"TELE 7 JOUR", "ELLE", "PARIS MATCH"}


def _normalize_nom_produit(lib_produit: str) -> str:
    """Extrait le nom du produit (avant '(') et regroupe la presse Hachette."""
    nom = (lib_produit or "").split("(", 1)[0].strip()
    if nom.upper() in _PRESS_NAMES:
        return "HACHETTE"
    return nom


@dataclass
class ProduitSTC:
    lib_produit: str
    qte: int = 0
    nb_pts: float = 0.0
    valeur: float = 0.0


@dataclass
class BaremeResult:
    produits: list[ProduitSTC] = field(default_factory=list)
    nb_tot_pts: float = 0.0
    nb_tot_ctts: int = 0
    total_valeurs: float = 0.0
    bareme: float = 0.0
    comm_pts_ctts: float = 0.0
    comm_tot_stc: float = 0.0

    def to_dict(self) -> dict:
        return {
            "produits": [
                {
                    "lib_produit": p.lib_produit,
                    "qte": p.qte,
                    "nb_pts": p.nb_pts,
                    "valeur": p.valeur,
                }
                for p in self.produits
            ],
            "nb_tot_pts": self.nb_tot_pts,
            "nb_tot_ctts": self.nb_tot_ctts,
            "total_valeurs": self.total_valeurs,
            "bareme": self.bareme,
            "comm_pts_ctts": self.comm_pts_ctts,
            "comm_tot_stc": self.comm_tot_stc,
        }


def _palier(nb_tot_pts: float) -> float:
    if nb_tot_pts < 21:
        return 5
    if nb_tot_pts < 41:
        return 20
    if nb_tot_pts < 61:
        return 25
    if nb_tot_pts < 81:
        return 30
    return 35


def compute_bareme(contrats: list[dict]) -> BaremeResult:
    """Calcule le bareme + commissions a partir des contrats selectionnes.

    Chaque contrat doit fournir au moins :
      - lib_produit (str)
      - partenaire  (str)  ex. 'ENI', 'SFR', 'OEN'
      - type_prod   (str)  ex. 'ELEC', 'GAZ', 'BOX'
      - nb_points   (int / float)
    """
    produits_by_nom: dict[str, ProduitSTC] = {}

    for ct in contrats:
        nom = _normalize_nom_produit(str(ct.get("lib_produit") or ""))
        if not nom:
            continue
        p = produits_by_nom.get(nom)
        if p is None:
            p = ProduitSTC(lib_produit=nom)
            produits_by_nom[nom] = p

        p.qte += 1

        partenaire = str(ct.get("partenaire") or "").upper()
        type_prod = str(ct.get("type_prod") or "").upper()
        try:
            pts_ctt = float(ct.get("nb_points") or 0)
        except (TypeError, ValueError):
            pts_ctt = 0.0

        if "ENI" in partenaire:
            if "ELEC" in type_prod:
                p.valeur += 8
            if "GAZ" in type_prod:
                p.nb_pts += pts_ctt
        else:
            p.nb_pts += pts_ctt

    produits = list(produits_by_nom.values())
    nb_tot_pts = sum(p.nb_pts for p in produits)
    nb_tot_ctts = sum(p.qte for p in produits)
    total_valeurs = sum(p.valeur for p in produits)

    bareme = _palier(nb_tot_pts)
    comm_pts_ctts = nb_tot_pts * bareme
    comm_tot_stc = comm_pts_ctts + total_valeurs

    return BaremeResult(
        produits=produits,
        nb_tot_pts=nb_tot_pts,
        nb_tot_ctts=nb_tot_ctts,
        total_valeurs=total_valeurs,
        bareme=bareme,
        comm_pts_ctts=comm_pts_ctts,
        comm_tot_stc=comm_tot_stc,
    )
