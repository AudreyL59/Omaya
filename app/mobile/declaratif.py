"""Endpoints mobile Declaratif (WebRest_Omayapp/Declaratif/*).

Portage iso-URL des 8 WS declaratif Presence/Production/Equipe :
  - Equipe                : rapport texte du declaratif de l'equipe
  - Pres/ListeByOrga      : STDecPres pour tous les salaries d'un orga
  - Pres/ListeBySalarie   : STDecPres pour un tableau de salaries donne
  - Pres/Save             : ajout / update declaratif presence
  - Prod/ListeByOrga      : STDecProd pour tous les salaries d'un orga
  - Prod/ListeBySalarie   : STDecProd pour un tableau de salaries donne
  - Prod/Save             : upsert de plusieurs lignes STDecProd
  - Prod/Type             : STTypeDecProd pour l'orga (filtre par
                             prefixes bdd partenaires actifs)

Reutilise les helpers agcial (_parse_jour, _test_vendeur_absent).
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime
from typing import Any, Iterable

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import (
    _new_id_wd, _parse_jour, _test_vendeur_absent, _to_int,
)
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-declaratif"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _orga_arbre(id_orga: int) -> list[dict]:
    """Portage minimaliste Omayapp_InfoOrganigramme.

    Retourne l'orga racine + tous les descendants (jusqu'a 5 niveaux
    via CTE recursive PG), en filtrant les modif_elem='suppr'.
    Format : [{id, Lib, TypeProd, Niveau, PARENT_ID, MasquePod, MasqueEff}]
    """
    if not id_orga:
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """WITH RECURSIVE arbre AS (
                   SELECT idorganigramme AS id,
                          lib_orga AS lib,
                          id_type_produit AS type_prod,
                          in_visible_podium AS masque_pod,
                          in_visible_effectif AS masque_eff,
                          1 AS niveau,
                          CAST(NULL AS bigint) AS parent_id,
                          CAST('' AS text) AS parent_lib,
                          modif_elem
                     FROM rh.pgt_organigramme
                    WHERE idorganigramme = ?
                   UNION ALL
                   SELECT o.idorganigramme, o.lib_orga, o.id_type_produit,
                          o.in_visible_podium, o.in_visible_effectif,
                          a.niveau + 1, a.id, a.lib, o.modif_elem
                     FROM rh.pgt_organigramme o
                     JOIN arbre a ON o.id_parent = a.id
                    WHERE a.niveau < 6
                      AND o.idorganigramme <> 20160729152638792
               )
               SELECT DISTINCT id, lib, type_prod, masque_pod,
                      masque_eff, niveau, parent_id, parent_lib, modif_elem
                 FROM arbre
                WHERE modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%'
                ORDER BY niveau, lib""",
            (int(id_orga),),
        ) or []
    except Exception:
        logger.exception("_orga_arbre id=%s", id_orga)
        return []
    return [
        {"id": int(r.get("id") or 0),
         "Lib": (r.get("lib") or "").strip(),
         "TypeProd": _to_int(r.get("type_prod")),
         "Niveau": _to_int(r.get("niveau")),
         "PARENT_ID": _to_int(r.get("parent_id")),
         "PARENT_Lib": (r.get("parent_lib") or "").strip(),
         "MasquePod": bool(r.get("masque_pod")),
         "MasqueEff": bool(r.get("masque_eff"))}
        for r in rows
    ]


def _salaries_orga(id_orga: int) -> list[dict]:
    """Portage minimaliste Info_SalariéOrga.

    Retourne les salaries actifs affectes a un organigramme donne.
    Filtres : en_activite=True, aff_actif=True, date_debut <= today,
    (date_fin=NULL ou date_fin>=today ou sentinelle 1900).
    """
    if not id_orga:
        return []
    today_iso = date.today().isoformat()
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT DISTINCT s.id_salarie, s.nom, s.prenom
                 FROM rh.pgt_salarie s
                 JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                 JOIN rh.pgt_salarie_organigramme so ON so.id_salarie = s.id_salarie
                WHERE so.idorganigramme = ?
                  AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
                  AND so.date_debut::date <= ?::date
                  AND (so.date_fin IS NULL
                       OR so.date_fin::date >= ?::date
                       OR so.date_fin::date < '1901-01-01')
                  AND COALESCE(se.en_activite, FALSE) = TRUE
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.nom, s.prenom""",
            (int(id_orga), today_iso, today_iso),
        ) or []
    except Exception:
        logger.exception("_salaries_orga id=%s", id_orga)
        return []
    return [
        {"ID": int(r.get("id_salarie") or 0),
         "Nom": (r.get("nom") or "").strip(),
         "Prenom": (r.get("prenom") or "").strip()}
        for r in rows
    ]


