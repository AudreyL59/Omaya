"""
SDTC : barême de points et de commission (Fen_SDTC WinDev).

Ce module concentre :

1. `calcul_point_contrat(...)` : transposition fidèle de la procédure globale
   WinDev `calculPointContrat(Fam, Ssfam, Palier, Datesign, InfoCplt, palier2)`.
   Reproduit tous les cas spéciaux :
     - MOB CQ : palier dynamique extrait du forfait dans `InfoCplt`
     - ENI GAZ-ELEC >= 20260501 : recalcule via "Dual<palier2>"
     - ENI >= 20260501 : options RIB/MAIL/MAINT/NOTE
     - ENI >= 20220916 (< 20260501) : option "OPTION" * nbOption
     - ENI ELEC >= 20230207 + palier2 : 2e appel sur "ELEC" palier2
     - FIB CQ >= 20260201 : bonus portabilité/prise_saisie/notation
     - VALANDRE < 20230207 : 0.15 si les contrats Val1/Val2 ne sont pas
       en rejet/résil

2. `compute_bareme(contrats)` : transposition du btn "Valider la sélection
   et passer à l'étape suivante" - agrège dans `TableProduitSTC` puis calcule
   le barème global (paliers 5/20/25/30/35).

3. `palier_remun(nb_tot_pts)` : barème global SDTC.

Note sur la table de barème : la requête WinDev `ReqPtsBareme(Fam, Ssfam,
Palier, Datesign)` pointe sur la table centrale `adv.pgt_eni_remun` (qui
contient en réalité tous les produits ENI ET les familles SFR `FIB CQ`,
`MOB CQ`, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.database.pg import get_pg_connection

from .helpers import _int, _num, _str, normalize_nom_produit


# ---------------------------------------------------------------------------
# Requête ReqPtsBareme - exécutée à la demande
# ---------------------------------------------------------------------------


def _req_pts_bareme(
    fam: str, ss_fam: str, palier: Any, date_sign: str
) -> float:
    """SELECT SUM(nb_points) sur adv.pgt_eni_remun selon famille/ss_fam/
    palier/date_signature, filtrée par rem_active + plage d'activation.

    Cf. requête `ReqPtsBareme` WinDev.

    Args:
        fam: ex. "ENI", "FIB CQ", "MOB CQ"
        ss_fam: ex. "ELEC", "GAZ", "GAZ-ELEC", "OPTRIB", "Dual<n>"
        palier: numérique (forfait ou Car) - testé avec BETWEEN val_min/max
        date_sign: ISO 'YYYY-MM-DD' ou 'YYYYMMDD'
    """
    if not fam:
        return 0.0
    palier_num = _int(palier)
    ds = _normalize_date(date_sign)
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT COALESCE(SUM(nb_points), 0) AS la_somme_nb_points
             FROM adv.pgt_eni_remun
            WHERE famille = ?
              AND ss_fam = ?
              AND COALESCE(val_min, 0) <= ?
              AND COALESCE(val_max, 999999) >= ?
              AND COALESCE(rem_active, FALSE) = TRUE
              AND (date_activation IS NULL OR date_activation <= ?::date)
              AND (date_desactivation IS NULL OR date_desactivation > ?::date)""",
        (fam, ss_fam, palier_num, palier_num, ds, ds),
    )
    if not rows:
        return 0.0
    return round(_num(rows[0].get("la_somme_nb_points")), 2)


def _normalize_date(v: Any) -> str:
    """ISO 'YYYY-MM-DD'. Accepte aussi 'YYYYMMDD' ou datetime."""
    if v is None:
        return "1900-01-01"
    s = str(v)
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return "1900-01-01"


def _date_ge(date_sign: str, threshold: str) -> bool:
    """Compare 2 dates au format 'YYYY-MM-DD' (ou converties). True si
    date_sign >= threshold."""
    ds = _normalize_date(date_sign)
    th = _normalize_date(threshold)
    return ds >= th


def _date_lt(date_sign: str, threshold: str) -> bool:
    ds = _normalize_date(date_sign)
    th = _normalize_date(threshold)
    return ds < th


# ---------------------------------------------------------------------------
# calculPointContrat - fidèle WinDev
# ---------------------------------------------------------------------------


