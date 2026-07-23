"""Endpoints mobile AgCial (WebRest_Omayapp/AgCial/*).

Portage iso-URL des 6 WS AgendaCommercial WinDev :
  - StatutsRDV    : liste des categories de RDV
  - ListeVendeur  : liste des vendeurs ayant le droit AgendaCial
  - ListeRDV      : RDV d'un vendeur pour une journee (+ absences)
  - InfoTkCall    : detail client du ticket lie a un RDV
  - AjoutRDV      : creation d'un RDV
  - StatuerRDV    : change le statut d'un RDV (avec report si statut=6)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.database.pg import get_pg_connection
from app.mobile.auth import _capitalise, _info_salarie_complet
from app.mobile.deps import mobile_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mobile-agcial"],
                    dependencies=[Depends(mobile_auth)])


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _new_id_wd() -> int:
    """idEntierDateHeureSys() de WinDev."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _parse_jour(v: Any) -> date | None:
    """Accepte YYYYMMDD (WinDev), YYYY-MM-DD (ISO) ou datetime ISO complet."""
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    # YYYY-MM-DD ou datetime ISO
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    # YYYYMMDD compact
    if len(s) >= 8 and s[:8].isdigit():
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            return None
    return None


def _parse_dt(v: Any) -> datetime | None:
    """Accepte ISO (YYYY-MM-DD HH:MM:SS ou avec T) ou compact WinDev (YYYYMMDDHHMMSS)."""
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip().replace("T", " ")
    if not s:
        return None
    # ISO
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
        pass
    try:
        return datetime.combine(date.fromisoformat(s[:10]), datetime.min.time())
    except ValueError:
        pass
    # Compact WinDev
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) >= 14:
        try:
            return datetime.strptime(digits[:14], "%Y%m%d%H%M%S")
        except ValueError:
            return None
    if len(digits) >= 8:
        try:
            return datetime.strptime(digits[:8], "%Y%m%d")
        except ValueError:
            return None
    return None


def _rdv_info_tk_call(id_ticket: int) -> dict:
    """Portage RdvCial_DonneInfoTkCall : detail client d'un ticket
    Call/CallSFR (route vers pgt_tk_call ou pgt_tk_call_sfr selon type)."""
    if not id_ticket:
        return {"IDTypeDemande": 0}
    tk_db = get_pg_connection("ticket")
    tkbo_db = get_pg_connection("ticket_bo")
    try:
        head = tk_db.query_one(
            """SELECT id_tk_type_demande
                 FROM ticket.pgt_tk_liste
                WHERE id_tk_liste = ? LIMIT 1""",
            (int(id_ticket),),
        )
    except Exception:
        logger.exception("_rdv_info_tk_call head id=%s", id_ticket)
        return {"IDTypeDemande": 0}
    if not head:
        return {"IDTypeDemande": 0}

    id_type_dem = int(head.get("id_tk_type_demande") or 0)
    if id_type_dem == 20:
        table = "ticket_bo.pgt_tk_call_sfr"
    else:
        table = "ticket_bo.pgt_tk_call"

    cols = ("civilite_client, nom_client, nom_marital_client, prenom_client, "
            "date_naiss, dep_naiss, adresse1, adresse2, cp, ville, adr_mail, "
            "mobile1, type_logement, client_pro, client_rs, client_siret")
    try:
        row = tkbo_db.query_one(
            f"SELECT {cols} FROM {table} WHERE id_tk_liste = ? LIMIT 1",
            (int(id_ticket),),
        )
    except Exception:
        logger.exception("_rdv_info_tk_call detail id=%s", id_ticket)
        return {"IDTypeDemande": id_type_dem}
    if not row:
        return {"IDTypeDemande": id_type_dem}

    dn = row.get("date_naiss")
    return {
        "IDTypeDemande": id_type_dem,
        "CiviliteClient": _to_int(row.get("civilite_client")),
        "NomClient": (row.get("nom_client") or "").strip(),
        "NomMaritalClient": (row.get("nom_marital_client") or "").strip(),
        "PrenomClient": (row.get("prenom_client") or "").strip(),
        "TypeLogement": _to_int(row.get("type_logement")),
        "ADRESSE1": (row.get("adresse1") or "").strip(),
        "ADRESSE2": (row.get("adresse2") or "").strip(),
        "CP": (row.get("cp") or "").strip(),
        "VILLE": (row.get("ville") or "").strip(),
        "Mobile1": (row.get("mobile1") or "").strip(),
        "adrMail": (row.get("adr_mail") or "").strip(),
        "ClientPro": bool(row.get("client_pro")),
        "ClientRS": (row.get("client_rs") or "").strip(),
        "ClientSiret": (row.get("client_siret") or "").strip(),
        "DATENAISS": dn.isoformat() if dn else "",
        "DEPNAISS": _to_int(row.get("dep_naiss")),
    }