def _iter_salaries_from_orga(id_orga: int, jour: date | None):
    """Genere (id_sal, nom, prenom, type_prod) unique pour tout l'arbre."""
    seen: set[int] = set()
    for orga in _orga_arbre(id_orga):
        type_prod = orga["TypeProd"]
        for s in _salaries_orga(orga["id"]):
            if s["ID"] in seen:
                continue
            seen.add(s["ID"])
            yield s["ID"], s["Nom"], s["Prenom"], type_prod


def _lib_absence(id_type_absence: int) -> str:
    if not id_type_absence:
        return ""
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT lib_absence FROM rh.pgt_type_absence
                WHERE id_type_absence = ? LIMIT 1""",
            (int(id_type_absence),),
        )
    except Exception:
        return ""
    return (row or {}).get("lib_absence", "").strip() if row else ""


def _type_sortie_courante(id_salarie: int) -> str:
    db = get_pg_connection("ticket_rh")
    try:
        row = db.query_one(
            """SELECT type_sortie
                 FROM ticket_rh.pgt_tk_demande_sortie_rh
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY id_tk_liste DESC
                LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        return ""
    return (row or {}).get("type_sortie", "").strip() if row else ""


def _recup_dec_pres_one(id_salarie: int, jour: date, type_prod: int,
                          is_scool: bool = False) -> dict:
    """Portage recupDecPres pour UN salarie. Retourne un dict STDecPres.

    Si aucun declaratif n'existe pour ce jour, en cree un par defaut :
    - Si le jour = date d'entree du salarie -> absent, motif 6 (Formation)
    - Sinon si absence -> absent avec motif = type_absence
    - Sinon -> present
    """
    dbrh = get_pg_connection("rh")

    # Recup date d'entree
    date_deb_entree: date | None = None
    try:
        row = dbrh.query_one(
            """SELECT date_debut FROM rh.pgt_salarie_embauche
                WHERE id_salarie = ? LIMIT 1""",
            (int(id_salarie),),
        )
        if row and row.get("date_debut"):
            v = row.get("date_debut")
            date_deb_entree = v if isinstance(v, date) else _parse_jour(v)
    except Exception:
        logger.exception("_recup_dec_pres_one: entree id=%s", id_salarie)

    # Cherche declaratif existant
    try:
        existing = dbrh.query_one(
            """SELECT id_declaratif_presence, is_scool, presence,
                      motifabsence, periode_absence,
                      emargement_matin, emargement_aprem
                 FROM rh.pgt_salarie_decl_presence
                WHERE id_salarie = ?
                  AND date::date = ?::date
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_salarie), jour.isoformat()),
        )
    except Exception:
        logger.exception("_recup_dec_pres_one: cherche id=%s", id_salarie)
        existing = None

    if existing:
        id_dec = int(existing.get("id_declaratif_presence") or 0)
        is_pres = bool(existing.get("presence"))
        motif = _to_int(existing.get("motifabsence"))
        periode = _to_int(existing.get("periode_absence"))

        # Regle WinDev : si dateEntree == jour et motif != 6 -> force Formation
        if date_deb_entree and date_deb_entree == jour and motif != 6:
            is_pres = False
            motif = 6
            periode = 3
            try:
                dbrh.query(
                    """UPDATE rh.pgt_salarie_decl_presence
                          SET presence = FALSE, motifabsence = 6,
                              periode_absence = 3, modif_date = ?,
                              modif_elem = 'modif'
                        WHERE id_declaratif_presence = ?""",
                    (datetime.now(), id_dec),
                )
            except Exception:
                logger.exception("_recup_dec_pres_one: force formation id=%s", id_dec)
            lib_motif = ""
            type_sortie = ""
        else:
            lib_motif = _lib_absence(motif) if not is_pres else ""
            type_sortie = ""
            if not is_pres and motif == 9:
                type_sortie = _type_sortie_courante(id_salarie)
            elif is_pres:
                abs_row = _test_vendeur_absent(id_salarie, jour)
                if abs_row and abs_row.get("id_absence"):
                    # Absence non declaree -> ajuste
                    is_pres = False
                    motif = 0
                    periode = 3

        if not is_pres and motif == 0:
            motif = 1

        return {
            "IDSalarie": int(id_salarie),
            "DateDec": jour.isoformat(),
            "typeProd": int(type_prod or 0),
            "IdDeclaratif": str(id_dec),
            "IsScool": bool(existing.get("is_scool")),
            "emargementMatin": 1 if existing.get("emargement_matin") else 0,
            "emargementAprem": 1 if existing.get("emargement_aprem") else 0,
            "ISPresent": is_pres,
            "MotifAbsence": motif,
            "LibMotifAbsence": lib_motif,
            "PeriodeAbsence": periode,
            "TypeSortie": type_sortie,
        }

    # Pas de declaratif -> creation par defaut
    is_pres_new = True
    motif_new = 0
    periode_new = 0
    type_sortie_new = ""

    if date_deb_entree and date_deb_entree == date.today():
        # 1er jour -> Formation
        is_pres_new = False
        motif_new = 6
        periode_new = 3
    else:
        abs_row = _test_vendeur_absent(id_salarie, jour)
        if abs_row and abs_row.get("id_absence"):
            is_pres_new = False
            motif_new = _to_int(abs_row.get("id_type_absence"))
            periode_new = 3

    now = datetime.now()
    id_new = _new_id_wd()
    try:
        dbrh.query(
            """INSERT INTO rh.pgt_salarie_decl_presence
                 (id_declaratif_presence_auto, id_declaratif_presence,
                  id_salarie, date, presence, motifabsence, periode_absence,
                  is_scool, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, int(id_salarie), jour, is_pres_new,
             motif_new, periode_new, bool(is_scool), now, int(id_salarie)),
        )
    except Exception:
        logger.exception("_recup_dec_pres_one: insert id=%s", id_salarie)

    return {
        "IDSalarie": int(id_salarie),
        "DateDec": jour.isoformat(),
        "typeProd": int(type_prod or 0),
        "IdDeclaratif": str(id_new),
        "IsScool": bool(is_scool),
        "emargementMatin": 0,
        "emargementAprem": 0,
        "ISPresent": is_pres_new,
        "MotifAbsence": motif_new if not is_pres_new else 0,
        "LibMotifAbsence": _lib_absence(motif_new) if not is_pres_new else "",
        "PeriodeAbsence": periode_new,
        "TypeSortie": type_sortie_new,
    }


