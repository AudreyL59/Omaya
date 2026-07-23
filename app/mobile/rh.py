"""Endpoints mobile RH (WebRest_Omayapp/RH/*).

Portage iso-URL des 16 WS RH mobile WinDev :

  ADF (auto-diagnostic formation) :
    - ADF/ListeType         : items d'evaluation
    - ADF/Save              : create/update d'un ADF (+ items)

  Cooptation :
    - AjoutCooptation       : ajout d'une cooptation dans cvtheque
    - ListeCooptation       : liste des coopts d'un cooptateur

  Photo :
    - ModifPhoto            : update photo salarie (base64)

  ProgEvo (programme d'evolution) :
    - ProgEvo/ListeBilan    : bilans d'un salarie
    - ProgEvo/ListeObjectifs: objectifs disponibles
    - ProgEvo/ListeTheme    : themes + nb objectifs par theme
    - ProgEvo/Save          : create/update d'un bilan + objectifs
    - ProgEvo/Validation    : cloture d'un bilan (TODO: FTP PDF)

  Rdv Recrutement :
    - RdvREC/ListeRDV       : RDV d'un recruteur pour un jour
    - RdvREC/StatuerRDV     : change le statut d'un RDV (+ CvSuivi)
    - StatutsRDV            : liste des categories de RDV

  RecupSalarie :
    - RecupSalarie/Info     : ST_SALARIE complet
    - RecupSalarie/Orga     : salaries d'un orga
    - RecupSalarie/RespEquipe: resp d'equipe actifs de l'orga

TODO (helpers WinDev non portes V1) :
  - ADF_ImprimePDF (WeasyPrint deja dispo, a brancher session dediee)
  - Animation_OrgaScore / envoiSMS / envoiMail (integration Perf-Exo)
  - FTP vers OVH (contexte serveur : rester en local + laisser sync
    faire le job)
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _new_id_wd, _parse_dt, _parse_jour, _to_int
from app.mobile.auth import _capitalise, _info_salarie_complet
from app.mobile.declaratif import _salaries_orga
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-rh"],
                    dependencies=[Depends(mobile_auth)])


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _format_num_tel(v: str) -> str:
    """FormateNumTel WinDev minimaliste : garde les chiffres."""
    return "".join(c for c in (v or "") if c.isdigit())


# ===========================================================================
#  ADF
# ===========================================================================

@router.post("/RH/ADF/ListeType")
def adf_liste_type(_payload: Any = Body(default=None)):
    """Portage ADF_ListeType. Types d'evaluation actifs."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_type_adf_item, lib_item
                 FROM rh.pgt_type_adf_item
                WHERE COALESCE(is_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY ordre_affichage ASC NULLS LAST""",
        ) or []
    except Exception:
        logger.exception("adf_liste_type")
        return []
    return [
        {"Id": str(int(r.get("id_type_adf_item") or 0)),
         "Lib": (r.get("lib_item") or "").strip()}
        for r in rows
    ]


@router.post("/RH/ADF/Save")
def adf_save(payload: dict = Body(...),
             id_auth: int = Depends(mobile_auth)):
    """Portage ADF_Enr. Create/update d'un ADF + items d'evaluation.

    Payload ST_ADF : { idAdf, idSalarie, Date, Horaires, idManager,
                        IDAgence, NBCttVendeur, NBCttManager,
                        Observations, Axe1, Axe2, mesItems: [{Item:{Id}, Note}] }
    """
    id_adf = _to_int(payload.get("idAdf"))
    id_sal = _to_int(payload.get("idSalarie"))
    id_manager = _to_int(payload.get("idManager") or id_auth)
    id_agence = _to_int(payload.get("IDAgence"))
    jour = _parse_jour(payload.get("Date"))
    horaires = payload.get("Horaires") or ""
    nb_ctt_v = _to_int(payload.get("NBCttVendeur"))
    nb_ctt_m = _to_int(payload.get("NBCttManager"))
    obs = payload.get("Observations") or ""
    axe1 = payload.get("Axe1") or ""
    axe2 = payload.get("Axe2") or ""
    items = payload.get("mesItems") or []

    if not id_sal or not jour:
        return {"nIdDemande": "0"}

    db = get_pg_connection("rh")
    now = datetime.now()

    if not id_adf:
        # Creation
        id_adf = _new_id_wd()
        try:
            db.query(
                """INSERT INTO rh.pgt_salarie_adf
                     (id_salarie_adf_auto, id_salarie_adf, id_salarie, date,
                      horaires, id_formateur, id_agence, nb_ctt_vendeur,
                      nb_ctt_formateur, observations, axe_travail1,
                      axe_travail2, modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_adf, id_adf, id_sal, jour, horaires, id_manager,
                 id_agence, nb_ctt_v, nb_ctt_m, obs, axe1, axe2, now, id_manager),
            )
            for it in items:
                item_obj = it.get("Item") or {}
                id_type = _to_int(item_obj.get("Id"))
                note = _to_int(it.get("Note"))
                if not id_type:
                    continue
                id_item = _new_id_wd()
                db.query(
                    """INSERT INTO rh.pgt_salarie_adf_item
                         (id_salarie_adf_item, id_salarie_adf,
                          id_type_adf_item, note, modif_date, modif_op,
                          modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, 'new')""",
                    (id_item, id_adf, id_type, note, now, id_manager),
                )
        except Exception as e:
            logger.exception("adf_save insert")
            return {"nIdDemande": "0", "sInfoData": str(e)}
    else:
        # Update
        try:
            db.query(
                """UPDATE rh.pgt_salarie_adf
                      SET nb_ctt_vendeur = ?, nb_ctt_formateur = ?,
                          observations = ?, axe_travail1 = ?,
                          axe_travail2 = ?, modif_date = ?, modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_salarie_adf = ?""",
                (nb_ctt_v, nb_ctt_m, obs, axe1, axe2, now, id_manager, id_adf),
            )
        except Exception as e:
            logger.exception("adf_save update id=%s", id_adf)
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # TODO V2 : ADF_ImprimePDF + FTP OVH / fDeplace (a porter en
    # session dediee - genereation via WeasyPrint + upload).
    return {"nIdDemande": str(id_adf)}


