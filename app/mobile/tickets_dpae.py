"""Endpoints mobile Tickets DPAE + DPAEDistrib (lot 4b).

Lot 4b = 14 endpoints (6 DPAE + 8 DPAEDistrib) extraits de tickets.py
pour lisibilite (le fichier tickets.py depasse deja 1800 lignes).

DPAE (schema ticket_dpae) :
  - Contenu, Save, ListePhoto
  - DocSign/Contenu, DocSign/Enr, DocSign/Liste

DPAEDistrib (schema ticket_bo) :
  - Contenu, Save, Verif, ListePart, ListePhoto
  - DocSign/Contenu, DocSign/Enr, DocSign/Liste

TODO V2 (non porte) :
  - iImprimeEtat / DocRHGenerationPDF (generation PDF via WeasyPrint)
  - FTP OVH upload -> a brancher en session dediee
  - Envoi mail RH pour DPAE cree apres midi
  - Fusion PDF Mutuelle 3 pages (Verif)
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.agcial import _new_id_wd, _parse_jour, _to_int
from app.mobile.auth import _capitalise
from app.mobile.deps import mobile_auth
from app.mobile.sfr import _create_ticket_liste
from app.mobile.tickets import _touch_tk_liste

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-tickets-dpae"],
                    dependencies=[Depends(mobile_auth)])


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


def _decode_b64(v) -> bytes | None:
    if not v:
        return None
    if isinstance(v, bytes):
        return v
    try:
        return base64.b64decode(str(v))
    except Exception:
        return None


def _iso_dt(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    return str(v)


# ===========================================================================
#  Helpers photos (DPAE + DPAEDistrib)
# ===========================================================================

def _dpae_photos(id_tk: int, schema: str, table: str) -> list[dict]:
    """Liste des photos deja renseignees (bytea non NULL OU nom_fichier
    rempli) pour un ticket DPAE. Utilise pour Contenu ET ListePhoto."""
    db = get_pg_connection(schema)
    try:
        rows = db.query(
            f"""SELECT id_tk_type_photo_dpae, nom, photo, nom_fichier
                 FROM {table}
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (int(id_tk),),
        ) or []
    except Exception:
        logger.exception("_dpae_photos %s id=%s", table, id_tk)
        return []
    result = []
    for r in rows:
        has_photo = r.get("photo") is not None
        has_fic = bool(r.get("nom_fichier"))
        if not (has_photo or has_fic):
            continue
        result.append({
            "IDTK_Liste": str(id_tk),
            "IDType": _to_int(r.get("id_tk_type_photo_dpae")),
            "nomPhoto": r.get("nom") or "",
        })
    return result


def _docsign_liste_generic(payload: dict, doc_field: str) -> list[dict]:
    """Portage DemandeDPAE_DocSignListe / DemandeDpaeDistrib_DocSignListe.

    doc_field = 'doc_dpae' ou 'doc_dpae_distrib'.
    Payload : {idste, IdProd}
    Retour : [STContenuCttW {idDocRh, ContenuHTML=Titre, IDDocDemat=IDTypeDoc,
                             TypeDoc=CodeTypeDoc}]
    Dedup sur IDTypeDoc (garde le premier trouve, tri IdSte DESC pour
    prioriser les docs specifiques a la societe sur les generiques IdSte=0).
    """
    id_ste = _to_int(payload.get("idste") or payload.get("IdSte"))
    id_prod = _to_int(payload.get("IdProd") or payload.get("IDProduit"))
    if not id_ste or not id_prod:
        return []
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            f"""SELECT dr.id_type_doc, dr.id_ste, dr.id_doc_rh, dr.titre,
                       dr.id_type_produit, tpd.code_type_doc
                  FROM rh.pgt_doc_rh dr
                  LEFT JOIN ticket_dpae.pgt_tk_type_photo_dpae tpd
                         ON tpd.id_tk_type_photo_dpae = dr.id_tk_type_photo_dpae
                 WHERE (dr.modif_elem IS NULL OR dr.modif_elem <> 'suppr')
                   AND COALESCE(dr.doc_actif, FALSE) = TRUE
                   AND (dr.id_ste = ? OR dr.id_ste = 0)
                   AND dr.id_type_produit = ?
                   AND COALESCE(dr.{doc_field}, FALSE) = TRUE
                 ORDER BY dr.id_ste DESC, dr.id_type_doc ASC""",
            (id_ste, id_prod),
        ) or []
    except Exception:
        logger.exception("_docsign_liste_generic")
        return []
    seen_types: set[int] = set()
    result = []
    for r in rows:
        id_type_doc = _to_int(r.get("id_type_doc"))
        if id_type_doc in seen_types:
            continue
        seen_types.add(id_type_doc)
        result.append({
            "idDocRh": str(int(r.get("id_doc_rh") or 0)),
            "ContenuHTML": r.get("titre") or "",
            "IDDocDemat": str(id_type_doc),
            "TypeDoc": (r.get("code_type_doc") or "").strip(),
        })
    return result


