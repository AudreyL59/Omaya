"""Transposition Python de la procédure WinDev `DonneInfoTicket`.

Pour chaque IDTK_TypeDemande, on va lire une (ou plusieurs) tables
satellites et construire la chaîne "Info" affichée dans la liste des
tickets (ex: "pour DEEN Soan", "pour BENMANSOUR Zineb", ...).

Implémentation par batch : on prend une LISTE d'id_ticket pour un type
donné et on retourne `{id_ticket: info_str}` en faisant 1 query SQL +
1 lookup salarie (au lieu de 1 query par ticket comme dans WinDev).

L'appelant ne fait qu'un appel pour tout l'affichage courant.

Mapping des cas (cf. WinDev DonneInfoTicket) :
  1  Commande Fourniture        TK_CommandeBS_Lignes (ticket_bo) -- non implem.
  2  Carte PRO                   TK_DemandeCartePro   (ticket_bo) -- non implem.
  3  DPAE                        TK_DemandeDPAE       (ticket_dpae)
  4  Contrat W - Signature       TK_DemandeCttW       (?)         -- non implem.
  9  Réservation                 TK_DemandeResa+TK_TypeResa (ticket_bo) -- non implem.
  10 Avance                      TK_DemandeAvance     (ticket_bo) -- non implem.
  11 SOS BO                      TK_DemandeSOS_BO     (ticket_bo) -- non implem.
  12 Sorties RH                  TK_DemandeSortieRH   (?)         -- non implem.
  13 Congés                      TK_DemandeConges     (?)         -- non implem.
  17 SOS Pôle JURI               TK_DemandeSOS_JU     (?)         -- non implem.
  20 Call SFR                    TK_CallSFR           (ticket_bo)
  21 DPAE à venir                TK_DemandeDPAE       (ticket_dpae)
  22 Call energie                TK_Call              (ticket_bo)
  23 Contrat de courtage         TK_DemandeCttCourtage(?)         -- non implem.
  24 Commande ExoCash            TK_CdeExoCash        (?)         -- non implem.
  25 Attribution ExoCash         Tk_DemandeAttExoCash (?)         -- non implem.
  26 Call SFR RET RDV Tech       TK_CallSFR_RetRDVTech(?)         -- non implem.
  27 Mutuelle                    TK_DemandeMutuelle   (?)
  28 Facturation Distrib         TK_DemandeFacturationDistrib (?) -- non implem.
  29 DPAE Distributeur           TK_DemandeDPAE_Distrib(?)        -- non implem.
  30 Intégration Distributeur    TK_DemandeDPAE_Distrib(?)        -- non implem.
  31 Demande Doc Distributeur    TK_DemandeDocDistrib (?)         -- non implem.
  33 Demande facturation         TK_DemandeFacturation(?)         -- non implem.
  35 PV Liv/Rest Ulease          TK_DemandeSignPVUlease(?)        -- non implem.
  36 Sorties FPE                 TK_DemandeSortieRH   (?)         -- non implem.
  37 Sorties Licenciement        TK_DemandeSortieRH   (?)         -- non implem.
  38 Demande code Vendeur        TK_DemandeCodeVendeur(?)         -- non implem.
  39 Désactivation code Vendeur  TK_DemandeCodeVendeur(?)         -- non implem.

Au démarrage, on implémente d'abord les cas faciles + DPAE/Call (déjà
des connexions BDD identifiées dans le code). Les autres seront remplis
au fur et à mesure des besoins de test.
"""

from __future__ import annotations

from app.core.database import get_connection

from .service import (
    _clean_id,
    _to_int,
    load_salaries_minimal,
)


# ---------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------

def _capit(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    return s[:1].upper() + s[1:].lower()


def _ids_in_clause(ids: list[int]) -> str:
    return ",".join(str(int(i)) for i in ids if int(i))


# ---------------------------------------------------------------
# Implémentations par cas (batch)
# ---------------------------------------------------------------

def _info_dpae(id_tickets: list[int]) -> dict[int, str]:
    """Cas 3 (DPAE) et 21 (DPAE à venir) — TK_DemandeDPAE dans ticket_dpae."""
    if not id_tickets:
        return {}
    db = get_connection("ticket_dpae")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT IDTK_Liste, Nom, Prenom FROM TK_DemandeDPAE
            WHERE IDTK_Liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("IDTK_Liste")))
        nom = (r.get("Nom") or "").strip()
        prenom = (r.get("Prenom") or "").strip()
        if idl and (nom or prenom):
            out[idl] = f"pour {nom} {_capit(prenom)}".strip()
    return out


def _info_call_sfr(id_tickets: list[int]) -> dict[int, str]:
    """Cas 20 — TK_CallSFR dans ticket_bo."""
    if not id_tickets:
        return {}
    db = get_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT IDTK_Liste, NomClient, PrenomClient, CP, VILLE
            FROM TK_CallSFR
            WHERE IDTK_Liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("IDTK_Liste")))
        if not idl:
            continue
        nom = (r.get("NomClient") or "").strip()
        prenom = (r.get("PrenomClient") or "").strip()
        cp = (r.get("CP") or "").strip()
        ville = (r.get("VILLE") or "").strip()
        # WinDev : ExtraitChaîne(VILLE,1,"(") → on coupe à "("
        if "(" in ville:
            ville = ville.split("(", 1)[0].strip()
        out[idl] = f"pour {nom} {_capit(prenom)}, {cp} {ville}".strip()
    return out


