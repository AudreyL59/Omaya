"""FI_RDVTech (type 19 — Retour RDV Technicien FIBRE).

Transposition de la fenêtre interne WinDev FI_RDVTech.

Affiche INFOS CLIENT + INFOS CONTRAT (lecture, depuis client/SFR_contrat/
SFR_produit/SFR_Cluster — base adv) à partir de l'IDcontrat stocké
dans TK_RetourRdvTechFIBRE (base ticket_bo).

Bouton « Je valide ce retour » :
  - met à jour SFR_contrat.IdSFR_StatutRDV
  - APPEND à SFR_contrat.InfoVenteSFR (date, libellé statut, infos
    vendeur, séparateurs « ------------------- »)
  - si statut = 8 et date fournie : met à jour SFR_contrat.DateRDVTech
  - persiste IdFIBRE_StatutRDV + InfoCplt dans TK_RetourRdvTechFIBRE
  - clôture le ticket (statut 4 Cloturée=1) + AjoutHistoTK
"""

from datetime import datetime

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    ajout_histo_tk,
    date_only_to_iso,
    iso_to_date_only,
    maj_op_traitement_ticket,
)

SFR_TYPE_VENTE_LABELS = {
    1: "Conquête", 2: "Conquête VLA",
    3: "Migration", 4: "Migration FTTB -> FTTH",
}
PERIODE_RDV_LABELS = {0: "Non défini", 1: "Matin", 2: "Après-Midi"}

_FR_JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
_FR_MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
            "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]


def _fr_now() -> str:
    """cf. WinDev 'Jjj JJ Mmm AAAA - HH:mm'."""
    d = datetime.now()
    return (
        f"{_FR_JOURS[d.weekday()]} {d.day:02d} "
        f"{_FR_MOIS[d.month - 1]} {d.year} - {d:%H:%M}"
    )


def _statuts_rdv() -> list[dict]:
    try:
        db = get_pg_connection("adv")
        return [
            {
                "id": _to_int(r.get("id_sfr_statut_rdv")),
                "lib": (r.get("lib_statut") or "").strip(),
            }
            for r in db.query(
                "SELECT id_sfr_statut_rdv, lib_statut FROM pgt_sfr_statut_rdv "
                "ORDER BY lib_statut"
            )
        ]
    except Exception:
        return []