def _test_vendeur_absent(id_salarie: int, jour: date) -> dict | None:
    """Retourne l'absence couvrant le jour donne ou None."""
    if not id_salarie or not jour:
        return None
    db = get_pg_connection("rh")
    try:
        row = db.query_one(
            """SELECT id_absence, date_debut, date_fin
                 FROM rh.pgt_absence
                WHERE id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                  AND date_debut::date <= ?::date
                  AND date_fin::date   >= ?::date
                LIMIT 1""",
            (int(id_salarie), jour.isoformat(), jour.isoformat()),
        )
    except Exception:
        logger.exception("_test_vendeur_absent id=%s j=%s", id_salarie, jour)
        return None
    return row


# ---------------------------------------------------------------------------
#  StatutsRDV
# ---------------------------------------------------------------------------

@router.post("/AgCial/StatutsRDV")
def statuts_rdv(_payload: dict = Body(default={})):
    """Liste des categories de RDV. Portage RdvCial_StatutRdv.
    Retour : [{Coul, ID, IDStatutCV, lib}]
    """
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT id_agenda_commercial_categorie AS id_cat,
                      couleur, id_cv_statut, lib_categorie
                 FROM adv.pgt_agenda_commercial_categorie
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY id_agenda_commercial_categorie""",
        ) or []
    except Exception:
        logger.exception("statuts_rdv")
        return []
    return [
        {"Coul": _to_int(r.get("couleur")),
         "ID": _to_int(r.get("id_cat")),
         "IDStatutCV": str(int(r.get("id_cv_statut") or 0)) if r.get("id_cv_statut") else "0",
         "lib": (r.get("lib_categorie") or "").strip()}
        for r in rows
    ]


# ---------------------------------------------------------------------------
#  ListeVendeur
# ---------------------------------------------------------------------------

@router.post("/AgCial/ListeVendeur")
def liste_vendeur(_payload: dict = Body(default={})):
    """Liste des salaries ayant le droit AgendaCial + en activite.
    Portage ListeVendAgCial. Retour : [ST_SALARIE, ...]
    """
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT DISTINCT sd.id_salarie
                 FROM rh.pgt_salarie_droit_acces sd
                 JOIN rh.pgt_type_droit_acces td
                        ON td.id_type_droit_acces = sd.id_type_droit_acces
                 JOIN rh.pgt_salarie_embauche se
                        ON se.id_salarie = sd.id_salarie
                WHERE COALESCE(sd.droit_actif, FALSE) = TRUE
                  AND td.code_interne = ?
                  AND COALESCE(se.en_activite, FALSE) = TRUE""",
            ("AgendaCial",),
        ) or []
    except Exception:
        logger.exception("liste_vendeur")
        return []

    result: list[dict] = []
    for r in rows:
        id_sal = int(r.get("id_salarie") or 0)
        if not id_sal:
            continue
        info = _info_salarie_complet(id_sal)
        if info.get("ID"):
            result.append(info)
    return result


# ---------------------------------------------------------------------------
#  ListeRDV
# ---------------------------------------------------------------------------

