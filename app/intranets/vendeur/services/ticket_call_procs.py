"""
Bibliotheque des procs Ticket Call (Energie + Fibre) portees en PG.

Chaque proc remplace un webservice WinDev (WebRest_Omayapp) au fur et
a mesure que le user fournit la spec. Cf.
`docs/tickets_call_screens_analysis.md` pour la liste complete des 27
endpoints proxy actuels.

Traduction depuis WinDev/WLangage :
- `HExécuteRequête + HLitPremier/HLitSuivant` -> `db.query(...)`.
- `Encode(bytea, encodeBASE64)` -> `base64.b64encode(bytea).decode()`.
- `RVB(r, v, b)` -> `r + v*256 + b*65536` (entier compose WinDev).
- Structures WLangage (`St_Part`, `ST_Ville`, etc.) -> dict Python
  avec les memes cles.
- La verification UUID token (`vérifUUID(idToken)`) est retiree :
  l'authentification est deja faite au niveau du router Vendeur via
  `require_intranet('vendeur')` + les droits (TkCALL / BS_SFR).

Cf. `d:/Claude/WinDev/WebServices/` pour les .txt source.
"""
from __future__ import annotations

import base64
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from app.core.config import WEBREST_BASE_URL
from app.core.database.pg import get_pg_connection


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Types de demande (cf. WinDev TK_TypeDemande)
# --------------------------------------------------------------------

IDTK_TYPE_DEMANDE_CALL_ENERGIE = 22
IDTK_TYPE_DEMANDE_CALL_FIBRE = 20

# Statut "en cours de saisie panier" (avant validation client par SMS)
IDTK_STATUT_EN_COURS = 28

# Statut "a traiter" (le panier vient d'etre valide par le client)
IDTK_STATUT_A_TRAITER = 1


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _rvb(r: int | None, v: int | None, b: int | None) -> int:
    """Reproduit RVB(r, v, b) de WinDev : entier compose (couleur 0..16M)."""
    return int(r or 0) + (int(v or 0) << 8) + (int(b or 0) << 16)


def _b64(raw) -> str:
    """Encode bytea en base64 (retourne '' si vide/None)."""
    if not raw:
        return ""
    if isinstance(raw, memoryview):
        raw = bytes(raw)
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    return base64.b64encode(raw).decode("ascii")