# ===========================================================================
#  Cooptation
# ===========================================================================

@router.post("/RH/AjoutCooptation")
def ajout_cooptation(payload: dict = Body(...),
                      id_auth: int = Depends(mobile_auth)):
    """Portage AjoutCoopt. Insert dans cvtheque + cvsuivi.
    Verif anti-doublon : meme GSM dans les 31 derniers jours.

    Payload STCooptation : { Origine, GSM, IDCommunes, NOM, PRENOM,
                              DateNaissance, IDcvposte, IDCOOPTEUR,
                              OBSERV, IdSte, OPSAISIE }

    Note V1 : SMS/mail bonus (Animation Perf-Exo, 1000EC coopt gagnante)
    NON portes ; a brancher en session dediee.
    """
    gsm = _format_num_tel(payload.get("GSM") or "")
    if not gsm:
        return {"nIdDemande": "0", "sInfoData": "GSM manquant"}

    db = get_pg_connection("recrutement")
    now = datetime.now()

    # 1. Verif anti-doublon 31 jours
    try:
        row = db.query_one(
            """SELECT id_cvtheque, date_saisie
                 FROM recrutement.pgt_cvtheque
                WHERE gsm LIKE ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY date_saisie DESC NULLS LAST
                LIMIT 1""",
            (f"%{gsm}",),
        )
    except Exception:
        logger.exception("ajout_cooptation verif")
        return {"nIdDemande": "0"}

    if row:
        ds = row.get("date_saisie")
        try:
            if isinstance(ds, datetime):
                delta = (date.today() - ds.date()).days
            elif isinstance(ds, date):
                delta = (date.today() - ds).days
            else:
                delta = (date.today() - date.fromisoformat(str(ds)[:10])).days
        except Exception:
            delta = 999
        if delta <= 31:
            return {"nIdDemande": "0",
                    "sInfoData": "Saisie Impossible : Cette cooptation a déjà été saisie il y a moins d'un mois."}

    op_saisie = _to_int(payload.get("OPSAISIE") or id_auth)
    id_new = _new_id_wd()
    try:
        db.query(
            """INSERT INTO recrutement.pgt_cvtheque
                 (id_cvtheque_auto, id_cvtheque, origine, gsm,
                  id_communes_france, nom, prenom, date_naissance,
                  id_cvsource, id_cvposte, id_elem_source, observ,
                  date_saisie, id_ste, ope_saisie, mots_cles,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, '',
                       ?, ?, 'new')""",
            (id_new, id_new,
             _to_int(payload.get("Origine")),
             gsm,
             _to_int(payload.get("IDCommunes")),
             payload.get("NOM") or "",
             payload.get("PRENOM") or "",
             _parse_jour(payload.get("DateNaissance")),
             _to_int(payload.get("IDcvposte")),
             _to_int(payload.get("IDCOOPTEUR")),
             payload.get("OBSERV") or "",
             now,
             _to_int(payload.get("IdSte")),
             op_saisie, now, op_saisie),
        )
        # CvSuivi
        id_suivi = _new_id_wd()
        db.query(
            """INSERT INTO recrutement.pgt_cvsuivi
                 (id_cv_suivi, id_cvtheque, op_crea, datecrea,
                  id_cv_statut, type_elem, id_elem, observation,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, 1, '', 0, '', ?, ?, 'new')""",
            (id_suivi, id_new, op_saisie, now, now, op_saisie),
        )
    except Exception as e:
        logger.exception("ajout_cooptation insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}

    return {"nIdDemande": str(id_new)}


@router.post("/RH/ListeCooptation")
def liste_cooptation(payload: dict = Body(...),
                      id_auth: int = Depends(mobile_auth)):
    """Portage ListeCooptVendeur. Coopts d'un cooptateur.
    Payload : { idCial } (fallback = user auth).
    """
    id_cial = _to_int(payload.get("idCial") or id_auth)
    if not id_cial:
        return []
    db = get_pg_connection("recrutement")
    try:
        rows = db.query(
            """SELECT nom, prenom, date_saisie
                 FROM recrutement.pgt_cvtheque
                WHERE id_elem_source = ?
                  AND id_cvsource = 1
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY date_saisie DESC NULLS LAST""",
            (id_cial,),
        ) or []
    except Exception:
        logger.exception("liste_cooptation id=%s", id_cial)
        return []
    return [
        {"NOM": (r.get("nom") or "").strip(),
         "PRENOM": (r.get("prenom") or "").strip(),
         "DateSAISIE": _iso_dt(r.get("date_saisie"))}
        for r in rows
    ]


# ===========================================================================
#  ModifPhoto
# ===========================================================================

@router.post("/RH/ModifPhoto")
def modif_photo(payload: dict = Body(...)):
    """Portage Omayapp_ModifPhoto. Update photo salarie.
    Payload ST_PHOTOSALARIE : { ID, Photo (base64) }
    """
    id_sal = _to_int(payload.get("ID") or payload.get("IDSalarie"))
    photo_b64 = payload.get("Photo") or ""
    if not id_sal or not photo_b64:
        return {"nIdDemande": "0"}

    try:
        photo_bytes = base64.b64decode(photo_b64)
    except Exception:
        return {"nIdDemande": "0", "sInfoData": "Base64 invalide"}

    import psycopg2
    db = get_pg_connection("rh")
    now = datetime.now()
    try:
        db.query(
            """UPDATE rh.pgt_salarie
                  SET photo = ?, modif_op = ?, modif_date = ?,
                      modif_elem = 'modif'
                WHERE id_salarie = ?""",
            (psycopg2.Binary(photo_bytes), id_sal, now, id_sal),
        )
        return {"nIdDemande": str(id_sal)}
    except Exception as e:
        logger.exception("modif_photo id=%s", id_sal)
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  ProgEvo (programme d'evolution)
# ===========================================================================

@router.post("/RH/ProgEvo/ListeTheme")
def progevo_liste_theme(_payload: Any = Body(default=None)):
    """Portage ProgEvo_ListeTheme."""
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT type_categorie, COUNT(*) AS nb
                 FROM divers.pgt_prog_evo_objectifs
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                GROUP BY type_categorie
                ORDER BY type_categorie""",
        ) or []
    except Exception:
        logger.exception("progevo_liste_theme")
        return []
    return [
        {"libTheme": (r.get("type_categorie") or "").strip(),
         "nbObj": _to_int(r.get("nb"))}
        for r in rows
    ]


@router.post("/RH/ProgEvo/ListeObjectifs")
def progevo_liste_objectifs(_payload: Any = Body(default=None)):
    """Portage ProgEvo_ListeObjectif."""
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT id_prog_evo_objectifs, type_categorie, lib_objectif,
                      nb_bouton, champ_libre, lib_bouton
                 FROM divers.pgt_prog_evo_objectifs
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY type_categorie ASC, lib_bouton ASC, lib_objectif ASC""",
        ) or []
    except Exception:
        logger.exception("progevo_liste_objectifs")
        return []
    result = []
    for r in rows:
        libs_str = r.get("lib_bouton") or ""
        libs = [x.strip() for x in libs_str.split(";") if x.strip()]
        result.append({
            "theme": {"libTheme": (r.get("type_categorie") or "").strip()},
            "idObjectif": str(int(r.get("id_prog_evo_objectifs") or 0)),
            "libObj": (r.get("lib_objectif") or "").strip(),
            "nbBouton": _to_int(r.get("nb_bouton")),
            "ChampLibre": bool(r.get("champ_libre")),
            "LibBtn": libs,
        })
    return result


def _progevo_contenu_liste(id_vend: int) -> list[dict]:
    """Portage ProgEvo_ContenuListe (proc globale). Retourne les bilans
    d'un salarie avec les objectifs imbriques."""
    if not id_vend:
        return []
    dbrh = get_pg_connection("rh")
    dbdiv = get_pg_connection("divers")
    try:
        bilans = dbrh.query(
            """SELECT id_salarie_prog_evo, id_salarie, date, id_da,
                      id_agence, niveau, avis, axe_travail1,
                      axe_travail2, cloture
                 FROM rh.pgt_salarie_progevo
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY date DESC NULLS LAST""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("_progevo_contenu_liste id=%s", id_vend)
        return []

    # Prefetch tous les objectifs de reference
    obj_ref_map: dict[int, dict] = {}
    try:
        objs = dbdiv.query(
            """SELECT id_prog_evo_objectifs, type_categorie, lib_objectif,
                      nb_bouton, champ_libre, lib_bouton
                 FROM divers.pgt_prog_evo_objectifs""",
        ) or []
        for o in objs:
            obj_ref_map[int(o.get("id_prog_evo_objectifs") or 0)] = o
    except Exception:
        logger.exception("_progevo_contenu_liste refs")

    result = []
    for b in bilans:
        id_bilan = int(b.get("id_salarie_prog_evo") or 0)
        try:
            objs_bilan = dbrh.query(
                """SELECT id_salarie_prog_evo_item, id_prog_evo_objectifs,
                          champ_libre, note
                     FROM rh.pgt_salarie_progevo_objectif
                    WHERE id_salarie_prog_evo = ?
                      AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
                (id_bilan,),
            ) or []
        except Exception:
            objs_bilan = []
        mes_obj = []
        for ob in objs_bilan:
            ref = obj_ref_map.get(int(ob.get("id_prog_evo_objectifs") or 0), {})
            libs_str = ref.get("lib_bouton") or ""
            libs = [x.strip() for x in libs_str.split(";") if x.strip()]
            mes_obj.append({
                "idObjSalarie": str(int(ob.get("id_salarie_prog_evo_item") or 0)),
                "Obj": {
                    "theme": {"libTheme": (ref.get("type_categorie") or "").strip()},
                    "idObjectif": str(int(ob.get("id_prog_evo_objectifs") or 0)),
                    "libObj": (ref.get("lib_objectif") or "").strip(),
                    "nbBouton": _to_int(ref.get("nb_bouton")),
                    "ChampLibre": bool(ref.get("champ_libre")),
                    "LibBtn": libs,
                },
                "note": _to_int(ob.get("note")),
                "champLibre": ob.get("champ_libre") or "",
            })
        result.append({
            "idBilan": str(id_bilan),
            "IdSalarie": int(b.get("id_salarie") or 0),
            "DateBilan": _iso_dt(b.get("date")),
            "IDDA": str(int(b.get("id_da") or 0)),
            "IdOrga": str(int(b.get("id_agence") or 0)),
            "niveau": _to_int(b.get("niveau")),
            "avis": b.get("avis") or "",
            "axe1": b.get("axe_travail1") or "",
            "axe2": b.get("axe_travail2") or "",
            "clos": bool(b.get("cloture")),
            "mesObj": mes_obj,
        })
    return result


@router.post("/RH/ProgEvo/ListeBilan")
def progevo_liste_bilan(payload: dict = Body(...),
                          id_auth: int = Depends(mobile_auth)):
    """Portage ProgEvo_Liste + ProgEvo_ContenuListe."""
    id_vend = _to_int(payload.get("idVend") or payload.get("IDSalarie")
                       or id_auth)
    return _progevo_contenu_liste(id_vend)


@router.post("/RH/ProgEvo/Save")
def progevo_save(payload: dict = Body(...),
                  id_cial: int = Depends(mobile_auth)):
    """Portage ProgEvo_Enr. Create/update d'un bilan + objectifs."""
    id_bilan = _to_int(payload.get("idBilan"))
    id_sal = _to_int(payload.get("IdSalarie"))
    date_bilan = _parse_jour(payload.get("DateBilan"))
    id_da = _to_int(payload.get("IDDA"))
    id_orga = _to_int(payload.get("IdOrga"))
    niveau = _to_int(payload.get("niveau"))
    avis = payload.get("avis") or ""
    axe1 = payload.get("axe1") or ""
    axe2 = payload.get("axe2") or ""
    mes_obj = payload.get("mesObj") or []

    if not id_sal or not date_bilan:
        return {"idBilan": "0"}

    db = get_pg_connection("rh")
    now = datetime.now()

    if not id_bilan:
        id_bilan = _new_id_wd()
        try:
            db.query(
                """INSERT INTO rh.pgt_salarie_progevo
                     (id_salarie_prog_evo, id_salarie, date, id_da,
                      id_agence, niveau, avis, axe_travail1, axe_travail2,
                      cloture, modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE, ?, ?, 'new')""",
                (id_bilan, id_sal, date_bilan, id_da, id_orga, niveau,
                 avis, axe1, axe2, now, id_cial),
            )
            for ob in mes_obj:
                obj = ob.get("Obj") or {}
                id_ref = _to_int(obj.get("idObjectif"))
                if not id_ref:
                    continue
                id_item = _new_id_wd()
                db.query(
                    """INSERT INTO rh.pgt_salarie_progevo_objectif
                         (id_salarie_prog_evo_item, id_salarie_prog_evo,
                          id_prog_evo_objectifs, champ_libre, note,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'modif')""",
                    (id_item, id_bilan, id_ref,
                     ob.get("champLibre") or "",
                     _to_int(ob.get("note")), now, id_cial),
                )
                ob["idObjSalarie"] = str(id_item)
        except Exception as e:
            logger.exception("progevo_save insert")
            return {"idBilan": "0", "sInfoData": str(e)}
    else:
        try:
            db.query(
                """UPDATE rh.pgt_salarie_progevo
                      SET date = ?, id_da = ?, id_agence = ?, niveau = ?,
                          avis = ?, axe_travail1 = ?, axe_travail2 = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'modif'
                    WHERE id_salarie_prog_evo = ?""",
                (date_bilan, id_da, id_orga, niveau, avis, axe1, axe2,
                 now, id_cial, id_bilan),
            )
            for ob in mes_obj:
                id_item = _to_int(ob.get("idObjSalarie"))
                if not id_item:
                    continue
                db.query(
                    """UPDATE rh.pgt_salarie_progevo_objectif
                          SET champ_libre = ?, note = ?, modif_date = ?,
                              modif_op = ?, modif_elem = 'modif'
                        WHERE id_salarie_prog_evo_item = ?""",
                    (ob.get("champLibre") or "", _to_int(ob.get("note")),
                     now, id_cial, id_item),
                )
        except Exception as e:
            logger.exception("progevo_save update id=%s", id_bilan)
            return {"idBilan": "0", "sInfoData": str(e)}

    # Retourne le payload modifie avec le nouvel idBilan
    payload["idBilan"] = str(id_bilan)
    return payload


@router.post("/RH/ProgEvo/Validation")
def progevo_validation(payload: dict = Body(...),
                        id_cial: int = Depends(mobile_auth)):
    """Portage ProgEvo_Validation. Cloture d'un bilan.

    TODO V2 : generation PDF + upload FTP (non porte V1). Ici on
    marque simplement cloture=TRUE.
    """
    id_bilan = _to_int(payload.get("idBilan"))
    if not id_bilan:
        return {"idBilan": "0", "clos": False}

    db = get_pg_connection("rh")
    now = datetime.now()
    try:
        db.query(
            """UPDATE rh.pgt_salarie_progevo
                  SET cloture = TRUE, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_salarie_prog_evo = ?""",
            (now, id_cial, id_bilan),
        )
    except Exception as e:
        logger.exception("progevo_validation id=%s", id_bilan)
        return {"idBilan": str(id_bilan), "clos": False,
                "sInfoData": str(e)}
    return {"idBilan": str(id_bilan), "clos": True}


# ===========================================================================
#  RdvREC
# ===========================================================================

def _rvb_to_int(r: Any, v: Any, b: Any) -> int:
    """WinDev RVB() = R + V*256 + B*65536."""
    ri, vi, bi = _to_int(r), _to_int(v), _to_int(b)
    return (bi << 16) | (vi << 8) | ri


@router.post("/RH/StatutsRDV")
def statuts_rdv(_payload: Any = Body(default=None)):
    """Portage ListeStatutRdv. Categories de RDV recrutement."""
    db = get_pg_connection("recrutement")
    try:
        rows = db.query(
            """SELECT id_agenda_categorie, lib_categorie, id_cv_statut,
                      couleur_r, couleur_v, couleur_b
                 FROM recrutement.pgt_agenda_categorie
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')""",
        ) or []
    except Exception:
        logger.exception("statuts_rdv")
        return []
    return [
        {"Coul": _rvb_to_int(r.get("couleur_r"), r.get("couleur_v"),
                              r.get("couleur_b")),
         "ID": _to_int(r.get("id_agenda_categorie")),
         "IDStatutCV": str(int(r.get("id_cv_statut") or 0))
                        if r.get("id_cv_statut") else "0",
         "lib": (r.get("lib_categorie") or "").strip()}
        for r in rows
    ]


@router.post("/RH/RdvREC/ListeRDV")
def rdvrec_liste(payload: dict = Body(...)):
    """Portage RdvRec_Liste. RDV recrutement d'un jour.

    Payload : { idRecruteur, Jour } (Jour = YYYYMMDD ou ISO).
    """
    id_rec = _to_int(payload.get("idRecruteur") or payload.get("IDSalarie"))
    jour = _parse_jour(payload.get("Jour"))
    if not id_rec or not jour:
        return []

    db = get_pg_connection("recrutement")
    try:
        rdvs = db.query(
            """SELECT ag.id_agenda_evenement, ag.id_categorie, ag.id_cv_suivi,
                      ag.titre, ag.contenu, ag.date_debut, ag.date_fin,
                      ag.id_cv_lieux, ag.id_prevision_recrut, ag.id_salon_visio,
                      cat.lib_categorie, cat.couleur_r, cat.couleur_v, cat.couleur_b
                 FROM recrutement.pgt_agenda_evenement ag
                 LEFT JOIN recrutement.pgt_agenda_categorie cat
                        ON cat.id_agenda_categorie = ag.id_categorie
                WHERE ag.id_salarie = ?
                  AND ag.date_debut::date = ?::date
                  AND (ag.modif_elem IS NULL OR ag.modif_elem <> 'suppr')
                ORDER BY ag.date_debut ASC""",
            (id_rec, jour.isoformat()),
        ) or []
    except Exception:
        logger.exception("rdvrec_liste id=%s j=%s", id_rec, jour)
        return []

    result = []
    for r in rdvs:
        id_lieu = _to_int(r.get("id_cv_lieux"))
        id_salon = _to_int(r.get("id_salon_visio"))
        id_cvs = _to_int(r.get("id_cv_suivi"))
        info_lieu = ""
        lien_cv = ""

        # InfoLieu depuis cv_lieu_rdv
        if id_lieu:
            try:
                lieu = db.query_one(
                    """SELECT cl.lib_lieu, cl.adresse1, cl.id_communes_france
                         FROM recrutement.pgt_cv_lieu_rdv cl
                        WHERE cl.id_cv_lieu_rdv = ? LIMIT 1""",
                    (id_lieu,),
                )
                if lieu:
                    dbdiv = get_pg_connection("divers")
                    cp = ville = ""
                    if lieu.get("id_communes_france"):
                        c = dbdiv.query_one(
                            """SELECT code_postal, nom_ville
                                 FROM divers.pgt_communes_france
                                WHERE id_communes_france = ? LIMIT 1""",
                            (int(lieu.get("id_communes_france") or 0),),
                        )
                        if c:
                            cp = (c.get("code_postal") or "").strip()
                            ville = (c.get("nom_ville") or "").strip()
                    info_lieu = (f"{(lieu.get('lib_lieu') or '').strip()}\n"
                                 f"{(lieu.get('adresse1') or '').strip()} - "
                                 f"{cp} {ville}")
            except Exception:
                logger.exception("rdvrec_liste lieu %s", id_lieu)

        # InfoLieu depuis salon_visio
        if id_salon:
            try:
                sv = db.query_one(
                    """SELECT sv.lib_salon, sv.lien_salon,
                              sv.id_salon, sv.mpd_salon
                         FROM recrutement.pgt_salon_visio sv
                        WHERE sv.id_salon_visio = ? LIMIT 1""",
                    (id_salon,),
                )
                if sv:
                    info_lieu = (f"{(sv.get('lib_salon') or '').strip()}\n"
                                 f"Lien : {sv.get('lien_salon') or ''}\n"
                                 f"ID : {sv.get('id_salon') or ''}\n"
                                 f"Mdp : {sv.get('mpd_salon') or ''}")
            except Exception:
                logger.exception("rdvrec_liste salon %s", id_salon)

        # LienCV depuis cvtheque via cv_suivi
        if id_cvs:
            try:
                cv = db.query_one(
                    """SELECT cvt.fic_cv
                         FROM recrutement.pgt_cvtheque cvt
                         JOIN recrutement.pgt_cvsuivi cs
                                ON cs.id_cvtheque = cvt.id_cvtheque
                        WHERE cs.id_cv_suivi = ? LIMIT 1""",
                    (id_cvs,),
                )
                if cv:
                    lien_cv = cv.get("fic_cv") or ""
            except Exception:
                logger.exception("rdvrec_liste cv %s", id_cvs)

        result.append({
            "Contenu": r.get("contenu") or "",
            "DateDebut": _iso_dt(r.get("date_debut")),
            "IDAgendaEvenement": str(int(r.get("id_agenda_evenement") or 0)),
            "IDCategorie": _to_int(r.get("id_categorie")),
            "IDCvSuivi": str(id_cvs) if id_cvs else "0",
            "libCategorie": (r.get("lib_categorie") or "").strip(),
            "CoulCategorie": _rvb_to_int(r.get("couleur_r"),
                                          r.get("couleur_v"),
                                          r.get("couleur_b")),
            "IdCvLieux": str(id_lieu) if id_lieu else "0",
            "IDprevisionRecrut": str(int(r.get("id_prevision_recrut") or 0)),
            "IDSalonVisio": str(id_salon) if id_salon else "0",
            "Titre": r.get("titre") or "",
            "InfoLieu": info_lieu,
            "LienCV": lien_cv,
        })
    return result


@router.post("/RH/RdvREC/StatuerRDV")
def rdvrec_statuer(payload: dict = Body(...),
                    id_op: int = Depends(mobile_auth)):
    """Portage RdvRec_Statuer. Change le statut d'un RDV + trace CvSuivi.

    Payload : { idRdv, IdStatut, monRdv: {Contenu} }
    TODO V2 : Animation SMSCOOPTRH (bonus livret + envoi SMS/mail) -
    non porte V1.
    """
    id_rdv = _to_int(payload.get("idRdv") or payload.get("IDAgendaEvenement"))
    id_statut = _to_int(payload.get("IdStatut") or payload.get("IDCategorie"))
    mon_rdv = payload.get("monRdv") or {}
    if not id_rdv or not id_statut:
        return {"nIdDemande": "0"}

    db = get_pg_connection("recrutement")
    dbrh = get_pg_connection("rh")
    now = datetime.now()

    # Recup statut + agenda
    try:
        stat = db.query_one(
            """SELECT lib_categorie, id_cv_statut
                 FROM recrutement.pgt_agenda_categorie
                WHERE id_agenda_categorie = ? LIMIT 1""",
            (id_statut,),
        )
        ag = db.query_one(
            """SELECT id_salarie, contenu, id_cv_suivi
                 FROM recrutement.pgt_agenda_evenement
                WHERE id_agenda_evenement = ? LIMIT 1""",
            (id_rdv,),
        )
    except Exception:
        logger.exception("rdvrec_statuer read")
        return {"nIdDemande": "0"}
    if not stat or not ag:
        return {"nIdDemande": "0"}

    lib_stat = (stat.get("lib_categorie") or "").strip()
    id_sal_rec = _to_int(ag.get("id_salarie"))

    # Info recruteur
    nom = prenom = ""
    try:
        s = dbrh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_sal_rec,),
        )
        if s:
            nom = (s.get("nom") or "").strip()
            prenom = _capitalise((s.get("prenom") or "").strip())
    except Exception:
        pass

    info_log = f"RDV statué en {lib_stat} par {nom} {prenom} (via l'appli Omayapp)"
    contenu_rdv = mon_rdv.get("Contenu") or ""
    if contenu_rdv:
        info_log += f" : {contenu_rdv}"
    new_contenu = ((ag.get("contenu") or "") + "\n"
                   + now.strftime("%d/%m/%Y à %H:%M") + " - " + info_log)

    # CvSuivi si lie
    id_cvs = _to_int(ag.get("id_cv_suivi"))
    if id_cvs:
        try:
            cv = db.query_one(
                """SELECT id_cvtheque FROM recrutement.pgt_cvsuivi
                    WHERE id_cv_suivi = ? LIMIT 1""",
                (id_cvs,),
            )
            if cv:
                id_new_suivi = _new_id_wd()
                db.query(
                    """INSERT INTO recrutement.pgt_cvsuivi
                         (id_cv_suivi, id_cvtheque, datecrea, op_crea,
                          id_cv_statut, type_elem, id_elem, observation,
                          modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, 'RDV', ?, ?, ?, ?, 'new')""",
                    (id_new_suivi, int(cv.get("id_cvtheque") or 0), now,
                     id_sal_rec, _to_int(stat.get("id_cv_statut")),
                     id_rdv, info_log, now, id_sal_rec),
                )
        except Exception:
            logger.exception("rdvrec_statuer cvsuivi")

    # Update agenda
    try:
        db.query(
            """UPDATE recrutement.pgt_agenda_evenement
                  SET id_categorie = ?, contenu = ?, motif_statut = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_agenda_evenement = ?""",
            (id_statut, new_contenu, contenu_rdv, now, id_op, id_rdv),
        )
        return {"nIdDemande": str(id_rdv)}
    except Exception as e:
        logger.exception("rdvrec_statuer update")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  RecupSalarie
