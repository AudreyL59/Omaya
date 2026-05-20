"""FI_RDVTech (type 19 — Retour RDV Technicien FIBRE).

Transposition de la fenêtre interne WinDev FI_RDVTech.

Affiche INFOS CLIENT + INFOS CONTRAT (lecture, depuis client/SFR_contrat/
SFR_produit/SFR_Cluster — base adv) à partir de l'IDcontrat stocké
dans TK_RetourRdvTechFIBRE (base ticket).

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
        db = get_connection("adv")
        return [
            {
                "id": _to_int(r.get("IdSFR_StatutRDV")),
                "lib": (r.get("LibStatut") or "").strip(),
            }
            for r in db.query(
                "SELECT IdSFR_StatutRDV, LibStatut FROM SFR_StatutRDV "
                "ORDER BY LibStatut"
            )
        ]
    except Exception:
        return []


def _memo_sfr(db, id_contrat: int, field: str) -> str:
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
        r = get_connection("adv").query_one(
            "SELECT IDclient, NOM, PRENOM, ADRESSE1, ADRESSE2, CP, VILLE, "
            "TEL, GSM, MAIL FROM client WHERE IDclient = ?",
            (int(id_client),),
        )
        if not r:
            return {}
        return {
            "nom": (r.get("NOM") or "").strip(),
            "prenom": (r.get("PRENOM") or "").strip(),
            "adresse1": (r.get("ADRESSE1") or "").strip(),
            "adresse2": (r.get("ADRESSE2") or "").strip(),
            "cp": (r.get("CP") or "").strip(),
            "ville": (r.get("VILLE") or "").strip(),
            "tel": (r.get("TEL") or "").strip(),
            "mobile": (r.get("GSM") or "").strip(),
            "mail": (r.get("MAIL") or "").strip(),
        }
    except Exception:
        return {}


def _contrat_info(id_contrat: int) -> dict:
    if not id_contrat:
        return {}
    adv = get_connection("adv")
    try:
        r = adv.query_one(
            """SELECT IDcontrat, IDclient, IDproduit, DateSignature,
                DateRDVTech, PériodeRDVTech, IDSFR_Cluster, IdSFR_StatutRDV,
                IDetatContrat, IDetatSFR, TypeVente
            FROM SFR_contrat WHERE IDcontrat = ?""",
            (int(id_contrat),),
        )
    except Exception:
        return {}
    if not r:
        return {}
    out = {
        "id_client": _clean_id(_to_int(r.get("IDclient"))),
        "id_produit": _to_int(r.get("IDproduit")),
        "num_bs": _memo_sfr(adv, id_contrat, "NumBS"),
        "info_vente_sfr": _memo_sfr(adv, id_contrat, "InfoVenteSFR"),
        "date_signature": date_only_to_iso(r.get("DateSignature")),
        "date_rdv_tech": date_only_to_iso(r.get("DateRDVTech")),
        "periode_rdv": _to_int(r.get("PériodeRDVTech")),
        "id_cluster": _to_int(r.get("IDSFR_Cluster")),
        "id_statut_rdv": _to_int(r.get("IdSFR_StatutRDV")),
        "id_etat_contrat": _to_int(r.get("IDetatContrat")),
        "id_etat_sfr": _to_int(r.get("IDetatSFR")),
        "type_vente": _to_int(r.get("TypeVente")),
        "offre_lib": "",
        "cluster_lib": "",
        "etat_vendeur_lib": "",
    }
    if out["id_produit"]:
        try:
            p = adv.query_one(
                "SELECT IDproduit, Lib_produit FROM SFR_produit "
                "WHERE IDproduit = ?",
                (int(out["id_produit"]),),
            )
            out["offre_lib"] = (p.get("Lib_produit") or "").strip() if p else ""
        except Exception:
            pass
    if out["id_cluster"]:
        try:
            cl = adv.query_one(
                "SELECT IDSFR_Cluster, NomCluster FROM SFR_Cluster "
                "WHERE IDSFR_Cluster = ?",
                (int(out["id_cluster"]),),
            )
            out["cluster_lib"] = (cl.get("NomCluster") or "").strip() if cl else ""
        except Exception:
            pass
    if out["id_etat_contrat"]:
        try:
            e = adv.query_one(
                "SELECT IDetat, Lib_Etat FROM SFR_etatContrat "
                "WHERE IDetat = ?",
                (int(out["id_etat_contrat"]),),
            )
            out["etat_vendeur_lib"] = (e.get("Lib_Etat") or "").strip() if e else ""
        except Exception:
            pass
    out["type_vente_lib"] = SFR_TYPE_VENTE_LABELS.get(out["type_vente"], "")
    out["periode_rdv_lib"] = PERIODE_RDV_LABELS.get(out["periode_rdv"], "")
    return out


def load(id_ticket: int) -> dict:
    db = get_connection("ticket")
    r = db.query_one(
        """SELECT IDTK_Liste, IDTK_RetourRdvTechFIBRE, IDcontrat,
            IdFIBRE_StatutRDV
        FROM TK_RetourRdvTechFIBRE WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_contrat = _clean_id(_to_int(r.get("IDcontrat")))
    info_cplt = ""
    try:
        rm = db.query_one(
            "SELECT IDTK_Liste, InfoCplt FROM TK_RetourRdvTechFIBRE "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        info_cplt = ((rm.get("InfoCplt") if rm else "") or "").strip()
    except Exception:
        pass
    contrat = _contrat_info(id_contrat)
    client = _client_info(contrat.get("id_client", 0))
    return {
        "found": True,
        "id_retour": str(_clean_id(_to_int(r.get("IDTK_RetourRdvTechFIBRE")))),
        "id_contrat": str(id_contrat) if id_contrat else "",
        "num_bs": contrat.get("num_bs", ""),
        "id_statut_rdv_choisi": _to_int(r.get("IdFIBRE_StatutRDV"))
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

    tk_db = get_connection("ticket")
    r = tk_db.query_one(
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
        tk_db.query(
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
