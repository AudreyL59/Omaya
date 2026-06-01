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

from app.core.database.pg import get_pg_connection

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


def _to_montant(v) -> str:
    """Format d'affichage d'une valeur monétaire (HFSQL Monétaire).

    Accepte int, float, ou string (avec ou sans décimales). Retourne une
    chaîne formatée sans décimales si entier, avec 2 décimales sinon
    (séparateur virgule).
    """
    if v is None or v == "":
        return "0"
    if isinstance(v, (int, float)):
        f = float(v)
    else:
        try:
            f = float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return "0"
    if f == int(f):
        return str(int(f))
    return f"{f:.2f}".replace(".", ",")


# ---------------------------------------------------------------
# Implémentations par cas (batch)
# ---------------------------------------------------------------

def _info_dpae(id_tickets: list[int]) -> dict[int, str]:
    """Cas 3 (DPAE) et 21 (DPAE à venir) — TK_DemandeDPAE dans ticket_dpae."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_dpae")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, nom, prenom FROM pgt_tk_demande_dpae
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        nom = (r.get("nom") or "").strip()
        prenom = (r.get("prenom") or "").strip()
        if idl and (nom or prenom):
            out[idl] = f"pour {nom} {_capit(prenom)}".strip()
    return out


def _info_call_sfr(id_tickets: list[int]) -> dict[int, str]:
    """Cas 20 — TK_CallSFR dans ticket_bo."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, nom_client, prenom_client, cp, ville
            FROM pgt_tk_call_sfr
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        if not idl:
            continue
        nom = (r.get("nom_client") or "").strip()
        prenom = (r.get("prenom_client") or "").strip()
        cp = (r.get("cp") or "").strip()
        ville = (r.get("ville") or "").strip()
        # WinDev : ExtraitChaîne(VILLE,1,"(") → on coupe à "("
        if "(" in ville:
            ville = ville.split("(", 1)[0].strip()
        out[idl] = f"pour {nom} {_capit(prenom)}, {cp} {ville}".strip()
    return out


def _info_call_energie(id_tickets: list[int]) -> dict[int, str]:
    """Cas 22 — TK_Call dans ticket_bo."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, nom_client, prenom_client, cp, ville
            FROM pgt_tk_call
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        if not idl:
            continue
        nom = (r.get("nom_client") or "").strip()
        prenom = (r.get("prenom_client") or "").strip()
        cp = (r.get("cp") or "").strip()
        ville = (r.get("ville") or "").strip()
        if "(" in ville:
            ville = ville.split("(", 1)[0].strip()
        out[idl] = f"pour {nom} {_capit(prenom)}, {cp} {ville}".strip()
    return out


def _info_via_id_salarie(
    id_tickets: list[int],
    db_key: str,
    table: str,
    id_col: str = "id_salarie",
    prefix: str = "pour ",
) -> dict[int, str]:
    """Cas générique : table satellite (db_key.table) avec une colonne
    qui pointe vers salarie. Retourne 'pour NOM Prenom'.

    Utilisé pour Mutuelle (27), Sortie RH (12, 36, 37), Contrat W (4, 40),
    Commande ExoCash (24), Attribution ExoCash (25), Contrat courtage (23).
    """
    if not id_tickets:
        return {}
    db = get_pg_connection(db_key)
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, {id_col}
            FROM {table}
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    # Map id_ticket → id_salarie
    ticket_to_salarie: dict[int, int] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
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


def _info_avance(id_tickets: list[int]) -> dict[int, str]:
    """Cas 10 — TK_DemandeAvance.Bénéficiaire + Montant."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, beneficiaire, montant
            FROM pgt_tk_demande_avance
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to: dict[int, tuple[int, str]] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        ids = _clean_id(_to_int(r.get("beneficiaire")))
        montant = _to_montant(r.get("montant"))
        if idl and ids:
            ticket_to[idl] = (ids, montant)
    if not ticket_to:
        return {}
    sals = load_salaries_minimal({ids for ids, _ in ticket_to.values()})
    out: dict[int, str] = {}
    for idl, (ids, mt) in ticket_to.items():
        s = sals.get(ids)
        if not s:
            continue
        out[idl] = f"pour {s['nom']} {_capit(s['prenom'])} ({mt} €)"
    return out


