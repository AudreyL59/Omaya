"""
Service Fen_FicheVehicule Plan 2 (Conducteurs).

Liste des attributions (vehicule_conducteur) + details pour edition +
liste docs Ulease edites lies a une attribution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.intranets.adm.services import vehicule_documents as doc_svc
from app.core.utils.sentinel_dates import is_sentinel


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso_date(v: Any) -> str:
    if v is None or v == "" or is_sentinel(v):
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 and s[4] == "-" else s


def _iso_time(v: Any) -> str:
    if v is None or v == "":
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%H:%M")
    s = str(v)
    return s[:5] if len(s) >= 5 else s


def list_conducteurs(id_vehicule: int) -> list[dict]:
    """Equivalent ReqListeCondByVehicule. Tri perception desc."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT vc.id_vehicule_pc, vc.perception_date, vc.perception_heure,
                  vc.restitution_date, vc.restitution_heure,
                  vc.id_conducteur, vc.id_ste,
                  c.nom_conducteur, c.prenom_conducteur, c.nom_marital,
                  c.id_salarie
             FROM ulease.pgt_vehicule_conducteur vc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
            WHERE vc.id_vehicule = ?
              AND (vc.modif_elem IS NULL OR vc.modif_elem NOT LIKE '%suppr%')
         ORDER BY vc.perception_date DESC, vc.perception_heure DESC""",
        (int(id_vehicule),),
    ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom_conducteur"))
        prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
        marital = _str(r.get("nom_marital"))
        nom_complet = f"{nom} {marital}".strip() if marital else nom
        out.append({
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "id_conducteur": str(_int(r.get("id_conducteur"))),
            "id_salarie": str(_int(r.get("id_salarie"))),
            "id_ste": str(_int(r.get("id_ste"))),
            "perception_date": _iso_date(r.get("perception_date")),
            "perception_heure": _iso_time(r.get("perception_heure")),
            "restitution_date": _iso_date(r.get("restitution_date")),
            "restitution_heure": _iso_time(r.get("restitution_heure")),
            "nom_complet": nom_complet,
            "prenom": prenom,
            "lib_conducteur": f"{nom_complet} {prenom}".strip(),
        })
    return out


def get_attribution(id_vehicule_pc: int) -> dict | None:
    """FichierVersEcran : toutes les colonnes pour la zone d'edition."""
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_vehicule_pc, id_vehicule, id_conducteur, id_ste,
                  perception_date, perception_heure,
                  restitution_date, restitution_heure,
                  conv_dispo, fiche_enlev, permis_cnd, info_vehicule,
                  k_mdepart, cg_conducteur, cg_originale_dossier,
                  c_vet_vignette, fiche_rest, temporaire
             FROM ulease.pgt_vehicule_conducteur
            WHERE id_vehicule_pc = ? LIMIT 1""",
        (int(id_vehicule_pc),),
    )
    if not r:
        return None
    return {
        "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
        "id_vehicule": str(_int(r.get("id_vehicule"))),
        "id_conducteur": str(_int(r.get("id_conducteur"))),
        "id_ste": str(_int(r.get("id_ste"))),
        "perception_date": _iso_date(r.get("perception_date")),
        "perception_heure": _iso_time(r.get("perception_heure")),
        "restitution_date": _iso_date(r.get("restitution_date")),
        "restitution_heure": _iso_time(r.get("restitution_heure")),
        "conv_dispo": bool(r.get("conv_dispo")),
        "fiche_enlev": bool(r.get("fiche_enlev")),
        "permis_cnd": bool(r.get("permis_cnd")),
        "info_vehicule": _str(r.get("info_vehicule")),
        "k_mdepart": _int(r.get("k_mdepart")),
        "cg_conducteur": bool(r.get("cg_conducteur")),
        "cg_originale_dossier": bool(r.get("cg_originale_dossier")),
        "c_vet_vignette": bool(r.get("c_vet_vignette")),
        "fiche_rest": bool(r.get("fiche_rest")),
        "temporaire": bool(r.get("temporaire")),
    }


def update_attribution(id_vehicule_pc: int, payload: dict, op_id: int) -> dict:
    """Btn Enregistrer : EcranVersFichier + HModifie vehicule_Conducteur.
    Met a jour uniquement les champs Plan 2 (les dates/heures de
    perception/restitution viennent normalement de Fen_Attribution)."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_conducteur
              SET id_ste = ?,
                  temporaire = ?,
                  conv_dispo = ?,
                  cg_originale_dossier = ?,
                  cg_conducteur = ?,
                  fiche_rest = ?,
                  c_vet_vignette = ?,
                  permis_cnd = ?,
                  fiche_enlev = ?,
                  info_vehicule = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_vehicule_pc = ?""",
        (
            _int(payload.get("id_ste")),
            bool(payload.get("temporaire")),
            bool(payload.get("conv_dispo")),
            bool(payload.get("cg_originale_dossier")),
            bool(payload.get("cg_conducteur")),
            bool(payload.get("fiche_rest")),
            bool(payload.get("c_vet_vignette")),
            bool(payload.get("permis_cnd")),
            bool(payload.get("fiche_enlev")),
            _str(payload.get("info_vehicule")),
            int(op_id),
            int(id_vehicule_pc),
        ),
    )
    return {"ok": True}


def delete_attribution(id_vehicule_pc: int, op_id: int) -> dict:
    """Btn Poubelle : HSupprime vehicule_Conducteur (soft delete)."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_vehicule_conducteur
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_vehicule_pc = ?""",
        (int(op_id), int(id_vehicule_pc)),
    )
    return {"ok": True}


def list_doc_ulease_for_pc(id_vehicule_pc: int) -> list[dict]:
    """DocUleaseEdité : unionsalarie_docUlease via TK_DemandeSignUlease
    + TK_DemandeSignPVUlease ou IdPC = id_vehicule_pc."""
    db_tk = get_pg_connection("ticket_rh")
    db_rh = get_pg_connection("rh")
    # 2 requetes : DemandeSignUlease + DemandeSignPVUlease
    sign1 = db_tk.query(
        """SELECT id_tk_liste, id_salarie_ulease, titre_contrat,
                  contrat_signe, contrat_genere, modif_date
             FROM ticket_rh.pgt_tk_demande_sign_ulease
            WHERE id_pc = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_vehicule_pc),),
    ) or []
    sign2 = db_tk.query(
        """SELECT id_tk_liste, id_salarie_ulease, titre_contrat,
                  contrat_signe, contrat_genere, modif_date
             FROM ticket_rh.pgt_tk_demande_sign_pv_ulease
            WHERE id_pc = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_vehicule_pc),),
    ) or []
    # Charger les details depuis salarie_doc_ulease
    su_ids = [_int(s.get("id_salarie_ulease")) for s in (sign1 + sign2)
              if _int(s.get("id_salarie_ulease"))]
    su_by_id: dict[int, dict] = {}
    if su_ids:
        ph = ",".join(["?"] * len(su_ids))
        rows = db_rh.query(
            f"""SELECT id_salarie_doc_ulease, id_doc_ulease_type,
                       date_edition, recu
                  FROM rh.pgt_salarie_doc_ulease
                 WHERE id_salarie_doc_ulease IN ({ph})""",
            tuple(su_ids),
        ) or []
        su_by_id = {_int(r.get("id_salarie_doc_ulease")): r for r in rows}

    type_lib = {
        1: "Mise à disposition",
        2: "PV de livraison",
        3: "PV de restitution",
    }

    out = []
    for s in sign1 + sign2:
        su_id = _int(s.get("id_salarie_ulease"))
        su = su_by_id.get(su_id, {})
        out.append({
            "id_tk_liste": str(_int(s.get("id_tk_liste"))),
            "type_doc": type_lib.get(_int(su.get("id_doc_ulease_type")),
                                     _str(s.get("titre_contrat"))),
            "date_edition": _iso_date(su.get("date_edition")) or _iso_date(s.get("modif_date")),
            "signe": bool(su.get("recu")) or bool(s.get("contrat_signe")),
        })
    out.sort(key=lambda x: x["date_edition"], reverse=True)
    return out


def _new_id() -> int:
    """idEntierDateHeureSys (cf. WinDev)."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


# ---------------------------------------------------------------------------
# Fen_Attribution (ajout/modif d'une attribution conducteur)
# ---------------------------------------------------------------------------


def search_salaries(query: str, limit: int = 50) -> list[dict]:
    """Liste de salaries pour le btn 'Choisir le conducteur' (Fen_
    RechercheNomSalarie). Match case-insensitive sur nom + prenom +
    nom_marital. Renvoie un mini-payload {id, nom_complet, prenom}."""
    q = (query or "").strip()
    db = get_pg_connection("rh")
    if not q:
        rows = db.query(
            """SELECT id_salarie, nom, nom_marital, prenom
                 FROM rh.pgt_salarie
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
             ORDER BY nom ASC, prenom ASC LIMIT ?""",
            (int(limit),),
        ) or []
    else:
        pat = f"%{q.lower()}%"
        rows = db.query(
            """SELECT id_salarie, nom, nom_marital, prenom
                 FROM rh.pgt_salarie
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND (LOWER(nom) LIKE ? OR LOWER(prenom) LIKE ?
                       OR LOWER(COALESCE(nom_marital, '')) LIKE ?)
             ORDER BY nom ASC, prenom ASC LIMIT ?""",
            (pat, pat, pat, int(limit)),
        ) or []
    out = []
    for r in rows:
        nom = _str(r.get("nom"))
        marital = _str(r.get("nom_marital"))
        prenom = _str(r.get("prenom")).strip().capitalize()
        nom_complet = f"{nom} {marital}".strip() if marital else nom
        out.append({
            "id_salarie": str(_int(r.get("id_salarie"))),
            "nom_complet": nom_complet,
            "prenom": prenom,
            "lib": f"{nom_complet} {prenom}".strip(),
        })
    return out


def ensure_conducteur_from_salarie(id_salarie: int, op_id: int) -> dict:
    """Btn 'Choisir le conducteur' apres selection : cree la fiche
    conducteur depuis le salarie si elle n'existe pas, sinon renvoie
    l'id_conducteur existant. Cf. WinDev (HExecuteRequete reqInfoCond +
    HAjoute(conducteur))."""
    if not id_salarie:
        return {"ok": False, "error": "id_salarie manquant"}
    db_ul = get_pg_connection("ulease")
    # 1. Existe ?
    r = db_ul.query_one(
        """SELECT id_conducteur FROM ulease.pgt_conducteur
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if r and _int(r.get("id_conducteur")):
        id_cnd = _int(r.get("id_conducteur"))
        return _conducteur_info(id_cnd)

    # 2. Charger les infos depuis le salarie + adresse + tel
    db_rh = get_pg_connection("rh")
    s = db_rh.query_one(
        """SELECT id_salarie, nom, nom_marital, prenom, sexe,
                  date_naiss, lieu_naiss, dep_naiss, nationalite, photo
             FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if not s:
        return {"ok": False, "error": "Salarie introuvable"}

    # Adresse + tel : table unique pgt_salarie_coordonnees
    coord = db_rh.query_one(
        """SELECT adresse1, adresse2, cp, ville, tel_fixe, tel_mob
             FROM rh.pgt_salarie_coordonnees
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    adr = coord
    tel = coord

    # 3. INSERT conducteur
    db_ul.query(
        """INSERT INTO ulease.pgt_conducteur
             (id_conducteur, id_salarie, nom_conducteur, nom_marital,
              prenom_conducteur, sexe_conducteur, date_naiss, lieu_naiss,
              dep_naiss, pays, photo_conducteur,
              tel, mobile, adresse1, adresse2, cp, ville,
              num_permis, type_permis, login, mdp_user,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   '', '', '', '', NOW(), ?, 'new')""",
        (
            int(id_salarie),  # id_conducteur = id_salarie (cf. WinDev)
            int(id_salarie),
            _str(s.get("nom")),
            _str(s.get("nom_marital")),
            _str(s.get("prenom")),
            _int(s.get("sexe")),
            s.get("date_naiss") or None,
            _str(s.get("lieu_naiss")),
            _int(s.get("dep_naiss")),
            _str(s.get("nationalite")),
            s.get("photo"),
            _str(tel.get("tel_fixe")),
            _str(tel.get("tel_mob")),
            _str(adr.get("adresse1")),
            _str(adr.get("adresse2")),
            _str(adr.get("cp")),
            _str(adr.get("ville")),
            int(op_id),
        ),
    )
    return _conducteur_info(int(id_salarie))


def _conducteur_info(id_conducteur: int) -> dict:
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_conducteur, id_salarie, nom_conducteur, nom_marital,
                  prenom_conducteur
             FROM ulease.pgt_conducteur WHERE id_conducteur = ? LIMIT 1""",
        (int(id_conducteur),),
    )
    if not r:
        return {"ok": False, "error": "Conducteur introuvable"}
    nom = _str(r.get("nom_conducteur"))
    prenom = _str(r.get("prenom_conducteur")).strip().capitalize()
    marital = _str(r.get("nom_marital"))
    nom_complet = f"{nom} {marital}".strip() if marital else nom
    return {
        "ok": True,
        "id_conducteur": str(_int(r.get("id_conducteur"))),
        "id_salarie": str(_int(r.get("id_salarie"))),
        "lib": f"{nom_complet} {prenom}".strip(),
    }


def save_attribution(payload: dict, op_id: int) -> dict:
    """Fen_Attribution btn Valider : create (id_vehicule_pc=0) ou update
    complet (toutes les colonnes du form, dates incluses).

    Cree aussi le dossier FTP /OMAYA/Vehicules/{id_vehicule}/{id_pc}/
    a la creation (cf. WinDev FTPRepCree)."""
    id_pc = _int(payload.get("id_vehicule_pc"))
    id_vehicule = _int(payload.get("id_vehicule"))
    id_conducteur = _int(payload.get("id_conducteur"))
    if not id_vehicule or not id_conducteur:
        return {"ok": False, "error": "id_vehicule et id_conducteur requis"}

    perception_date = payload.get("perception_date") or None
    perception_heure = payload.get("perception_heure") or None
    restitution_date = payload.get("restitution_date") or None
    restitution_heure = payload.get("restitution_heure") or None
    if perception_date == "":
        perception_date = None
    if perception_heure == "":
        perception_heure = None
    if restitution_date == "":
        restitution_date = None
    if restitution_heure == "":
        restitution_heure = None

    db = get_pg_connection("ulease")
    if id_pc == 0:
        new_id = _new_id()
        db.query(
            """INSERT INTO ulease.pgt_vehicule_conducteur
                 (id_vehicule_pc, id_vehicule, id_conducteur, id_ste,
                  perception_date, perception_heure,
                  restitution_date, restitution_heure,
                  k_mdepart, temporaire,
                  conv_dispo, cg_originale_dossier, cg_conducteur,
                  fiche_rest, c_vet_vignette, permis_cnd,
                  fiche_enlev, info_vehicule,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       FALSE, '', ?, NOW(), 'new')""",
            (
                new_id, id_vehicule, id_conducteur,
                _int(payload.get("id_ste")),
                perception_date, perception_heure,
                restitution_date, restitution_heure,
                _int(payload.get("k_mdepart")),
                bool(payload.get("temporaire")),
                bool(payload.get("conv_dispo")),
                bool(payload.get("cg_originale_dossier")),
                bool(payload.get("cg_conducteur")),
                bool(payload.get("fiche_rest")),
                bool(payload.get("c_vet_vignette")),
                bool(payload.get("permis_cnd")),
                int(op_id),
            ),
        )
        # Creer le dossier FTP /OMAYA/Vehicules/{id}/{new_id}/
        ftp = doc_svc._ftp_connect()
        if ftp:
            try:
                rep = doc_svc._rep_ftp(id_vehicule, str(new_id))
                doc_svc._ftp_makedirs(ftp, rep)
            finally:
                try:
                    ftp.quit()
                except Exception:
                    pass
        return {"ok": True, "id_vehicule_pc": str(new_id)}

    # Update existant
    db.query(
        """UPDATE ulease.pgt_vehicule_conducteur
              SET id_conducteur = ?, id_ste = ?,
                  perception_date = ?, perception_heure = ?,
                  restitution_date = ?, restitution_heure = ?,
                  k_mdepart = ?, temporaire = ?,
                  conv_dispo = ?, cg_originale_dossier = ?,
                  cg_conducteur = ?, fiche_rest = ?,
                  c_vet_vignette = ?, permis_cnd = ?,
                  modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_vehicule_pc = ?""",
        (
            id_conducteur,
            _int(payload.get("id_ste")),
            perception_date, perception_heure,
            restitution_date, restitution_heure,
            _int(payload.get("k_mdepart")),
            bool(payload.get("temporaire")),
            bool(payload.get("conv_dispo")),
            bool(payload.get("cg_originale_dossier")),
            bool(payload.get("cg_conducteur")),
            bool(payload.get("fiche_rest")),
            bool(payload.get("c_vet_vignette")),
            bool(payload.get("permis_cnd")),
            int(op_id), id_pc,
        ),
    )
    return {"ok": True, "id_vehicule_pc": str(id_pc)}


def generer_pv(id_vehicule_pc: int, type_pv: str, suivi_edition: bool,
               op_id: int) -> dict:
    """Btn Generer PV livraison / restitution.

    Cree :
    - (optionnel) salarie_doc_ulease (suivi d'edition, type=3) si demande.
    - tk_demande_sign_pv_ulease (titre = 'PV de livraison' ou 'PV de restitution')
    - tk_liste (service=JU, type=35, statut=1)
    - tk_demandesignpv_photo pour chaque typecapacite_photo lie a la capacite.
    """
    if type_pv not in ("livraison", "restitution"):
        return {"ok": False, "error": "type_pv invalide"}
    titre = "PV de livraison" if type_pv == "livraison" else "PV de restitution"

    db_ul = get_pg_connection("ulease")
    db_rh = get_pg_connection("rh")
    db_tk = get_pg_connection("ticket")
    db_tkr = get_pg_connection("ticket_rh")

    # 1. Recuperer le conducteur + l'id_vehicule + type_capacite
    row = db_ul.query_one(
        """SELECT vc.id_vehicule, c.id_salarie,
                  vf.id_vehicule_type_capacite
             FROM ulease.pgt_vehicule_conducteur vc
        LEFT JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
        LEFT JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
            WHERE vc.id_vehicule_pc = ? LIMIT 1""",
        (int(id_vehicule_pc),),
    )
    if not row:
        return {"ok": False, "error": "Attribution introuvable"}
    id_salarie_cond = _int(row.get("id_salarie"))
    id_type_capacite = _int(row.get("id_vehicule_type_capacite"))

    # 2. Suivi edition (optionnel)
    id_rh_edit = 0
    if suivi_edition:
        id_rh_edit = _new_id()
        db_rh.query(
            """INSERT INTO rh.pgt_salarie_doc_ulease
                 (id_salarie_doc_ulease, id_doc_ulease_type, id_salarie,
                  id_da, date_edition, recu,
                  modif_op, modif_date, modif_elem)
               VALUES (?, 3, ?, ?, NOW(), FALSE, ?, NOW(), 'new')""",
            (id_rh_edit, int(op_id), id_salarie_cond, int(op_id)),
        )

    # 3. tk_demande_sign_pv_ulease
    id_pv = _new_id()
    db_tkr.query(
        """INSERT INTO ticket_rh.pgt_tk_demande_sign_pv_ulease
             (id_demande_sign_pv_ulease, id_tk_liste, idorganigramme,
              id_salarie_ulease, id_salarie, id_da, id_pc,
              titre_contrat, contrat_genere, contrat_valide, contrat_signe,
              contrat_annul,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, 0, ?, ?, 0, ?, ?, TRUE, TRUE, FALSE, FALSE,
                   NOW(), ?, 'new')""",
        (
            id_pv, id_pv, id_rh_edit, id_salarie_cond, int(id_vehicule_pc),
            titre, int(op_id),
        ),
    )

    # 4. tk_liste (Service=JU, type=35, statut=1)
    db_tk.query(
        """INSERT INTO ticket.pgt_tk_liste
             (id_tk_liste, date_crea, op_crea, op_dest, service,
              id_tk_type_demande, id_tk_statut, cloturee,
              op_traitement_staff, ordre_traitement_staff,
              modif_date, modif_op, modif_elem)
           VALUES (?, NOW(), ?, ?, 'JU', 35, 1, FALSE, 0, 0,
                   NOW(), ?, 'new')""",
        (id_pv, int(op_id), id_salarie_cond, int(op_id)),
    )

    # 5. tk_demandesignpv_photo pour chaque typecapacite_photo
    photos = db_ul.query(
        """SELECT id_type_capacite_photo FROM ulease.pgt_typecapacite_photo
            WHERE id_vehicule_type_capacite = ?
              AND (modif_elem IS NULL OR modif_elem <> 'suppr')
         ORDER BY lib_photo ASC""",
        (id_type_capacite,),
    ) or []
    for p in photos:
        id_photo = _new_id()
        db_tkr.query(
            """INSERT INTO ticket_rh.pgt_tk_demandesignpv_photo
                 (id_tk_demande_sign_pv_photo, id_demande_sign_ulease_auto,
                  id_type_capacite_photo,
                  modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, NOW(), ?, 'new')""",
            (id_photo, id_pv, _int(p.get("id_type_capacite_photo")), int(op_id)),
        )

    return {
        "ok": True,
        "id_tk_liste": str(id_pv),
        "titre": titre,
        "nb_photos": len(photos),
    }


def add_info_complementaire(id_vehicule_pc: int, commentaire: str,
                            user_prenom: str, op_id: int) -> dict:
    """Btn Information complementaire : append au champ info_vehicule.
    Cf. WinDev InfoVehicule1 += RC + DateVersChaine + ' par '+ prenom +
    ' : ' + Nouveau_commentaire1."""
    if not commentaire.strip():
        return {"ok": False, "error": "Commentaire vide"}
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT info_vehicule FROM ulease.pgt_vehicule_conducteur
            WHERE id_vehicule_pc = ?""",
        (int(id_vehicule_pc),),
    )
    if not r:
        return {"ok": False, "error": "Attribution introuvable"}
    from datetime import datetime
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    current = _str(r.get("info_vehicule"))
    line = f"\n{stamp} par {user_prenom} : {commentaire.strip()}"
    new_text = (current + line).strip()
    db.query(
        """UPDATE ulease.pgt_vehicule_conducteur
              SET info_vehicule = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_vehicule_pc = ?""",
        (new_text, int(op_id), int(id_vehicule_pc)),
    )
    return {"ok": True, "info_vehicule": new_text}