def _docsign_contenu_generic(payload: dict) -> dict:
    """Portage DemandeDPAE_DocSignContenu / DemandeDpaeDistrib_DocSignContenu.

    Retour minimal STContenuCttW = { idDocRh, TypeDoc, ContenuHTML }.
    Le WinDev appelle DocSignGenereContenu (proc globale complexe, ~200
    lignes de mise en forme HTML) - NON portee V1. On retourne l'entete
    du docRH pour que le mobile puisse afficher le titre ; le mobile
    devra recuperer le contenu HTML deja rendu ailleurs (endpoint
    dedie DonneInfo/Doc a utiliser).
    """
    id_doc_rh = _to_int(payload.get("idDocRH") or payload.get("IDdocRH"))
    if not id_doc_rh:
        return {"idDocRh": "0", "TypeDoc": "", "ContenuHTML": ""}
    db_rh = get_pg_connection("rh")
    db_dpae = get_pg_connection("ticket_dpae")
    try:
        d = db_rh.query_one(
            """SELECT id_doc_rh, titre, id_tk_type_photo_dpae
                 FROM rh.pgt_doc_rh
                WHERE id_doc_rh = ? LIMIT 1""",
            (id_doc_rh,),
        )
    except Exception:
        logger.exception("_docsign_contenu_generic")
        return {"idDocRh": "0", "TypeDoc": "", "ContenuHTML": ""}
    if not d:
        return {"idDocRh": "0", "TypeDoc": "", "ContenuHTML": ""}

    code = ""
    try:
        tpd = db_dpae.query_one(
            """SELECT code_type_doc FROM ticket_dpae.pgt_tk_type_photo_dpae
                WHERE id_tk_type_photo_dpae = ? LIMIT 1""",
            (_to_int(d.get("id_tk_type_photo_dpae")),),
        )
        if tpd:
            code = (tpd.get("code_type_doc") or "").strip()
    except Exception:
        pass
    return {
        "idDocRh": str(int(d.get("id_doc_rh") or 0)),
        "TypeDoc": code,
        "ContenuHTML": d.get("titre") or "",
    }


# ===========================================================================
#  DPAE / Contenu
# ===========================================================================