def _memo_sfr(db, id_contrat: int, field: str) -> str:
    """Lecture isolee InfoVenteSFR / NumBS de SFR_contrat. **HFSQL**
    car save fait un read-modify-write (concat InfoVenteSFR) qui doit
    voir la valeur la plus fraiche (pas de lag PG)."""
    try:
        r = db.query_one(
            f"SELECT IDcontrat, {field} FROM SFR_contrat WHERE IDcontrat = ?",
            (int(id_contrat),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def _client_info(id_client: int) -> dict:
    if not id_client:
        return {}
    try:
        r = get_pg_connection("adv").query_one(
            "SELECT id_client, nom, prenom, adresse1, adresse2, cp, ville, "
            "tel, gsm, mail FROM pgt_client WHERE id_client = ?",
            (int(id_client),),
        )
        if not r:
            return {}
        return {
            "nom": (r.get("nom") or "").strip(),
            "prenom": (r.get("prenom") or "").strip(),
            "adresse1": (r.get("adresse1") or "").strip(),
            "adresse2": (r.get("adresse2") or "").strip(),
            "cp": (r.get("cp") or "").strip(),
            "ville": (r.get("ville") or "").strip(),
            "tel": (r.get("tel") or "").strip(),
            "mobile": (r.get("gsm") or "").strip(),
            "mail": (r.get("mail") or "").strip(),
        }
    except Exception:
        return {}


def _contrat_info(id_contrat: int) -> dict:
    """Infos contrat SFR pour l'affichage (PG en lecture, lag tolere).
    NB : NumBS / InfoVenteSFR (memos lus via _memo_sfr) restent en HFSQL
    pour le concat read-modify-write au moment du save."""
    if not id_contrat:
        return {}
    adv_pg = get_pg_connection("adv")
    adv_hf = get_connection("adv")  # pour _memo_sfr (memos critiques)
    try:
        r = adv_pg.query_one(
            """SELECT id_contrat, id_client, id_produit, date_signature,
                date_rdv_tech, periode_rdv_tech, id_sfr_cluster, id_sfr_statut_rdv,
                id_etat_contrat, id_etat_sfr, type_vente
            FROM pgt_sfr_contrat WHERE id_contrat = ?""",
            (int(id_contrat),),
        )
    except Exception:
        return {}
    if not r:
        return {}
    out = {
        "id_client": _clean_id(_to_int(r.get("id_client"))),
        "id_produit": _to_int(r.get("id_produit")),
        "num_bs": _memo_sfr(adv_hf, id_contrat, "NumBS"),
        "info_vente_sfr": _memo_sfr(adv_hf, id_contrat, "InfoVenteSFR"),
        "date_signature": date_only_to_iso(r.get("date_signature")),
        "date_rdv_tech": date_only_to_iso(r.get("date_rdv_tech")),
        "periode_rdv": _to_int(r.get("periode_rdv_tech")),
        "id_cluster": _to_int(r.get("id_sfr_cluster")),
        "id_statut_rdv": _to_int(r.get("id_sfr_statut_rdv")),
        "id_etat_contrat": _to_int(r.get("id_etat_contrat")),
        "id_etat_sfr": _to_int(r.get("id_etat_sfr")),
        "type_vente": _to_int(r.get("type_vente")),
        "offre_lib": "",
        "cluster_lib": "",
        "etat_vendeur_lib": "",
    }
    if out["id_produit"]:
        try:
            p = adv_pg.query_one(
                "SELECT id_produit, lib_produit FROM pgt_sfr_produit "
                "WHERE id_produit = ?",
                (int(out["id_produit"]),),
            )
            out["offre_lib"] = (p.get("lib_produit") or "").strip() if p else ""
        except Exception:
            pass
    if out["id_cluster"]:
        try:
            cl = adv_pg.query_one(
                "SELECT id_sfr_cluster, nom_cluster FROM pgt_sfr_cluster "
                "WHERE id_sfr_cluster = ?",
                (int(out["id_cluster"]),),
            )
            out["cluster_lib"] = (cl.get("nom_cluster") or "").strip() if cl else ""
        except Exception:
            pass
    if out["id_etat_contrat"]:
        try:
            e = adv_pg.query_one(
                "SELECT id_etat, lib_etat FROM pgt_sfr_etat_contrat "
                "WHERE id_etat = ?",
                (int(out["id_etat_contrat"]),),
            )
            out["etat_vendeur_lib"] = (e.get("lib_etat") or "").strip() if e else ""
        except Exception:
            pass
    out["type_vente_lib"] = SFR_TYPE_VENTE_LABELS.get(out["type_vente"], "")
    out["periode_rdv_lib"] = PERIODE_RDV_LABELS.get(out["periode_rdv"], "")
    return out


def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_bo")
    r = db.query_one(
        """SELECT id_tk_liste, id_tk_retour_rdv_tech_fibre, id_contrat,
            id_fibre_statut_rdv
        FROM pgt_tk_retour_rdv_tech_fibre WHERE id_tk_liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_contrat = _clean_id(_to_int(r.get("id_contrat")))
    info_cplt = ""
    try:
        rm = db.query_one(
            "SELECT id_tk_liste, info_cplt FROM pgt_tk_retour_rdv_tech_fibre "
            "WHERE id_tk_liste = ?",
            (int(id_ticket),),
        )
        info_cplt = ((rm.get("info_cplt") if rm else "") or "").strip()
    except Exception:
        pass
    contrat = _contrat_info(id_contrat)
    client = _client_info(contrat.get("id_client", 0))
    return {
        "found": True,
        "id_retour": str(_clean_id(_to_int(r.get("id_tk_retour_rdv_tech_fibre")))),
        "id_contrat": str(id_contrat) if id_contrat else "",
        "num_bs": contrat.get("num_bs", ""),
        "id_statut_rdv_choisi": _to_int(r.get("id_fibre_statut_rdv"))
            or contrat.get("id_statut_rdv", 0),
        "info_cplt": info_cplt,
        "statuts_rdv": _statuts_rdv(),
        "client": client,
        "contrat": contrat,
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    if str(payload.get("action") or "valider") != "valider":
        return {"ok": False, "error": "Action non disponible"}
    now = _now_windev()
    id_statut = _to_int(payload.get("id_statut_rdv"))
    if not id_statut:
        return {"ok": False, "error": "Choisis un statut RDV"}
    info_cplt = str(payload.get("info_cplt") or "")
    new_date_rdv = payload.get("new_date_rdv")  # ISO ou "clear" pour vider

    bo_db = get_connection("ticket_bo")
    tk_db = get_connection("ticket")
    r = bo_db.query_one(
        "SELECT IDTK_Liste, IDcontrat FROM TK_RetourRdvTechFIBRE "
        "WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    if not r:
        return {"ok": False, "error": "Retour RDV introuvable"}
    id_contrat = _clean_id(_to_int(r.get("IDcontrat")))
    if not id_contrat:
        return {"ok": False, "error": "Contrat introuvable"}

    adv = get_connection("adv")
    lib_statut = ""
    try:
        s = adv.query_one(
            "SELECT IdSFR_StatutRDV, LibStatut FROM SFR_StatutRDV "
            "WHERE IdSFR_StatutRDV = ?",
            (int(id_statut),),
        )
        lib_statut = (s.get("LibStatut") or "").strip() if s else ""
    except Exception:
        pass

    # Append InfoVenteSFR
    existing = _memo_sfr(adv, id_contrat, "InfoVenteSFR")
    block = ""
    if existing:
        block += "\r\n-------------------\r\n"
    block += f"{_fr_now()} , RDV Tech statué en '{lib_statut}'"
    if info_cplt:
        block += "\r\nInfos données par le vendeur :\r\n" + info_cplt
    block += "\r\n-------------------"
    new_info_vente = (existing or "") + block

    try:
        adv.query(
            """UPDATE SFR_contrat SET
                IdSFR_StatutRDV = ?, InfoVenteSFR = ?,
                ModifDate = ?, ModifOP = ?, ModifELEM = 'new'
            WHERE IDcontrat = ?""",
            (
                int(id_statut), new_info_vente, now, int(user_id),
                int(id_contrat),
            ),
        )
    except Exception as e:
        return {"ok": False, "error": f"SFR_contrat : {e}"}

    # cas statut = 8 : mise à jour optionnelle de DateRDVTech
    if int(id_statut) == 8 and new_date_rdv is not None:
        s = str(new_date_rdv or "").strip()
        date_value = ""
        if s and s.lower() not in ("clear", "vide"):
            date_value = iso_to_date_only(s)
        try:
            adv.query(
                "UPDATE SFR_contrat SET DateRDVTech = ?, ModifDate = ? "
                "WHERE IDcontrat = ?",
                (date_value, now, int(id_contrat)),
            )
        except Exception:
            pass

    # Persistance TK_RetourRdvTechFIBRE (traçabilité)
    try:
        bo_db.query(
            """UPDATE TK_RetourRdvTechFIBRE SET
                IdFIBRE_StatutRDV = ?, InfoCplt = ?, ModifDate = ?,
                ModifOP = ?, ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (int(id_statut), info_cplt, now, int(user_id), int(id_ticket)),
        )
    except Exception:
        pass

    # Clôture ticket statut 4 + histo
    try:
        tk_db.query(
            """UPDATE TK_Liste SET
                Cloturée = 1, DateCloture = ?, IDTK_Statut = 4,
                modification = 1, opModif = ?, idModif = 0,
                TypeModif = 'TKSTATUT', ModifDate = ?, ModifOP = ?,
                ModifELEM = 'modif'
            WHERE IDTK_Liste = ?""",
            (now, int(user_id), now, int(user_id), int(id_ticket)),
        )
        ajout_histo_tk(int(id_ticket), 4, int(user_id))
    except Exception as e:
        return {"ok": False, "error": f"Clôture : {e}"}

    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True, "closed": True}