def _info_attr_exocash(id_tickets: list[int]) -> dict[int, str]:
    """Cas 25 — Tk_DemandeAttExoCash.IDSalarie + MontantEC (Monétaire).

    Table dans ticket_rh.
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_rh")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_salarie, montant_ec
            FROM pgt_tk_demande_att_exo_cash
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to: dict[int, tuple[int, str]] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        ids = _clean_id(_to_int(r.get("id_salarie")))
        mt = _to_montant(r.get("montant_ec"))
        if idl and ids:
            ticket_to[idl] = (ids, mt)
    sals = load_salaries_minimal({ids for ids, _ in ticket_to.values()})
    out: dict[int, str] = {}
    for idl, (ids, mt) in ticket_to.items():
        s = sals.get(ids)
        if not s:
            continue
        out[idl] = f"pour {s['nom']} {_capit(s['prenom'])} ({mt} EC)"
    return out


def _info_sos_bo(id_tickets: list[int]) -> dict[int, str]:
    """Cas 11 — TK_DemandeSOS_BO.Bénéficiaire + TK_TypeSOS_BO.Lib_TypeSos.

    Format : "{Lib_TypeSos} pour NOM Prenom".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    # 1. Demandes
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, beneficiaire, id_tk_type_sos_bo
            FROM pgt_tk_demande_sos_bo
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to: dict[int, tuple[int, int]] = {}
    type_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        ben = _clean_id(_to_int(r.get("beneficiaire")))
        idtype = _clean_id(_to_int(r.get("id_tk_type_sos_bo")))
        if idl:
            ticket_to[idl] = (ben, idtype)
            type_ids.add(idtype)
    # 2. Types SOS BO
    type_libs: dict[int, str] = {}
    if type_ids:
        try:
            ids_t = ",".join(str(i) for i in type_ids if i)
            if ids_t:
                trows = db.query(
                    f"""SELECT id_tk_type_sos_bo, lib_type_sos
                    FROM pgt_tk_type_sos_bo
                    WHERE id_tk_type_sos_bo IN ({ids_t})"""
                )
                for t in trows:
                    type_libs[_clean_id(_to_int(t.get("id_tk_type_sos_bo")))] = (
                        t.get("lib_type_sos") or ""
                    ).strip()
        except Exception:
            pass
    # 3. Salaries
    sals = load_salaries_minimal({ben for ben, _ in ticket_to.values() if ben})
    out: dict[int, str] = {}
    for idl, (ben, idtype) in ticket_to.items():
        lib = type_libs.get(idtype, "")
        s = sals.get(ben, {}) if ben else {}
        parts: list[str] = []
        if lib:
            parts.append(lib)
        if s:
            parts.append(f"pour {s['nom']} {_capit(s['prenom'])}")
        if parts:
            out[idl] = " ".join(parts)
    return out


def _info_dpae_distrib(id_tickets: list[int]) -> dict[int, str]:
    """Cas 29 — TK_DemandeDPAE_Distrib.Nom + Prenom."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, nom, prenom
            FROM pgt_tk_demande_dpae_distrib
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        nom = (r.get("nom") or "").strip()
        prenom = (r.get("prenom") or "").strip()
        if idl and (nom or prenom):
            out[idl] = f"pour {nom} {_capit(prenom)}".strip()
    return out


def _info_integration_distrib(id_tickets: list[int]) -> dict[int, str]:
    """Cas 30 — TK_DemandeDPAE_Distrib : Nom + Prenom + RaisonSociale.

    NOM, PRENOM, RaisonSociale sont 3 mémos texte. Le bridge HFSQL tronque
    les mémos dans les SELECT multi-colonnes → on splitte en 2 requêtes :
    (Nom + Prenom) puis (RaisonSociale séparément).
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    nom_prenom: dict[int, tuple[str, str]] = {}
    raison_sociale: dict[int, str] = {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, nom, prenom
            FROM pgt_tk_demande_dpae_distrib
            WHERE id_tk_liste IN ({ids_sql})"""
        )
        for r in rows:
            idl = _clean_id(_to_int(r.get("id_tk_liste")))
            if idl:
                nom_prenom[idl] = (
                    (r.get("nom") or "").strip(),
                    (r.get("prenom") or "").strip(),
                )
    except Exception:
        pass
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, raison_sociale
            FROM pgt_tk_demande_dpae_distrib
            WHERE id_tk_liste IN ({ids_sql})"""
        )
        for r in rows:
            idl = _clean_id(_to_int(r.get("id_tk_liste")))
            if idl:
                raison_sociale[idl] = (r.get("raison_sociale") or "").strip()
    except Exception:
        pass
    out: dict[int, str] = {}
    for idl in set(nom_prenom) | set(raison_sociale):
        nom, prenom = nom_prenom.get(idl, ("", ""))
        rs = raison_sociale.get(idl, "")
        parts: list[str] = []
        if nom or prenom:
            parts.append(f"pour {nom} {_capit(prenom)}".strip())
        if rs:
            parts.append(f"Ste {rs}")
        if parts:
            out[idl] = ", ".join(parts)
    return out


