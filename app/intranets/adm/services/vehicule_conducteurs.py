"""
Service Fen_FicheVehicule Plan 2 (Conducteurs).

Liste des attributions (vehicule_conducteur) + details pour edition +
liste docs Ulease edites lies a une attribution.
"""

from __future__ import annotations

from typing import Any

from app.core.database.pg import get_pg_connection


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
    if v is None or v == "":
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