def _info_call_energie(id_tickets: list[int]) -> dict[int, str]:
    """Cas 22 — TK_Call dans ticket_bo."""
    if not id_tickets:
        return {}
    db = get_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT IDTK_Liste, NomClient, PrenomClient, CP, VILLE
            FROM TK_Call
            WHERE IDTK_Liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("IDTK_Liste")))
        if not idl:
            continue
        nom = (r.get("NomClient") or "").strip()
        prenom = (r.get("PrenomClient") or "").strip()
        cp = (r.get("CP") or "").strip()
        ville = (r.get("VILLE") or "").strip()
        if "(" in ville:
            ville = ville.split("(", 1)[0].strip()
        out[idl] = f"pour {nom} {_capit(prenom)}, {cp} {ville}".strip()
    return out


def _info_via_id_salarie(
    id_tickets: list[int],
    db_key: str,
    table: str,
    id_col: str = "IDSalarie",
    prefix: str = "pour ",
) -> dict[int, str]:
    """Cas générique : table satellite (db_key.table) avec une colonne
    qui pointe vers salarie. Retourne 'pour NOM Prenom'.

    Utilisé pour Mutuelle (27), Sortie RH (12, 36, 37), Contrat W (4, 40),
    Commande ExoCash (24), Attribution ExoCash (25), Contrat courtage (23).
    """
    if not id_tickets:
        return {}
    db = get_connection(db_key)
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT IDTK_Liste, {id_col}
            FROM {table}
            WHERE IDTK_Liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    # Map id_ticket → id_salarie
    ticket_to_salarie: dict[int, int] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("IDTK_Liste")))
        ids = _clean_id(_to_int(r.get(id_col)))
        if idl and ids:
            ticket_to_salarie[idl] = ids
    if not ticket_to_salarie:
        return {}
    sals = load_salaries_minimal(set(ticket_to_salarie.values()))
    out: dict[int, str] = {}
    for idl, ids in ticket_to_salarie.items():
        s = sals.get(ids)
        if s:
            out[idl] = f"{prefix}{s['nom']} {_capit(s['prenom'])}".strip()
    return out


# ---------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------

# Cas avec implémentation directe (ne va PAS via _info_via_id_salarie)
_DIRECT_CASES = {
    3: _info_dpae,
    21: _info_dpae,
    20: _info_call_sfr,
    22: _info_call_energie,
}

# Cas via id_salarie : (db_key, table, id_col, prefix)
_SALARIE_CASES: dict[int, tuple[str, str, str, str]] = {
    # Cas WinDev → tables TK_Demande*. Les db_key sont des PARIS — à corriger
    # selon où sont effectivement stockées les tables. Le SELECT plante
    # silencieusement (try/except) si la table n'existe pas dans la BDD,
    # auquel cas on renvoie chaîne vide (pas de blocage).
    27: ("ticket_bo", "TK_DemandeMutuelle", "IDSalarie", "pour "),
    24: ("ticket_bo", "TK_CdeExoCash", "IDSalarie", "pour "),
    23: ("ticket_bo", "TK_DemandeCttCourtage", "IDSalarie", "pour "),
    4:  ("ticket_bo", "TK_DemandeCttW", "IDSalarie", "pour "),
    40: ("ticket_bo", "TK_DemandeCttW", "IDSalarie", "pour "),
    12: ("ticket_bo", "TK_DemandeSortieRH", "IDSalarie", "pour "),
    36: ("ticket_bo", "TK_DemandeSortieRH", "IDSalarie", "pour "),
    37: ("ticket_bo", "TK_DemandeSortieRH", "IDSalarie", "pour "),
    13: ("ticket_bo", "TK_DemandeConges", "IDSalarie", "pour "),
}


def donne_info_ticket_batch(
    id_type_demande: int,
    id_tickets: list[str | int],
) -> dict[str, str]:
    """Retourne {id_ticket_str: info_str} pour la liste de tickets fournie.

    On ne fait qu'UN passage pour le type donné (toutes les requêtes en
    batch). Les cas non implémentés renvoient une chaîne vide.
    """
    ids_int = [int(i) for i in id_tickets if str(i).isdigit()]
    if not ids_int:
        return {}

    if id_type_demande in _DIRECT_CASES:
        result = _DIRECT_CASES[id_type_demande](ids_int)
    elif id_type_demande in _SALARIE_CASES:
        db_key, table, id_col, prefix = _SALARIE_CASES[id_type_demande]
        result = _info_via_id_salarie(ids_int, db_key, table, id_col, prefix)
    else:
        result = {}
    return {str(k): v for k, v in result.items()}
