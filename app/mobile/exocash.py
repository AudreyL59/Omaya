"""Endpoints mobile ExoCash (WebRest_Omayapp/ExoCash/*).

Portage iso-URL des 12 WS ExoCash mobile WinDev :
  - Attribution/Contenu       : detail d'un ticket d'attribution ExoCash
  - Attribution/Save          : create/update d'une attribution
  - Catalogue/ListerV2/{id}   : catalogue produits (id 'tous' ou id categ)
  - Categorie/Lister          : familles/categories de lots
  - Commandes/Lister          : historique commandes du vendeur
  - Livret/Lister             : historique operations livret
  - Livret/Solde              : {credit=solde, debit=cde en cours}
  - Panier/Encours            : contenu du panier en cours (ticket 24/28)
  - Panier/Prod/Ajout         : ajout d'un produit au panier
  - Panier/Prod/ModifQte      : modif de quantite
  - Panier/Prod/Suppr         : suppr (soft) d'un produit
  - Panier/Validation         : validation de la commande (statut 1)
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.intranets.adm.services import fiche_exo_cash as exo_cash_svc
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-exocash"],
                    dependencies=[Depends(mobile_auth)])


TYPE_DEMANDE_CDE_EC = 24
STATUT_ENCOURS_PANIER = 28
STATUT_VALIDE_EN_ATTENTE = 1


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _to_num(v: Any) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _new_id_wd() -> int:
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _bytea_to_b64(v) -> str:
    if not v:
        return ""
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, str):
        return v
    try:
        return base64.b64encode(v).decode("ascii")
    except Exception:
        return ""


def _capitalise(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _prix_ensolde(row: dict) -> tuple[bool, float]:
    """Renvoie (en_solde_active, prix_solde) pour un ExoCashLot."""
    if not row.get("en_solde"):
        return False, 0.0
    deb, fin = row.get("solde_deb"), row.get("solde_fin")
    now = datetime.now()
    if deb and fin:
        try:
            d = deb if isinstance(deb, datetime) else datetime.fromisoformat(str(deb)[:19])
            f = fin if isinstance(fin, datetime) else datetime.fromisoformat(str(fin)[:19])
            if d <= now <= f:
                return True, _to_num(row.get("montant_solde"))
        except Exception:
            pass
    return False, 0.0


def _get_or_create_ticket_encours(id_vend: int, db_ticket, db_ticket_rh) -> int:
    """Retourne l'IDTK_Liste du panier en cours du vendeur (statut 28,
    type demande 24), en le creant si absent."""
    row = db_ticket.query_one(
        """SELECT id_tk_liste FROM ticket.pgt_tk_liste
            WHERE id_tk_type_demande = ?
              AND id_tk_statut = ?
              AND COALESCE(cloturee, FALSE) = FALSE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND op_crea = ?
            ORDER BY id_tk_liste DESC
            LIMIT 1""",
        (TYPE_DEMANDE_CDE_EC, STATUT_ENCOURS_PANIER, int(id_vend)),
    )
    if row:
        return int(row.get("id_tk_liste") or 0)

    # Creation ticket + entete commande
    id_new = _new_id_wd()
    now = datetime.now()
    db_ticket.query(
        """INSERT INTO ticket.pgt_tk_liste
             (id_tk_liste_auto, id_tk_liste, date_crea, op_crea, op_dest,
              service, id_tk_type_demande, id_tk_statut, cloturee,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, 'RH', ?, ?, FALSE, ?, ?, 'new')""",
        (id_new, id_new, now, int(id_vend), int(id_vend),
         TYPE_DEMANDE_CDE_EC, STATUT_ENCOURS_PANIER, now, int(id_vend)),
    )

    # Adresse de livraison depuis salarie_coordonnees
    dbrh = get_pg_connection("rh")
    adr = ""
    try:
        c = dbrh.query_one(
            """SELECT adresse1, adresse2, cp, ville
                 FROM rh.pgt_salarie_coordonnees
                WHERE id_salarie = ? LIMIT 1""",
            (int(id_vend),),
        )
        if c:
            parts = [
                (c.get("adresse1") or "").strip(),
                (c.get("adresse2") or "").strip(),
                f"{(c.get('cp') or '').strip()} {(c.get('ville') or '').strip()}".strip(),
            ]
            adr = "\n".join(p for p in parts if p)
    except Exception:
        logger.exception("adresse livraison id_sal=%s", id_vend)

    db_ticket_rh.query(
        """INSERT INTO ticket_rh.pgt_tk_cde_exo_cash
             (id_tk_cde_exo_cash_auto, id_tk_cde_exo_cash, id_tk_liste,
              id_salarie, date_commande, adresse_livraison, commande_validee,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, FALSE, ?, ?, 'new')""",
        (id_new, id_new, id_new, int(id_vend), now, adr, now, int(id_vend)),
    )
    return id_new


# ---------------------------------------------------------------------------
#  Attribution/Contenu
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Attribution/Contenu")
def attribution_contenu(payload: dict = Body(...)):
    """Portage DemandeAttEC_Contenu. Detail d'une attribution."""
    id_ticket = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {
        "Beneficiaire": 0, "IDTk_DemandeAttExoCash": "0",
        "IDTK_Liste": "0", "Montant": 0.0,
        "NomBeneficiaire": "", "PrenomBeneficiaire": "", "InfoAtt": "",
    }
    if not id_ticket:
        return empty

    db = get_pg_connection("ticket_rh")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_att_exo_cash, id_tk_liste,
                      id_salarie, montant_ec, info_attribution
                 FROM ticket_rh.pgt_tk_demande_att_exo_cash
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                LIMIT 1""",
            (id_ticket,),
        )
    except Exception:
        logger.exception("attribution_contenu id=%s", id_ticket)
        return empty
    if not row:
        return empty

    id_sal = int(row.get("id_salarie") or 0)
    dbrh = get_pg_connection("rh")
    nom = prenom = ""
    try:
        s = dbrh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_sal,),
        )
        if s:
            nom = (s.get("nom") or "").strip()
            prenom = (s.get("prenom") or "").strip()
    except Exception:
        pass

    return {
        "Beneficiaire": id_sal,
        "IDTk_DemandeAttExoCash": str(int(row.get("id_tk_demande_att_exo_cash") or 0)),
        "IDTK_Liste": str(int(row.get("id_tk_liste") or 0)),
        "Montant": _to_num(row.get("montant_ec")),
        "NomBeneficiaire": nom,
        "PrenomBeneficiaire": prenom,
        "InfoAtt": row.get("info_attribution") or "",
    }


# ---------------------------------------------------------------------------
#  Attribution/Save
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Attribution/Save")
def attribution_save(payload: dict = Body(...),
                     id_cial: int = Depends(mobile_auth)):
    """Portage DemandeAttEC_Save. Cree ou modifie une attribution."""
    id_tk = _to_int(payload.get("IDTK_Liste"))
    id_benef = _to_int(payload.get("Beneficiaire"))
    montant = _to_num(payload.get("Montant"))
    info_att = payload.get("InfoAtt") or ""

    db_trh = get_pg_connection("ticket_rh")
    db_t = get_pg_connection("ticket")
    now = datetime.now()

    if id_tk:
        # Update
        try:
            row = db_trh.query_one(
                """SELECT id_tk_demande_att_exo_cash
                     FROM ticket_rh.pgt_tk_demande_att_exo_cash
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk,),
            )
            if not row:
                return {"nIdDemande": "0"}
            db_trh.query(
                """UPDATE ticket_rh.pgt_tk_demande_att_exo_cash
                      SET id_salarie = ?, montant_ec = ?,
                          info_attribution = ?, modif_date = ?,
                          modif_op = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (id_benef, montant, info_att, now, id_cial, id_tk),
            )
            db_t.query(
                """UPDATE ticket.pgt_tk_liste
                      SET modification = TRUE, op_modif = ?, op_dest = ?,
                          modif_date = ?, modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (id_cial, id_benef, now, id_tk),
            )
            return {"nIdDemande": str(id_tk)}
        except Exception as e:
            logger.exception("attribution_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert : nouveau ticket + attribution
    id_new = _new_id_wd()
    try:
        db_t.query(
            """INSERT INTO ticket.pgt_tk_liste
                 (id_tk_liste_auto, id_tk_liste, date_crea, op_crea, op_dest,
                  service, id_tk_type_demande, id_tk_statut, cloturee,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, 'RH', 25, 1, FALSE, ?, ?, 'new')""",
            (id_new, id_new, now, id_cial, id_benef, now, id_cial),
        )
        db_trh.query(
            """INSERT INTO ticket_rh.pgt_tk_demande_att_exo_cash
                 (id_tk_demande_att_exo_cash_auto, id_tk_demande_att_exo_cash,
                  id_tk_liste, id_salarie, montant_ec, info_attribution,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_new, id_benef, montant, info_att,
             now, id_cial),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("attribution_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  Catalogue/ListerV2/{id}
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Catalogue/ListerV2/{id_cate}")
def catalogue_lister_v2(id_cate: str, _payload: Any = Body(default=None)):
    """Portage ListerCatalogue1. Retourne le catalogue.
    id_cate == 'tous' -> toutes categories. Photos en base64.
    """
    db = get_pg_connection("divers")

    if str(id_cate).lower() == "tous":
        sql = """SELECT * FROM divers.pgt_exo_cash_lot
                  WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                    AND COALESCE(is_actif, FALSE) = TRUE"""
        params: tuple = ()
    else:
        sql = """SELECT * FROM divers.pgt_exo_cash_lot
                  WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                    AND COALESCE(is_actif, FALSE) = TRUE
                    AND id_exo_cash_famille_lot = ?"""
        params = (_to_int(id_cate),)

    try:
        rows = db.query(sql, params) or []
    except Exception:
        logger.exception("catalogue_lister_v2 id=%s", id_cate)
        return []

    # Familles lookup
    fam_map: dict[int, str] = {}
    try:
        fams = db.query(
            "SELECT id_exo_cash_famille_lot, lib_famille_lot FROM divers.pgt_exo_cash_famille_lot",
        ) or []
        fam_map = {int(f.get("id_exo_cash_famille_lot") or 0):
                   (f.get("lib_famille_lot") or "").strip() for f in fams}
    except Exception:
        pass

    genres = ["", "Femme", "Homme", "Unisexe"]

    result = []
    for r in rows:
        marque = (r.get("marque") or "").strip() or "Sans marque"
        en_solde, prix_solde = _prix_ensolde(r)
        cat = _to_int(r.get("categorie"))
        item = {
            "ID": str(int(r.get("id_exo_cash_lot") or 0)),
            "IDCategorie": str(int(r.get("id_exo_cash_famille_lot") or 0)),
            "Lib": (r.get("lib_lot") or "").strip(),
            "Marque": marque,
            "Description": r.get("description") or "",
            "Prix": _to_num(r.get("montant")),
            "EnSolde": en_solde,
            "PrixSolde": prix_solde if en_solde else 0.0,
            "Stock": _to_int(r.get("stock")),
            "SurCommande": bool(r.get("sur_commande")),
            "Genre": cat,
            "LibGenre": genres[cat] if 0 < cat < len(genres) else "",
            "LibCategorie": fam_map.get(_to_int(r.get("id_exo_cash_famille_lot")), ""),
            "Photo1": _bytea_to_b64(r.get("photo1")),
            "Photo2": _bytea_to_b64(r.get("photo2")),
            "Photo3": _bytea_to_b64(r.get("photo3")),
        }
        result.append(item)
    return result


# ---------------------------------------------------------------------------
#  Categorie/Lister
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Categorie/Lister")
def categorie_lister(_payload: Any = Body(default=None)):
    """Portage ListerCategorie."""
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_exo_cash_famille_lot, lib_famille_lot, icone
                 FROM divers.pgt_exo_cash_famille_lot
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_famille_lot ASC""",
        ) or []
    except Exception:
        logger.exception("categorie_lister")
        return []
    return [
        {"ID": str(int(r.get("id_exo_cash_famille_lot") or 0)),
         "Lib": (r.get("lib_famille_lot") or "").strip(),
         "Icone": _bytea_to_b64(r.get("icone"))}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  Commandes/Lister
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Commandes/Lister")
def commandes_lister(payload: dict = Body(...),
                     id_auth: int = Depends(mobile_auth)):
    """Portage ListerCommandes. Historique des commandes du vendeur."""
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie") or id_auth)
    if not id_vend:
        return []

    db_trh = get_pg_connection("ticket_rh")
    db_t = get_pg_connection("ticket")

    # Header commandes
    try:
        cdes = db_trh.query(
            """SELECT tc.id_tk_liste, tc.id_salarie, tc.date_commande,
                      tc.commande_validee, tc.date_validation,
                      tc.adresse_livraison
                 FROM ticket_rh.pgt_tk_cde_exo_cash tc
                WHERE tc.id_salarie = ?
                  AND (tc.modif_elem IS NULL OR tc.modif_elem NOT LIKE '%suppr%')
                ORDER BY tc.date_commande DESC""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("commandes_lister header id=%s", id_vend)
        return []

    if not cdes:
        return []

    id_tk_list = [int(c.get("id_tk_liste") or 0) for c in cdes]
    id_tk_list = [x for x in id_tk_list if x]

    # Statut/cloturee depuis ticket.pgt_tk_liste
    tk_map: dict[int, dict] = {}
    if id_tk_list:
        try:
            placeholders = ",".join("?" for _ in id_tk_list)
            tks = db_t.query(
                f"""SELECT id_tk_liste, id_tk_statut, cloturee, modif_elem
                     FROM ticket.pgt_tk_liste
                    WHERE id_tk_liste IN ({placeholders})
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                      AND id_tk_statut <> 28""",
                tuple(id_tk_list),
            ) or []
            tk_map = {int(t.get("id_tk_liste") or 0): t for t in tks}
        except Exception:
            logger.exception("commandes_lister tks")

    result = []
    for c in cdes:
        id_tk = int(c.get("id_tk_liste") or 0)
        tk = tk_map.get(id_tk)
        if not tk:
            continue

        if c.get("commande_validee"):
            statut = "Validee"
        elif tk.get("cloturee"):
            statut = "Annulee"
        elif int(tk.get("id_tk_statut") or 0) == 1:
            statut = "NonTraite"
        else:
            statut = "EnCours"

        panier = _panier_from_ticket(id_tk)
        colis = _colis_from_ticket(id_tk)

        result.append({
            "idTicket": str(id_tk),
            "DateCommande": _iso_dt(c.get("date_commande")),
            "Statut": statut,
            "Panier": panier,
            "SuiviColis": colis,
        })
    return result


def _panier_from_ticket(id_tk_liste: int) -> list[dict]:
    db_trh = get_pg_connection("ticket_rh")
    db_div = get_pg_connection("divers")
    try:
        rows = db_trh.query(
            """SELECT tkcl.id_tk_cde_exo_cash_lot, tkcl.num_suivi,
                      tkcl.montant_paye, tkcl.id_exo_cash_lot, tkcl.qte
                 FROM ticket_rh.pgt_tk_cde_exo_cash_lot tkcl
                WHERE tkcl.id_tk_liste = ?
                  AND (tkcl.modif_elem IS NULL OR tkcl.modif_elem NOT LIKE '%suppr%')""",
            (int(id_tk_liste),),
        ) or []
    except Exception:
        logger.exception("_panier_from_ticket id=%s", id_tk_liste)
        return []

    lot_ids = [int(r.get("id_exo_cash_lot") or 0) for r in rows if r.get("id_exo_cash_lot")]
    lot_map: dict[int, dict] = {}
    if lot_ids:
        try:
            placeholders = ",".join("?" for _ in lot_ids)
            lots = db_div.query(
                f"""SELECT id_exo_cash_lot, marque, lib_lot, photo1
                     FROM divers.pgt_exo_cash_lot
                    WHERE id_exo_cash_lot IN ({placeholders})""",
                tuple(lot_ids),
            ) or []
            lot_map = {int(l.get("id_exo_cash_lot") or 0): l for l in lots}
        except Exception:
            logger.exception("_panier_from_ticket lots")

    result = []
    for r in rows:
        lot = lot_map.get(int(r.get("id_exo_cash_lot") or 0), {})
        marque = (lot.get("marque") or "").strip() or "Sans marque"
        result.append({
            "ID": str(int(r.get("id_exo_cash_lot") or 0)),
            "Lib": (lot.get("lib_lot") or "").strip(),
            "Marque": marque,
            "Prix": _to_num(r.get("montant_paye")),
            "Stock": _to_int(r.get("qte")),
            "NumSuivi": r.get("num_suivi") or "",
            "Photo1": _bytea_to_b64(lot.get("photo1")),
        })
    return result


def _colis_from_ticket(id_tk_liste: int) -> list[dict]:
    db = get_pg_connection("ticket_rh")
    try:
        rows = db.query(
            """SELECT id_tk_cde_exo_cash_envoi, num_suivi, transporteur, date_envoi
                 FROM ticket_rh.pgt_tk_cde_exo_cash_envoi
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (int(id_tk_liste),),
        ) or []
    except Exception:
        return []
    return [
        {"ID": str(int(r.get("id_tk_cde_exo_cash_envoi") or 0)),
         "Numsuivi": r.get("num_suivi") or "",
         "Transporteur": r.get("transporteur") or "",
         "DateEnvoi": _iso_dt(r.get("date_envoi"))}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  Livret/Lister
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Livret/Lister")
def livret_lister(payload: dict = Body(...),
                  id_auth: int = Depends(mobile_auth)):
    """Portage ListerLivret. Historique operations livret."""
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie") or id_auth)
    if not id_vend:
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT sl.id_type_operation_livret, sl.date_operation,
                      sl.montant_credit, sl.montant_debit, sl.id_tk_liste,
                      sl.id_challenge, sl.id_salarie,
                      tol.lib_opeation
                 FROM rh.pgt_salarie_livret sl
                 LEFT JOIN rh.pgt_type_operation_livret tol
                        ON tol.id_type_operation_livret = sl.id_type_operation_livret
                WHERE sl.id_salarie = ?
                  AND (sl.modif_elem IS NULL OR sl.modif_elem NOT LIKE '%suppr%')
                ORDER BY sl.date_operation DESC NULLS LAST""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("livret_lister id=%s", id_vend)
        return []
    return [
        {"ID": _to_int(r.get("id_type_operation_livret")),
         "Date": _iso_dt(r.get("date_operation")),
         "MontantCredit": _to_num(r.get("montant_credit")),
         "MontantDedit": _to_num(r.get("montant_debit")),
         "Lib": (r.get("lib_opeation") or "").strip()}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  Livret/Solde
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Livret/Solde")
def livret_solde(payload: dict = Body(...),
                 id_auth: int = Depends(mobile_auth)):
    """Portage SoldeLivret. Retour STLivretEC minimal :
    MontantCredit = solde disponible, MontantDedit = commande en cours."""
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie") or id_auth)
    if not id_vend:
        return {"MontantCredit": 0.0, "MontantDedit": 0.0}
    try:
        soldes = exo_cash_svc.compute_soldes(int(id_vend))
    except Exception:
        logger.exception("livret_solde id=%s", id_vend)
        return {"MontantCredit": 0.0, "MontantDedit": 0.0}
    return {
        "MontantCredit": soldes.get("solde_actuel", 0.0),
        "MontantDedit": soldes.get("cde_en_cours", 0.0),
    }


# ---------------------------------------------------------------------------
#  Panier/Encours
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Panier/Encours")
def panier_encours(payload: dict = Body(...),
                   id_auth: int = Depends(mobile_auth)):
    """Portage ListerPanierEncours. Contenu du panier en cours."""
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie") or id_auth)
    if not id_vend:
        return []

    db_t = get_pg_connection("ticket")
    db_trh = get_pg_connection("ticket_rh")

    # Cherche le ticket panier en cours (statut 28)
    try:
        row = db_t.query_one(
            """SELECT id_tk_liste FROM ticket.pgt_tk_liste
                WHERE id_tk_type_demande = ?
                  AND id_tk_statut = ?
                  AND COALESCE(cloturee, FALSE) = FALSE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND op_crea = ?
                ORDER BY id_tk_liste DESC
                LIMIT 1""",
            (TYPE_DEMANDE_CDE_EC, STATUT_ENCOURS_PANIER, int(id_vend)),
        )
    except Exception:
        logger.exception("panier_encours cherche ticket id=%s", id_vend)
        return []
    if not row:
        return []
    id_tk = int(row.get("id_tk_liste") or 0)

    try:
        rows = db_trh.query(
            """SELECT tkcl.id_tk_liste, tkcl.id_tk_cde_exo_cash_lot,
                      tkcl.id_exo_cash_lot, tkcl.qte, tkcl.num_suivi,
                      tc.adresse_livraison
                 FROM ticket_rh.pgt_tk_cde_exo_cash_lot tkcl
                 JOIN ticket_rh.pgt_tk_cde_exo_cash tc
                        ON tc.id_tk_cde_exo_cash = tkcl.id_tk_cde_exo_cash
                WHERE tkcl.id_tk_liste = ?
                  AND (tkcl.modif_elem IS NULL OR tkcl.modif_elem <> 'suppr')""",
            (id_tk,),
        ) or []
    except Exception:
        logger.exception("panier_encours lignes id=%s", id_tk)
        return []
    return [
        {"ID": str(int(r.get("id_exo_cash_lot") or 0)),
         "idTicket": str(int(r.get("id_tk_liste") or 0)),
         "idTicketPanier": str(int(r.get("id_tk_cde_exo_cash_lot") or 0)),
         "Qte": _to_int(r.get("qte")),
         "adresseLivraison": r.get("adresse_livraison") or ""}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  Panier/Prod/Ajout
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Panier/Prod/Ajout")
def panier_prod_ajout(payload: dict = Body(...),
                       id_auth: int = Depends(mobile_auth)):
    """Portage PanierAjoutProd. Ajoute un produit au panier
    (cree le ticket panier si absent)."""
    id_prod = _to_int(payload.get("idProd"))
    id_ticket = _to_int(payload.get("idTicket"))
    id_vend = _to_int(payload.get("idVend") or id_auth)
    if not id_prod or not id_vend:
        return {"ID": 0}

    db_t = get_pg_connection("ticket")
    db_trh = get_pg_connection("ticket_rh")
    db_div = get_pg_connection("divers")

    if not id_ticket:
        id_ticket = _get_or_create_ticket_encours(id_vend, db_t, db_trh)
    if not id_ticket:
        return {"ID": 0}

    # Recup entete commande pour le id_tk_cde_exo_cash
    try:
        cde = db_trh.query_one(
            """SELECT id_tk_cde_exo_cash, adresse_livraison
                 FROM ticket_rh.pgt_tk_cde_exo_cash
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_ticket,),
        )
    except Exception:
        logger.exception("panier_prod_ajout entete id_tk=%s", id_ticket)
        return {"ID": 0}
    if not cde:
        return {"ID": 0}

    # Recup prix (avec solde si applicable)
    try:
        lot = db_div.query_one(
            """SELECT montant, en_solde, montant_solde, solde_deb, solde_fin
                 FROM divers.pgt_exo_cash_lot
                WHERE id_exo_cash_lot = ? LIMIT 1""",
            (id_prod,),
        )
    except Exception:
        logger.exception("panier_prod_ajout lot id=%s", id_prod)
        return {"ID": 0}
    if not lot:
        return {"ID": 0}
    prix = _to_num(lot.get("montant"))
    en_solde, prix_solde = _prix_ensolde(lot)
    if en_solde and prix_solde > 0:
        prix = prix_solde

    id_new = _new_id_wd()
    now = datetime.now()
    try:
        db_trh.query(
            """INSERT INTO ticket_rh.pgt_tk_cde_exo_cash_lot
                 (id_tk_cde_exo_cash_lot_auto, id_tk_cde_exo_cash_lot,
                  id_tk_cde_exo_cash, id_tk_liste, id_exo_cash_lot,
                  qte, montant_paye, num_suivi,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, 1, ?, '', ?, ?, 'new')""",
            (id_new, id_new,
             int(cde.get("id_tk_cde_exo_cash") or 0), id_ticket,
             id_prod, prix, now, id_vend),
        )
    except Exception as e:
        logger.exception("panier_prod_ajout insert")
        return {"ID": 0, "sInfoData": str(e)}

    return {
        "ID": str(id_prod),
        "idTicket": str(id_ticket),
        "idTicketPanier": str(id_new),
        "Qte": 1,
        "adresseLivraison": cde.get("adresse_livraison") or "",
    }


# ---------------------------------------------------------------------------
#  Panier/Prod/ModifQte
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Panier/Prod/ModifQte")
def panier_prod_modif_qte(payload: dict = Body(...),
                             id_auth: int = Depends(mobile_auth)):
    """Portage PanierModifQteProd. Modif de la quantite."""
    id_panier = _to_int(payload.get("idPanier"))
    qte = _to_int(payload.get("Qte"))
    id_vend = _to_int(payload.get("idVend") or id_auth)
    if not id_panier:
        return {"nIdDemande": "0"}

    db = get_pg_connection("ticket_rh")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket_rh.pgt_tk_cde_exo_cash_lot
                  SET qte = ?, modif_elem = 'modif',
                      modif_date = ?, modif_op = ?
                WHERE id_tk_cde_exo_cash_lot = ?""",
            (qte, now, id_vend, id_panier),
        )
        return {"nIdDemande": str(id_panier)}
    except Exception as e:
        logger.exception("panier_prod_modif_qte id=%s", id_panier)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  Panier/Prod/Suppr
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Panier/Prod/Suppr")
def panier_prod_suppr(payload: dict = Body(...),
                       id_auth: int = Depends(mobile_auth)):
    """Portage PanierSupprimeProd. Suppr (soft) d'une ligne de panier."""
    id_panier = _to_int(payload.get("idPanier"))
    id_vend = _to_int(payload.get("idVend") or id_auth)
    if not id_panier:
        return {"nIdDemande": "0"}

    db = get_pg_connection("ticket_rh")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket_rh.pgt_tk_cde_exo_cash_lot
                  SET modif_elem = 'suppr', modif_date = ?, modif_op = ?
                WHERE id_tk_cde_exo_cash_lot = ?""",
            (now, id_vend, id_panier),
        )
        return {"nIdDemande": str(id_panier)}
    except Exception as e:
        logger.exception("panier_prod_suppr id=%s", id_panier)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  Panier/Validation
# ---------------------------------------------------------------------------

@router.post("/ExoCash/Panier/Validation")
def panier_validation(payload: dict = Body(...),
                       id_auth: int = Depends(mobile_auth)):
    """Portage ValidationCommande. Valide le panier (statut 1) et
    reactualise les prix.

    TODO : envoi mail marie@ + envoiSMS au vendeur + envoiSMS au staff
    (non porte en V1 - ces helpers WinDev n'ont pas encore d'equivalent
    Python cote mobile ; ils resteront a brancher).
    """
    id_ticket = _to_int(payload.get("idTicket"))
    adresse = payload.get("adresseLivraison") or ""
    id_vend = _to_int(payload.get("idVend") or id_auth)
    if not id_ticket:
        return {"nIdDemande": "0"}

    db_t = get_pg_connection("ticket")
    db_trh = get_pg_connection("ticket_rh")
    db_div = get_pg_connection("divers")
    now = datetime.now()

    # 1. Update commande header
    try:
        db_trh.query(
            """UPDATE ticket_rh.pgt_tk_cde_exo_cash
                  SET date_commande = ?, adresse_livraison = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (now, adresse, now, id_vend, id_ticket),
        )
    except Exception:
        logger.exception("panier_validation header id=%s", id_ticket)
        return {"nIdDemande": "0"}

    # 2. Update statut ticket -> 1 (En attente traitement)
    try:
        db_t.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = ?, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (STATUT_VALIDE_EN_ATTENTE, now, id_vend, id_ticket),
        )
    except Exception:
        logger.exception("panier_validation statut id=%s", id_ticket)
        return {"nIdDemande": "0"}

    # 3. Actualise les prix (en cas de changement de solde entre-temps)
    try:
        lignes = db_trh.query(
            """SELECT tkcl.id_tk_cde_exo_cash_lot, tkcl.id_exo_cash_lot,
                      tkcl.qte, tkcl.montant_paye
                 FROM ticket_rh.pgt_tk_cde_exo_cash_lot tkcl
                WHERE tkcl.id_tk_liste = ?
                  AND (tkcl.modif_elem IS NULL OR tkcl.modif_elem NOT LIKE '%suppr%')""",
            (id_ticket,),
        ) or []
        for l in lignes:
            id_lot = int(l.get("id_exo_cash_lot") or 0)
            if not id_lot:
                continue
            lot = db_div.query_one(
                """SELECT montant, en_solde, montant_solde,
                          solde_deb, solde_fin
                     FROM divers.pgt_exo_cash_lot
                    WHERE id_exo_cash_lot = ? LIMIT 1""",
                (id_lot,),
            )
            if not lot:
                continue
            prix = _to_num(lot.get("montant"))
            en_solde, prix_solde = _prix_ensolde(lot)
            if en_solde and prix_solde > 0:
                prix = prix_solde
            if abs(prix - _to_num(l.get("montant_paye"))) > 0.001:
                db_trh.query(
                    """UPDATE ticket_rh.pgt_tk_cde_exo_cash_lot
                          SET montant_paye = ?, modif_date = ?
                        WHERE id_tk_cde_exo_cash_lot = ?""",
                    (prix, now, int(l.get("id_tk_cde_exo_cash_lot") or 0)),
                )
    except Exception:
        logger.exception("panier_validation prix id=%s", id_ticket)

    return {"nIdDemande": str(id_ticket)}
