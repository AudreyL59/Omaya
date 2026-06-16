"""
Service Fen_DPAE_Nouvelle (ADM).

Transposition de la fenetre WinDev, scope V1 (Plan 1) :
  - Lookups (societes, mutuelles, postes, types ctt/horaire, situations
    familiales, partenaires portail)
  - load_preremplissage : depuis CV / fiche salarie / TK ticket / vierge
  - save_dpae : INSERT salarie + coord + embauche + sortie vide + mutuelle
    + organigramme + droits_acces. Si TypeDpae=1 (CV) : crea CvSuivi
    JO + maj AgendaEvenement IDCategorie=8.

Plan 2 (codes partenaires, URSSAF, charte ethique, terminer) : V2.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta
from typing import Any

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _new_id() -> int:
    """idEntierDateHeureSys WinDev : YYYYMMDDHHMMSSmmm."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _strip_accents_and_spaces(s: str) -> str:
    """Equivalent ChaineFormate(s, ccSansAccent+ccSansEspace) WinDev."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    out = "".join(c for c in nfkd if not unicodedata.combining(c))
    return out.replace(" ", "")


def _digits_only(s: str) -> str:
    """ccSansEspaceIntérieur+ccSansEspace+ccSansPonctuationNiEspace."""
    return "".join(c for c in (s or "") if c.isdigit())


def _capitalize(s: str) -> str:
    return (s[:1].upper() + s[1:].lower()) if s else ""


def _matricule_tr(nom: str, prenom: str, date_naiss: str) -> str:
    """NN_PP_DDMMYYYY (cf. WinDev MatriculeTR)."""
    nom2 = _capitalize(nom[:2]) if nom else "  "
    pre2 = _capitalize(prenom[:2]) if prenom else "  "
    iso = _iso_date(date_naiss)
    if iso and len(iso) >= 10:
        ddmm = f"{iso[8:10]}{iso[5:7]}{iso[0:4]}"
    else:
        ddmm = ""
    return f"{nom2}_{pre2}_{ddmm}"


# ---------------------------------------------------------------------------
# Lookups (combos)
# ---------------------------------------------------------------------------


def list_societes() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, raison_sociale, rs_interne
             FROM rh.pgt_societe
            WHERE COALESCE(is_actif, FALSE) = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY raison_sociale""",
    ) or []
    return [{
        "id_ste": str(r.get("id_ste") or ""),
        "lib": _str(r.get("rs_interne") or r.get("raison_sociale")),
    } for r in rows]


def list_mutuelles() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_mutuelle, lib_mutuelle, is_actif
             FROM rh.pgt_mutuelle
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
            ORDER BY lib_mutuelle""",
    ) or []
    return [{
        "id_mutuelle": _int(r.get("id_mutuelle")),
        "lib": _str(r.get("lib_mutuelle")),
        "is_actif": bool(r.get("is_actif")),
    } for r in rows]


def list_postes() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_poste, lib_poste, categorie
             FROM rh.pgt_type_poste
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
            ORDER BY lib_poste""",
    ) or []
    return [{
        "id_type_poste": _int(r.get("id_type_poste")),
        "lib": _str(r.get("lib_poste")),
        "categorie": _str(r.get("categorie")),
    } for r in rows]


def list_types_ctt() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_ctt, intitule
             FROM rh.pgt_type_ctt_travail
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
            ORDER BY intitule""",
    ) or []
    return [{
        "id_type_ctt": _int(r.get("id_type_ctt")),
        "lib": _str(r.get("intitule")),
    } for r in rows]


def list_types_horaire() -> list[dict]:
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_horaire, lib_horaire
             FROM rh.pgt_type_horaire_travail
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
            ORDER BY lib_horaire""",
    ) or []
    return [{
        "id_type_horaire": _int(r.get("id_type_horaire")),
        "lib": _str(r.get("lib_horaire")),
    } for r in rows]