def _bool(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ("true", "1", "vrai", "t", "y", "yes")


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _now_wd() -> str:
    """DateHeureSys() de WinDev : 'YYYYMMDDHHMMSSMMM'."""
    return datetime.now().strftime("%Y%m%d%H%M%S000")


def _new_id_wd() -> int:
    """idEntierDateHeureSys() de WinDev : entier 8 octets base sur
    la date+heure du systeme. On produit 'YYYYMMDDHHMMSSMMM' comme int.
    """
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _doc_exists(id_ticket: int, kind: str) -> bool:
    """Test HEAD HTTP sur rest.omaya.fr/DocOmaya/{id}_{kind}.png ou .pdf.

    Remplace la verification `fFichierExiste(cheminParDefaut+...)` qui
    testait le FS local du serveur WinDev. HEAD HTTP est robuste et
    fonctionne quel que soit le serveur d'execution.
    """
    for ext in ("png", "pdf"):
        url = f"{WEBREST_BASE_URL.rstrip('/')}/DocOmaya/{id_ticket}_{kind}.{ext}"
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if 200 <= resp.status < 300:
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (200, 206):
                return True
        except Exception:
            pass
    return False


# Mapping table produits par prefixe partenaire (part_produit dynamique WinDev)
_TABLE_PRODUIT_PAR_PART: dict[str, str] = {
    "OEN": "adv.pgt_oen_produit",
    "ENI": "adv.pgt_eni_produit",
    "STR": "adv.pgt_str_produit",
    "VAL": "adv.pgt_val_produit",
    "PRO": "adv.pgt_pro_produit",
}


def _tab_lib_partenaires() -> dict[str, str]:
    """Reproduit TabLibPartenaires WinDev : {prefixe: lib_partenaire}."""
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT prefixe_bdd, lib_partenaire
                 FROM adv.pgt_partenaire""",
        ) or []
    except Exception:
        return {}
    return {
        (r.get("prefixe_bdd") or "").strip(): (r.get("lib_partenaire") or "").strip()
        for r in rows
        if (r.get("prefixe_bdd") or "").strip()
    }


# --------------------------------------------------------------------
# ENERGIE
# --------------------------------------------------------------------

def list_part_call() -> list[dict]:
    """WS `POST /PartCall` -> liste des partenaires actifs pour Call.

    Portage WinDev/WLangage source :
      SELECT * FROM Partenaire
       WHERE IsActif = 1 AND TkCall = 1
       ORDER BY Lib_Partenaire ASC

    Retour : liste de St_Part {Nom, Bdd, Logo (base64), Couleur (RVB)}.
    """
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            """SELECT lib_partenaire, prefixe_bdd, logo,
                      couleur_r, couleur_v, couleur_b
                 FROM adv.pgt_partenaire
                WHERE COALESCE(is_actif, FALSE) = TRUE
                  AND COALESCE(tk_call, FALSE) = TRUE
                ORDER BY lib_partenaire ASC""",
        ) or []
    except Exception:
        logger.exception("list_part_call")
        return []
    return [
        {
            "Nom": (r.get("lib_partenaire") or "").strip(),
            "Bdd": (r.get("prefixe_bdd") or "").strip(),
            "Logo": _b64(r.get("logo")),
            "Couleur": _rvb(r.get("couleur_r"), r.get("couleur_v"),
                             r.get("couleur_b")),
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/{idVend}
# --------------------------------------------------------------------

def liste_clients_non_finalises(id_vend: int) -> list[dict]:
    """WS `POST /Call/ClientsNonFinalises/{idVend}`.

    Portage WinDev :
      SELECT ... FROM TK_Liste, TK_Call
       WHERE TypeDemande=22 AND Statut=28 AND !cloturee AND !suppr
         AND TK_Call.IDSalarie = idVend
         AND TK_Call.IDTK_Liste = TK_Liste.IDTK_Liste

    PhotoOK / KbisOK : verification HTTP HEAD sur DocOmaya (remplace
    le test filesystem WinDev, cf. _doc_exists).

    Retour : liste de STTKCall (champs client + PhotoOK + KbisOK).
    """
    db_tk = get_pg_connection("ticket")
    db_bo = get_pg_connection("ticket_bo")
    try:
        rows_liste = db_tk.query(
            """SELECT id_tk_liste FROM ticket.pgt_tk_liste
                WHERE id_tk_type_demande = ?
                  AND id_tk_statut = ?
                  AND COALESCE(cloturee, FALSE) = FALSE
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')""",
            (IDTK_TYPE_DEMANDE_CALL_ENERGIE, IDTK_STATUT_EN_COURS),
        ) or []
    except Exception:
        logger.exception("liste_clients_non_finalises: pgt_tk_liste")
        return []
    if not rows_liste:
        return []
    ids_sql = ",".join(str(_to_int(r.get("id_tk_liste"))) for r in rows_liste)
    try:
        rows = db_bo.query(
            f"""SELECT id_tk_call, id_tk_liste, id_salarie,
                       civilite_client, nom_client, nom_marital_client,
                       prenom_client, date_naiss, dep_naiss,
                       adresse1, adresse2, cp, ville, adr_mail,
                       mobile1, code_valid, type_logement,
                       client_pro, client_rs, client_siret
                  FROM ticket_bo.pgt_tk_call
                 WHERE id_tk_liste IN ({ids_sql})
                   AND id_salarie = ?""",
            (int(id_vend),),
        ) or []
    except Exception:
        logger.exception("liste_clients_non_finalises: pgt_tk_call")
        return []
    out = []
    for r in rows:
        id_tk = _to_int(r.get("id_tk_liste"))
        out.append({
            "IDTK_Liste": id_tk,
            "CiviliteClient": _to_int(r.get("civilite_client")),
            "NomClient": r.get("nom_client") or "",
            "NomMaritalClient": r.get("nom_marital_client") or "",
            "PrenomClient": r.get("prenom_client") or "",
            "DATENAISS": str(r.get("date_naiss") or ""),
            "DEPNAISS": _to_int(r.get("dep_naiss")),
            "ADRESSE1": r.get("adresse1") or "",
            "ADRESSE2": r.get("adresse2") or "",
            "CP": r.get("cp") or "",
            "VILLE": r.get("ville") or "",
            "adrMail": r.get("adr_mail") or "",
            "Mobile1": r.get("mobile1") or "",
            "TypeLogement": _to_int(r.get("type_logement")),
            "Code": r.get("code_valid") or "",
            "PhotoOK": _doc_exists(id_tk, "PieceIdentite"),
            "KbisOK": _doc_exists(id_tk, "KBIS"),
            "ClientPro": _bool(r.get("client_pro")),
            "ClientRS": r.get("client_rs") or "",
            "ClientSiret": r.get("client_siret") or "",
        })
    return out


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/{idTicket}
# --------------------------------------------------------------------