@router.post("/AgCial/ListeRDV")
def liste_rdv(payload: dict = Body(...),
              id_demandeur_auth: int = Depends(mobile_auth)):
    """Liste des RDV d'un vendeur pour un jour donne.

    Payload : { IDSalarie (recruteur), Jour, IdSalarieDemandeur (optionnel) }
    Retour : [ST_AGENDA_Cial]

    Bonus WinDev : si le vendeur est absent ce jour, ajoute une entree
    'Absence' 8h-20h dans la liste.
    Si le demandeur != recruteur, masque Titre/Contenu et affiche
    seulement 'RDV a CP VILLE' du ticket call associe.
    """
    id_recruteur = _to_int(payload.get("IDSalarie") or payload.get("idRecruteur"))
    id_demandeur = _to_int(payload.get("IdSalarieDemandeur")
                            or payload.get("idDemandeur")
                            or id_demandeur_auth)
    jour = _parse_jour(payload.get("Jour"))
    if not id_recruteur or not jour:
        return []

    result: list[dict] = []

    # 1. Test absence
    abs_row = _test_vendeur_absent(id_recruteur, jour)
    if abs_row:
        deb = datetime.combine(jour, datetime.min.time()).replace(hour=8)
        fin = deb.replace(hour=20)
        db_deb, df_fin = abs_row.get("date_debut"), abs_row.get("date_fin")
        contenu_abs = ""
        if db_deb and df_fin and db_deb != df_fin:
            try:
                d_deb = db_deb.date() if hasattr(db_deb, "date") else _parse_jour(db_deb)
                d_fin = df_fin.date() if hasattr(df_fin, "date") else _parse_jour(df_fin)
                if d_deb and d_fin:
                    contenu_abs = (f"Du {d_deb.strftime('%d/%m/%Y')} "
                                   f"au {d_fin.strftime('%d/%m/%Y')}")
            except Exception:
                contenu_abs = ""
        result.append({
            "Titre": "Absence",
            "Contenu": contenu_abs,
            "IDAgendaEvenement": "0",
            "IDTK_Liste": "0",
            "DateDebut": deb.isoformat(sep=" "),
            "DateFin": fin.isoformat(sep=" "),
            "libCategorie": "Absence",
            "CoulCategorie": 0xC0C0C0,  # GrisClair WinDev
            "IDCategorie": 0,
            "InfoLieu": "",
        })

    # 2. RDV du jour
    db = get_pg_connection("adv")
    try:
        rdvs = db.query(
            """SELECT ag.id_agenda_commercial, ag.id_agenda_commercial_categorie,
                      ag.id_tk_liste, ag.titre, ag.contenu,
                      ag.date_debut, ag.date_fin,
                      cat.lib_categorie, cat.couleur
                 FROM adv.pgt_agenda_commercial ag
                 LEFT JOIN adv.pgt_agenda_commercial_categorie cat
                        ON cat.id_agenda_commercial_categorie
                             = ag.id_agenda_commercial_categorie
                WHERE ag.id_salarie = ?
                  AND ag.date_debut::date = ?::date
                  AND (ag.modif_elem IS NULL OR ag.modif_elem <> 'suppr')
                ORDER BY ag.date_debut ASC""",
            (int(id_recruteur), jour.isoformat()),
        ) or []
    except Exception:
        logger.exception("liste_rdv id_rec=%s jour=%s", id_recruteur, jour)
        return result

    for r in rdvs:
        deb = r.get("date_debut")
        fin = r.get("date_fin")
        id_tk = _to_int(r.get("id_tk_liste"))
        id_ag = _to_int(r.get("id_agenda_commercial"))
        id_cat = _to_int(r.get("id_agenda_commercial_categorie"))
        item = {
            "IDAgendaEvenement": str(id_ag) if id_ag else "0",
            "IDTK_Liste": str(id_tk) if id_tk else "0",
            "IDCategorie": id_cat,
            "libCategorie": (r.get("lib_categorie") or "").strip(),
            "CoulCategorie": _to_int(r.get("couleur")),
            "DateDebut": deb.isoformat(sep=" ") if deb else "",
            "DateFin": fin.isoformat(sep=" ") if fin else "",
            "InfoLieu": "",
        }
        if id_demandeur == id_recruteur:
            item["Titre"] = r.get("titre") or ""
            item["Contenu"] = r.get("contenu") or ""
        else:
            item["Contenu"] = ""
            if id_tk:
                info_call = _rdv_info_tk_call(id_tk)
                item["Titre"] = (f"RDV a {info_call.get('CP', '')} "
                                 f"{info_call.get('VILLE', '')}").strip()
            else:
                item["Titre"] = ""
        result.append(item)

    return result


# ---------------------------------------------------------------------------
#  InfoTkCall
# ---------------------------------------------------------------------------