# ---------------------------------------------------------------------------
# Preremplissage
# ---------------------------------------------------------------------------


def load_preremplissage(
    type_dpae: int,
    id_elem: int,
    id_cv_suivi: int,
    id_ticket: int,
) -> dict:
    """Renvoie tous les champs deja connus selon le mode d'ouverture.

    type_dpae :
        0 = vierge (eventuellement avec ticket)
        1 = depuis CV (id_elem = id_cvtheque)
        2 = depuis fiche salarie sortie (id_elem = id_salarie)
        3 = poursuivre une DPAE en cours
        4 = depuis TK_DemandeDPAE_Distrib (distributeur)

    Cf. RecupInfoFicheCV / RecupInfoFicheSa / RecupInfoTkDpae.
    """
    out: dict[str, Any] = _empty_payload()
    out["type_dpae"] = type_dpae
    out["id_ticket"] = str(id_ticket) if id_ticket else ""

    # JO directe par defaut (cf. cas vierge WinDev)
    if type_dpae == 0:
        out["jodirecte"] = True

    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")
    db_div = get_pg_connection("divers")

    # 1) Preremplissage depuis TK_DemandeDPAE (s'il y a un ticket et que le
    # mode n'est pas distribteur=4)
    if id_ticket and type_dpae != 4:
        # Cherche dans ticket_dpae.pgt_tk_demande_dpae
        try:
            db_tkdpae = get_pg_connection("ticket_dpae")
            tk = db_tkdpae.query_one(
                """SELECT * FROM ticket_dpae.pgt_tk_demande_dpae
                    WHERE id_tk_liste = ? LIMIT 1""",
                (int(id_ticket),),
            )
        except Exception:
            tk = None
        if tk:
            out["civilite"] = _int(tk.get("civilite"))
            out["sexe"] = "H" if out["civilite"] == 1 else "F"
            out["nom"] = _str(tk.get("nom"))
            out["nom_marital"] = _str(tk.get("nom_marital"))
            out["prenom"] = _str(tk.get("prenom"))
            out["date_naiss"] = _iso_date(tk.get("dnaiss"))
            out["lieu_naiss"] = _str(tk.get("lnaiss"))
            out["dep_naiss"] = _int(tk.get("depnaiss"))
            out["num_ss"] = _str(tk.get("numss"))
            out["num_cin"] = _str(tk.get("numcin"))
            out["adresse1"] = _str(tk.get("adresse"))
            out["cp"] = _str(tk.get("cp"))
            out["ville"] = _str(tk.get("ville"))
            out["cpam"] = _str(tk.get("cpam"))
            out["tel_mob"] = _str(tk.get("gsm"))
            out["mail"] = _str(tk.get("mail"))
            out["situation_fam"] = _int(tk.get("situation_fam"))
            out["avec_enfant"] = bool(tk.get("avec_enfant"))
            out["nb_enfants"] = _int(tk.get("nb_enfants"))
            out["urg_nom"] = _str(tk.get("urgnom"))
            out["urg_lien"] = _str(tk.get("urglien"))
            out["urg_tel"] = _str(tk.get("urgtel"))
            out["date_debut"] = _iso_date(tk.get("date_debut"))
            out["adhesion"] = bool(tk.get("mutuelle"))
            out["adhesion_date"] = _iso_date(tk.get("mutdate"))
            out["travailleur_handi"] = bool(tk.get("travailleur_handi"))
            out["idorganigramme"] = str(_int(tk.get("id_equipe")) or "")
            out["coopte"] = bool(tk.get("coopte"))
            out["coopteur"] = str(_int(tk.get("coopteur")) or "")
            out["jodirecte"] = bool(tk.get("jodirecte"))
            out["jo_coopteur"] = str(_int(tk.get("jo_coopteur")) or "")

    # 2) TypeDpae = 1 : CV -> precharge depuis cvtheque
    if type_dpae == 1 and id_elem:
        out["id_cvtheque"] = str(id_elem)
        cv = db_rec.query_one(
            """SELECT date_naissance, nom, prenom, adresse, gsm, mail,
                      id_communes_france, id_cvsource, id_elem_source
                 FROM recrutement.pgt_cvtheque
                WHERE id_cvtheque = ? LIMIT 1""",
            (int(id_elem),),
        )
        if cv and not id_ticket:
            out["date_naiss"] = _iso_date(cv.get("date_naissance"))
            out["nom"] = _str(cv.get("nom"))
            out["prenom"] = _str(cv.get("prenom"))
            out["adresse1"] = _str(cv.get("adresse"))
            out["tel_mob"] = _str(cv.get("gsm"))
            out["mail"] = _str(cv.get("mail"))
            out["nationalite"] = "Française"
            id_commune = _int((cv or {}).get("id_communes_france"))
            if id_commune:
                cmn = db_div.query_one(
                    """SELECT code_postal, nom_ville FROM divers.pgt_communes_france
                        WHERE id_communes_france = ? LIMIT 1""",
                    (id_commune,),
                )
                if cmn:
                    out["cp"] = _str(cmn.get("code_postal"))
                    out["ville"] = _str(cmn.get("nom_ville"))
        # Coopte si IDcvsource=1 (cooptation)
        if cv and _int(cv.get("id_cvsource")) == 1:
            out["coopte"] = True
            id_coopt = _int(cv.get("id_elem_source"))
            out["coopteur"] = str(id_coopt) if id_coopt else ""
            # Si pas de RDV dans CvSuivi -> JO directe avec coopteur
            cnt = db_rec.query_one(
                """SELECT COUNT(*) AS n FROM recrutement.pgt_cvsuivi
                    WHERE id_cvtheque = ? AND type_elem = 'RDV'""",
                (int(id_elem),),
            )
            if not cnt or _int(cnt.get("n")) == 0:
                out["jodirecte"] = True
                out["jo_coopteur"] = out["coopteur"]
            else:
                out["jodirecte"] = False

    # 3) TypeDpae = 2 : Salarie sorti -> precharge depuis salarie + coord
    if type_dpae == 2 and id_elem:
        sal = db_rh.query_one(
            """SELECT civilite, nom, nom_marital, prenom, sexe, nationalite,
                      date_naiss, lieu_naiss, dep_naiss, num_ss, cpam,
                      num_cin, situation_fam, avec_enfant, nb_enfants,
                      travailleur_handi
                 FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1""",
            (int(id_elem),),
        )
        if sal:
            for k in ("civilite", "nom", "nom_marital", "prenom", "sexe",
                      "nationalite", "lieu_naiss", "dep_naiss", "num_ss",
                      "cpam", "num_cin", "situation_fam", "nb_enfants"):
                v = sal.get(k)
                if v is not None:
                    out[k] = v if not isinstance(v, bool) else bool(v)
            out["date_naiss"] = _iso_date(sal.get("date_naiss"))
            out["avec_enfant"] = bool(sal.get("avec_enfant"))
            out["travailleur_handi"] = bool(sal.get("travailleur_handi"))
        coord = db_rh.query_one(
            """SELECT adresse1, adresse2, cp, ville, tel_mob, tel_fixe,
                      mail, urg_nom, urg_lien, urg_tel, iban, bic
                 FROM rh.pgt_salarie_coordonnees WHERE id_salarie = ? LIMIT 1""",
            (int(id_elem),),
        )
        if coord:
            for k in ("adresse1", "adresse2", "cp", "ville", "tel_mob",
                     "tel_fixe", "mail", "urg_nom", "urg_lien", "urg_tel",
                     "iban", "bic"):
                v = coord.get(k)
                if v is not None:
                    out[k] = _str(v)

    return out