def contenu_panier_call(id_ticket: int) -> list[dict]:
    """WS `POST /Call/ClientsNonFinalises/Panier/{idTicket}`.

    Portage :
      SELECT ... FROM TK_Call_Panier WHERE IDTK_Liste = ?
      -> resolution lib_offre par partenaire (SELECT dyn sur part_produit).

    OHM : lib hardcode 'Pompe a chaleur'.
    """
    db_bo = get_pg_connection("ticket_bo")
    db_adv = get_pg_connection("adv")
    lib_partenaires = _tab_lib_partenaires()
    try:
        rows = db_bo.query(
            """SELECT id_tk_call_panier, id_tk_call, id_tk_liste,
                      partenaire, id_produit, num_bs,
                      opt_energie_verte_elec, opt_reforestation,
                      opt_energie_verte_gaz, opt_mail, opt_mandat,
                      format_numerique
                 FROM ticket_bo.pgt_tk_call_panier
                WHERE id_tk_liste = ?""",
            (int(id_ticket),),
        ) or []
    except Exception:
        logger.exception("contenu_panier_call")
        return []
    out = []
    for r in rows:
        part = (r.get("partenaire") or "").strip().upper()
        id_prod = _to_int(r.get("id_produit"))
        lib_offre = ""
        if part == "OHM":
            lib_offre = "Pompe à chaleur"
        elif part in _TABLE_PRODUIT_PAR_PART and id_prod:
            table = _TABLE_PRODUIT_PAR_PART[part]
            try:
                p = db_adv.query_one(
                    f"SELECT lib_produit FROM {table} WHERE id_produit = ?",
                    (id_prod,),
                )
                lib_offre = ((p or {}).get("lib_produit") or "").strip()
            except Exception:
                logger.exception("lib_produit lookup part=%s", part)
        out.append({
            "IDtk_Call_Panier": _to_int(r.get("id_tk_call_panier")),
            "Part": lib_partenaires.get(part, part),
            "IDProduit": id_prod,
            "LibOffre": lib_offre,
            "NumBS": r.get("num_bs") or "",
        })
    return out


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Suppr/{idVend}
# --------------------------------------------------------------------