def _info_facturation(id_tickets: list[int]) -> dict[int, str]:
    """Cas 33 — TK_DemandeFacturation.LibFacture + Montant."""
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, lib_facture, montant
            FROM pgt_tk_demande_facturation
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    out: dict[int, str] = {}
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        lib = (r.get("lib_facture") or "").strip()
        mt = _to_int(r.get("montant"))
        if idl and (lib or mt):
            parts: list[str] = []
            if lib:
                parts.append(lib)
            parts.append(f"{mt} €")
            out[idl] = ", ".join(parts)
    return out


def _info_commande_fourniture(id_tickets: list[int]) -> dict[int, str]:
    """Cas 1 — Commande Fourniture (multi-lignes par ticket).

    Joint TK_DemandeFourniture × TK_TypeCommande (Qté + LibTypeBS).
    Format : "{Qté} {LibTypeBS}" séparé par ", " + "..." si > 1.
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, qte, id_tk_type_commande
            FROM pgt_tk_demande_fourniture
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    grouped: dict[int, list[tuple[int, int]]] = {}  # id_ticket -> [(qte, id_typecmd)]
    type_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        qt = _to_int(r.get("qte"))
        idtc = _clean_id(_to_int(r.get("id_tk_type_commande")))
        if not idl:
            continue
        grouped.setdefault(idl, []).append((qt, idtc))
        if idtc:
            type_ids.add(idtc)
    if not grouped:
        return {}
    type_libs: dict[int, str] = {}
    if type_ids:
        try:
            ids_t = ",".join(str(i) for i in type_ids)
            trows = db.query(
                f"""SELECT id_tk_type_commande, lib_type_bs
                FROM pgt_tk_type_commande
                WHERE id_tk_type_commande IN ({ids_t})"""
            )
            for t in trows:
                type_libs[_clean_id(_to_int(t.get("id_tk_type_commande")))] = (
                    t.get("lib_type_bs") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, items in grouped.items():
        labels = [
            f"{qt} {type_libs.get(idtc, '')}".strip()
            for qt, idtc in items
            if type_libs.get(idtc) or qt
        ]
        if not labels:
            continue
        text = ", ".join(labels[:1])
        if len(labels) > 1:
            text += "..."
        out[idl] = text
    return out


def _info_reservation(id_tickets: list[int]) -> dict[int, str]:
    """Cas 9 — Réservation. TK_DemandeResa × TK_TypeResaSSFam × TK_TypeResa.

    Format : "pour NOM Prenom : Lib_TypeResa" + " (Aller-Retour)" si AR=1
             et IDTK_TypeResa=2. Si pas de Bénéficiaire → fallback sur le
             1er nom de ListeBénéSupp.
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, beneficiaire, id_tk_type_resa_ss_fam, ar
            FROM pgt_tk_demande_resa
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    base: dict[int, dict] = {}
    ssfam_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        if not idl:
            continue
        ssfam = _clean_id(_to_int(r.get("id_tk_type_resa_ss_fam")))
        base[idl] = {
            "ben": _clean_id(_to_int(r.get("beneficiaire"))),
            "ssfam": ssfam,
            "ar": bool(r.get("ar")),
        }
        if ssfam:
            ssfam_ids.add(ssfam)
    # Fallback ListeBénéSupp (mémo, fetch séparé)
    listebs: dict[int, str] = {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, liste_bene_supp
            FROM pgt_tk_demande_resa
            WHERE id_tk_liste IN ({ids_sql})"""
        )
        for r in rows:
            idl = _clean_id(_to_int(r.get("id_tk_liste")))
            if idl:
                listebs[idl] = (r.get("liste_bene_supp") or "").strip()
    except Exception:
        pass
    # Charge TypeResaSSFam → TypeResa → Lib_TypeResa
    ssfam_to_resa: dict[int, int] = {}
    resa_ids: set[int] = set()
    if ssfam_ids:
        try:
            ids_t = ",".join(str(i) for i in ssfam_ids)
            srows = db.query(
                f"""SELECT id_tk_type_resa_ss_fam, id_tk_type_resa
                FROM pgt_tk_type_resa_ss_fam
                WHERE id_tk_type_resa_ss_fam IN ({ids_t})"""
            )
            for s in srows:
                idss = _clean_id(_to_int(s.get("id_tk_type_resa_ss_fam")))
                idr = _clean_id(_to_int(s.get("id_tk_type_resa")))
                if idss and idr:
                    ssfam_to_resa[idss] = idr
                    resa_ids.add(idr)
        except Exception:
            pass
    resa_libs: dict[int, str] = {}
    if resa_ids:
        try:
            ids_t = ",".join(str(i) for i in resa_ids)
            rrows = db.query(
                f"""SELECT id_tk_type_resa, lib_type_resa
                FROM pgt_tk_type_resa
                WHERE id_tk_type_resa IN ({ids_t})"""
            )
            for r in rrows:
                resa_libs[_clean_id(_to_int(r.get("id_tk_type_resa")))] = (
                    r.get("lib_type_resa") or ""
                ).strip()
        except Exception:
            pass
    sals = load_salaries_minimal({d["ben"] for d in base.values() if d["ben"]})
    out: dict[int, str] = {}
    for idl, d in base.items():
        s = sals.get(d["ben"]) if d["ben"] else None
        if s:
            qui = f"pour {s['nom']} {_capit(s['prenom'])}"
        else:
            # ListeBénéSupp = "Nom1//Nom2//..." → on prend le 1er
            l = listebs.get(idl, "")
            first = l.split("//", 1)[0].strip() if l else ""
            qui = f"pour {first}..." if first else ""
        idr = ssfam_to_resa.get(d["ssfam"], 0)
        lib = resa_libs.get(idr, "")
        text = qui
        if lib:
            text = f"{qui} : {lib}" if qui else lib
        if idr == 2 and d["ar"]:
            text += " (Aller-Retour)"
        if text:
            out[idl] = text
    return out


def _info_sos_juri(id_tickets: list[int]) -> dict[int, str]:
    """Cas 17 — SOS Pôle JURI. TK_DemandeSOS_JU + TK_TypeSOS_JU (ticket_rh).

    Format simplifié : "{Lib_TypeSos} {RefDemande}" + résolution de IdElem
    pour TypeForm=Salarie/Societe (les autres TypeForm renvoient juste la
    référence).
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_rh")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_tk_type_sos_ju, id_elem
            FROM pgt_tk_demande_sos_ju
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    base: dict[int, dict] = {}
    type_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        if not idl:
            continue
        idtype = _clean_id(_to_int(r.get("id_tk_type_sos_ju")))
        idelem = _clean_id(_to_int(r.get("id_elem")))
        base[idl] = {"idtype": idtype, "idelem": idelem}
        if idtype:
            type_ids.add(idtype)
    # RefDemande mémo (fetch séparé)
    refs: dict[int, str] = {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, ref_demande
            FROM pgt_tk_demande_sos_ju
            WHERE id_tk_liste IN ({ids_sql})"""
        )
        for r in rows:
            idl = _clean_id(_to_int(r.get("id_tk_liste")))
            if idl:
                refs[idl] = (r.get("ref_demande") or "").strip()
    except Exception:
        pass
    type_info: dict[int, dict] = {}
    if type_ids:
        try:
            ids_t = ",".join(str(i) for i in type_ids)
            trows = db.query(
                f"""SELECT id_tk_type_sos_ju, lib_type_sos, type_form
                FROM pgt_tk_type_sos_ju
                WHERE id_tk_type_sos_ju IN ({ids_t})"""
            )
            for t in trows:
                type_info[_clean_id(_to_int(t.get("id_tk_type_sos_ju")))] = {
                    "lib": (t.get("lib_type_sos") or "").strip(),
                    "form": (t.get("type_form") or "").strip(),
                }
        except Exception:
            pass
    # Résolution IdElem selon TypeForm = "Salarie"
    salarie_ids = {
        d["idelem"] for idl, d in base.items()
        if type_info.get(d["idtype"], {}).get("form") == "Salarie" and d["idelem"]
    }
    sals = load_salaries_minimal(salarie_ids)
    # Résolution IdElem pour TypeForm = "Societe" → societe.RaisonSociale (rh)
    societe_ids = {
        d["idelem"] for idl, d in base.items()
        if type_info.get(d["idtype"], {}).get("form") == "Societe" and d["idelem"]
    }
    societes: dict[int, str] = {}
    if societe_ids:
        try:
            db_rh = get_pg_connection("rh")
            ids_t = ",".join(str(i) for i in societe_ids)
            srows = db_rh.query(
                f"""SELECT id_ste, rs_interne FROM pgt_societe WHERE id_ste IN ({ids_t})"""
            )
            for s in srows:
                societes[_clean_id(_to_int(s.get("id_ste")))] = (
                    s.get("rs_interne") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, d in base.items():
        ti = type_info.get(d["idtype"], {})
        lib = ti.get("lib", "")
        form = ti.get("form", "")
        ref = refs.get(idl, "")
        text = lib
        if form == "Salarie":
            s = sals.get(d["idelem"])
            if s:
                text += f" pour {s['nom']} {_capit(s['prenom'])}"
        elif form == "Societe":
            rs = societes.get(d["idelem"], "")
            if rs:
                text += f" pour {rs}"
        elif form == "Vehicule":
            if ref:
                text += f" pour {ref.upper()}"
        else:
            if ref:
                text += f" {ref}"
                if d["idtype"] == 1:
                    text += " €"
        if text:
            out[idl] = text.strip()
    return out


def _info_call_sfr_ret_rdv_tech(id_tickets: list[int]) -> dict[int, str]:
    """Cas 26 — Call SFR RET RDV Tech. TK_CallSFR_RetRDVTech → SFR_contrat → client.

    Format : "pour {client.NOM} ({SFR_contrat.NumBS})".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_contrat
            FROM pgt_tk_call_sfr_ret_rdv_tech
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to_contrat: dict[int, int] = {}
    contrat_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        idc = _clean_id(_to_int(r.get("id_contrat")))
        if idl and idc:
            ticket_to_contrat[idl] = idc
            contrat_ids.add(idc)
    if not contrat_ids:
        return {}
    contrat_to_client: dict[int, tuple[int, str]] = {}  # idc -> (idclient, numbs)
    client_ids: set[int] = set()
    try:
        db_adv = get_pg_connection("adv")
        ids_t = ",".join(str(i) for i in contrat_ids)
        crows = db_adv.query(
            f"""SELECT id_contrat, id_client, num_bs
            FROM pgt_sfr_contrat
            WHERE id_contrat IN ({ids_t})"""
        )
        for c in crows:
            idc = _clean_id(_to_int(c.get("id_contrat")))
            idcl = _clean_id(_to_int(c.get("id_client")))
            num = (c.get("num_bs") or "").strip()
            if idc:
                contrat_to_client[idc] = (idcl, num)
                if idcl:
                    client_ids.add(idcl)
    except Exception:
        return {}
    client_noms: dict[int, str] = {}
    if client_ids:
        try:
            db_adv = get_pg_connection("adv")
            ids_t = ",".join(str(i) for i in client_ids)
            clrows = db_adv.query(
                f"""SELECT id_client, nom FROM pgt_client WHERE id_client IN ({ids_t})"""
            )
            for cl in clrows:
                client_noms[_clean_id(_to_int(cl.get("id_client")))] = (
                    cl.get("nom") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, idc in ticket_to_contrat.items():
        idcl, num = contrat_to_client.get(idc, (0, ""))
        nom = client_noms.get(idcl, "")
        if nom:
            out[idl] = f"pour {nom} ({num})" if num else f"pour {nom}"
    return out


def _info_facturation_distrib(id_tickets: list[int]) -> dict[int, str]:
    """Cas 28 — Facturation Distrib. TK_DemandeFacturationDistrib + societe.

    Format : "pour {RaisonSociale}, montant {Montant} €".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_ste, montant
            FROM pgt_tk_demande_facturation_distrib
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to: dict[int, tuple[int, str]] = {}
    ste_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        idste = _clean_id(_to_int(r.get("id_ste")))
        mt = _to_montant(r.get("montant"))
        if idl:
            ticket_to[idl] = (idste, mt)
            if idste:
                ste_ids.add(idste)
    societes: dict[int, str] = {}
    if ste_ids:
        try:
            db_rh = get_pg_connection("rh")
            ids_t = ",".join(str(i) for i in ste_ids)
            srows = db_rh.query(
                f"""SELECT id_ste, raison_sociale FROM pgt_societe WHERE id_ste IN ({ids_t})"""
            )
            for s in srows:
                societes[_clean_id(_to_int(s.get("id_ste")))] = (
                    s.get("raison_sociale") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, (idste, mt) in ticket_to.items():
        rs = societes.get(idste, "")
        parts: list[str] = []
        if rs:
            parts.append(f"pour {rs}")
        parts.append(f"montant {mt} €")
        out[idl] = ", ".join(parts)
    return out


def _info_doc_distrib(id_tickets: list[int]) -> dict[int, str]:
    """Cas 31 — Demande Doc Distributeur.

    TK_DemandeDocDistrib (ticket_bo) → Doc_Distrib (rh)
        → TypeDocDistributeur (rh) + societe (rh).
    Format : "{LibDoc}, Ste {RaisonSociale}".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_doc_distrib
            FROM pgt_tk_demande_doc_distrib
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to_doc: dict[int, int] = {}
    doc_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        idd = _clean_id(_to_int(r.get("id_doc_distrib")))
        if idl and idd:
            ticket_to_doc[idl] = idd
            doc_ids.add(idd)
    if not doc_ids:
        return {}
    db_rh = get_pg_connection("rh")
    doc_info: dict[int, dict] = {}
    typedoc_ids: set[int] = set()
    ste_ids: set[int] = set()
    try:
        ids_t = ",".join(str(i) for i in doc_ids)
        drows = db_rh.query(
            f"""SELECT id_doc_distrib, id_type_doc_distributeur, id_ste
            FROM pgt_doc_distrib
            WHERE id_doc_distrib IN ({ids_t})"""
        )
        for d in drows:
            idd = _clean_id(_to_int(d.get("id_doc_distrib")))
            idtd = _clean_id(_to_int(d.get("id_type_doc_distributeur")))
            idste = _clean_id(_to_int(d.get("id_ste")))
            if idd:
                doc_info[idd] = {"idtd": idtd, "idste": idste}
                if idtd:
                    typedoc_ids.add(idtd)
                if idste:
                    ste_ids.add(idste)
    except Exception:
        return {}
    typedoc_libs: dict[int, str] = {}
    if typedoc_ids:
        try:
            ids_t = ",".join(str(i) for i in typedoc_ids)
            trows = db_rh.query(
                f"""SELECT id_type_doc_distributeur, lib_doc
                FROM pgt_type_doc_distributeur
                WHERE id_type_doc_distributeur IN ({ids_t})"""
            )
            for t in trows:
                typedoc_libs[_clean_id(_to_int(t.get("id_type_doc_distributeur")))] = (
                    t.get("lib_doc") or ""
                ).strip()
        except Exception:
            pass
    societes: dict[int, str] = {}
    if ste_ids:
        try:
            ids_t = ",".join(str(i) for i in ste_ids)
            srows = db_rh.query(
                f"""SELECT id_ste, raison_sociale FROM pgt_societe WHERE id_ste IN ({ids_t})"""
            )
            for s in srows:
                societes[_clean_id(_to_int(s.get("id_ste")))] = (
                    s.get("raison_sociale") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, idd in ticket_to_doc.items():
        info = doc_info.get(idd, {})
        lib = typedoc_libs.get(info.get("idtd", 0), "")
        rs = societes.get(info.get("idste", 0), "")
        parts: list[str] = []
        if lib:
            parts.append(lib)
        if rs:
            parts.append(f"Ste {rs}")
        if parts:
            out[idl] = ", ".join(parts)
    return out


def _info_pv_ulease(id_tickets: list[int]) -> dict[int, str]:
    """Cas 35 — PV Liv/Rest Ulease.

    TK_DemandeSignPVUlease (ticket_rh) → vehicule_Conducteur (ulease)
        → vehicule_Fiche (ulease) → Vehicule_TypeCapacité (ulease).
    Format : "{Modèle} {IMMAT} // {Lib_Type}".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_rh")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_pc
            FROM pgt_tk_demande_sign_pv_ulease
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    ticket_to_pc: dict[int, int] = {}
    pc_ids: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        idpc = _clean_id(_to_int(r.get("id_pc")))
        if idl and idpc:
            ticket_to_pc[idl] = idpc
            pc_ids.add(idpc)
    if not pc_ids:
        return {}
    db_ul = get_pg_connection("ulease")
    # vehicule_Conducteur (PC) → IDvehicule
    pc_to_vehicule: dict[int, int] = {}
    veh_ids: set[int] = set()
    try:
        ids_t = ",".join(str(i) for i in pc_ids)
        vcrows = db_ul.query(
            f"""SELECT id_vehicule_pc, id_vehicule
            FROM pgt_vehicule_conducteur
            WHERE id_vehicule_pc IN ({ids_t})"""
        )
        for v in vcrows:
            idpc = _clean_id(_to_int(v.get("id_vehicule_pc")))
            idv = _clean_id(_to_int(v.get("id_vehicule")))
            if idpc and idv:
                pc_to_vehicule[idpc] = idv
                veh_ids.add(idv)
    except Exception:
        return {}
    veh_info: dict[int, dict] = {}
    typecapa_ids: set[int] = set()
    if veh_ids:
        try:
            ids_t = ",".join(str(i) for i in veh_ids)
            vfrows = db_ul.query(
                f"""SELECT id_vehicule, immat, id_vehicule_type_capacite
                FROM pgt_vehicule_fiche
                WHERE id_vehicule IN ({ids_t})"""
            )
            for v in vfrows:
                idv = _clean_id(_to_int(v.get("id_vehicule")))
                immat = (v.get("immat") or "").strip()
                idtc = _clean_id(_to_int(v.get("id_vehicule_type_capacite")))
                if idv:
                    veh_info[idv] = {"immat": immat, "idtc": idtc, "modele": ""}
                    if idtc:
                        typecapa_ids.add(idtc)
        except Exception:
            pass
    # Modèle est mémo → fetch séparé
    if veh_ids:
        try:
            ids_t = ",".join(str(i) for i in veh_ids)
            mrows = db_ul.query(
                f"""SELECT id_vehicule, modele
                FROM pgt_vehicule_fiche
                WHERE id_vehicule IN ({ids_t})"""
            )
            for m in mrows:
                idv = _clean_id(_to_int(m.get("id_vehicule")))
                if idv in veh_info:
                    veh_info[idv]["modele"] = (m.get("modele") or "").strip()
        except Exception:
            pass
    typecapa_libs: dict[int, str] = {}
    if typecapa_ids:
        try:
            ids_t = ",".join(str(i) for i in typecapa_ids)
            tcrows = db_ul.query(
                f"""SELECT id_vehicule_type_capacite, lib_type
                FROM pgt_vehicule_typecapacite
                WHERE id_vehicule_type_capacite IN ({ids_t})"""
            )
            for t in tcrows:
                typecapa_libs[_clean_id(_to_int(t.get("id_vehicule_type_capacite")))] = (
                    t.get("lib_type") or ""
                ).strip()
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, idpc in ticket_to_pc.items():
        idv = pc_to_vehicule.get(idpc, 0)
        v = veh_info.get(idv, {})
        modele = v.get("modele", "")
        immat = v.get("immat", "")
        lib_type = typecapa_libs.get(v.get("idtc", 0), "")
        parts: list[str] = []
        if modele or immat:
            parts.append(f"{modele} {immat}".strip())
        if lib_type:
            parts.append(lib_type)
        if parts:
            out[idl] = " // ".join(parts)
    return out


def _info_code_vendeur(id_tickets: list[int], desactivation: bool = False) -> dict[int, str]:
    """Cas 38 / 39 — Demande / Désactivation code Vendeur.

    TK_DemandeCodeVendeur : TypeOri ('TK' = depuis ticket DPAE_Distrib,
    sinon = IDSalarie direct), IDElem, IDPartenaire.

    Format : "Code {Lib_Partenaire} pour NOM Prenom".
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, type_ori, id_elem, id_partenaire
            FROM pgt_tk_demande_code_vendeur
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    base: dict[int, dict] = {}
    part_ids: set[int] = set()
    salarie_ids: set[int] = set()
    distrib_ids: set[int] = set()  # IDTK_Liste de TK_DemandeDPAE_Distrib
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        if not idl:
            continue
        idp = _clean_id(_to_int(r.get("id_partenaire")))
        idelem = _clean_id(_to_int(r.get("id_elem")))
        typeori = (r.get("type_ori") or "").strip().upper()
        base[idl] = {"typeori": typeori, "idelem": idelem, "idp": idp}
        if idp:
            part_ids.add(idp)
        if idelem:
            if typeori == "TK":
                distrib_ids.add(idelem)
            else:
                salarie_ids.add(idelem)
    # Partenaires
    part_libs: dict[int, str] = {}
    if part_ids:
        try:
            db_adv = get_pg_connection("adv")
            ids_t = ",".join(str(i) for i in part_ids)
            prows = db_adv.query(
                f"""SELECT id_partenaire, lib_partenaire FROM pgt_partenaire
                WHERE id_partenaire IN ({ids_t})"""
            )
            for p in prows:
                part_libs[_clean_id(_to_int(p.get("id_partenaire")))] = (
                    p.get("lib_partenaire") or ""
                ).strip()
        except Exception:
            pass
    # Salaries
    sals = load_salaries_minimal(salarie_ids)
    # Distrib (TK_DemandeDPAE_Distrib avec NOM/PRENOM mémos)
    distrib_names: dict[int, tuple[str, str]] = {}
    if distrib_ids:
        try:
            ids_t = ",".join(str(i) for i in distrib_ids)
            drows = db.query(
                f"""SELECT id_tk_liste, nom, prenom
                FROM pgt_tk_demande_dpae_distrib
                WHERE id_tk_liste IN ({ids_t})"""
            )
            for d in drows:
                idl_d = _clean_id(_to_int(d.get("id_tk_liste")))
                if idl_d:
                    distrib_names[idl_d] = (
                        (d.get("nom") or "").strip(),
                        (d.get("prenom") or "").strip(),
                    )
        except Exception:
            pass
    out: dict[int, str] = {}
    for idl, d in base.items():
        lib_part = part_libs.get(d["idp"], "")
        if d["typeori"] == "TK":
            nom, prenom = distrib_names.get(d["idelem"], ("", ""))
        else:
            s = sals.get(d["idelem"])
            nom = s["nom"] if s else ""
            prenom = s["prenom"] if s else ""
        if not (nom or prenom):
            continue
        out[idl] = f"Code {lib_part} pour {nom} {_capit(prenom)}".strip()
    return out


def _info_carte_pro(id_tickets: list[int]) -> dict[int, str]:
    """Cas 2 — TK_DemandeCartePRO (peut avoir plusieurs lignes par ticket).

    Pas de NOM/PRENOM dans la table — il faut joindre via IDSalarie.
    Format : "Pour NOM Prenom" (+ "..." si plus d'1 carte par ticket).
    """
    if not id_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = _ids_in_clause(id_tickets)
    if not ids_sql:
        return {}
    try:
        rows = db.query(
            f"""SELECT id_tk_liste, id_salarie
            FROM pgt_tk_demande_carte_pro
            WHERE id_tk_liste IN ({ids_sql})"""
        )
    except Exception:
        return {}
    grouped: dict[int, list[int]] = {}
    all_salaries: set[int] = set()
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_liste")))
        ids = _clean_id(_to_int(r.get("id_salarie")))
        if not idl or not ids:
            continue
        grouped.setdefault(idl, []).append(ids)
        all_salaries.add(ids)
    if not grouped:
        return {}
    sals = load_salaries_minimal(all_salaries)
    out: dict[int, str] = {}
    for idl, salarie_ids in grouped.items():
        labels: list[str] = []
        for sid in salarie_ids:
            s = sals.get(sid)
            if s:
                labels.append(f"{s['nom']} {_capit(s['prenom'])}".strip())
        if not labels:
            continue
        if len(labels) > 1:
            out[idl] = f"Pour {labels[0]}, ..."
        else:
            out[idl] = f"Pour {labels[0]}"
    return out


# ---------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------

# Cas avec implémentation directe (ne va PAS via _info_via_id_salarie)
_DIRECT_CASES = {
    3:  _info_dpae,
    21: _info_dpae,
    20: _info_call_sfr,
    22: _info_call_energie,
    10: _info_avance,
    25: _info_attr_exocash,
    11: _info_sos_bo,
    29: _info_dpae_distrib,
    30: _info_integration_distrib,
    33: _info_facturation,
    2:  _info_carte_pro,
    1:  _info_commande_fourniture,
    9:  _info_reservation,
    17: _info_sos_juri,
    26: _info_call_sfr_ret_rdv_tech,
    28: _info_facturation_distrib,
    31: _info_doc_distrib,
    35: _info_pv_ulease,
    38: lambda ids: _info_code_vendeur(ids, desactivation=False),
    39: lambda ids: _info_code_vendeur(ids, desactivation=True),
}

# Cas via id_salarie : (db_key, table, id_col, prefix)
# Mapping BDD : les tables liées aux RH sont dans `ticket_rh`, les autres
# dans `ticket_bo`. La doc projet liste les tables ticket_rh (CttW, Conges,
# CdeExoCash, AttExoCash, Mutuelle, SignPVUlease, SortieRH, SOS_JU, ...).
_SALARIE_CASES: dict[int, tuple[str, str, str, str]] = {
    27: ("ticket_rh", "pgt_tk_demande_mutuelle", "id_salarie", "pour "),
    24: ("ticket_rh", "pgt_tk_cde_exo_cash", "id_salarie", "pour "),
    23: ("ticket_bo", "pgt_tk_demande_ctt_courtage", "id_salarie", "pour "),
    4:  ("ticket_rh", "pgt_tk_demande_ctt_w", "id_salarie", "pour "),
    40: ("ticket_rh", "pgt_tk_demande_ctt_w", "id_salarie", "pour "),
    12: ("ticket_rh", "pgt_tk_demande_sortie_rh", "id_salarie", "pour "),
    36: ("ticket_rh", "pgt_tk_demande_sortie_rh", "id_salarie", "pour "),
    37: ("ticket_rh", "pgt_tk_demande_sortie_rh", "id_salarie", "pour "),
    13: ("ticket_rh", "pgt_tk_demande_conges", "id_salarie", "pour "),
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