def _recup_dec_pres(salaries: Iterable[dict]) -> list[dict]:
    """Portage recupDecPres."""
    result = []
    for s in salaries:
        id_sal = _to_int(s.get("Idsalarie") or s.get("IDSalarie") or s.get("id_salarie"))
        jour = _parse_jour(s.get("DateDec") or s.get("date_dec") or s.get("Date"))
        type_prod = _to_int(s.get("typeProd") or s.get("TypeProd"))
        is_scool = bool(s.get("IsScool") or s.get("is_scool"))
        if not id_sal or not jour:
            continue
        result.append(_recup_dec_pres_one(id_sal, jour, type_prod, is_scool))
    return result


def _recup_dec_prod(salaries: Iterable[dict]) -> list[dict]:
    """Portage recupDecProd. Retourne les lignes de production
    declarees par salarie/jour, jointes avec pgt_type_prod_dec pour
    le libelle."""
    dbrh = get_pg_connection("rh")
    result = []
    for s in salaries:
        id_sal = _to_int(s.get("Idsalarie") or s.get("IDSalarie") or s.get("id_salarie"))
        jour = _parse_jour(s.get("DateDec") or s.get("date_dec") or s.get("Date"))
        if not id_sal or not jour:
            continue
        try:
            rows = dbrh.query(
                """SELECT p.id_declaratif_production,
                          p.id_type_prod_dec, p.nb_brut, p.nb_adf,
                          t.lib_type_prod_dec
                     FROM rh.pgt_salarie_decl_production p
                     LEFT JOIN adv.pgt_type_prod_dec t
                            ON t.id_type_prod_dec = p.id_type_prod_dec
                    WHERE p.id_salarie = ?
                      AND p.date::date = ?::date
                      AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
                    ORDER BY t.lib_type_prod_dec""",
                (int(id_sal), jour.isoformat()),
            ) or []
        except Exception:
            logger.exception("_recup_dec_prod id_sal=%s", id_sal)
            continue
        for r in rows:
            result.append({
                "Idsalarie": int(id_sal),
                "DateDec": jour.isoformat(),
                "IdDeclaratif": str(int(r.get("id_declaratif_production") or 0)),
                "IdTypeDec": str(int(r.get("id_type_prod_dec") or 0)),
                "LibProd": (r.get("lib_type_prod_dec") or "").strip(),
                "nBrut": _to_int(r.get("nb_brut")),
                "nAdf": _to_int(r.get("nb_adf")),
            })
    return result