@router.post("/Tickets/DPAE/Contenu")
def dpae_contenu(payload: dict = Body(...)):
    """Portage DemandeDPAE_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"IDTK_DemandeDPAE": "0", "idorganigramme": 0,
             "Civilite": 0, "NOM": "", "NOM_MARITAL": "", "PRENOM": "",
             "NUMSS": "", "DNAISS": "", "LNAISS": "", "DEPNAISS": 0,
             "NUMCIN": "", "ADRESSE1": "", "Cp": "", "VILLE": "",
             "CPAM": "", "GSM": "", "MAIL": "",
             "URGNOM": "", "URGLIEN": "", "URGTEL": "",
             "DateDebut": "", "Coopte": False, "Coopteur": 0,
             "JO": False, "JOCoopteur": 0,
             "MUTUELLE": False, "MUTDATE": "",
             "TravailleurHandi": False, "SituationFam": 0,
             "AvecEnfant": False, "nbEnfant": 0, "MesPhotos": []}
    if not id_tk:
        return empty
    db = get_pg_connection("ticket_dpae")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_dpae, idorganigramme, civilite, nom,
                      nom_marital, prenom, num_ss, dnaiss, lnaiss, dep_naiss,
                      num_cin, adresse1, cp, ville, cpam, gsm, mail,
                      urg_nom, urg_lien, urg_tel, date_debut, coopte, coopteur,
                      j_odirecte, jo_coopteur, mutuelle, mut_date,
                      travailleur_handi, situation_fam, avec_enfant, nb_enfants
                 FROM ticket_dpae.pgt_tk_demande_dpae
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("dpae_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty
    return {
        "IDTK_DemandeDPAE": str(int(row.get("id_tk_demande_dpae") or 0)),
        "idorganigramme": _to_int(row.get("idorganigramme")),
        "Civilite": _to_int(row.get("civilite")),
        "NOM": (row.get("nom") or "").strip(),
        "NOM_MARITAL": (row.get("nom_marital") or "").strip(),
        "PRENOM": (row.get("prenom") or "").strip(),
        "NUMSS": (row.get("num_ss") or "").strip(),
        "DNAISS": _iso_dt(row.get("dnaiss")),
        "LNAISS": (row.get("lnaiss") or "").strip(),
        "DEPNAISS": _to_int(row.get("dep_naiss")),
        "NUMCIN": (row.get("num_cin") or "").strip(),
        "ADRESSE1": (row.get("adresse1") or "").strip(),
        "Cp": (row.get("cp") or "").strip(),
        "VILLE": (row.get("ville") or "").strip(),
        "CPAM": (row.get("cpam") or "").strip(),
        "GSM": (row.get("gsm") or "").strip(),
        "MAIL": (row.get("mail") or "").strip(),
        "URGNOM": (row.get("urg_nom") or "").strip(),
        "URGLIEN": (row.get("urg_lien") or "").strip(),
        "URGTEL": (row.get("urg_tel") or "").strip(),
        "DateDebut": _iso_dt(row.get("date_debut")),
        "Coopte": bool(row.get("coopte")),
        "Coopteur": _to_int(row.get("coopteur")),
        "JO": bool(row.get("j_odirecte")),
        "JOCoopteur": _to_int(row.get("jo_coopteur")),
        "MUTUELLE": bool(row.get("mutuelle")),
        "MUTDATE": _iso_dt(row.get("mut_date")),
        "TravailleurHandi": bool(row.get("travailleur_handi")),
        "SituationFam": _to_int(row.get("situation_fam")),
        "AvecEnfant": bool(row.get("avec_enfant")),
        "nbEnfant": _to_int(row.get("nb_enfants")),
        "MesPhotos": _dpae_photos(id_tk, "ticket_dpae",
                                    "ticket_dpae.pgt_tk_demande_dpae_photo"),
    }


# ===========================================================================
#  DPAE / Save
# ===========================================================================

@router.post("/Tickets/DPAE/Save")
def dpae_save(payload: dict = Body(...),
              id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDPAE_Save. Type demande=3, service=RH.

    Regle WinDev : si TK_Liste.IDTK_TypeDemande == 21 (draft ?),
    la modification passe a 3 (DPAE final).
    TODO V2 : envoi mail RH si heure > 12h (create tardif)."""
    id_dem = _to_int(payload.get("IDTK_DemandeDPAE"))
    op_crea = _to_int(payload.get("OPCrea") or id_cial)

    fields = {
        "idorganigramme": _to_int(payload.get("idorganigramme")),
        "civilite": _to_int(payload.get("Civilite")),
        "nom": payload.get("NOM") or "",
        "nom_marital": payload.get("NOM_MARITAL") or "",
        "prenom": payload.get("PRENOM") or "",
        "num_ss": payload.get("NUMSS") or "",
        "dnaiss": _parse_jour(payload.get("DNAISS")),
        "nationalite": payload.get("NATIONALITE") or "",
        "lnaiss": payload.get("LNAISS") or "",
        "dep_naiss": (payload.get("DEPNAISS") or "")[:2]
                       if isinstance(payload.get("DEPNAISS"), str)
                       else _to_int(payload.get("DEPNAISS")),
        "num_cin": payload.get("NUMCIN") or "",
        "adresse1": payload.get("ADRESSE1") or "",
        "cp": payload.get("Cp") or "",
        "ville": payload.get("VILLE") or "",
        "cpam": payload.get("CPAM") or "",
        "gsm": payload.get("GSM") or "",
        "mail": payload.get("MAIL") or "",
        "urg_nom": payload.get("URGNOM") or "",
        "urg_lien": payload.get("URGLIEN") or "",
        "urg_tel": payload.get("URGTEL") or "",
        "date_debut": _parse_jour(payload.get("DateDebut")) or date.today(),
        "coopte": bool(payload.get("Coopte")),
        "coopteur": _to_int(payload.get("Coopteur")),
        "j_odirecte": bool(payload.get("JO")),
        "jo_coopteur": _to_int(payload.get("JOCoopteur")),
        "mutuelle": bool(payload.get("MUTUELLE")),
        "mut_date": _parse_jour(payload.get("MUTDATE")),
        "travailleur_handi": bool(payload.get("TravailleurHandi")),
    }
    if _to_int(payload.get("SituationFam")):
        fields["situation_fam"] = _to_int(payload.get("SituationFam"))
    if payload.get("AvecEnfant"):
        fields["avec_enfant"] = True
        fields["nb_enfants"] = _to_int(payload.get("nbEnfant"))

    db = get_pg_connection("ticket_dpae")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()

    if id_dem:
        # Update
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_dpae.pgt_tk_demande_dpae
                    WHERE id_tk_demande_dpae = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            id_tk = _to_int(row.get("id_tk_liste"))
            cols = list(fields.keys())
            vals = list(fields.values())
            set_sql = ", ".join(f"{c} = ?" for c in cols)
            db.query(
                f"""UPDATE ticket_dpae.pgt_tk_demande_dpae
                       SET {set_sql}, modif_date = ?, modif_op = ?,
                           modif_elem = 'modif'
                     WHERE id_tk_demande_dpae = ?""",
                tuple(vals + [now, id_cial, id_dem]),
            )
            # Passage type 21 -> 3 si necessaire
            tk = db_tk.query_one(
                "SELECT id_tk_type_demande FROM ticket.pgt_tk_liste WHERE id_tk_liste = ? LIMIT 1",
                (id_tk,),
            )
            if tk and _to_int(tk.get("id_tk_type_demande")) == 21:
                db_tk.query(
                    """UPDATE ticket.pgt_tk_liste
                          SET id_tk_type_demande = 3
                        WHERE id_tk_liste = ?""",
                    (id_tk,),
                )
            _touch_tk_liste(id_tk, id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("dpae_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("RH", 3, 1, op_crea, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        cols = list(fields.keys())
        vals = list(fields.values())
        placeholders = ", ".join("?" for _ in cols)
        col_sql = ", ".join(cols)
        db.query(
            f"""INSERT INTO ticket_dpae.pgt_tk_demande_dpae
                 (id_tk_demande_dpae_auto, id_tk_demande_dpae, id_tk_liste,
                  op_crea, date_crea, {col_sql},
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, {placeholders}, ?, ?, 'new')""",
            tuple([id_new, id_new, id_tk_new, op_crea, now] + vals
                    + [now, id_cial]),
        )
        # TODO V2 : envoi mail RH si heure > 12h
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("dpae_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  DPAE / ListePhoto
# ===========================================================================

@router.post("/Tickets/DPAE/ListePhoto")
def dpae_liste_photo(payload: dict = Body(...)):
    """Portage DemandeDPAE_InfoPhoto (endpoint dedie)."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk:
        return []
    return _dpae_photos(id_tk, "ticket_dpae",
                        "ticket_dpae.pgt_tk_demande_dpae_photo")


# ===========================================================================
#  DPAE / DocSign / Liste
# ===========================================================================

@router.post("/Tickets/DPAE/DocSign/Liste")
def dpae_docsign_liste(payload: dict = Body(...)):
    """Portage DemandeDPAE_DocSignListe. Filtre docRH.DocDPAE=1."""
    return _docsign_liste_generic(payload, "doc_dpae")


# ===========================================================================
#  DPAE / DocSign / Contenu
# ===========================================================================

@router.post("/Tickets/DPAE/DocSign/Contenu")
def dpae_docsign_contenu(payload: dict = Body(...)):
    """Portage DemandeDPAE_DocSignContenu (entete uniquement V1)."""
    return _docsign_contenu_generic(payload)


# ===========================================================================
#  DPAE / DocSign / Enr
# ===========================================================================

def _docsign_enr_generic(payload: dict, id_cial: int, type_doc: str,
                          table_demat: str, id_pk_col: str,
                          schema: str, distrib: bool) -> dict:
    """Portage commun DemandeDPAE_DocSignEnr / DemandeDpaeDistrib_DocSignEnr.

    Upsert TK_DPAE_DocDemat[_Distrib] + stockage signature/photo/luapp
    en bytea (mobile envoie du base64).

    TODO V2 : generation PDF (iImprimeEtat/DocRHGenerationPDF) + FTP OVH
    upload + insert TK_DemandeDPAEPhoto[_Distrib] pour tracer le PDF.
    """
    import psycopg2
    id_dem = _to_int(payload.get("IDDocDemat"))
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk or not type_doc:
        return {"nIdDemande": "0"}

    sig = _decode_b64(payload.get("Signature"))
    photo = _decode_b64(payload.get("PHOTO") or payload.get("Photo"))
    luapp = _decode_b64(payload.get("LuApp"))
    cmu = bool(payload.get("Cmu"))
    mut = bool(payload.get("Mut"))
    mut_nom = payload.get("MutNom") or ""
    mut_date_fin = _parse_jour(payload.get("MutDateFin"))

    db = get_pg_connection(schema)
    db_tk = get_pg_connection("ticket")
    now = datetime.now()

    # Cherche si existe deja (par IDDocDemat ou par (id_tk_liste, type_doc))
    row = None
    try:
        if id_dem:
            row = db.query_one(
                f"""SELECT {id_pk_col}, id_tk_liste
                     FROM {table_demat}
                    WHERE {id_pk_col} = ? LIMIT 1""",
                (id_dem,),
            )
        if not row:
            row = db.query_one(
                f"""SELECT {id_pk_col}, id_tk_liste
                     FROM {table_demat}
                    WHERE id_tk_liste = ? AND type_doc = ? LIMIT 1""",
                (id_tk, type_doc),
            )
    except Exception:
        logger.exception("_docsign_enr_generic read %s", table_demat)

    id_pk = 0
    try:
        if row:
            id_pk = _to_int(row.get(id_pk_col))
            db.query(
                f"""UPDATE {table_demat}
                       SET date_signature = ?, cmu = ?, mutuelle = ?,
                           nom_mutuelle = ?, date_fin_mutuelle = ?,
                           photo = COALESCE(?, photo),
                           signature = COALESCE(?, signature),
                           lu_app = COALESCE(?, lu_app),
                           modif_date = ?, modif_op = ?, modif_elem = 'modif'
                     WHERE {id_pk_col} = ?""",
                (date.today(), cmu, mut, mut_nom, mut_date_fin,
                 psycopg2.Binary(photo) if photo else None,
                 psycopg2.Binary(sig) if sig else None,
                 psycopg2.Binary(luapp) if luapp else None,
                 now, id_cial, id_pk),
            )
        else:
            id_pk = _new_id_wd()
            id_auto_col = id_pk_col + "_auto"
            db.query(
                f"""INSERT INTO {table_demat}
                     ({id_auto_col}, {id_pk_col}, id_tk_liste, type_doc,
                      date_signature, cmu, mutuelle, nom_mutuelle,
                      date_fin_mutuelle, photo, signature, lu_app,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_pk, id_pk, id_tk, type_doc, date.today(),
                 cmu, mut, mut_nom, mut_date_fin,
                 psycopg2.Binary(photo) if photo else None,
                 psycopg2.Binary(sig) if sig else None,
                 psycopg2.Binary(luapp) if luapp else None,
                 now, id_cial),
            )
    except Exception as e:
        logger.exception("_docsign_enr_generic upsert %s", table_demat)
        return {"nIdDemande": "0", "sInfoData": str(e)}

    # Passage type 21 -> 3
    try:
        tk = db_tk.query_one(
            "SELECT id_tk_type_demande FROM ticket.pgt_tk_liste WHERE id_tk_liste = ? LIMIT 1",
            (id_tk,),
        )
        if tk and _to_int(tk.get("id_tk_type_demande")) == 21:
            db_tk.query(
                """UPDATE ticket.pgt_tk_liste
                      SET id_tk_type_demande = 3, modif_date = ?, modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (now, id_cial, id_tk),
            )
    except Exception:
        logger.exception("_docsign_enr_generic tk update")

    # TODO V2 : generation PDF + FTP OVH + insert TK_DemandeDPAEPhoto[_Distrib]
    return {"nIdDemande": str(id_pk)}


@router.post("/Tickets/DPAE/DocSign/Enr")
def dpae_docsign_enr(payload: dict = Body(...),
                      id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDPAE_DocSignEnr. TypeDoc dans payload."""
    type_doc = payload.get("TypeDoc") or ""
    return _docsign_enr_generic(
        payload, id_cial, type_doc,
        "ticket_dpae.pgt_tk_dpae_doc_demat",
        "id_tk_dpae_doc_demat",
        "ticket_dpae",
        distrib=False,
    )


# ===========================================================================
#  DPAEDistrib / ListePart
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/ListePart")
def dpaedistrib_liste_part(_payload: Any = Body(default=None)):
    """Portage DemandeDpaeDistrib_ListePart. Liste fixe de partenaires."""
    return ["ENI", "SFR", "ASSU", "PRESSE", "OHM Énergie"]


# ===========================================================================
#  DPAEDistrib / Contenu
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/Contenu")
def dpaedistrib_contenu(payload: dict = Body(...)):
    """Portage DemandeDpaeDistrib_Contenu."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    empty = {"IDTK_DemandeDPAE": "0", "idorganigramme": 0,
             "Civilite": 0, "NOM": "", "NOM_MARITAL": "", "PRENOM": "",
             "NUMSS": "", "DNAISS": "", "LNAISS": "", "DEPNAISS": 0,
             "NUMCIN": "", "ADRESSE1": "", "Cp": "", "VILLE": "",
             "GSM": "", "MAIL": "", "DateDebut": "", "MesPhotos": []}
    if not id_tk:
        return empty
    db = get_pg_connection("ticket_bo")
    try:
        row = db.query_one(
            """SELECT id_tk_demande_dpae_distrib, idorganigramme, civilite, nom,
                      nom_marital, prenom, num_ss, dnaiss, lnaiss, dep_naiss,
                      num_cin, adresse1, cp, ville, gsm, mail, date_debut
                 FROM ticket_bo.pgt_tk_demande_dpae_distrib
                WHERE id_tk_liste = ? LIMIT 1""",
            (id_tk,),
        )
    except Exception:
        logger.exception("dpaedistrib_contenu id=%s", id_tk)
        return empty
    if not row:
        return empty
    return {
        "IDTK_DemandeDPAE": str(int(row.get("id_tk_demande_dpae_distrib") or 0)),
        "idorganigramme": _to_int(row.get("idorganigramme")),
        "Civilite": _to_int(row.get("civilite")),
        "NOM": (row.get("nom") or "").strip(),
        "NOM_MARITAL": (row.get("nom_marital") or "").strip(),
        "PRENOM": (row.get("prenom") or "").strip(),
        "NUMSS": (row.get("num_ss") or "").strip(),
        "DNAISS": _iso_dt(row.get("dnaiss")),
        "LNAISS": (row.get("lnaiss") or "").strip(),
        "DEPNAISS": _to_int(row.get("dep_naiss")),
        "NUMCIN": (row.get("num_cin") or "").strip(),
        "ADRESSE1": (row.get("adresse1") or "").strip(),
        "Cp": (row.get("cp") or "").strip(),
        "VILLE": (row.get("ville") or "").strip(),
        "GSM": (row.get("gsm") or "").strip(),
        "MAIL": (row.get("mail") or "").strip(),
        "DateDebut": _iso_dt(row.get("date_debut")),
        "MesPhotos": _dpae_photos(id_tk, "ticket_bo",
                                    "ticket_bo.pgt_tk_demande_dpae_distrib_photo"),
    }


# ===========================================================================
#  DPAEDistrib / Save
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/Save")
def dpaedistrib_save(payload: dict = Body(...),
                       id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDpaeDistrib_Save. Type demande=29, service=BO."""
    id_dem = _to_int(payload.get("IDTK_DemandeDPAE"))
    op_crea = _to_int(payload.get("OPCrea") or id_cial)

    fields = {
        "idorganigramme": _to_int(payload.get("idorganigramme")),
        "civilite": _to_int(payload.get("Civilite")),
        "nom": payload.get("NOM") or "",
        "nom_marital": payload.get("NOM_MARITAL") or "",
        "prenom": payload.get("PRENOM") or "",
        "num_ss": payload.get("NUMSS") or "",
        "dnaiss": _parse_jour(payload.get("DNAISS")),
        "lnaiss": payload.get("LNAISS") or "",
        "num_cin": payload.get("NUMCIN") or "",
        "adresse1": payload.get("ADRESSE1") or "",
        "cp": payload.get("Cp") or "",
        "ville": payload.get("VILLE") or "",
        "gsm": payload.get("GSM") or "",
        "mail": payload.get("MAIL") or "",
        "date_debut": _parse_jour(payload.get("DateDebut")) or date.today(),
    }

    db = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()

    if id_dem:
        try:
            row = db.query_one(
                """SELECT id_tk_liste FROM ticket_bo.pgt_tk_demande_dpae_distrib
                    WHERE id_tk_demande_dpae_distrib = ? LIMIT 1""",
                (id_dem,),
            )
            if not row:
                return {"nIdDemande": "0"}
            id_tk = _to_int(row.get("id_tk_liste"))
            cols = list(fields.keys())
            vals = list(fields.values())
            set_sql = ", ".join(f"{c} = ?" for c in cols)
            db.query(
                f"""UPDATE ticket_bo.pgt_tk_demande_dpae_distrib
                       SET {set_sql}, modif_date = ?, modif_op = ?,
                           modif_elem = 'modif'
                     WHERE id_tk_demande_dpae_distrib = ?""",
                tuple(vals + [now, id_cial, id_dem]),
            )
            # Type 21 -> 3
            tk = db_tk.query_one(
                "SELECT id_tk_type_demande FROM ticket.pgt_tk_liste WHERE id_tk_liste = ? LIMIT 1",
                (id_tk,),
            )
            if tk and _to_int(tk.get("id_tk_type_demande")) == 21:
                db_tk.query(
                    """UPDATE ticket.pgt_tk_liste
                          SET id_tk_type_demande = 3
                        WHERE id_tk_liste = ?""",
                    (id_tk,),
                )
            _touch_tk_liste(id_tk, id_cial)
            return {"nIdDemande": str(id_dem)}
        except Exception as e:
            logger.exception("dpaedistrib_save update")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    # Insert
    id_new = _new_id_wd()
    id_tk_new = _create_ticket_liste("BO", 29, 1, op_crea, id_new)
    if not id_tk_new:
        return {"nIdDemande": "0"}
    try:
        cols = list(fields.keys())
        vals = list(fields.values())
        placeholders = ", ".join("?" for _ in cols)
        col_sql = ", ".join(cols)
        db.query(
            f"""INSERT INTO ticket_bo.pgt_tk_demande_dpae_distrib
                 (id_tk_demande_dpae_distrib_auto, id_tk_demande_dpae_distrib,
                  id_tk_liste, op_crea, date_crea, {col_sql},
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, {placeholders}, ?, ?, 'new')""",
            tuple([id_new, id_new, id_tk_new, op_crea, now] + vals
                    + [now, id_cial]),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("dpaedistrib_save insert")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ===========================================================================
#  DPAEDistrib / ListePhoto
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/ListePhoto")
def dpaedistrib_liste_photo(payload: dict = Body(...)):
    """Portage DemandeDpaeDistrib_InfoPhoto (endpoint dedie)."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    if not id_tk:
        return []
    return _dpae_photos(id_tk, "ticket_bo",
                        "ticket_bo.pgt_tk_demande_dpae_distrib_photo")


# ===========================================================================
#  DPAEDistrib / Verif
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/Verif")
def dpaedistrib_verif(payload: dict = Body(...),
                        id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDpaeDistrib_PhotoVerif.
    Payload : { idTicket, IDType, NomPhoto }
    Insert/update TK_DemandeDPAE_DistribPhoto avec NomFichier.
    TODO V2 : upload FTP OVH + fusion PDF Mutuelle (3 pages)."""
    id_tk = _to_int(payload.get("idTicket") or payload.get("IDTK_Liste"))
    id_type = _to_int(payload.get("IDType"))
    nom_photo = payload.get("NomPhoto") or ""
    if not id_tk or not nom_photo:
        return {"nIdDemande": "0"}

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    now = datetime.now()
    nom_fichier = f"{id_tk}_{nom_photo}.pdf"

    # Cherche existant
    try:
        row = db_bo.query_one(
            """SELECT id_tk_demande_dpae_photo, id_tk_demande_dpae
                 FROM ticket_bo.pgt_tk_demande_dpae_distrib_photo
                WHERE id_tk_liste = ? AND nom = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_tk, nom_photo),
        )
    except Exception:
        logger.exception("dpaedistrib_verif read")
        row = None

    if row:
        try:
            db_bo.query(
                """UPDATE ticket_bo.pgt_tk_demande_dpae_distrib_photo
                      SET id_tk_type_photo_dpae = ?, nom_fichier = ?,
                          modif_date = ?, modif_op = ?, modif_elem = 'new'
                    WHERE id_tk_demande_dpae_photo = ?""",
                (id_type, nom_fichier, now, id_cial,
                 _to_int(row.get("id_tk_demande_dpae_photo"))),
            )
        except Exception as e:
            logger.exception("dpaedistrib_verif update")
            return {"nIdDemande": "0", "sInfoData": str(e)}
    else:
        # Recup id_tk_demande_dpae du parent
        try:
            parent = db_bo.query_one(
                """SELECT id_tk_demande_dpae_distrib, op_crea
                     FROM ticket_bo.pgt_tk_demande_dpae_distrib
                    WHERE id_tk_liste = ? LIMIT 1""",
                (id_tk,),
            )
        except Exception:
            parent = None
        id_parent = _to_int((parent or {}).get("id_tk_demande_dpae_distrib"))
        op_parent = _to_int((parent or {}).get("op_crea"))

        id_new = _new_id_wd()
        try:
            db_bo.query(
                """INSERT INTO ticket_bo.pgt_tk_demande_dpae_distrib_photo
                     (id_tk_demande_dpae_photo_auto, id_tk_demande_dpae_photo,
                      id_tk_demande_dpae, id_tk_type_photo_dpae, id_tk_liste,
                      op_crea, nom, nom_fichier,
                      modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (id_new, id_new, id_parent, id_type, id_tk,
                 op_parent, nom_photo, nom_fichier,
                 now, id_cial),
            )
        except Exception as e:
            logger.exception("dpaedistrib_verif insert")
            return {"nIdDemande": "0", "sInfoData": str(e)}

    _touch_tk_liste(id_tk, id_cial)
    return {"nIdDemande": str(id_tk)}


# ===========================================================================
#  DPAEDistrib / DocSign / Liste / Contenu / Enr
# ===========================================================================

@router.post("/Tickets/DPAEDistrib/DocSign/Liste")
def dpaedistrib_docsign_liste(payload: dict = Body(...)):
    """Portage DemandeDpaeDistrib_DocSignListe. Filtre docRH.DocDPAE_Distrib=1."""
    return _docsign_liste_generic(payload, "doc_dpae_distrib")


@router.post("/Tickets/DPAEDistrib/DocSign/Contenu")
def dpaedistrib_docsign_contenu(payload: dict = Body(...)):
    """Portage DemandeDpaeDistrib_DocSignContenu."""
    return _docsign_contenu_generic(payload)


@router.post("/Tickets/DPAEDistrib/DocSign/Enr")
def dpaedistrib_docsign_enr(payload: dict = Body(...),
                              id_cial: int = Depends(mobile_auth)):
    """Portage DemandeDpaeDistrib_DocSignEnr."""
    type_doc = payload.get("TypeDoc") or ""
    return _docsign_enr_generic(
        payload, id_cial, type_doc,
        "ticket_bo.pgt_tk_dpae_doc_demat_distrib",
        "id_tk_dpae_doc_demat_distrib",
        "ticket_bo",
        distrib=True,
    )