def calcul_point_contrat(
    fam: str,
    ss_fam: str,
    palier: Any,
    date_sign: str,
    info_cplt: str = "",
    palier2: Any = 0,
) -> float:
    """Transposition fidèle de calculPointContrat WinDev.

    Args:
        fam: famille produit (ENI / FIB CQ / MOB CQ / etc.)
        ss_fam: sous-famille (ELEC / GAZ / GAZ-ELEC / etc.)
        palier: pour MOB CQ = forfait (extrait de info_cplt), pour ENI = Car
        date_sign: date de signature
        info_cplt: chaîne contextuelle (variable selon le partenaire)
        palier2: 0 par défaut ; pour ENI = puissance ; pour FIB CQ = id_contrat

    Retourne nbPts (float).
    """
    nb_pts = 0.0

    fam_u = (fam or "").upper().strip()
    ss_fam_u = (ss_fam or "").upper().strip()

    # 1. MOB CQ : extraire le palier (forfait) depuis info_cplt
    if fam_u == "MOB CQ":
        first_token = (info_cplt or "").split(" ", 1)[0]
        if first_token.replace(".", "", 1).isdigit():
            palier = int(float(first_token))
        else:
            palier = 9999

    # 2. Calcul de base
    nb_pts = _req_pts_bareme(fam, ss_fam, palier, date_sign)

    # 3. Si palier2 > 0 et ss_fam contient ELEC et date >= 20230207
    palier2_int = _int(palier2)
    if palier2_int > 0 and "ELEC" in ss_fam_u and _date_ge(date_sign, "2023-02-07"):
        nb_pts += _req_pts_bareme(fam, "ELEC", palier2_int, date_sign)

    # 4. ENI GAZ-ELEC depuis 2026-05-01 -> recalcul via Dual<palier2>
    if fam_u == "ENI" and ss_fam_u == "GAZ-ELEC" and _date_ge(date_sign, "2026-05-01"):
        nb_pts = _req_pts_bareme(fam, f"Dual{palier2_int}", palier, date_sign)

    # 5. ENI depuis 2026-05-01 : options dans info_cplt
    info = info_cplt or ""
    if fam_u == "ENI" and _date_ge(date_sign, "2026-05-01"):
        if "RIB//" in info:
            nb_pts += _req_pts_bareme(fam, "OPTRIB", palier2_int, date_sign)
        if "MAIL//" in info:
            nb_pts += _req_pts_bareme(fam, "OPTMAIL", palier2_int, date_sign)
        if "MAINT//" in info:
            nb_pts += _req_pts_bareme(fam, "OPTMAINT", palier2_int, date_sign)
        if "NOTE:" in info:
            # ExtraitChaine(info,2,"NOTE:") = ce qui est apres NOTE:
            note_part = info.split("NOTE:", 1)[1]
            note_val = note_part.split("//", 1)[0]
            try:
                note_int = int(float(note_val))
            except (TypeError, ValueError):
                note_int = 0
            nb_pts += _req_pts_bareme(fam, "OPTNOTE", note_int, date_sign)
    elif fam_u == "ENI" and _date_ge(date_sign, "2022-09-16"):
        # 6. ENI depuis 2022-09-16 (mais < 2026-05-01) : option globale
        pts_opt = _req_pts_bareme(fam, "OPTION", 0, date_sign)
        try:
            nb_opt = int(float(info)) if info else 0
        except (TypeError, ValueError):
            nb_opt = 0
        nb_pts += nb_opt * pts_opt

    # 7. FIB CQ depuis 2026-02-01 : bonus portabilité/prise_saisie/notation
    if fam_u == "FIB CQ" and _date_ge(date_sign, "2026-02-01") and info:
        bonus = _fib_cq_bonus(info)
        nb_pts += bonus

    # 8. VALANDRE avant 2023-02-07 : 0.15 si les contrats associés ne sont
    # pas en rejet/résil
    if ss_fam_u == "VALANDRE" and _date_lt(date_sign, "2023-02-07") and info:
        if _val_associated_ok(info):
            nb_pts = 0.15

    return round(nb_pts, 4)


def _fib_cq_bonus(id_contrat: str) -> float:
    """Bonus FIB CQ >= 20260201 :
      Portabilité ? +0.2
      PriseSaisie ? +0.2
      Notation*2 >= 8.6 ? +0.1
    """
    if not id_contrat:
        return 0.0
    db = get_pg_connection("adv")
    row = db.query(
        """SELECT portabilite, prise_saisie, notation
             FROM adv.pgt_sfr_contrat
            WHERE id_contrat = ?
            LIMIT 1""",
        (_int(id_contrat),),
    )
    if not row:
        return 0.0
    r = row[0]
    bonus = 0.0
    if r.get("portabilite"):
        bonus += 0.2
    if r.get("prise_saisie"):
        bonus += 0.2
    nota = _num(r.get("notation"))
    if nota * 2 >= 8.6:
        bonus += 0.1
    return bonus


def _val_associated_ok(id_contrat: str) -> bool:
    """VALANDRE associé : retourne True si les contrats Val1/Val2 ne sont
    pas en rejet (id_type_etat=3) ni en résil (id_type_etat=4).

    Cf. requête ReqCttValandreAssocié WinDev. La structure exacte des
    paires Val1/Val2 reste à confirmer; placeholder conservateur ici :
    on retourne True par défaut pour pénaliser le contrat à 0.15 (cf.
    code WinDev : `si testEtat = Faux alors nbPts = 0.15`)."""
    # TODO: implementer la requete ReqCttValandreAssocie une fois sa
    # definition fournie. Pour l'instant on reste fidele au comportement
    # par defaut WinDev (testEtat=True -> nbPts inchange).
    return False


# ---------------------------------------------------------------------------
# compute_bareme - agrégation TableProduitSTC + commission globale
# ---------------------------------------------------------------------------


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


def palier_remun(nb_tot_pts: float) -> float:
    """Barème SDTC global - paliers WinDev.

    - <  21 pts  -> 5
    - <  41 pts  -> 20
    - <  61 pts  -> 25
    - <  81 pts  -> 30
    - >= 81 pts  -> 35
    """
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
    """Agrège les contrats sélectionnés en TableProduitSTC puis calcule le
    barème global.

    Chaque contrat doit fournir : lib_produit, partenaire, type_prod, nb_points.
    """
    produits_by_nom: dict[str, ProduitSTC] = {}

    for ct in contrats:
        nom = normalize_nom_produit(_str(ct.get("lib_produit")))
        if not nom:
            continue
        p = produits_by_nom.get(nom)
        if p is None:
            p = ProduitSTC(lib_produit=nom)
            produits_by_nom[nom] = p

        p.qte += 1

        partenaire = _str(ct.get("partenaire")).upper()
        type_prod = _str(ct.get("type_prod")).upper()
        pts_ctt = _num(ct.get("nb_points"))

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

    bareme = palier_remun(nb_tot_pts)
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