# ---------------------------------------------------------------------------
#  Endpoint : Prod/Type
# ---------------------------------------------------------------------------

@router.post("/Declaratif/Prod/Type")
def prod_type(payload: dict = Body(...)):
    """Portage DecProd_ListeType. Retourne les types de production
    declarables pour l'organigramme (filtre par prefixes bdd des
    partenaires lies au type_produit de chaque orga)."""
    id_orga = _to_int(payload.get("idOrga") or payload.get("IdOrga"))
    if not id_orga:
        return []

    orgas = _orga_arbre(id_orga)
    type_prod_ids = {o["TypeProd"] for o in orgas if o.get("TypeProd")}

    db = get_pg_connection("rh")

    # Prefixes autorises (partenaires actifs lies aux type_produit)
    prefixes: set[str] = set()
    if type_prod_ids:
        placeholders = ",".join("?" for _ in type_prod_ids)
        try:
            rows = db.query(
                f"""SELECT DISTINCT p.prefixe_bdd
                     FROM rh.pgt_type_produit_partenaire tp
                     JOIN adv.pgt_partenaire p
                            ON p.id_partenaire = tp.id_partenaire
                    WHERE tp.id_type_produit IN ({placeholders})
                      AND (tp.modif_elem IS NULL OR tp.modif_elem NOT LIKE '%suppr%')""",
                tuple(int(x) for x in type_prod_ids),
            ) or []
            prefixes = {(r.get("prefixe_bdd") or "").upper().strip()
                        for r in rows if r.get("prefixe_bdd")}
        except Exception:
            logger.exception("prod_type: prefixes id_orga=%s", id_orga)

    # Types actifs
    try:
        types = db.query(
            """SELECT id_type_prod_dec, lib_type_prod_dec,
                      prefixe_bdd, a_comptabilise_dans_tot_bs
                 FROM adv.pgt_type_prod_dec
                WHERE COALESCE(prod_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY lib_type_prod_dec""",
        ) or []
    except Exception:
        logger.exception("prod_type: types")
        return []

    result = []
    for t in types:
        prefix = (t.get("prefixe_bdd") or "").upper().strip()
        if prefix != "RH" and prefix not in prefixes:
            continue
        id_dec = _to_int(t.get("id_type_prod_dec"))
        famille = prefix
        if id_dec == 18:  # Migration Fibre : Windev force FIBRE
            famille = "FIBRE"
        result.append({
            "FamilleProd": famille,
            "LibProd": (t.get("lib_type_prod_dec") or "").strip(),
            "IdTypeDec": str(id_dec) if id_dec else "0",
            "AComptabiliseDansTotBS": bool(t.get("a_comptabilise_dans_tot_bs")),
        })
    return result


