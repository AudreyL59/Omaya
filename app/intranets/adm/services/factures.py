"""Service Fen_FacturesSuivi (ADM > Suivi des factures).

Transposition WinDev : recherche multi-critères dans la table
`divers.pgt_commande` avec indicateur visuel selon presence/montant
de la facture jointe dans `divers.pgt_commande_facture`.

Indicateur (etat) :
  - 'ok'        : montant facture = montant commande (vert)
  - 'partiel'   : facture presente mais montant != commande (orange)
  - 'ko'        : pas de facture ou montant 0 (rouge)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


# ---------- Schemas ----------------------------------------------------

class OperateurItem(BaseModel):
    id_salarie: str
    nom_prenom: str


class EnseigneItem(BaseModel):
    enseigne: str


class SocieteItem(BaseModel):
    id_ste: str
    raison_sociale: str
    rs_interne: str = ""


class FactureSearchFilters(BaseModel):
    du: Optional[date] = None
    au: Optional[date] = None
    num_commande: str = ""
    id_ope_achat: int = 0           # 0 = tous
    id_ste: int = 0                 # 0 = toutes
    enseigne: str = ""              # '' ou '%' = toutes
    mode_paiement: str = ""         # '' ou '%' = tous (CB/CBL/CH/PRLV/ESP)
    description: str = ""           # recherche contient
    montant_min: float = 0.0
    montant_max: float = 0.0
    # Bénéficiaire : soit salarié (bene_service=False) soit service
    # (bene_service=True). 0 = pas de filtre bénéficiaire.
    bene_service: bool = False
    bene_id: int = 0


class FactureLigne(BaseModel):
    id_commande: str
    date_achat: str = ""
    ope_achat_nom: str = ""
    enseigne: str = ""
    num_commande: str = ""
    description: str = ""
    montant_ttc: float = 0.0
    mode_paiement: str = ""
    bene_nom: str = ""              # nom salarié ou libellé service
    bene_service: bool = False
    etat: str = "ko"                # ok / partiel / ko
    montant_facture: float = 0.0


# ---------- Référentiels (combo) ---------------------------------------


def list_operateurs_staff() -> list[OperateurItem]:
    """Liste des salaries actifs en categorie STAFF avec nom (Prenom)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT DISTINCT s.id_salarie,
                  s.nom,
                  s.prenom,
                  tp.lib_poste
             FROM rh.pgt_salarie s
             JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
             JOIN rh.pgt_type_poste tp ON tp.id_type_poste = se.id_type_poste
            WHERE (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
              AND tp.categorie = 'STAFF'
            ORDER BY s.nom, s.prenom"""
    ) or []
    out: list[OperateurItem] = []
    for r in rows:
        nom = (r.get("nom") or "").strip()
        prenom = (r.get("prenom") or "").strip()
        prenom_fmt = (prenom[:1].upper() + prenom[1:].lower()) if prenom else ""
        lib = r.get("lib_poste") or ""
        label = f"{nom} {prenom_fmt}"
        if lib:
            label += f" ({lib})"
        out.append(OperateurItem(
            id_salarie=str(r["id_salarie"]),
            nom_prenom=label,
        ))
    return out


def list_enseignes() -> list[EnseigneItem]:
    """Liste DISTINCT des enseignes presentes dans pgt_commande."""
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT DISTINCT enseigne FROM divers.pgt_commande
            WHERE enseigne IS NOT NULL AND enseigne <> ''
            ORDER BY enseigne"""
    ) or []
    return [EnseigneItem(enseigne=r["enseigne"]) for r in rows]


def list_societes() -> list[SocieteItem]:
    """Liste des societes (rs_interne en priorite pour affichage)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, raison_sociale, rs_interne FROM rh.pgt_societe
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY COALESCE(NULLIF(rs_interne, ''), raison_sociale)"""
    ) or []
    return [SocieteItem(
        id_ste=str(r["id_ste"]),
        raison_sociale=r.get("raison_sociale") or "",
        rs_interne=r.get("rs_interne") or "",
    ) for r in rows]


# ---------- Recherche principale --------------------------------------


_PAIEMENT_LABELS = {
    "CB": "CB", "CBL": "Carte Logée", "CH": "Chèque",
    "PRLV": "Prélèvement", "ESP": "Espèce",
}


def _capitalize_prenom(p: str) -> str:
    return (p[:1].upper() + p[1:].lower()) if p else ""


