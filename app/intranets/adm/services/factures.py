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

from datetime import date, datetime
from typing import Optional
from unicodedata import normalize

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


def _new_id() -> int:
    """ID 8 octets timestamp (cf idEntierDateHeureSys WinDev)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def normalize_enseigne(s: str) -> str:
    """MAJUSCULE + sans accent + sans espace (cf ChaineFormate WinDev
    ccMajuscule+ccSansAccent+ccSansEspace)."""
    s = normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return s.upper().replace(" ", "")


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


class BeneficiaireItem(BaseModel):
    id: str
    label: str
    sous_label: str = ""        # ex : agence/équipe pour un salarié


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


# ---------- Picker beneficiaire (salarie OU service) -------------------


def search_beneficiaires(
    mode: str, query: str = "", limit: int = 100,
) -> list[BeneficiaireItem]:
    """Cherche un beneficiaire selon le mode :
      - 'salarie' : pgt_salarie en activite, label = "Nom Prenom"
      - 'service' : pgt_organigramme, label = lib_orga
    Recherche par "contient" (case-insensitive)."""
    db = get_pg_connection("rh")
    q = (query or "").strip().lower()
    if mode == "service":
        if q:
            rows = db.query(
                """SELECT idorganigramme AS id, lib_orga AS label
                     FROM rh.pgt_organigramme
                    WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                      AND LOWER(lib_orga) LIKE ?
                    ORDER BY lib_orga LIMIT ?""",
                (f"%{q}%", int(limit)),
            ) or []
        else:
            rows = db.query(
                """SELECT idorganigramme AS id, lib_orga AS label
                     FROM rh.pgt_organigramme
                    WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    ORDER BY lib_orga LIMIT ?""",
                (int(limit),),
            ) or []
        return [BeneficiaireItem(id=str(r["id"]), label=r.get("label") or "")
                for r in rows]
    else:  # salarie
        params: list = []
        where = ["(s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')"]
        if q:
            where.append("(LOWER(s.nom) LIKE ? OR LOWER(s.prenom) LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        params.append(int(limit))
        rows = db.query(
            f"""SELECT s.id_salarie AS id, s.nom, s.prenom
                  FROM rh.pgt_salarie s
                 WHERE {' AND '.join(where)}
                 ORDER BY s.nom, s.prenom LIMIT ?""",
            tuple(params),
        ) or []
        out: list[BeneficiaireItem] = []
        for r in rows:
            nom = (r.get("nom") or "").strip()
            prenom = _capitalize_prenom((r.get("prenom") or "").strip())
            out.append(BeneficiaireItem(
                id=str(r["id"]),
                label=f"{nom} {prenom}".strip(),
            ))
        return out


# ---------- Creation (Fen_FactureAjout) -------------------------------


class CommandeCreatePayload(BaseModel):
    date_achat: date
    ope_achat: int                  # IDSalarie de l'acheteur (combo Par)
    id_ste: int = 0
    enseigne: str = ""              # sera normalisee (MAJ + sans accent/espace)
    mode_paiement: str              # CB / CBL / CH / PRLV / ESP
    description: str = ""
    montant_ttc: float
    num_commande: str = ""
    bene_service: bool              # False=salarie, True=service
    bene_id: int                    # id_salarie OU idorganigramme


def create_commande(p: CommandeCreatePayload, op_id: int) -> int:
    """Cree une nouvelle commande dans pgt_commande.
    Retourne l'id_commande genere (8 octets timestamp)."""
    db = get_pg_connection("divers")
    id_new = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_commande_auto), 0) + 1 AS n FROM divers.pgt_commande"
    )
    auto_n = int(auto["n"]) if auto else 1
    enseigne_norm = normalize_enseigne(p.enseigne)
    db.query(
        """INSERT INTO divers.pgt_commande
              (id_commande_auto, id_commande, date_achat, ope_achat,
               num_commande, montant_ttc, enseigne, description,
               mode_paiement, bene_service, bene_id, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (auto_n, id_new, p.date_achat, int(p.ope_achat),
         p.num_commande or "", float(p.montant_ttc),
         enseigne_norm, p.description or "",
         p.mode_paiement, bool(p.bene_service), int(p.bene_id),
         int(p.id_ste) if p.id_ste else None,
         int(op_id)),
    )
    return id_new


# ---------- Detail commande (Fen_FactureFiche) ------------------------


class CommandeDetail(BaseModel):
    id_commande: str
    date_achat: str = ""
    ope_achat: int = 0
    ope_achat_nom: str = ""
    num_commande: str = ""
    montant_ttc: float = 0.0
    enseigne: str = ""
    description: str = ""
    id_ste: int = 0
    mode_paiement: str = ""
    bene_service: bool = False
    bene_id: int = 0
    bene_nom: str = ""
    # Calcules :
    somme_factures: float = 0.0
    montant_restant: float = 0.0


class FactureItem(BaseModel):
    id_commande_facture: str
    date_ajout: str = ""
    montant_ttc: float = 0.0
    nom_fic: str = ""


def get_commande_detail(id_commande: int) -> Optional[CommandeDetail]:
    """Charge le detail d'une commande pour Fen_FactureFiche."""
    db_d = get_pg_connection("divers")
    db_rh = get_pg_connection("rh")
    r = db_d.query_one(
        """SELECT id_commande, date_achat, ope_achat, num_commande,
                  montant_ttc, enseigne, description, id_ste, mode_paiement,
                  bene_service, bene_id
             FROM divers.pgt_commande WHERE id_commande = ? LIMIT 1""",
        (int(id_commande),),
    )
    if not r:
        return None
    # Resolution noms operateur + beneficiaire
    ope_id = int(r.get("ope_achat") or 0)
    bene_id = int(r.get("bene_id") or 0)
    bene_service = bool(r.get("bene_service"))
    ope_nom = ""; bene_nom = ""
    if ope_id:
        s = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (ope_id,),
        )
        if s:
            ope_nom = (f"{(s.get('nom') or '').strip()} "
                       f"{_capitalize_prenom((s.get('prenom') or '').strip())}").strip()
    if bene_id:
        if bene_service:
            o = db_rh.query_one(
                "SELECT lib_orga FROM rh.pgt_organigramme WHERE idorganigramme = ?",
                (bene_id,),
            )
            if o: bene_nom = o.get("lib_orga") or ""
        else:
            s = db_rh.query_one(
                "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
                (bene_id,),
            )
            if s:
                bene_nom = (f"{(s.get('nom') or '').strip()} "
                            f"{_capitalize_prenom((s.get('prenom') or '').strip())}").strip()
    # Somme des factures associees
    sum_r = db_d.query_one(
        """SELECT COALESCE(SUM(montant_ttc), 0) AS s
             FROM divers.pgt_commande_facture
            WHERE id_commande = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_commande),),
    )
    somme = float(sum_r.get("s") or 0)
    montant = float(r.get("montant_ttc") or 0)
    return CommandeDetail(
        id_commande=str(r["id_commande"]),
        date_achat=str(r.get("date_achat") or ""),
        ope_achat=ope_id, ope_achat_nom=ope_nom,
        num_commande=r.get("num_commande") or "",
        montant_ttc=montant, enseigne=r.get("enseigne") or "",
        description=r.get("description") or "",
        id_ste=int(r.get("id_ste") or 0),
        mode_paiement=r.get("mode_paiement") or "",
        bene_service=bene_service, bene_id=bene_id, bene_nom=bene_nom,
        somme_factures=somme, montant_restant=round(montant - somme, 2),
    )


def list_factures_for_commande(id_commande: int) -> list[FactureItem]:
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_commande_facture, date_ajout, montant_ttc, nom_fic
             FROM divers.pgt_commande_facture
            WHERE id_commande = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY date_ajout DESC""",
        (int(id_commande),),
    ) or []
    return [FactureItem(
        id_commande_facture=str(r["id_commande_facture"]),
        date_ajout=str(r.get("date_ajout") or ""),
        montant_ttc=float(r.get("montant_ttc") or 0),
        nom_fic=r.get("nom_fic") or "",
    ) for r in rows]