# ---------------------------------------------------------------------------
#  Endpoints : Pres/ListeByOrga et Prod/ListeByOrga
# ---------------------------------------------------------------------------

def _salaries_from_orga_payload(payload: dict) -> tuple[list[dict], date | None]:
    """Construit la liste STDecSalarie a partir d'un payload
    {idOrga, dateDec}."""
    id_orga = _to_int(payload.get("idOrga") or payload.get("IdOrga"))
    jour = _parse_jour(payload.get("dateDec") or payload.get("DateDec")
                        or payload.get("Date"))
    if not id_orga or not jour:
        return [], jour
    salaries = []
    for id_sal, _nom, _prenom, type_prod in _iter_salaries_from_orga(id_orga, jour):
        salaries.append({
            "Idsalarie": id_sal,
            "DateDec": jour.isoformat(),
            "typeProd": type_prod,
        })
    return salaries, jour


@router.post("/Declaratif/Pres/ListeByOrga")
def pres_liste_by_orga(payload: dict = Body(...)):
    """Portage DecPres_Organigramme."""
    salaries, _jour = _salaries_from_orga_payload(payload)
    return _recup_dec_pres(salaries)


@router.post("/Declaratif/Prod/ListeByOrga")
def prod_liste_by_orga(payload: dict = Body(...)):
    """Portage DecProd_Organigramme."""
    salaries, _jour = _salaries_from_orga_payload(payload)
    return _recup_dec_prod(salaries)


# ---------------------------------------------------------------------------
#  Endpoints : Pres/ListeBySalarie et Prod/ListeBySalarie
# ---------------------------------------------------------------------------

