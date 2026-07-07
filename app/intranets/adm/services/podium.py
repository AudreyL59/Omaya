"""
Service Fen_GestionPodium - Gestion des Podiums.

Ce fichier contient :
  - Combos (types podium actifs, distributeurs)
  - CRUD PodiumType et PodiumTypePart (onglet Parametres)
  - Valider annee (onglet Annee Podium)
  - Recherche podium vendeurs + score visible + telecharger (onglet 1)
  - Calcul podium (proc Podium_Calcul dans podium_calcul.py)
"""
from __future__ import annotations

import io as _io
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.podium import (
    CalculPodiumParams, CalculPodiumResult, ComboItem, PodiumType,
    PodiumTypePart, PodiumTypePartPayload, PodiumTypePayload,
    RechercherPodiumParams, RechercherPodiumResult, SauveScoreVisibleParams,
    TelechargerParams, ValiderAnneeParams, ValiderAnneeResult,
    VendeurPodiumRow,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers communs
# --------------------------------------------------------------------

def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _iso_date(v) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper()


# --------------------------------------------------------------------
# Combos (Types podium, Distributeurs)
# --------------------------------------------------------------------

def list_types_podium_actifs() -> list[ComboItem]:
    """Combo 'Type Podium' onglet 1.
    Cf. WinDev : PodiumType actifs, tri par ordre_affichage.
    """
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_podium_type, lib_podium_type
                 FROM divers.pgt_podium_type
                WHERE is_actif = TRUE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY ordre_affichage ASC NULLS LAST,
                         lib_podium_type ASC""",
        ) or []
    except Exception:
        logger.exception("list_types_podium_actifs")
        return []
    return [
        ComboItem(
            id=_clean_id(r.get("id_podium_type")),
            lib=(r.get("lib_podium_type") or "").strip(),
        )
        for r in rows
    ]


def list_distributeurs() -> list[ComboItem]:
    """Combo 'Distrib' onglet 1. Cf. WinDev ReqListeDitrib :
    organigramme dont le parent est un enfant de racine (id_ste=4),
    en excluant l'orga 20160729152638792.
    """
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT o.idorganigramme, o.lib_orga
                 FROM pgt_organigramme o
                 JOIN pgt_organigramme p
                      ON p.idorganigramme = o.id_parent
                WHERE p.id_parent = 0
                  AND p.idorganigramme <> 20160729152638792
                  AND p.id_ste = 4
                  AND (o.modif_elem IS NULL
                       OR o.modif_elem NOT LIKE '%suppr%')
                ORDER BY o.lib_orga ASC""",
        ) or []
    except Exception:
        logger.exception("list_distributeurs")
        return []
    return [
        ComboItem(
            id=_clean_id(r.get("idorganigramme")),
            lib=(r.get("lib_orga") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Onglet 2 - CRUD PodiumType (gauche)
# --------------------------------------------------------------------

def list_podium_types() -> list[PodiumType]:
    """Liste tous les PodiumType non supprimes (tri par ordre_affichage)."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_podium_type, lib_podium_type, lib_court,
                      prod_groupe, qualite, espoir, is_actif,
                      ordre_affichage
                 FROM divers.pgt_podium_type
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY ordre_affichage ASC NULLS LAST,
                         lib_podium_type ASC""",
        ) or []
    except Exception:
        logger.exception("list_podium_types")
        return []
    return [
        PodiumType(
            id_podium_type=_clean_id(r.get("id_podium_type")),
            lib_podium_type=(r.get("lib_podium_type") or "").strip(),
            lib_court=(r.get("lib_court") or "").strip(),
            prod_groupe=bool(r.get("prod_groupe")),
            qualite=bool(r.get("qualite")),
            espoir=bool(r.get("espoir")),
            is_actif=bool(r.get("is_actif")),
            ordre_affichage=int(r.get("ordre_affichage") or 0),
        )
        for r in rows
    ]


def create_podium_type(p: PodiumTypePayload, op_id: int) -> str:
    """Cree un PodiumType. Retourne l'id cree en string."""
    db = get_pg_connection("rh")
    r = db.query_one(
        """INSERT INTO divers.pgt_podium_type
              (lib_podium_type, lib_court, prod_groupe, qualite, espoir,
               is_actif, ordre_affichage,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')
           RETURNING id_podium_type""",
        (
            p.lib_podium_type.strip(), p.lib_court.strip(),
            p.prod_groupe, p.qualite, p.espoir,
            p.is_actif, p.ordre_affichage, int(op_id),
        ),
    )
    return _clean_id(r.get("id_podium_type")) if r else ""


def update_podium_type(id_pt: str, p: PodiumTypePayload, op_id: int) -> bool:
    if not id_pt or id_pt == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_podium_type
              SET lib_podium_type = ?, lib_court = ?, prod_groupe = ?,
                  qualite = ?, espoir = ?, is_actif = ?,
                  ordre_affichage = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_podium_type = ?""",
        (
            p.lib_podium_type.strip(), p.lib_court.strip(),
            p.prod_groupe, p.qualite, p.espoir, p.is_actif,
            p.ordre_affichage, int(op_id), int(id_pt),
        ),
    )
    return True


def delete_podium_type(id_pt: str, op_id: int) -> bool:
    """Soft delete : marque modif_elem='suppr' (cf. WinDev)."""
    if not id_pt or id_pt == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_podium_type
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_podium_type = ?""",
        (int(op_id), int(id_pt)),
    )
    return True


# --------------------------------------------------------------------
# Onglet 2 - CRUD PodiumTypePart (droite)
# --------------------------------------------------------------------

def list_podium_type_parts(id_podium_type: str) -> list[PodiumTypePart]:
    """Liste les Parts d'un PodiumType donne."""
    if not id_podium_type or id_podium_type == "0":
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_podium_type_part, id_podium_type,
                      famille, sous_fam, prefixe_bdd, type_prod,
                      option_vente, jour_cial_deb, jour_cial_fin
                 FROM divers.pgt_podium_type_part
                WHERE id_podium_type = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY prefixe_bdd ASC, famille ASC""",
            (int(id_podium_type),),
        ) or []
    except Exception:
        logger.exception("list_podium_type_parts")
        return []
    return [
        PodiumTypePart(
            id_podium_type_part=_clean_id(r.get("id_podium_type_part")),
            id_podium_type=_clean_id(r.get("id_podium_type")),
            famille=(r.get("famille") or "Tous").strip(),
            sous_fam=(r.get("sous_fam") or "Tous").strip(),
            prefixe_bdd=(r.get("prefixe_bdd") or "").strip(),
            type_prod=(r.get("type_prod") or "").strip(),
            option_vente=(r.get("option_vente") or "").strip(),
            jour_cial_deb=int(r.get("jour_cial_deb") or 1),
            jour_cial_fin=int(r.get("jour_cial_fin") or 31),
        )
        for r in rows
    ]


def create_podium_type_part(p: PodiumTypePartPayload, op_id: int) -> str:
    db = get_pg_connection("rh")
    r = db.query_one(
        """INSERT INTO divers.pgt_podium_type_part
              (id_podium_type, famille, sous_fam, prefixe_bdd, type_prod,
               option_vente, jour_cial_deb, jour_cial_fin,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')
           RETURNING id_podium_type_part""",
        (
            int(p.id_podium_type),
            p.famille.strip() or "Tous",
            p.sous_fam.strip() or "Tous",
            p.prefixe_bdd.strip(),
            p.type_prod.strip(),
            p.option_vente.strip(),
            int(p.jour_cial_deb),
            int(p.jour_cial_fin),
            int(op_id),
        ),
    )
    return _clean_id(r.get("id_podium_type_part")) if r else ""


def update_podium_type_part(
    id_ptp: str, p: PodiumTypePartPayload, op_id: int,
) -> bool:
    if not id_ptp or id_ptp == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_podium_type_part
              SET id_podium_type = ?, famille = ?, sous_fam = ?,
                  prefixe_bdd = ?, type_prod = ?, option_vente = ?,
                  jour_cial_deb = ?, jour_cial_fin = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_podium_type_part = ?""",
        (
            int(p.id_podium_type),
            p.famille.strip() or "Tous",
            p.sous_fam.strip() or "Tous",
            p.prefixe_bdd.strip(), p.type_prod.strip(),
            p.option_vente.strip(),
            int(p.jour_cial_deb), int(p.jour_cial_fin),
            int(op_id), int(id_ptp),
        ),
    )
    return True


def delete_podium_type_part(id_ptp: str, op_id: int) -> bool:
    if not id_ptp or id_ptp == "0":
        return False
    db = get_pg_connection("rh")
    db.execute(
        """UPDATE divers.pgt_podium_type_part
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_podium_type_part = ?""",
        (int(op_id), int(id_ptp)),
    )
    return True


# --------------------------------------------------------------------
# Onglet 3 - Valider annee
# --------------------------------------------------------------------

def valider_annee(p: ValiderAnneeParams, op_id: int) -> ValiderAnneeResult:
    """Cf. WinDev 'Valider l'annee' :
    Pour chaque PodiumType non supprime, cree 12 lignes PodiumMois si
    elles n'existent pas encore (score_visible = TRUE par defaut).
    """
    if p.annee < 2020 or p.annee > 2100:
        return ValiderAnneeResult(
            ok=False, message="Annee invalide",
        )
    db = get_pg_connection("rh")
    try:
        types = db.query(
            """SELECT id_podium_type FROM divers.pgt_podium_type
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception as e:
        return ValiderAnneeResult(ok=False, message=f"Erreur SQL : {e}")

    nb_crees = 0
    for t in types:
        id_pt = int(t.get("id_podium_type") or 0)
        if not id_pt:
            continue
        for mois in range(1, 13):
            try:
                existing = db.query_one(
                    """SELECT id_podium_mois FROM divers.pgt_podium_mois
                        WHERE id_podium_type = ? AND mois = ? AND annee = ?
                        LIMIT 1""",
                    (id_pt, mois, str(p.annee)),
                )
                if existing:
                    continue
                db.execute(
                    """INSERT INTO divers.pgt_podium_mois
                          (mois, annee, id_podium_type, score_visible,
                           modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, TRUE, NOW(), ?, 'new')""",
                    (mois, str(p.annee), id_pt, int(op_id)),
                )
                nb_crees += 1
            except Exception:
                logger.exception(
                    "valider_annee : insert id_pt=%s mois=%s",
                    id_pt, mois,
                )
    return ValiderAnneeResult(
        ok=True,
        nb_crees=nb_crees,
        message=(
            f"{nb_crees} PodiumMois cree(s) pour l'annee {p.annee}"
            if nb_crees else f"Annee {p.annee} deja complete"
        ),
    )