def search_factures(f: FactureSearchFilters) -> list[FactureLigne]:
    """Recherche les commandes selon les filtres + calcule l'indicateur
    visuel (etat) par comparaison avec la SUM des facture(s) jointes.
    """
    db_d = get_pg_connection("divers")
    db_rh = get_pg_connection("rh")

    where = ["(c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')"]
    params: list = []

    # Dates : si num_commande fourni, on elargit la plage (WinDev = 20100101 -> auj)
    if f.num_commande:
        where.append("c.num_commande ILIKE ?")
        params.append(f"%{f.num_commande}%")
    else:
        if f.du:
            where.append("c.date_achat >= ?")
            params.append(f.du)
        if f.au:
            where.append("c.date_achat <= ?")
            params.append(f.au)

    if f.id_ope_achat:
        where.append("c.ope_achat = ?")
        params.append(int(f.id_ope_achat))
    if f.id_ste:
        where.append("c.id_ste = ?")
        params.append(int(f.id_ste))
    if f.enseigne and f.enseigne not in ("%", ""):
        where.append("c.enseigne = ?")
        params.append(f.enseigne)
    if f.mode_paiement and f.mode_paiement not in ("%", ""):
        where.append("c.mode_paiement = ?")
        params.append(f.mode_paiement)
    if f.description:
        where.append("c.description ILIKE ?")
        params.append(f"%{f.description}%")
    if f.bene_id:
        where.append("c.bene_service = ?")
        where.append("c.bene_id = ?")
        params.append(bool(f.bene_service))
        params.append(int(f.bene_id))

    # Filtre montant : si min OU max fourni, applique sur montant_ttc commande
    # ET (via UNION) sur montant_ttc des factures associees (WinDev fait
    # 2 requetes successives et merge ; on simplifie en OR via EXISTS).
    montant_filter_sql = ""
    if f.montant_min > 0 or f.montant_max > 0:
        mn = f.montant_min if f.montant_min > 0 else 0
        mx = f.montant_max if f.montant_max > 0 else 99999999
        montant_filter_sql = (
            " AND (c.montant_ttc BETWEEN ? AND ? OR EXISTS ("
            "  SELECT 1 FROM divers.pgt_commande_facture cf"
            "   WHERE cf.id_commande = c.id_commande"
            "     AND (cf.modif_elem IS NULL OR cf.modif_elem NOT LIKE '%suppr%')"
            "     AND cf.montant_ttc BETWEEN ? AND ?))"
        )
        params.extend([mn, mx, mn, mx])

    sql = f"""
        SELECT c.id_commande, c.date_achat, c.ope_achat, c.num_commande,
               c.description, c.enseigne, c.mode_paiement,
               c.montant_ttc, c.bene_service, c.bene_id,
               COALESCE((
                  SELECT SUM(cf.montant_ttc)
                    FROM divers.pgt_commande_facture cf
                   WHERE cf.id_commande = c.id_commande
                     AND (cf.modif_elem IS NULL OR cf.modif_elem NOT LIKE '%suppr%')
               ), 0) AS montant_facture
          FROM divers.pgt_commande c
         WHERE {' AND '.join(where)}{montant_filter_sql}
         ORDER BY c.date_achat ASC
         LIMIT 5000
    """
    rows = db_d.query(sql, tuple(params)) or []

    # Resolution noms beneficiaires (en batch pour eviter N+1)
    id_sals: set[int] = set()
    id_orgas: set[int] = set()
    id_opes: set[int] = set()
    for r in rows:
        if r.get("bene_service"):
            if r.get("bene_id"): id_orgas.add(int(r["bene_id"]))
        else:
            if r.get("bene_id"): id_sals.add(int(r["bene_id"]))
        if r.get("ope_achat"): id_opes.add(int(r["ope_achat"]))

    salaries_map: dict[int, str] = {}
    if id_sals or id_opes:
        ids = ",".join(str(i) for i in (id_sals | id_opes))
        rows_s = db_rh.query(
            f"""SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
                 WHERE id_salarie IN ({ids})"""
        ) or []
        for s in rows_s:
            nom = (s.get("nom") or "").strip()
            prenom = _capitalize_prenom((s.get("prenom") or "").strip())
            salaries_map[int(s["id_salarie"])] = f"{nom} {prenom}".strip()

    orgas_map: dict[int, str] = {}
    if id_orgas:
        ids = ",".join(str(i) for i in id_orgas)
        rows_o = db_rh.query(
            f"""SELECT idorganigramme, lib_orga FROM rh.pgt_organigramme
                 WHERE idorganigramme IN ({ids})"""
        ) or []
        for o in rows_o:
            orgas_map[int(o["idorganigramme"])] = o.get("lib_orga") or ""

    out: list[FactureLigne] = []
    for r in rows:
        montant_ttc = float(r.get("montant_ttc") or 0)
        montant_fact = float(r.get("montant_facture") or 0)
        if montant_fact == 0:
            etat = "ko"
        elif abs(montant_fact - montant_ttc) < 0.01:
            etat = "ok"
        else:
            etat = "partiel"

        bene_id = int(r.get("bene_id") or 0)
        bene_service = bool(r.get("bene_service"))
        bene_nom = (orgas_map.get(bene_id, "") if bene_service
                    else salaries_map.get(bene_id, ""))

        mp = r.get("mode_paiement") or ""
        out.append(FactureLigne(
            id_commande=str(r["id_commande"]),
            date_achat=str(r.get("date_achat") or ""),
            ope_achat_nom=salaries_map.get(int(r.get("ope_achat") or 0), ""),
            enseigne=r.get("enseigne") or "",
            num_commande=r.get("num_commande") or "",
            description=r.get("description") or "",
            montant_ttc=montant_ttc,
            mode_paiement=_PAIEMENT_LABELS.get(mp, mp),
            bene_nom=bene_nom,
            bene_service=bene_service,
            etat=etat,
            montant_facture=montant_fact,
        ))
    return out
