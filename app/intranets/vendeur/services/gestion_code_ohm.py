"""Service Gestion Code OHM (intranet Vendeur).

Portage de Page_GestionCodeOhm WinDev :
  - Liste des demandes de code (partenaire OHM = 562949953421321) :
      * Onglet 1 (encours)   : id_tk_type_demande = 38, cloturee = FALSE
      * Onglet 2 (a desactiver) : id_tk_type_demande = 39, cloturee = FALSE
  - Voir contenu d'une demande (code, login, mdp + fichiers)
  - Enregistrer (modif code/login/mdp)
  - Rejet manque documents (passe le statut a 38 + envoi mail au BO ou RH)

Codes statut :
  1  : nouveau (blanc)
  35 : envoye (bleu)
  36 : recu/traite (vert)
  38 : rejet manque documents (violet)

TypeOri :
  'TK'    : origine ticket distributeur -> infos via pgt_tk_demande_dpae_distrib
  'DPAE'  : origine embauche interne    -> infos via pgt_salarie + pgt_salarie_coordonnees
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection

logger = logging.getLogger(__name__)

# ID partenaire OHM (constante WinDev 562949953421321)
ID_PART_OHM = 562949953421321
TYPE_DEMANDE_ENCOURS = 38
TYPE_DEMANDE_A_DESACTIVER = 39


def _str_id(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _iso_datetime(v: Any) -> str:
    if not v:
        return ""
    if isinstance(v, str):
        return v
    try:
        return v.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(v)


def liste_demandes(type_demande: int) -> list[dict]:
    """Liste des demandes de code (encours=38 ou desactivation=39).

    Retourne chaque demande enrichie de : nom, prenom, num_tel + libelle
    statut. Tri par statut ASC puis date crea ASC.
    """
    if type_demande not in (TYPE_DEMANDE_ENCOURS, TYPE_DEMANDE_A_DESACTIVER):
        return []
    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")

    try:
        rows = db_bo.query(
            """SELECT d.id_tk_liste, d.id_tk_demande_code_vendeur,
                      d.id_elem, d.type_ori, d.id_partenaire,
                      d.code, d.login, d.mdp,
                      d.modif_date, d.modif_elem
                 FROM ticket_bo.pgt_tk_demande_code_vendeur d
                WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
                  AND d.id_partenaire = ?""",
            (int(ID_PART_OHM),),
        ) or []
    except Exception:
        logger.exception("liste_demandes: fetch demande code vendeur")
        return []

    if not rows:
        return []

    # JOIN cote pgt_tk_liste (schema ticket)
    ids_liste = [int(r.get("id_tk_liste") or 0) for r in rows]
    ids_liste = [i for i in ids_liste if i]
    if not ids_liste:
        return []
    ids_sql = ",".join(str(i) for i in ids_liste)
    try:
        liste_rows = db_tk.query(
            f"""SELECT id_tk_liste, date_crea, id_tk_statut,
                      id_tk_type_demande, cloturee
                 FROM ticket.pgt_tk_liste
                WHERE id_tk_liste IN ({ids_sql})
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND id_tk_type_demande = ?
                  AND COALESCE(cloturee, FALSE) = FALSE""",
            (int(type_demande),),
        ) or []
    except Exception:
        logger.exception("liste_demandes: fetch tk_liste")
        return []
    liste_map = {int(r.get("id_tk_liste") or 0): r for r in liste_rows}
    if not liste_map:
        return []

    # Libelles statuts
    statuts_ids = {int(r.get("id_tk_statut") or 0)
                    for r in liste_rows} - {0}
    lib_statut_map: dict[int, str] = {}
    if statuts_ids:
        try:
            libs = db_tk.query(
                f"""SELECT id_tk_statut, lib_statut
                     FROM ticket.pgt_tk_statut
                    WHERE id_tk_statut IN ({','.join(str(i) for i in statuts_ids)})""",
            ) or []
            for l in libs:
                lib_statut_map[int(l.get("id_tk_statut") or 0)] = l.get("lib_statut") or ""
        except Exception:
            logger.exception("liste_demandes: fetch lib_statut")

    # Resolution nom/prenom/tel selon TypeOri
    ids_dpae_distrib = [int(r.get("id_elem") or 0) for r in rows
                        if (r.get("type_ori") or "").upper() == "TK"]
    ids_salarie = [int(r.get("id_elem") or 0) for r in rows
                   if (r.get("type_ori") or "").upper() != "TK"]
    ids_dpae_distrib = [i for i in ids_dpae_distrib if i]
    ids_salarie = [i for i in ids_salarie if i]

    dpae_map: dict[int, dict] = {}
    if ids_dpae_distrib:
        ids_dp = ",".join(str(i) for i in ids_dpae_distrib)
        try:
            drows = db_bo.query(
                f"""SELECT id_tk_liste, nom, prenom, gsm
                     FROM ticket_bo.pgt_tk_demande_dpae_distrib
                    WHERE id_tk_liste IN ({ids_dp})""",
            ) or []
            for d in drows:
                dpae_map[int(d.get("id_tk_liste") or 0)] = d
        except Exception:
            logger.exception("liste_demandes: fetch dpae_distrib")

    sal_map: dict[int, dict] = {}
    if ids_salarie:
        ids_s = ",".join(str(i) for i in ids_salarie)
        try:
            srows = db_rh.query(
                f"""SELECT s.id_salarie, s.nom, s.prenom, sc.tel_mob
                     FROM rh.pgt_salarie s
                     LEFT JOIN rh.pgt_salarie_coordonnees sc
                            ON sc.id_salarie = s.id_salarie
                    WHERE s.id_salarie IN ({ids_s})""",
            ) or []
            for s in srows:
                sal_map[int(s.get("id_salarie") or 0)] = s
        except Exception:
            logger.exception("liste_demandes: fetch salarie")

    out = []
    for r in rows:
        id_l = int(r.get("id_tk_liste") or 0)
        if id_l not in liste_map:
            continue  # exclu par le filtre type/cloture
        l = liste_map[id_l]
        type_ori = (r.get("type_ori") or "").upper()
        id_elem = int(r.get("id_elem") or 0)
        nom = prenom = num_tel = ""
        if type_ori == "TK":
            info = dpae_map.get(id_l, {})
            nom = (info.get("nom") or "").strip()
            prenom = _capitalise((info.get("prenom") or "").strip())
            num_tel = (info.get("gsm") or "").strip()
        else:
            info = sal_map.get(id_elem, {})
            nom = (info.get("nom") or "").strip()
            prenom = _capitalise((info.get("prenom") or "").strip())
            num_tel = (info.get("tel_mob") or "").strip()

        out.append({
            "IDTK_Liste": _str_id(id_l),
            "IDTK_DemandeCodeVendeur": _str_id(r.get("id_tk_demande_code_vendeur")),
            "IdElem": _str_id(id_elem) if id_elem else "",
            "TypeOri": type_ori,
            "IDPartenaire": _str_id(r.get("id_partenaire")),
            "Code": r.get("code") or "",
            "Login": r.get("login") or "",
            "MDP": r.get("mdp") or "",
            "DateCrea": _iso_datetime(l.get("date_crea")),
            "IDTKStatut": int(l.get("id_tk_statut") or 0),
            "LibStatut": lib_statut_map.get(int(l.get("id_tk_statut") or 0), ""),
            "Nom": nom,
            "Prenom": prenom,
            "NomPrenom": f"{nom} {prenom}".strip(),
            "NumTel": num_tel,
        })
    # Tri : statut ASC puis date crea ASC
    out.sort(key=lambda x: (x["IDTKStatut"], x["DateCrea"]))
    return out


def fichiers_demande(id_tk_liste: int) -> list[dict]:
    """Retourne les fichiers d'une demande. Chaque fichier a :
    NomFichier, LienFichier (chemin relatif), Url (URL publique construite
    depuis DOCS_URL, pattern DocOmaya/PhotoDPAE/{lien_fichier}).
    """
    if not id_tk_liste:
        return []
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_demandecodevendeur_fichier, nom_fichier, lien_fichier
                 FROM ticket_bo.pgt_tk_demandecodevendeur_fichier
                WHERE id_tk_liste = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
            (int(id_tk_liste),),
        ) or []
    except Exception:
        logger.exception("fichiers_demande id=%s", id_tk_liste)
        return []
    base = (os.environ.get("DOCS_URL", "") or "").rstrip("/")
    out = []
    for r in rows:
        lien = (r.get("lien_fichier") or "").strip()
        url = f"{base}/PhotoDPAE/{lien}" if base and lien else ""
        out.append({
            "IDFichier": _str_id(r.get("id_tk_demandecodevendeur_fichier")),
            "NomFichier": r.get("nom_fichier") or "",
            "LienFichier": lien,
            "Url": url,
        })
    return out


def enregistrer_modif(id_tk_liste: int, code: str, login: str,
                       mdp: str, user_id: int) -> bool:
    """Update code/login/mdp sur pgt_tk_demande_code_vendeur (equivalent
    ÉcranVersFichier + HModifie du WinDev)."""
    if not id_tk_liste:
        return False
    db = get_pg_connection("ticket_bo")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket_bo.pgt_tk_demande_code_vendeur
                  SET code = ?, login = ?, mdp = ?,
                      modif_date = ?, modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (code or "", login or "", mdp or "",
             now, int(user_id), int(id_tk_liste)),
        )
        return True
    except Exception:
        logger.exception("enregistrer_modif id=%s", id_tk_liste)
        return False


def rejet_manque_document(id_tk_liste: int, user_id: int) -> bool:
    """Passe le statut de la demande a 38 (Rejet - Manque Documents).

    TODO(mail) : envoi mail au BO (type_ori='TK') ou RH (autre) avec le
    template WinDev. En attendant : mise a jour statut uniquement.
    """
    if not id_tk_liste:
        return False
    db = get_pg_connection("ticket")
    now = datetime.now()
    try:
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = 38, modif_date = ?, modif_op = ?,
                      modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (now, int(user_id), int(id_tk_liste)),
        )
        return True
    except Exception:
        logger.exception("rejet_manque_document id=%s", id_tk_liste)
        return False
