"""
SDTC - btn 'Génération du tableau à imprimer' + Récap BO.

Transposition fidèle :
1. Fusionne TableContrat + TableContrat1 -> TableContratTOT (1 ligne par
   contrat coché + non coché). Tri DESC par date_signature.
2. Construit TableRecapProd (compteurs par état) et TableRecapProdPts
   (sommes de points par état). États : En_Attente_CONTRAT / ENVOYE_CHEZ_OPE /
   REJETS_BO / RESILIATION / VALIDE_PAYE / DECOMMISION.
3. Calcule NB_TR (jours travaillés) :
   - Filtre : date_signature >= Date1, partenaire ∈ {ENI,IAG,SFR,OEN},
     type_etat contenant 'Résil' / 'Valid' / 'En Attente'
   - Pour SFR : type_prod = 2 (compte différemment)
   - 1 TR = jour avec >=3 contrats (TypeProd=1) ou >=1 contrat (TypeProd=2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .contrats import lib_type_vente_sfr
from .helpers import _int, _iso, _num, _str, normalize_nom_produit_recap


# Etats trackés dans TableRecapProd / TableRecapProdPts (cf. WinDev selon)
_RECAP_ETATS = (
    "En_Attente_CONTRAT",   # Temporaire
    "ENVOYE_CHEZ_OPE",       # En Attente opérateur
    "REJETS_BO",             # En Rejet ou Anomalie
    "RESILIATION",           # Résiliation
    "VALIDE_PAYE",           # Validé-Payé
    "DECOMMISION",           # Décommission
)


@dataclass
class RecapProdRow:
    lib_produit: str
    en_attente_contrat: float = 0.0
    envoye_chez_ope: float = 0.0
    rejets_bo: float = 0.0
    resiliation: float = 0.0
    valide_paye: float = 0.0
    decommision: float = 0.0

    def to_dict(self) -> dict:
        return {
            "lib_produit": self.lib_produit,
            "en_attente_contrat": self.en_attente_contrat,
            "envoye_chez_ope": self.envoye_chez_ope,
            "rejets_bo": self.rejets_bo,
            "resiliation": self.resiliation,
            "valide_paye": self.valide_paye,
            "decommision": self.decommision,
        }


@dataclass
class RecapResult:
    contrat_tot: list[dict] = field(default_factory=list)
    recap_prod: list[RecapProdRow] = field(default_factory=list)   # compteurs
    recap_prod_pts: list[RecapProdRow] = field(default_factory=list)  # points
    nb_tr: int = 0

    def to_dict(self) -> dict:
        return {
            "contrat_tot": self.contrat_tot,
            "recap_prod": [r.to_dict() for r in self.recap_prod],
            "recap_prod_pts": [r.to_dict() for r in self.recap_prod_pts],
            "nb_tr": self.nb_tr,
        }


def _ajoute_recap(
    rec_count: dict[str, RecapProdRow],
    rec_pts: dict[str, RecapProdRow],
    nom_prod: str,
    type_etat: str,
    pts: float,
) -> None:
    """Incrémente compteur + points selon le type_etat (cf. WinDev selon)."""
    if not nom_prod:
        return
    rc = rec_count.get(nom_prod)
    if rc is None:
        rc = RecapProdRow(lib_produit=nom_prod)
        rec_count[nom_prod] = rc
    rp = rec_pts.get(nom_prod)
    if rp is None:
        rp = RecapProdRow(lib_produit=nom_prod)
        rec_pts[nom_prod] = rp

    te = (type_etat or "").strip()
    if te == "Temporaire":
        rc.en_attente_contrat += 1
        rp.en_attente_contrat += pts
    elif te == "En Attente opérateur":
        rc.envoye_chez_ope += 1
        rp.envoye_chez_ope += pts
    elif te in ("En Rejet", "Anomalie"):
        rc.rejets_bo += 1
        rp.rejets_bo += pts
    elif te == "Résiliation":
        rc.resiliation += 1
        rp.resiliation += pts
    elif te == "Validé-Payé":
        rc.valide_paye += 1
        rp.valide_paye += pts
    elif te == "Décommission":
        rc.decommision += 1
        rp.decommision += pts


def _build_contrat_tot_row(ct: dict, *, stc_coche: bool) -> dict:
    """Construit une ligne de TableContratTOT depuis TableContrat ou TableContrat1."""
    partenaire = _str(ct.get("partenaire")).upper()
    lib_produit = _str(ct.get("lib_produit"))
    if partenaire == "SFR":
        sfr = ct.get("sfr") or {}
        if sfr.get("box8"):
            lib_produit += "+Box8"
        tv_lib = lib_type_vente_sfr(sfr.get("type_vente"))
        if tv_lib:
            lib_produit += f" - {tv_lib}"

    return {
        "id_contrat": str(ct.get("id_contrat")),
        "partenaire": partenaire,
        "client_nom": _str(ct.get("client_nom")),
        "client_adresse": _str(ct.get("client_adresse")),
        "client_cp": _str(ct.get("client_cp")),
        "client_ville_complete": (
            f"{_str(ct.get('client_ville'))} ({_str(ct.get('client_cp'))})"
        ).strip(),
        "num_bs": _str(ct.get("num_bs")),
        "date_signature": _iso(ct.get("date_signature")),
        "lib_produit": lib_produit,
        "type_prod": _str(ct.get("type_prod")),
        "etat_contrat": _str(ct.get("etat_contrat_lib")),
        "type_etat": _str(ct.get("type_etat_lib")),
        "mois_paiement": _str(ct.get("mois_paiement")),
        "nb_points": _num(ct.get("nb_points")),
        "stc": bool(stc_coche),
    }


def generer_tableau(
    *,
    contrats_traites: list[dict],
    contrats_a_traiter: list[dict],
    selected_ids_traites: set[str],
    selected_ids_a_traiter: set[str],
    date_ref: str,
) -> RecapResult:
    """Btn 'Génération du tableau à imprimer'.

    Args:
        date_ref: 'YYYY-MM-DD' utilisée pour filtrer le calcul NB_TR
                  (Date1 WinDev).
    """
    contrat_tot: list[dict] = []
    rec_count: dict[str, RecapProdRow] = {}
    rec_pts: dict[str, RecapProdRow] = {}

    # 1. TableContrat (traités finalisés)
    for ct in contrats_traites:
        stc_coche = str(ct.get("id_contrat")) in selected_ids_traites
        row = _build_contrat_tot_row(ct, stc_coche=stc_coche)
        contrat_tot.append(row)
        _ajoute_recap(
            rec_count,
            rec_pts,
            normalize_nom_produit_recap(_str(ct.get("lib_produit"))),
            _str(ct.get("type_etat_lib")),
            _num(ct.get("nb_points")),
        )

    # 2. TableContrat1 (en cours)
    for ct in contrats_a_traiter:
        stc_coche = str(ct.get("id_contrat")) in selected_ids_a_traiter
        row = _build_contrat_tot_row(ct, stc_coche=stc_coche)
        contrat_tot.append(row)
        _ajoute_recap(
            rec_count,
            rec_pts,
            normalize_nom_produit_recap(_str(ct.get("lib_produit"))),
            _str(ct.get("type_etat_lib")),
            _num(ct.get("nb_points")),
        )

    # 3. Tri DESC par date_signature
    contrat_tot.sort(key=lambda r: r["date_signature"] or "", reverse=True)

    # 4. NB_TR
    nb_tr = _calcule_nb_tr(contrat_tot, date_ref)

    return RecapResult(
        contrat_tot=contrat_tot,
        recap_prod=list(rec_count.values()),
        recap_prod_pts=list(rec_pts.values()),
        nb_tr=nb_tr,
    )


def _calcule_nb_tr(contrat_tot: list[dict], date_ref_iso: str) -> int:
    """Cf. WinDev :
      - Filtre : date_signature >= Date1, partenaire ∈ {ENI,IAG,SFR,OEN}
      - Type_Etat contient 'Résil' / 'Valid' / 'En Attente'
      - Comptage par jour
      - SFR : type_prod = 2 (compte avec seuil 1)
      - Autres : type_prod = 1 (compte avec seuil 3)
      - 1 TR = jour avec >=3 contrats (type=1) ou >=1 contrat (type=2)
    """
    if not date_ref_iso:
        return 0

    # Filtrage
    parts_eligibles = {"ENI", "IAG", "SFR", "OEN"}

    # {date_iso: (nb_count, type_prod)}
    par_jour: dict[str, list] = {}
    for ct in contrat_tot:
        date_sign = ct.get("date_signature") or ""
        if not date_sign or date_sign < date_ref_iso:
            continue
        partenaire = ct.get("partenaire") or ""
        if partenaire not in parts_eligibles:
            continue
        type_etat = ct.get("type_etat") or ""
        if not (
            "Résil" in type_etat
            or "Valid" in type_etat
            or "En Attente" in type_etat
        ):
            continue
        entry = par_jour.setdefault(date_sign, [0, 1])
        entry[0] += 1
        if partenaire == "SFR":
            entry[1] = 2

    nb_tr = 0
    for date_sign, (nb, type_prod) in par_jour.items():
        if type_prod == 1 and nb >= 3:
            nb_tr += 1
        elif type_prod == 2 and nb >= 1:
            nb_tr += 1
    return nb_tr


def to_iso_date(v) -> str:
    """Helper interne pour normaliser une date en ISO."""
    if v is None or v == "":
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    return _iso(v)