def _empty_payload() -> dict[str, Any]:
    """Champ par defaut (vide) pour le payload."""
    return {
        "type_dpae": 0,
        "id_ticket": "",
        "id_cvtheque": "",
        "civilite": 0,
        "sexe": "",
        "nom": "",
        "nom_marital": "",
        "prenom": "",
        "nationalite": "Française",
        "date_naiss": "",
        "lieu_naiss": "",
        "dep_naiss": 0,
        "num_ss": "",
        "cpam": "",
        "num_cin": "",
        "situation_fam": 0,
        "avec_enfant": False,
        "nb_enfants": 0,
        "travailleur_handi": False,
        "adresse1": "",
        "adresse2": "",
        "cp": "",
        "ville": "",
        "tel_mob": "",
        "tel_fixe": "",
        "mail": "",
        "urg_nom": "",
        "urg_lien": "",
        "urg_tel": "",
        "iban": "",
        "bic": "",
        "idorganigramme": "",
        "id_ste": "",
        "id_type_poste": 0,
        "id_type_ctt": 1,
        "id_type_horaire": 1,
        "date_debut": "",
        "coopte": False,
        "coopteur": "",
        "jodirecte": False,
        "jo_coopteur": "",
        "id_mutuelle": 0,
        "adhesion": False,
        "adhesion_date": "",
        "mutuelle_dossier": False,
        "mutuelle_att_ss": False,
        "mutuelle_rib": False,
    }