def update_commande(id_commande: int, p: CommandeCreatePayload,
                     op_id: int) -> bool:
    db = get_pg_connection("divers")
    db.query(
        """UPDATE divers.pgt_commande
              SET date_achat=?, ope_achat=?, num_commande=?, montant_ttc=?,
                  enseigne=?, description=?, id_ste=?, mode_paiement=?,
                  bene_service=?, bene_id=?,
                  modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_commande=?""",
        (p.date_achat, int(p.ope_achat), p.num_commande or "",
         float(p.montant_ttc), normalize_enseigne(p.enseigne),
         p.description or "", int(p.id_ste) if p.id_ste else None,
         p.mode_paiement, bool(p.bene_service), int(p.bene_id),
         int(op_id), int(id_commande)),
    )
    return True


# ---------- Upload / Download facture ----------------------------------


def _factures_dir(id_commande: int):
    """Dossier de stockage des factures d'une commande."""
    from app.core.config import DOCS_BASE_PATH
    return DOCS_BASE_PATH / "factures" / str(id_commande)


def add_facture(
    id_commande: int, file_content: bytes, file_name: str,
    montant_ttc: float, op_id: int,
) -> int:
    """Sauve le fichier sur disque + INSERT pgt_commande_facture.
    Retourne id_commande_facture."""
    import os, pathlib
    folder = _factures_dir(id_commande)
    folder.mkdir(parents=True, exist_ok=True)
    # Nouveau nom : timestamp + extension (cf WinDev DateHeureSys()+ResExtension)
    ext = pathlib.Path(file_name).suffix or ""
    new_name = datetime.now().strftime("%Y%m%d%H%M%S") + ext
    target = folder / new_name
    target.write_bytes(file_content)

    db = get_pg_connection("divers")
    id_new = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_commande_facture_auto), 0) + 1 AS n"
        " FROM divers.pgt_commande_facture"
    )
    auto_n = int(auto["n"]) if auto else 1
    db.query(
        """INSERT INTO divers.pgt_commande_facture
              (id_commande_facture_auto, id_commande_facture, id_commande,
               date_ajout, montant_ttc, nom_fic,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, NOW(), ?, ?, NOW(), ?, 'new')""",
        (auto_n, id_new, int(id_commande),
         float(montant_ttc), new_name, int(op_id)),
    )
    return id_new