# ===========================================================================

@router.post("/RH/RecupSalarie/Info")
def recup_salarie_info(payload: dict = Body(...)):
    """Portage Omayapp_CR_InfoSalarie. ST_SALARIE complet."""
    id_sal = _to_int(payload.get("idSalarie") or payload.get("IDSalarie"))
    if not id_sal:
        return {"ID": 0, "Nom": "BADTOKEN"}
    return _info_salarie_complet(id_sal)


@router.post("/RH/RecupSalarie/Orga")
def recup_salarie_orga(payload: dict = Body(...)):
    """Portage Omayapp_SalarieOrga1 + Info_SalariéOrga.

    Payload : { idOrga } ou monOrga.id
    """
    mon_orga = payload.get("monOrga") or {}
    id_orga = _to_int(payload.get("idOrga")
                       or mon_orga.get("id")
                       or payload.get("ID"))
    if not id_orga:
        return []
    salaries = _salaries_orga(id_orga)
    return [_info_salarie_complet(s["ID"]) for s in salaries if s.get("ID")]


@router.post("/RH/RecupSalarie/RespEquipe")
def recup_salarie_resp_equipe(payload: dict = Body(...)):
    """Portage RecupRespEquipe. Resp d'equipe actifs d'un orga."""
    id_orga = _to_int(payload.get("id_Orga") or payload.get("idOrga")
                       or payload.get("ID"))
    if not id_orga:
        return []
    today_iso = date.today().isoformat()
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT so.id_salarie, s.nom, s.prenom
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
                  AND COALESCE(se.resp_equipe, FALSE) = TRUE
                  AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY se.resp_equipe DESC, se.resp_adjoint DESC,
                          s.nom ASC, s.prenom ASC""",
            (id_orga, today_iso, today_iso),
        ) or []
    except Exception:
        logger.exception("recup_salarie_resp_equipe id=%s", id_orga)
        return []
    return [
        {"ID": int(r.get("id_salarie") or 0),
         "Nom": (r.get("nom") or "").strip(),
         "Prenom": _capitalise((r.get("prenom") or "").strip())}
        for r in rows
    ]