# ---------------------------------------------------------------------------
# Save (Btn Enregistrer Plan 1)
# ---------------------------------------------------------------------------


def save_dpae(payload: dict, op_id: int) -> dict:
    """Cree le salarie et toutes les tables dependantes. Cf. Btn Enregistrer
    Plan 1 du WinDev.

    Retourne {ok: True, id_salarie: '...', matricule_tr: '...'}.

    Leve ValueError si validation echoue.
    """
    # Validations (cf. WinDev en debut de Btn Enregistrer)
    id_orga = _int(payload.get("idorganigramme"))
    if not id_orga:
        raise ValueError("Merci de choisir l'équipe de rattachement")
    date_debut = payload.get("date_debut") or ""
    if not date_debut or len(date_debut) < 10:
        raise ValueError("Merci de choisir une date de début valide")
    if payload.get("coopte") and not _int(payload.get("coopteur")):
        raise ValueError("Merci de choisir le coopteur")
    if payload.get("jodirecte") and not _int(payload.get("jo_coopteur")):
        raise ValueError("Merci de choisir le coopteur de JO Directe")

    id_salarie = _new_id()
    nom = _strip_accents_and_spaces(payload.get("nom") or "")
    prenom = _strip_accents_and_spaces(payload.get("prenom") or "")
    tel_mob = _digits_only(payload.get("tel_mob") or "")
    mail = (payload.get("mail") or "").replace(" ", "").lower()

    matricule = _matricule_tr(nom, prenom, payload.get("date_naiss") or "")
    type_dpae = _int(payload.get("type_dpae"))

    db_rh = get_pg_connection("rh")
    db_rec = get_pg_connection("recrutement")

    # 1. Si TypeDpae=2 : prefixe l'ancien salarie "Z " + login "-old"
    id_elem = _int(payload.get("id_elem"))
    if type_dpae == 2 and id_elem:
        old = db_rh.query_one(
            "SELECT nom, login FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (id_elem,),
        )
        if old:
            new_nom = "Z " + _str(old.get("nom"))
            new_login = _str(old.get("login"))
            if "-old" not in new_login:
                new_login += "-old"
            db_rh.query(
                """UPDATE rh.pgt_salarie
                      SET nom = ?, login = ?, modif_date = NOW(),
                          modif_op = ?, modif_elem = 'modif'
                    WHERE id_salarie = ?""",
                (new_nom, new_login, op_id, id_elem),
            )

    # 2. INSERT salarie
    db_rh.query(
        """INSERT INTO rh.pgt_salarie
              (id_salarie, civilite, nom, nom_marital, prenom, sexe,
               nationalite, date_naiss, lieu_naiss, dep_naiss,
               num_ss, cpam, num_cin, situation_fam, avec_enfant,
               nb_enfants, travailleur_handi, matricule_tr,
               agenda_actif, op_crea, datecrea, active_log,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   ?, ?, ?,
                   FALSE, ?, NOW(), FALSE,
                   NOW(), ?, 'new')""",
        (
            id_salarie, _int(payload.get("civilite")), nom,
            _str(payload.get("nom_marital")), prenom,
            _str(payload.get("sexe")),
            _str(payload.get("nationalite")) or "Française",
            payload.get("date_naiss") or None,
            _str(payload.get("lieu_naiss")), _int(payload.get("dep_naiss")),
            _str(payload.get("num_ss")), _str(payload.get("cpam")),
            _str(payload.get("num_cin")), _int(payload.get("situation_fam")),
            bool(payload.get("avec_enfant")),
            _int(payload.get("nb_enfants")),
            bool(payload.get("travailleur_handi")), matricule,
            int(op_id),
            int(op_id),
        ),
    )

    # 3. Si TypeDpae=1 : crea CvSuivi (JO) + maj AgendaEvenement
    id_cv_suivi = _int(payload.get("id_cv_suivi"))
    id_cvtheque = _int(payload.get("id_cvtheque"))
    if type_dpae == 1 and id_cvtheque:
        db_rec.query(
            """INSERT INTO recrutement.pgt_cvsuivi
                  (id_cv_suivi, id_cvtheque, datecrea, op_crea,
                   id_cv_statut, type_elem, id_elem, observation,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, NOW(), ?, 106, 'JO', ?, '',
                       NOW(), ?, 'new')""",
            (_new_id(), id_cvtheque, op_id, id_salarie, op_id),
        )
        if id_cv_suivi:
            db_rec.query(
                """UPDATE recrutement.pgt_agenda_evenement
                      SET id_categorie = 8,
                          contenu = COALESCE(contenu, '') ||
                                    CHR(13) || 'Passé en JO le ' ||
                                    to_char(NOW(), 'DD/MM/YYYY HH24:MI'),
                          modif_date = NOW()
                    WHERE id_cv_suivi = ?""",
                (id_cv_suivi,),
            )

    # 4. INSERT salarie_coordonnees
    db_rh.query(
        """INSERT INTO rh.pgt_salarie_coordonnees
              (id_salarie, adresse1, adresse2, cp, ville,
               tel_fixe, tel_mob, mail, urg_nom, urg_lien, urg_tel,
               iban, bic, modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   '', ?, ?, ?, ?, ?,
                   ?, ?, NOW(), ?, 'new')""",
        (
            id_salarie, _str(payload.get("adresse1")),
            _str(payload.get("adresse2")), _str(payload.get("cp")),
            _str(payload.get("ville")), tel_mob, mail,
            _str(payload.get("urg_nom")), _str(payload.get("urg_lien")),
            _str(payload.get("urg_tel")), _str(payload.get("iban")),
            _str(payload.get("bic")), int(op_id),
        ),
    )

    # 5. INSERT salarie_embauche
    iso_dd = payload.get("date_debut") or None
    iso_perai = None
    if iso_dd:
        try:
            d = datetime.strptime(iso_dd[:10], "%Y-%m-%d").date()
            iso_perai = (d + timedelta(days=90) - timedelta(days=1)).isoformat()
        except Exception:
            iso_perai = None
    coopte = bool(payload.get("coopte"))
    jodirecte = bool(payload.get("jodirecte"))
    id_ste = _int(payload.get("id_ste"))
    db_rh.query(
        """INSERT INTO rh.pgt_salarie_embauche
              (id_salarie, date_debut, date_fin_per_essai, date_anciennete,
               en_activite, dpae_date, dpae_num, dpae_ope, id_type_poste,
               id_type_ctt, id_type_horaire, id_ste, id_ste_dpae_energie,
               id_ste_dpae_fibre, coopte, coopteur, j_odirecte, jo_coopteur,
               resp_equipe, resp_adjoint, chauffeur, multi_prod, en_pause,
               id_absence, id_cvtheque, cin_envoyee, cj_envoye,
               formation_iag, permis_vente_suspendu, permis_cumul_primes,
               modif_date, modif_op, modif_elem, id_salarie_trans_prod)
           VALUES (?, ?, ?, ?, TRUE, NULL, '', NULL,
                   ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?,
                   FALSE, FALSE, FALSE, FALSE, FALSE,
                   0, ?, FALSE, FALSE,
                   FALSE, FALSE, 0,
                   NOW(), ?, 'new', 0)""",
        (
            id_salarie, iso_dd, iso_perai, iso_dd,
            _int(payload.get("id_type_poste")),
            _int(payload.get("id_type_ctt")) or 1,
            _int(payload.get("id_type_horaire")) or 1,
            id_ste, id_ste, id_ste,
            coopte, _int(payload.get("coopteur")) if coopte else 0,
            jodirecte, _int(payload.get("jo_coopteur")) if jodirecte else 0,
            id_cvtheque, int(op_id),
        ),
    )

    # 6. INSERT salarie_sortie (vide)
    db_rh.query(
        """INSERT INTO rh.pgt_salarie_sortie
              (id_salarie_sortie, id_salarie, id_type_sortie,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, 0, ?, NOW(), 'new')""",
        (_new_id(), id_salarie, int(op_id)),
    )

    # 7. INSERT salarie_mutuelle
    db_rh.query(
        """INSERT INTO rh.pgt_salarie_mutuelle
              (id_salarie_mutuelle, id_salarie, adhesion, adhesion_date,
               id_mutuelle, mutuelle_dossier, mutuelle_att_ss, mutuelle_rib,
               mutuelle_doc_envoyes, mutuelle_recep_certif,
               mutuelle_pas_adhesion, mutuelle_resilie,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                   FALSE, FALSE, FALSE, FALSE,
                   NOW(), ?, 'new')""",
        (
            _new_id(), id_salarie, bool(payload.get("adhesion")),
            payload.get("adhesion_date") or None,
            _int(payload.get("id_mutuelle")),
            bool(payload.get("mutuelle_dossier")),
            bool(payload.get("mutuelle_att_ss")),
            bool(payload.get("mutuelle_rib")),
            int(op_id),
        ),
    )

    # 8. INSERT salarie_organigramme
    db_rh.query(
        """INSERT INTO rh.pgt_salarie_organigramme
              (id_salarie_organigramme, id_salarie, idorganigramme,
               date_debut, aff_actif, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, TRUE, ?, NOW(), ?, 'new')""",
        (_new_id(), id_salarie, id_orga, iso_dd, id_ste, int(op_id)),
    )

    # 9. Droits d'acces selon categorie du poste
    id_poste = _int(payload.get("id_type_poste"))
    if id_poste:
        poste = db_rh.query_one(
            "SELECT categorie FROM rh.pgt_type_poste WHERE id_type_poste = ? LIMIT 1",
            (id_poste,),
        )
        if poste:
            cat = _str(poste.get("categorie"))
            droits = db_rh.query(
                """SELECT id_type_droit_acces FROM rh.pgt_type_droit_acces
                    WHERE categorie = ?
                      AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                (cat,),
            ) or []
            for d in droits:
                db_rh.query(
                    """INSERT INTO rh.pgt_salarie_droit_acces
                          (id_salarie, id_type_droit_acces, droit_actif,
                           modif_date, modif_op, modif_elem)
                       VALUES (?, ?, TRUE, NOW(), ?, 'new')""",
                    (id_salarie, _int(d.get("id_type_droit_acces")), int(op_id)),
                )

    return {
        "ok": True,
        "id_salarie": str(id_salarie),
        "matricule_tr": matricule,
    }