@router.post("/AgCial/InfoTkCall")
def info_tk_call(payload: dict = Body(...)):
    """Detail client d'un ticket call associe a un RDV.
    Portage RdvCial_InfoTkCall + RdvCial_DonneInfoTkCall.

    Payload : { IDTK_Liste: int } (ou idTicket)
    """
    id_tk = _to_int(payload.get("IDTK_Liste") or payload.get("idTicket"))
    return _rdv_info_tk_call(id_tk)


# ---------------------------------------------------------------------------
#  AjoutRDV
# ---------------------------------------------------------------------------

@router.post("/AgCial/AjoutRDV")
def ajout_rdv(payload: dict = Body(...),
              id_vend: int = Depends(mobile_auth)):
    """Creation d'un RDV. Portage RdvCial_Ajout.

    Payload (ST_AGENDA_Cial) :
      { IDTK_Liste, IDSalarie, DateDebut, DateFin, IDOrigine, InfoCompl }
    Retour STRéponseTK : { nIdDemande: id_du_nouveau_RDV }
    """
    id_tk = _to_int(payload.get("IDTK_Liste"))
    id_sal_rdv = _to_int(payload.get("IDSalarie") or id_vend)
    date_deb = _parse_dt(payload.get("DateDebut"))
    date_fin = _parse_dt(payload.get("DateFin"))
    id_origine = _to_int(payload.get("IDOrigine"))
    info_compl = payload.get("InfoCompl") or ""
    if not id_tk or not id_sal_rdv or not date_deb or not date_fin:
        return {"nIdDemande": "0"}

    info = _rdv_info_tk_call(id_tk)
    type_dem = "SFR" if info.get("IDTypeDemande") == 20 else "Énergie"

    # Contenu WinDev : ClientRS \n adr1 \n adr2 \n CP VILLE \n
    # Tel : mob1 \n MAIL : mail \n Siret : siret \n Type Demande : type
    contenu = "\n".join([
        info.get("ClientRS", ""),
        info.get("ADRESSE1", ""),
        info.get("ADRESSE2", ""),
        f"{info.get('CP', '')} {info.get('VILLE', '')}".strip(),
        f"Tél : {info.get('Mobile1', '')}",
        f"MAIL : {info.get('adrMail', '')}",
        f"Siret : {info.get('ClientSiret', '')}",
        f"Type Demande :{type_dem}",
    ])
    titre = f"RDV avec {info.get('NomClient', '')} {_capitalise(info.get('PrenomClient', ''))}".strip()

    id_new = _new_id_wd()
    now = datetime.now()
    db = get_pg_connection("adv")
    try:
        db.query(
            """INSERT INTO adv.pgt_agenda_commercial
                 (id_agenda_commercial_auto, id_agenda_commercial,
                  id_salarie, id_agenda_commercial_categorie,
                  motif_statut, titre, contenu, info_compl,
                  date_debut, date_fin, id_tk_liste,
                  id_agenda_commercial_origine,
                  op_crea, datecrea, modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, 1, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (id_new, id_new, id_sal_rdv, titre, contenu, info_compl,
             date_deb, date_fin, id_tk, id_origine,
             id_vend, now, id_vend, now),
        )
        return {"nIdDemande": str(id_new)}
    except Exception as e:
        logger.exception("ajout_rdv")
        return {"nIdDemande": "0", "sInfoData": str(e)}


# ---------------------------------------------------------------------------
#  StatuerRDV
# ---------------------------------------------------------------------------

@router.post("/AgCial/StatuerRDV")
def statuer_rdv(payload: dict = Body(...),
                id_op: int = Depends(mobile_auth)):
    """Change le statut d'un RDV. Portage RdvCial_Statuer.

    Payload :
      { idRdv, IdStatut, monRdv: {Contenu, InfoCompl, DateReport, OPCrea} }
    Regle WinDev : si IdStatut == 6 (Report), cree en plus un nouveau RDV
    a DateReport (marque ID_ORIGINE_REPORT).
    """
    id_rdv = _to_int(payload.get("idRdv") or payload.get("IDAgendaEvenement"))
    id_statut = _to_int(payload.get("IdStatut") or payload.get("IDCategorie"))
    mon_rdv = payload.get("monRdv") or payload
    if not id_rdv or not id_statut:
        return {"nIdDemande": "0"}

    db = get_pg_connection("adv")
    db_rh = get_pg_connection("rh")

    # 1. Recup libelle statut
    try:
        stat = db.query_one(
            """SELECT lib_categorie FROM adv.pgt_agenda_commercial_categorie
                WHERE id_agenda_commercial_categorie = ? LIMIT 1""",
            (id_statut,),
        )
    except Exception:
        logger.exception("statuer_rdv: lib statut")
        return {"nIdDemande": "0"}
    lib_stat = (stat or {}).get("lib_categorie", "").strip() if stat else ""

    # 2. Recup RDV + salarie
    try:
        rdv = db.query_one(
            """SELECT id_salarie, contenu, id_agenda_commercial_origine, op_crea
                 FROM adv.pgt_agenda_commercial
                WHERE id_agenda_commercial = ? LIMIT 1""",
            (id_rdv,),
        )
    except Exception:
        logger.exception("statuer_rdv: read rdv")
        return {"nIdDemande": "0"}
    if not rdv:
        return {"nIdDemande": "0"}

    # 3. Recup identite du salarie (pour le log 'statue par ...')
    id_sal = int(rdv.get("id_salarie") or 0)
    nom = ""
    prenom = ""
    try:
        s = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_sal,),
        )
        if s:
            nom = (s.get("nom") or "").strip()
            prenom = _capitalise((s.get("prenom") or "").strip())
    except Exception:
        logger.exception("statuer_rdv: read salarie")

    # 4. Compose le nouveau contenu (append log)
    now = datetime.now()
    info_log = (f"RDV statué en {lib_stat} par {nom} {prenom}"
                " (via l'appli Omayapp)")
    new_contenu = ((rdv.get("contenu") or "")
                   + "\n"
                   + now.strftime("%d/%m/%Y à %H:%M")
                   + " - " + info_log)

    # 5. UPDATE
    try:
        db.query(
            """UPDATE adv.pgt_agenda_commercial
                  SET id_agenda_commercial_categorie = ?,
                      contenu = ?, motif_statut = ?, info_compl = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_agenda_commercial = ?""",
            (id_statut, new_contenu,
             mon_rdv.get("Contenu") or "",
             mon_rdv.get("InfoCompl") or "",
             now, id_op, id_rdv),
        )
    except Exception:
        logger.exception("statuer_rdv: update")
        return {"nIdDemande": "0"}

    # 6. Si statut = 6 (Report), cree un nouveau RDV
    if id_statut == 6:
        date_report = _parse_dt(mon_rdv.get("DateReport"))
        if date_report:
            id_new = _new_id_wd()
            date_rep_fin = date_report + timedelta(hours=2)
            id_origine_new = _to_int(rdv.get("id_agenda_commercial_origine")) or 2
            op_crea = _to_int(mon_rdv.get("OPCrea")) or _to_int(rdv.get("op_crea")) or id_op
            motif = (f"<ID_ORIGINE_REPORT>{id_rdv}</ID_ORIGINE_REPORT>\n")
            try:
                # Reprise des champs de base du RDV source (titre + tk + contenu vide)
                src = db.query_one(
                    """SELECT titre, id_tk_liste
                         FROM adv.pgt_agenda_commercial
                        WHERE id_agenda_commercial = ? LIMIT 1""",
                    (id_rdv,),
                )
                titre_src = (src or {}).get("titre") or ""
                id_tk_src = _to_int((src or {}).get("id_tk_liste"))
                db.query(
                    """INSERT INTO adv.pgt_agenda_commercial
                         (id_agenda_commercial_auto, id_agenda_commercial,
                          id_salarie, id_agenda_commercial_categorie,
                          motif_statut, titre, contenu, info_compl,
                          date_debut, date_fin, id_tk_liste,
                          id_agenda_commercial_origine,
                          op_crea, datecrea, modif_op, modif_date, modif_elem)
                       VALUES (?, ?, ?, 1, ?, ?, '', '', ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (id_new, id_new, id_sal, motif, titre_src,
                     date_report, date_rep_fin, id_tk_src, id_origine_new,
                     op_crea, now, op_crea, now),
                )
            except Exception:
                logger.exception("statuer_rdv: insert report")

    return {"nIdDemande": str(id_rdv)}