def _payload_as_salarie_list(payload: Any) -> list[dict]:
    """Payload peut etre un tableau [STDecSalarie] direct ou un objet
    contenant une cle 'tabMesSalariés' ou 'salaries'."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("tabMesSalariés", "tabMesSalaries", "salaries", "salariés"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
        return [payload] if payload.get("Idsalarie") or payload.get("IDSalarie") else []
    return []


@router.post("/Declaratif/Pres/ListeBySalarie")
def pres_liste_by_salarie(payload: Any = Body(...)):
    """Portage DecPres_DecBySalariés."""
    return _recup_dec_pres(_payload_as_salarie_list(payload))


@router.post("/Declaratif/Prod/ListeBySalarie")
def prod_liste_by_salarie(payload: Any = Body(...)):
    """Portage DecProd_DecBySalariés."""
    return _recup_dec_prod(_payload_as_salarie_list(payload))


# ---------------------------------------------------------------------------
#  Endpoints : Pres/Save et Prod/Save
# ---------------------------------------------------------------------------

@router.post("/Declaratif/Pres/Save")
def pres_save(payload: dict = Body(...),
              id_op: int = Depends(mobile_auth)):
    """Portage DecPres_Save.

    Payload STDecPres :
      { IDSalarie, DateDec, IsScool, ISPresent, MotifAbsence,
        PeriodeAbsence, emargementMatin (base64), emargementAprem (base64) }
    Retour STRéponseTK : { nIdDemande }
    """
    id_sal = _to_int(payload.get("IDSalarie") or payload.get("Idsalarie"))
    jour = _parse_jour(payload.get("DateDec") or payload.get("Date"))
    is_scool = bool(payload.get("IsScool"))
    is_pres = bool(payload.get("ISPresent"))
    motif = _to_int(payload.get("MotifAbsence"))
    periode = _to_int(payload.get("PeriodeAbsence"))
    em_m_b64 = payload.get("emargementMatin") or ""
    em_a_b64 = payload.get("emargementAprem") or ""
    if not id_sal or not jour:
        return {"nIdDemande": "0"}

    em_m = base64.b64decode(em_m_b64) if em_m_b64 else None
    em_a = base64.b64decode(em_a_b64) if em_a_b64 else None

    db = get_pg_connection("rh")
    now = datetime.now()
    try:
        existing = db.query_one(
            """SELECT id_declaratif_presence FROM rh.pgt_salarie_decl_presence
                WHERE id_salarie = ? AND date::date = ?::date
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_sal), jour.isoformat()),
        )
    except Exception:
        logger.exception("pres_save: cherche id=%s", id_sal)
        return {"nIdDemande": "0"}

    import psycopg2

    if not existing:
        id_new = _new_id_wd()
        try:
            db.query(
                """INSERT INTO rh.pgt_salarie_decl_presence
                     (id_declaratif_presence_auto, id_declaratif_presence,
                      id_salarie, date, presence, motifabsence,
                      periode_absence, is_scool,
                      emargement_matin, emargement_aprem,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_new, id_new, int(id_sal), jour, is_pres, motif, periode,
                 is_scool,
                 psycopg2.Binary(em_m) if em_m else None,
                 psycopg2.Binary(em_a) if em_a else None,
                 now, id_op),
            )
            return {"nIdDemande": str(id_new)}
        except Exception as e:
            logger.exception("pres_save: insert")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    id_dec = int(existing.get("id_declaratif_presence") or 0)
    try:
        db.query(
            """UPDATE rh.pgt_salarie_decl_presence
                  SET presence = ?, is_scool = ?, motifabsence = ?,
                      periode_absence = ?, modif_op = ?, modif_date = ?,
                      modif_elem = 'modif'
                WHERE id_declaratif_presence = ?""",
            (is_pres, is_scool, motif, periode, id_op, now, id_dec),
        )
        if is_scool and (em_m or em_a):
            fields = []
            params: list[Any] = []
            if em_m:
                fields.append("emargement_matin = ?")
                params.append(psycopg2.Binary(em_m))
            if em_a:
                fields.append("emargement_aprem = ?")
                params.append(psycopg2.Binary(em_a))
            params.append(id_dec)
            db.query(
                f"""UPDATE rh.pgt_salarie_decl_presence
                      SET {', '.join(fields)}
                    WHERE id_declaratif_presence = ?""",
                tuple(params),
            )
        return {"nIdDemande": str(id_dec)}
    except Exception as e:
        logger.exception("pres_save: update id=%s", id_dec)
        return {"nIdDemande": "0", "sInfoData": str(e)}


@router.post("/Declaratif/Prod/Save")
def prod_save(payload: Any = Body(...),
              id_op: int = Depends(mobile_auth)):
    """Portage DecProd_Save.

    Payload : {isScool, IdSalarie, tabMesDecProd: [STDecProd]}
    ou directement un tableau [STDecProd].
    Retour STRéponseTK : { nIdDemande = dernier id upsert }
    """
    if isinstance(payload, list):
        lst = payload
        is_scool = False
        id_sal = 0
    else:
        is_scool = bool(payload.get("isScool"))
        id_sal = _to_int(payload.get("Idsalarié") or payload.get("IdSalarie")
                          or payload.get("IDSalarie") or id_op)
        lst = payload.get("tabMesDecProd") or payload.get("declProd") or []

    db = get_pg_connection("rh")
    now = datetime.now()
    last_id = 0

    for item in lst:
        id_target_sal = _to_int(item.get("Idsalarie") or item.get("IDSalarie") or id_sal)
        jour = _parse_jour(item.get("DateDec") or item.get("Date"))
        id_type = _to_int(item.get("IdTypeDec"))
        nb_brut = _to_int(item.get("nBrut") or item.get("nbBrut"))
        nb_adf = _to_int(item.get("nAdf") or item.get("nbADF"))
        if not id_target_sal or not jour or not id_type:
            continue
        try:
            row = db.query_one(
                """SELECT id_declaratif_production
                     FROM rh.pgt_salarie_decl_production
                    WHERE id_salarie = ?
                      AND date::date = ?::date
                      AND id_type_prod_dec = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                    LIMIT 1""",
                (int(id_target_sal), jour.isoformat(), int(id_type)),
            )
        except Exception:
            logger.exception("prod_save: cherche")
            continue

        if not row:
            if nb_brut <= 0:
                continue  # WinDev : nBrut<=0 sans existant -> skip
            id_new = _new_id_wd()
            try:
                db.query(
                    """INSERT INTO rh.pgt_salarie_decl_production
                         (id_declaratif_production_auto, id_declaratif_production,
                          id_salarie, date, id_type_prod_dec,
                          nb_brut, nb_adf, is_scool,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (id_new, id_new, int(id_target_sal), jour, int(id_type),
                     int(nb_brut), int(nb_adf), bool(is_scool), now, id_op),
                )
                last_id = id_new
            except Exception:
                logger.exception("prod_save: insert")
        else:
            id_dec = int(row.get("id_declaratif_production") or 0)
            try:
                db.query(
                    """UPDATE rh.pgt_salarie_decl_production
                          SET nb_brut = ?, nb_adf = ?, is_scool = ?,
                              modif_date = ?, modif_op = ?, modif_elem = 'modif'
                        WHERE id_declaratif_production = ?""",
                    (int(nb_brut), int(nb_adf), bool(is_scool), now, id_op, id_dec),
                )
                last_id = id_dec
            except Exception:
                logger.exception("prod_save: update id=%s", id_dec)

    return {"nIdDemande": str(last_id) if last_id else "0"}


# ---------------------------------------------------------------------------
#  Endpoint : Equipe (rapport texte)
# ---------------------------------------------------------------------------

@router.post("/Declaratif/Equipe")
def equipe(payload: dict = Body(...)):
    """Portage Dec_Equipe. Retourne un rapport texte concatene du
    declaratif Presence + Production pour toute l'equipe d'un orga
    a une date donnee. Le WinDev retourne ChaîneVersUTF8() ; ici on
    renvoie une string JSON classique (FastAPI encode UTF-8 par defaut).
    """
    id_orga = _to_int(payload.get("idOrga") or payload.get("IdOrga"))
    jour = _parse_jour(payload.get("dateDec") or payload.get("DateDec"))
    if not id_orga or not jour:
        return ""

    dbrh = get_pg_connection("rh")
    orgas = _orga_arbre(id_orga)

    lines: list[str] = []
    for orga in orgas:
        lines.append(orga["Lib"])
        lines.append("")
        salaries = _salaries_orga(orga["id"])
        type_prod = orga.get("TypeProd") or 0
        for s in salaries:
            id_sal = s["ID"]
            dec = _recup_dec_pres_one(id_sal, jour, type_prod)
            if dec["ISPresent"]:
                etat = "Présent"
            else:
                motif = dec.get("MotifAbsence") or 0
                if motif == 9:
                    etat = "Sortant"
                elif motif == 6:
                    etat = "Formation"
                else:
                    etat = "Absent"

            ligne = f"{s['Nom']} {_capitalise(s['Prenom'])}, {etat}"

            # Ajoute la prod du jour
            try:
                prods = dbrh.query(
                    """SELECT p.nb_brut, t.lib_type_prod_dec
                         FROM rh.pgt_salarie_decl_production p
                         LEFT JOIN adv.pgt_type_prod_dec t
                                ON t.id_type_prod_dec = p.id_type_prod_dec
                        WHERE p.id_salarie = ?
                          AND p.date::date = ?::date
                          AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
                          AND p.nb_brut > 0""",
                    (int(id_sal), jour.isoformat()),
                ) or []
            except Exception:
                prods = []
            if prods:
                ligne += " => "
                for pr in prods:
                    ligne += (f"{pr.get('lib_type_prod_dec') or ''} : "
                              f"{pr.get('nb_brut') or 0}, ")

            lines.append(ligne)
        lines.append("-------------")

    return "\n".join(lines)