def delete_facture(id_facture: int, op_id: int) -> bool:
    db = get_pg_connection("divers")
    db.query(
        """UPDATE divers.pgt_commande_facture
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_commande_facture=?""",
        (int(op_id), int(id_facture)),
    )
    return True


def get_facture_file_path(id_facture: int):
    """Retourne (path, nom_original) pour le download."""
    db = get_pg_connection("divers")
    r = db.query_one(
        """SELECT id_commande, nom_fic FROM divers.pgt_commande_facture
            WHERE id_commande_facture = ?""",
        (int(id_facture),),
    )
    if not r:
        return None, None
    p = _factures_dir(int(r["id_commande"])) / (r.get("nom_fic") or "")
    return (p if p.exists() else None), r.get("nom_fic") or "facture.pdf"


# ---------- Suppression (soft delete) ----------------------------------


def delete_commande(id_commande: int, op_id: int) -> bool:
    """Soft-delete d'une commande : positionne modif_elem='suppr'.
    Soft-delete cascade aussi les factures liees. Le sync HFSQL->PG
    incremental detectera la modif_date pour propager."""
    db = get_pg_connection("divers")
    db.query(
        """UPDATE divers.pgt_commande
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_commande=?""",
        (int(op_id), int(id_commande)),
    )
    db.query(
        """UPDATE divers.pgt_commande_facture
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_commande=?""",
        (int(op_id), int(id_commande)),
    )
    return True


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