def supprimer_ticket_call(id_tk_liste: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Suppr/{idVend}`.

    NOTE : le .txt Suppr fourni est vide. Portage deduit : suppression
    logique du ticket via modif_elem = 'suppr' (pattern standard WinDev
    plutot que DELETE physique). A confirmer avec le user si le code
    WinDev est different.
    """
    db_tk = get_pg_connection("ticket")
    now = _now_wd()
    try:
        db_tk.query(
            """UPDATE ticket.pgt_tk_liste
                  SET modif_elem = 'suppr', modif_date = ?
                WHERE id_tk_liste = ?""",
            (now, int(id_tk_liste)),
        )
        return {"nIdDemande": id_tk_liste}
    except Exception as e:
        logger.exception("supprimer_ticket_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /Call/ProduitActifs/{part}
# --------------------------------------------------------------------

def liste_produit_actif_by_part(part: str) -> list[dict]:
    """WS `POST /Call/ProduitActifs/{part}`.

    Portage : SELECT * FROM {part}_produit
      WHERE modif_elem <> 'suppr' AND pro_actif = 1

    Retour : liste de STProduitSte {IDProduit, LibProd}.
    """
    part_up = (part or "").strip().upper()
    table = _TABLE_PRODUIT_PAR_PART.get(part_up)
    if not table:
        return []
    db = get_pg_connection("adv")
    try:
        rows = db.query(
            f"""SELECT id_produit, lib_produit FROM {table}
                 WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                   AND COALESCE(pro_actif, 0) = 1""",
        ) or []
    except Exception:
        logger.exception("liste_produit_actif_by_part part=%s", part_up)
        return []
    return [
        {
            "IDProduit": _to_int(r.get("id_produit")),
            "LibProd": r.get("lib_produit") or "",
        }
        for r in rows
    ]


# --------------------------------------------------------------------
# WS : GET /Call/OHM/ListeTypeInstall
# --------------------------------------------------------------------

def ohm_liste_type_install() -> list[dict]:
    """WS `GET /Call/OHM/ListeTypeInstall`.

    Liste HARDCODEE cote WinDev (4 types) : chaudiere gaz, chauffage
    elec, poele granule/bois, chaudiere fioul.
    """
    types = [
        (1, "Chaudière à gaz"),
        (2, "Chauffage électrique"),
        (3, "Poêle granule/bois"),
        (4, "Chaudière fioul"),
    ]
    return [
        {
            "idLead": 0,
            "TypeInstall": type_id,
            "LibTypeInstall": lib,
            "Chauffage": False,
            "EauChaude": False,
        }
        for type_id, lib in types
    ]


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/Produit/Ajout
# --------------------------------------------------------------------

def ajouter_produit_panier_call(payload: dict) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Panier/Produit/Ajout`.

    Portage : INSERT dans pgt_tk_call_panier (+ pgt_ohm_leads_type_install
    si OHM — table absente du schema PG interne, insertion skip si
    absente).

    NOTE : la colonne opt_maintenance est absente du schema PG interne
    (existe cote HFSQL OVH) — la valeur du payload est ignoree
    silencieusement (voir aussi tickets_call_actions_energie.py).
    """
    db = get_pg_connection("ticket_bo")
    new_id = _new_id_wd()
    now = _now_wd()
    id_tk_liste = _to_int(payload.get("IDTK_Liste"))
    num_bs = (payload.get("NumBS") or "").strip()
    try:
        db.query(
            """INSERT INTO ticket_bo.pgt_tk_call_panier (
                  id_tk_call_panier, id_tk_call, id_tk_liste,
                  partenaire, id_produit, num_bs, num_date_saisie,
                  opt_energie_verte_elec, opt_reforestation,
                  opt_energie_verte_gaz, opt_mail, opt_e_communication,
                  opt_e_facture, opt_optin_commercial,
                  opt_consent_consult_distri, opt_accept_com_parte,
                  opt_mandat, format_numerique,
                  motif_annulation, statut_prod,
                  nb_pers_foyer, sit_pro, rfr, date_entree,
                  annee_construction, annee_installation, supercie,
                  autre_install, autre_installation,
                  chauffage_appoint, isolation_combles,
                  montant_mens_elec, montant_mens_gaz, observations,
                  modif_date, modif_elem
              ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, 'new'
              )""",
            (
                new_id, id_tk_liste, id_tk_liste,
                payload.get("Part") or "",
                _to_int(payload.get("IDProduit")),
                num_bs,
                now if num_bs else None,
                _bool(payload.get("OPT_EnergieVerteElec")),
                _bool(payload.get("OPT_Reforestation")),
                _bool(payload.get("OPT_EnergieVerteGaz")),
                _bool(payload.get("OPT_Mail")),
                _bool(payload.get("OPT_eCommunication")),
                _bool(payload.get("OPT_eFacture")),
                _bool(payload.get("OPT_optinCommercial")),
                _bool(payload.get("OPT_ConsentDistri")),
                _bool(payload.get("OPT_CialPart")),
                _bool(payload.get("Opt_Mandat")),
                _bool(payload.get("FormatNumerique")),
                "", 0,
                _to_int(payload.get("NBPersFoyer")),
                payload.get("SitPro") or "",
                _to_int(payload.get("RFR")),
                payload.get("DateEntree") or None,
                _to_int(payload.get("AnneeConstruction")),
                _to_int(payload.get("AnneeInstallation")),
                _to_int(payload.get("Supercie")),   # typo preservee
                _bool(payload.get("AutreInstall")),
                payload.get("AutreInstallation") or "",
                _bool(payload.get("ChauffageAppoint")),
                _bool(payload.get("IsolationCombles")),
                _to_int(payload.get("MontantMensELEC")),
                _to_int(payload.get("MontantMensGAZ")),
                payload.get("Observations") or "",
                now,
            ),
        )
        # OHM : insertion dans OHM_LeadsTypeIntall skipppee (table
        # absente du schema PG interne pour l'instant).
        return {"nIdDemande": new_id}
    except Exception as e:
        logger.exception("ajouter_produit_panier_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Panier/Produit/Suppr
# --------------------------------------------------------------------

def supprimer_produit_panier_call(id_tk_call_panier: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Panier/Produit/Suppr`.

    Portage : DELETE physique (cf. WinDev HSupprime).
    """
    db = get_pg_connection("ticket_bo")
    try:
        db.query(
            """DELETE FROM ticket_bo.pgt_tk_call_panier
                WHERE id_tk_call_panier = ?""",
            (int(id_tk_call_panier),),
        )
        return {"nIdDemande": 0}
    except Exception as e:
        logger.exception("supprimer_produit_panier_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/EnvoiLien/{code}
# --------------------------------------------------------------------

def envoi_lien_client_call(id_tk_liste: int, code: str) -> dict:
    """WS `POST /Call/ClientsNonFinalises/EnvoiLien/{code}`.

    Portage :
      1. UPDATE TK_Call.CodeValid = code
      2. SELECT Mobile1, adrMail, NomClient, PrenomClient
      3. Envoi SMS avec lien https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB
         /FR/Page-ConsentClient.awp?P1=ENI{IDTK_Liste}
      4. Envoi mail HTML avec bouton vers le meme lien

    Utilise app.shared.notifications.sms + envoi mail helper.
    """
    db = get_pg_connection("ticket_bo")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_call
                  SET code_valid = ?, modif_date = ?
                WHERE id_tk_liste = ?""",
            (str(code), now, int(id_tk_liste)),
        )
        r = db.query_one(
            """SELECT mobile1, adr_mail, nom_client, prenom_client
                 FROM ticket_bo.pgt_tk_call WHERE id_tk_liste = ?""",
            (int(id_tk_liste),),
        )
    except Exception as e:
        logger.exception("envoi_lien_client_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}
    if not r:
        return {"nIdDemande": 0, "sInfoData": "Ticket introuvable"}
    lien = (
        f"https://groupe-exo.omaya.fr/PAGESEXTERNES_WEB/FR/"
        f"Page-ConsentClient.awp?P1=ENI{id_tk_liste}"
    )
    mobile = (r.get("mobile1") or "").strip()
    mail = (r.get("adr_mail") or "").strip()
    nom = r.get("nom_client") or ""
    prenom = r.get("prenom_client") or ""
    if mobile:
        try:
            from app.shared.notifications.sms import envoi_sms
            texte = (
                "Bonjour,\n"
                "Veuillez cliquer sur le lien suivant pour obtenir "
                f"le code de validation.\n{lien}"
            )
            envoi_sms(texte, mobile, emetteur="Code-Verify")
        except Exception:
            logger.exception("envoi_sms")
    # Envoi mail HTML
    try:
        _envoyer_mail_code_validation(mail, nom, prenom, lien)
    except Exception:
        logger.exception("_envoyer_mail_code_validation")
    return {"nIdDemande": id_tk_liste}


def _envoyer_mail_code_validation(mail_dest: str, nom: str,
                                    prenom: str, lien: str) -> None:
    """Envoi mail HTML avec bouton 'Cliquez ici pour obtenir le code'.

    Fallback destinataire : intranet@omaya.fr si mail_dest invalide.
    """
    from app.shared.notifications.mail import envoi_mail
    prenom_cap = prenom.capitalize() if prenom else ""
    bouton = (
        f'<table width="250px" border="0" cellspacing="0" cellpadding="0" '
        f'style="border-radius:10px; padding:15px 40px; background-color:#202021;">'
        f'<tr><td bgcolor="#202021" style="padding:15px 40px;">'
        f'<p style="margin:0; font-family:Arial; font-size:12px; text-align:center; color:#FFF; letter-spacing:4px;">'
        f'<a href="{lien}" target="_blank" style="color:#FFF; text-decoration:none;">'
        f'Cliquez ici pour obtenir le code</a>'
        f'</p></td></tr></table>'
    )
    html = (
        f"<font face='arial' style='font-size:10pt;'>"
        f"Bonjour {prenom_cap} {nom},<br/>"
        f"<p>Veuillez cliquer sur ce bouton pour obtenir le code de validation.</p>"
        f"{bouton}"
        f"<p>Cordialement.</p><br/>"
        f"<b>Le Service Validation</b><br/>"
        f"<i>Ceci est un mail automatique, ne pas y répondre.</i></font>"
    )
    dest = mail_dest.strip() if mail_dest and "@" in mail_dest else "intranet@omaya.fr"
    cci = ["intranet@omaya.fr", "bo@exosphere.fr"] if dest != "intranet@omaya.fr" else []
    envoi_mail(
        sujet="Code de validation",
        html=html,
        destinataires=[dest],
        cci=cci,
        expediteur="intranet@omaya.fr",
    )


# --------------------------------------------------------------------
# WS : POST /Call/ClientsNonFinalises/Validation/{idVend}
# --------------------------------------------------------------------

def validation_tk_call(id_tk_liste: int, id_vend: int) -> dict:
    """WS `POST /Call/ClientsNonFinalises/Validation/{idVend}`.

    Portage :
      UPDATE TK_Liste SET IDTK_Statut = 1, opModif = idVend,
             ModifDate = now, Datecrea = now
       WHERE IDTK_Liste = ?
    """
    db = get_pg_connection("ticket")
    now = _now_wd()
    try:
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = ?, op_modif = ?,
                      modif_date = ?, date_crea = ?
                WHERE id_tk_liste = ?""",
            (IDTK_STATUT_A_TRAITER, int(id_vend),
             datetime.now(), datetime.now(), int(id_tk_liste)),
        )
        return {"nIdDemande": id_tk_liste}
    except Exception as e:
        logger.exception("validation_tk_call")
        return {"nIdDemande": 0, "sInfoData": str(e)}


# --------------------------------------------------------------------
# WS : GET /Call/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}
# --------------------------------------------------------------------

def verif_photo(id_tk_liste: int, nom_photo: str) -> dict:
    """WS `GET /Call/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}`.

    Retourne {nIdDemande: id_ticket} si le fichier {id}_{type}.png ou
    .pdf existe sur DocOmaya (HEAD HTTP, cf. _doc_exists), sinon
    {nIdDemande: 0}.
    """
    exists = _doc_exists(int(id_tk_liste), nom_photo)
    return {"nIdDemande": id_tk_liste if exists else 0}
