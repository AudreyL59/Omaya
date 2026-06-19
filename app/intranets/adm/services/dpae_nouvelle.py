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
from app.shared.notifications.mail import envoi_mail
from app.shared.notifications.sms import envoi_sms


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


def _iso_date_birth(v: Any) -> str:
    """Comme _iso_date mais avec pivot 30 sur les annees < 100. WinDev/HFSQL
    stocke parfois 'JJ/MM/AA' en interpretant 'AA' comme an 0017 au lieu de
    2017 (cf. dates de naissance des tickets DPAE)."""
    s = _iso_date(v)
    if not s or len(s) < 10:
        return s
    try:
        year = int(s[:4])
    except ValueError:
        return s
    if year >= 1900:
        return s
    if year < 100:
        new_year = 2000 + year if year < 30 else 1900 + year
        return f"{new_year:04d}{s[4:]}"
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

    # 1bis) TypeDpae=4 : ticket DPAE Distributeur (table separee)
    # cf. WinDev RecupInfoTkDpaeDistrib
    if type_dpae == 4 and id_ticket:
        try:
            db_tkbo = get_pg_connection("ticket_bo")
            tkd = db_tkbo.query_one(
                """SELECT * FROM ticket_bo.pgt_tk_demande_dpae_distrib
                    WHERE id_tk_liste = ? LIMIT 1""",
                (int(id_ticket),),
            )
        except Exception:
            tkd = None
        if tkd:
            out["civilite"] = _int(tkd.get("civilite"))
            out["sexe"] = "H" if out["civilite"] == 1 else "F"
            out["nom"] = _str(tkd.get("nom"))
            out["nom_marital"] = _str(tkd.get("nom_marital"))
            out["prenom"] = _str(tkd.get("prenom"))
            out["date_naiss"] = _iso_date_birth(tkd.get("dnaiss"))
            out["lieu_naiss"] = _str(tkd.get("lnaiss"))
            out["dep_naiss"] = _int(tkd.get("dep_naiss"))
            out["num_ss"] = _str(tkd.get("num_ss"))
            out["num_cin"] = _str(tkd.get("num_cin"))
            out["adresse1"] = _str(tkd.get("adresse1"))
            out["cp"] = _str(tkd.get("cp"))
            out["ville"] = _str(tkd.get("ville"))
            out["tel_mob"] = _str(tkd.get("gsm"))
            out["mail"] = _str(tkd.get("mail"))
            out["date_debut"] = _iso_date(tkd.get("date_debut")) or \
                datetime.now().strftime("%Y-%m-%d")
            out["idorganigramme"] = str(_int(tkd.get("idorganigramme")) or "")
            out["id_ste"] = str(_int(tkd.get("id_ste")) or "4")
            # Defauts WinDev pour distributeur
            out["id_type_poste"] = 1
            out["nationalite"] = "Française"

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
            # Noms exacts (cf. schema/ticket_dpae.sql) :
            #   dnaiss, lnaiss, dep_naiss, num_ss, num_cin, adresse1,
            #   urg_nom/lien/tel, mut_date, j_odirecte, idorganigramme
            out["civilite"] = _int(tk.get("civilite"))
            out["sexe"] = "H" if out["civilite"] == 1 else "F"
            out["nom"] = _str(tk.get("nom"))
            out["nom_marital"] = _str(tk.get("nom_marital"))
            out["prenom"] = _str(tk.get("prenom"))
            out["date_naiss"] = _iso_date_birth(tk.get("dnaiss"))
            out["lieu_naiss"] = _str(tk.get("lnaiss"))
            out["dep_naiss"] = _int(tk.get("dep_naiss"))
            out["num_ss"] = _str(tk.get("num_ss"))
            out["num_cin"] = _str(tk.get("num_cin"))
            out["adresse1"] = _str(tk.get("adresse1"))
            out["cp"] = _str(tk.get("cp"))
            out["ville"] = _str(tk.get("ville"))
            out["cpam"] = _str(tk.get("cpam"))
            out["tel_mob"] = _str(tk.get("gsm"))
            out["mail"] = _str(tk.get("mail"))
            out["situation_fam"] = _int(tk.get("situation_fam"))
            out["avec_enfant"] = bool(tk.get("avec_enfant"))
            out["nb_enfants"] = _int(tk.get("nb_enfants"))
            out["urg_nom"] = _str(tk.get("urg_nom"))
            out["urg_lien"] = _str(tk.get("urg_lien"))
            out["urg_tel"] = _str(tk.get("urg_tel"))
            out["date_debut"] = _iso_date(tk.get("date_debut"))
            out["adhesion"] = bool(tk.get("mutuelle"))
            out["adhesion_date"] = _iso_date(tk.get("mut_date"))
            out["travailleur_handi"] = bool(tk.get("travailleur_handi"))
            out["idorganigramme"] = str(_int(tk.get("idorganigramme")) or "")
            out["coopte"] = bool(tk.get("coopte"))
            out["coopteur"] = str(_int(tk.get("coopteur")) or "")
            out["jodirecte"] = bool(tk.get("j_odirecte"))
            out["jo_coopteur"] = str(_int(tk.get("jo_coopteur")) or "")
            out["nationalite"] = _str(tk.get("nationalite")) or "Française"

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
            out["date_naiss"] = _iso_date_birth(cv.get("date_naissance"))
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

    # 3) TypeDpae = 2 ou 3 : Registre RH -> precharge depuis salarie +
    # coord + embauche + organigramme courant (cf. WinDev RecupInfoFicheSa
    # + PoursuivreDPAE)
    if type_dpae in (2, 3) and id_elem:
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
            out["date_naiss"] = _iso_date_birth(sal.get("date_naiss"))
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
        emb = db_rh.query_one(
            """SELECT date_debut, id_type_poste, id_type_ctt, id_type_horaire,
                      id_ste, coopte, coopteur, j_odirecte, jo_coopteur,
                      id_cvtheque
                 FROM rh.pgt_salarie_embauche
                WHERE id_salarie = ? LIMIT 1""",
            (int(id_elem),),
        )
        if emb:
            out["date_debut"] = _iso_date(emb.get("date_debut"))
            out["id_type_poste"] = _int(emb.get("id_type_poste"))
            out["id_type_ctt"] = _int(emb.get("id_type_ctt")) or 1
            out["id_type_horaire"] = _int(emb.get("id_type_horaire")) or 1
            out["id_ste"] = str(_int(emb.get("id_ste")) or "")
            out["coopte"] = bool(emb.get("coopte"))
            out["coopteur"] = str(_int(emb.get("coopteur")) or "")
            out["jodirecte"] = bool(emb.get("j_odirecte"))
            out["jo_coopteur"] = str(_int(emb.get("jo_coopteur")) or "")
            out["id_cvtheque"] = str(_int(emb.get("id_cvtheque")) or "")
        # Organigramme courant (cf. ReqOrgaCourantetParentByVendeur)
        org = db_rh.query_one(
            """SELECT idorganigramme FROM rh.pgt_salarie_organigramme
                WHERE id_salarie = ? AND COALESCE(aff_actif, FALSE) = TRUE
             ORDER BY date_debut DESC LIMIT 1""",
            (int(id_elem),),
        )
        if org:
            out["idorganigramme"] = str(_int(org.get("idorganigramme")) or "")
        # Mutuelle existante
        mut = db_rh.query_one(
            """SELECT id_mutuelle, adhesion, adhesion_date, mutuelle_dossier,
                      mutuelle_att_ss, mutuelle_rib
                 FROM rh.pgt_salarie_mutuelle WHERE id_salarie = ? LIMIT 1""",
            (int(id_elem),),
        )
        if mut:
            out["id_mutuelle"] = _int(mut.get("id_mutuelle"))
            out["adhesion"] = bool(mut.get("adhesion"))
            out["adhesion_date"] = _iso_date(mut.get("adhesion_date"))
            out["mutuelle_dossier"] = bool(mut.get("mutuelle_dossier"))
            out["mutuelle_att_ss"] = bool(mut.get("mutuelle_att_ss"))
            out["mutuelle_rib"] = bool(mut.get("mutuelle_rib"))

    # 4) Resolution des libelles (equipe + coopteur + JO coopteur) pour
    # afficher correctement sur les boutons cote frontend
    _enrich_libelles(out, db_rh)

    return out


def _enrich_libelles(out: dict, db_rh: Any) -> None:
    """Resout les libelles a afficher sur les boutons (sinon le frontend
    affiche 'Choisir l'equipe' meme quand idorganigramme est rempli)."""
    out["orga_lib"] = ""
    out["coopteur_lib"] = ""
    out["jo_coopteur_lib"] = ""

    id_orga = _int(out.get("idorganigramme"))
    if id_orga:
        org = db_rh.query_one(
            """SELECT lib_orga FROM rh.pgt_organigramme
                WHERE idorganigramme = ? LIMIT 1""",
            (id_orga,),
        )
        if org:
            out["orga_lib"] = _str(org.get("lib_orga"))

    for src_key, lib_key in (
        ("coopteur", "coopteur_lib"),
        ("jo_coopteur", "jo_coopteur_lib"),
    ):
        sid = _int(out.get(src_key))
        if not sid:
            continue
        sal = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
            (sid,),
        )
        if sal:
            nom = _str(sal.get("nom"))
            prenom = _str(sal.get("prenom"))
            prenom_cap = (prenom[:1].upper() + prenom[1:].lower()) if prenom else ""
            out[lib_key] = f"{nom} {prenom_cap}".strip()


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


# ===========================================================================
# Plan 2 - Codes partenaires (cf. WinDev Fen_DPAE_Nouvelle..Plan = 2)
# ===========================================================================


URSSAF_PSEUDO_ID = "0"  # URSSAF n'existe pas dans pgt_partenaire (institution)


def get_societe_salarie(id_salarie: int) -> dict:
    """Societe d'embauche du salarie + raison sociale + SIRET.
    Cf. WinDev infoUrssaf : LOGIN = ChaineFormate(societe.SIRET, ccSansEspaceInterieur).
    """
    db = get_pg_connection("rh")
    emb = db.query_one(
        """SELECT s.id_ste, st.raison_sociale, st.rs_interne, st.siret
             FROM rh.pgt_salarie_embauche s
        LEFT JOIN rh.pgt_societe st ON st.id_ste = s.id_ste
            WHERE s.id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if not emb or not _int(emb.get("id_ste")):
        return {}
    siret_clean = "".join(c for c in _str(emb.get("siret")) if c.isdigit())
    return {
        "id_ste": str(_int(emb.get("id_ste"))),
        "raison_sociale": _str(emb.get("rs_interne") or emb.get("raison_sociale")),
        "siret": siret_clean,
    }


def list_partenaires_portail() -> list[dict]:
    """Combo Partenaire du Plan 2 : SELECT DISTINCT pgt_portail_partenaire
    JOIN pgt_partenaire WHERE IsActif = TRUE.

    URSSAF ajoute en tete (pas dans pgt_partenaire, cf. WinDev qui le
    hardcode car ce n'est pas un partenaire commercial)."""
    db_rec = get_pg_connection("recrutement")
    db_adv = get_pg_connection("adv")

    rows = db_rec.query(
        """SELECT DISTINCT id_partenaire
             FROM recrutement.pgt_portail_partenaire
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND COALESCE(is_actif, FALSE) = TRUE
              AND id_partenaire IS NOT NULL""",
    ) or []
    ids = [_int(r.get("id_partenaire")) for r in rows if _int(r.get("id_partenaire"))]

    parts = db_adv.query(
        "SELECT id_partenaire, lib_partenaire FROM adv.pgt_partenaire",
    ) or []
    lib_by_id = {_int(p.get("id_partenaire")): _str(p.get("lib_partenaire")) for p in parts}

    out = []
    for id_part in ids:
        lib = lib_by_id.get(id_part) or f"#{id_part}"
        out.append({
            "id_partenaire": str(id_part),
            "lib_partenaire": lib,
        })
    out.sort(key=lambda x: x["lib_partenaire"])
    # URSSAF en premiere position
    out.insert(0, {
        "id_partenaire": URSSAF_PSEUDO_ID,
        "lib_partenaire": "URSSAF",
    })
    return out


def get_portail_credentials(id_partenaire: int) -> dict:
    """Charge le lien portail + login + mdp + mail_contact du partenaire."""
    # Cas special URSSAF (pseudo id=0) : lien DUE en dur, pas de login/mdp
    # generique (cf. WinDev infoUrssaf qui utilisait societe.SIRET).
    if int(id_partenaire) == 0:
        return {
            "lien_portail": "https://www.due.urssaf.fr/declarant/index.jsf",
            "login": "",
            "mdp": "",
            "mail_contact": "",
            "id_entite": "",
        }

    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT lien_portail, login, mdp, mail_contact, id_entite
             FROM recrutement.pgt_portail_partenaire
            WHERE id_partenaire = ? AND COALESCE(is_actif, FALSE) = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            LIMIT 1""",
        (int(id_partenaire),),
    )
    if not row:
        return {}
    return {
        "lien_portail": _str(row.get("lien_portail")),
        "login": _str(row.get("login")),
        "mdp": _str(row.get("mdp")),
        "mail_contact": _str(row.get("mail_contact")),
        "id_entite": _str(row.get("id_entite")),
    }


def list_codes_salarie(id_salarie: int) -> list[dict]:
    """Liste les partenaires deja codes pour le salarie (cf. ZR_ElemsFaits
    WinDev qui s'enrichit a chaque validation).

    Si le salarie a deja un DPAE_num (URSSAF deja valide auparavant pour
    une reprise type_dpae=3), URSSAF est ajoute en tete de la liste."""
    db_rh = get_pg_connection("rh")
    db_adv = get_pg_connection("adv")

    rows = db_rh.query(
        """SELECT id_partenaire, code, login, mdp, modif_date
             FROM rh.pgt_salarie_partenaire
            WHERE id_salarie = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY modif_date DESC""",
        (int(id_salarie),),
    ) or []

    parts = db_adv.query(
        "SELECT id_partenaire, lib_partenaire FROM adv.pgt_partenaire",
    ) or []
    lib_by_id = {_int(p.get("id_partenaire")): _str(p.get("lib_partenaire")) for p in parts}

    out: list[dict] = []
    # URSSAF marquee comme faite si dpae_num deja saisi sur salarie_embauche
    emb = db_rh.query_one(
        """SELECT dpae_num, dpae_date FROM rh.pgt_salarie_embauche
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if emb and _str(emb.get("dpae_num")).strip():
        out.append({
            "id_partenaire": "0",
            "lib_partenaire": "URSSAF",
            "code": _str(emb.get("dpae_num")),
            "login": "",
            "mdp": "",
        })

    for r in rows:
        id_p = _int(r.get("id_partenaire"))
        out.append({
            "id_partenaire": str(id_p),
            "lib_partenaire": lib_by_id.get(id_p) or f"#{id_p}",
            "code": _str(r.get("code")),
            "login": _str(r.get("login")),
            "mdp": _str(r.get("mdp")),
        })
    return out


def get_dpae_state(id_salarie: int) -> dict:
    """Etat URSSAF du salarie (dpae_num + dpae_date). Utilise pour
    pre-remplir le champ N° DPAE en reprise type_dpae=3."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT dpae_num, dpae_date FROM rh.pgt_salarie_embauche
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if not row:
        return {"dpae_num": "", "dpae_date": ""}
    return {
        "dpae_num": _str(row.get("dpae_num")),
        "dpae_date": _iso_date(row.get("dpae_date")),
    }


def update_dpae_urssaf(id_salarie: int, dpae_num: str, op_id: int) -> dict:
    """Btn 'Valider les infos URSSAF' du Plan 2 :
    UPDATE pgt_salarie_embauche.DPAE_num/date/Ope."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_embauche
              SET dpae_date = NOW()::date,
                  dpae_num = ?,
                  dpae_ope = ?,
                  modif_date = NOW()
            WHERE id_salarie = ?""",
        (dpae_num.strip(), int(op_id), int(id_salarie)),
    )
    return {"ok": True}


def save_codes_partenaire(
    id_salarie: int,
    id_partenaire: int,
    code: str,
    login: str,
    mdp: str,
    op_id: int,
) -> dict:
    """Btn 'Valider les codes Partenaires' : UPSERT pgt_salarie_partenaire."""
    db = get_pg_connection("rh")
    existing = db.query_one(
        """SELECT id_salarie_partenaire FROM rh.pgt_salarie_partenaire
            WHERE id_salarie = ? AND id_partenaire = ? LIMIT 1""",
        (int(id_salarie), int(id_partenaire)),
    )
    if existing:
        db.query(
            """UPDATE rh.pgt_salarie_partenaire
                  SET code = ?, login = ?, mdp = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_salarie_partenaire = ?""",
            (code, login, mdp, int(op_id),
             _int(existing.get("id_salarie_partenaire"))),
        )
    else:
        db.query(
            """INSERT INTO rh.pgt_salarie_partenaire
                  (id_salarie_partenaire, id_salarie, id_partenaire,
                   code, login, mdp, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (_new_id(), int(id_salarie), int(id_partenaire),
             code, login, mdp, int(op_id)),
        )
    return {"ok": True}


def envoyer_charte_ethique(
    id_salarie: int,
    id_partenaire: int,
    op_id: int,
) -> dict:
    """Btn 'Envoyer la charte Ethique' : cree TK_DemandeCodeVendeur +
    TK_Liste + TK_DemandeCodeVendeur_Fichier (CNI + Charte).

    Cf. WinDev : envoi mail RH + xlsx avec coordonnees. Pour V1, on
    cree juste les enregistrements de demande - le mail/xlsx pourra
    etre ajoute plus tard."""
    db_tk = get_pg_connection("ticket_bo")
    id_new = _new_id()

    db_tk.query(
        """INSERT INTO ticket_bo.pgt_tk_demande_code_vendeur
              (id_tk_demande_code_vendeur, id_tk_liste, type_ori,
               id_elem, id_partenaire, code, login, mdp,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, 'DPAE', ?, ?, '', '', '',
                   NOW(), ?, 'new')""",
        (id_new, id_new, int(id_salarie), int(id_partenaire), int(op_id)),
    )

    # TK_Liste (ticket de service BO, type 38 = demande code vendeur)
    db_tk.query(
        """INSERT INTO ticket_bo.pgt_tk_liste
              (id_tk_liste_auto, id_tk_liste, datecrea, op_crea, op_dest,
               op_traitement_staff, ordre_traitement_staff, service,
               id_tk_type_demande, id_tk_statut, cloturee,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, NOW(), ?, ?, 0, 0, 'BO',
                   38, 1, FALSE,
                   NOW(), ?, 'new')""",
        (id_new, id_new, int(op_id), int(op_id), int(op_id)),
    )
    return {"ok": True, "id_ticket": str(id_new)}


def terminer_dpae(id_salarie: int, id_ticket: int, op_id: int) -> dict:
    """Btn 'Terminer ma DPAE' : (re)applique les droits selon le poste
    + cloture le ticket DPAE source si fourni."""
    db_rh = get_pg_connection("rh")

    # Recharge le poste du salarie
    emb = db_rh.query_one(
        "SELECT id_type_poste FROM rh.pgt_salarie_embauche WHERE id_salarie = ? LIMIT 1",
        (int(id_salarie),),
    )
    if emb:
        id_poste = _int(emb.get("id_type_poste"))
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
                    id_d = _int(d.get("id_type_droit_acces"))
                    # UPSERT manuel (existe deja apres save_dpae pour les nouvelles
                    # DPAE - mais peut manquer pour les TypeDpae=3 reprises)
                    ex = db_rh.query_one(
                        """SELECT 1 FROM rh.pgt_salarie_droit_acces
                            WHERE id_salarie = ? AND id_type_droit_acces = ?
                            LIMIT 1""",
                        (int(id_salarie), id_d),
                    )
                    if not ex:
                        db_rh.query(
                            """INSERT INTO rh.pgt_salarie_droit_acces
                                  (id_salarie, id_type_droit_acces,
                                   droit_actif, modif_date, modif_op, modif_elem)
                               VALUES (?, ?, TRUE, NOW(), ?, 'new')""",
                            (int(id_salarie), id_d, int(op_id)),
                        )

    # Cloture le ticket DPAE source (cf. WinDev UPDATE TK_Liste)
    if id_ticket:
        try:
            db_tk = get_pg_connection("ticket_bo")
            db_tk.query(
                """UPDATE ticket_bo.pgt_tk_liste
                      SET cloturee = TRUE,
                          date_cloture = NOW(),
                          modif_date = NOW(),
                          modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_tk_liste = ?""",
                (int(op_id), int(id_ticket)),
            )
        except Exception:
            # ticket pas dans ticket_bo ? essaye ticket_dpae
            try:
                db_tkdpae = get_pg_connection("ticket_dpae")
                db_tkdpae.query(
                    """UPDATE ticket_dpae.pgt_tk_liste
                          SET cloturee = TRUE,
                              date_cloture = NOW(),
                              modif_date = NOW(),
                              modif_op = ?,
                              modif_elem = 'modif'
                        WHERE id_tk_liste = ?""",
                    (int(op_id), int(id_ticket)),
                )
            except Exception:
                pass
    return {"ok": True}


def recup_da_dr_mails(id_organigramme: int) -> list[str]:
    """Cf. WinDev RecupListeDaDr : pour chaque orga de la chaine id_parent,
    recupere les responsables actifs (resp_equipe / resp_adjoint, DateFin
    vide) et filtre ceux dont le poste contient 'Dir'."""
    if not id_organigramme:
        return []
    db = get_pg_connection("rh")
    ids: list[int] = []
    seen: set[int] = set()
    current = int(id_organigramme)
    while current and current not in seen and len(ids) < 10:
        seen.add(current)
        ids.append(current)
        row = db.query_one(
            """SELECT id_parent FROM rh.pgt_organigramme
                WHERE idorganigramme = ? LIMIT 1""",
            (current,),
        )
        if not row:
            break
        current = _int(row.get("id_parent"))
    if not ids:
        return []

    # Pour chaque orga, requete responsables actifs uniquement (cf. WinDev
    # ReqRespOrgaActif_byOrgaID : HLitPremier + DateFin=''). On collecte
    # par ordre de remontee (le DA le plus proche d'abord).
    mails_seen: set[str] = set()
    out: list[str] = []
    for oid in ids:
        rows = db.query(
            """SELECT sc.mail, tp.lib_poste
                 FROM rh.pgt_salarie_organigramme so
                 JOIN rh.pgt_salarie_embauche se
                      ON se.id_salarie = so.id_salarie
            LEFT JOIN rh.pgt_type_poste tp
                      ON tp.id_type_poste = se.id_type_poste
            LEFT JOIN rh.pgt_salarie_coordonnees sc
                      ON sc.id_salarie = so.id_salarie
                WHERE so.idorganigramme = ?
                  AND COALESCE(so.aff_actif, FALSE) = TRUE
                  AND so.date_fin IS NULL
                  AND COALESCE(se.en_activite, FALSE) = TRUE
                  AND (COALESCE(se.resp_equipe, FALSE) = TRUE
                       OR COALESCE(se.resp_adjoint, FALSE) = TRUE)""",
            (oid,),
        ) or []
        for r in rows:
            mail = _str(r.get("mail")).strip()
            poste = _str(r.get("lib_poste")).lower()
            if not mail or mail in mails_seen:
                continue
            if "dir" not in poste:
                continue
            mails_seen.add(mail)
            out.append(mail)
    return out


def envoyer_infos_partenaire(
    id_salarie: int,
    id_partenaire: int,
    lib_partenaire: str,
    code: str,
    login: str,
    mdp: str,
    dpae_num: str = "",
    op_id: int = 0,
    pdf_filename: str = "",
) -> dict:
    """envoieInfoPartenaire WinDev : SMS au candidat + mail HTML
    (avec eventuel PDF DPAE en PJ pour URSSAF).

    pdf_filename : nom du fichier DPAE stocke dans gestionRH/{id}/. Si
    fourni et URSSAF, telecharge depuis FTP et attache au mail.
    """
    # Import lazy pour eviter cycle (fiche_documents -> SMTP qui peut
    # importer dpae_nouvelle un jour)
    from app.intranets.adm.services import fiche_documents as docs_svc

    db_rh = get_pg_connection("rh")
    cv = db_rh.query_one(
        """SELECT tel_mob, mail FROM rh.pgt_salarie_coordonnees
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    gsm = _str(cv.get("tel_mob"))
    mail_candidat = _str(cv.get("mail"))

    sal = db_rh.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
        (int(id_salarie),),
    ) or {}
    nom = _str(sal.get("nom"))
    prenom = _str(sal.get("prenom"))
    prenom_cap = (prenom[:1].upper() + prenom[1:].lower()) if prenom else ""

    # Cc Directeurs de l'orga du salarie (cf. WinDev RecupListeDaDr)
    org = db_rh.query_one(
        """SELECT idorganigramme FROM rh.pgt_salarie_organigramme
            WHERE id_salarie = ? AND COALESCE(aff_actif, FALSE) = TRUE
         ORDER BY date_debut DESC LIMIT 1""",
        (int(id_salarie),),
    )
    mails_da = recup_da_dr_mails(_int((org or {}).get("idorganigramme")))

    lib_upper = lib_partenaire.upper()
    if lib_upper == "URSSAF":
        texte = (
            "Votre DPAE a ete faite aupres des URSSAF\n"
            "Vous recevrez une copie par mail\n"
            f"Num DPAE : {dpae_num}\n"
            "---\nCdt"
        )
        sujet = f"DPAE {nom} {prenom} du {datetime.now().strftime('%d/%m/%Y')}"
        html = (
            "<p>Bonjour,</p>"
            f"<p>La DPAE pour <b>{nom} {prenom_cap}</b> a été faite ce jour "
            "auprès des URSSAF :</p>"
            "<ul>"
            f"<li><b>N° de DUE :</b> {dpae_num}</li>"
            f"<li><b>Faite le :</b> {datetime.now().strftime('%d/%m/%Y')}</li>"
            "</ul>"
            "<p>Demande de casier judiciaire : "
            "<a href='https://casier-judiciaire.justice.gouv.fr/'>"
            "casier-judiciaire.justice.gouv.fr</a></p>"
            "<p>Cordialement.</p>"
            "<p><i>PS : Ceci est un mail automatique, ne pas répondre.</i></p>"
        )
    elif lib_upper == "IAG":
        texte = (
            "Votre inscription IAG est faite.\n"
            "A FAIRE OBLIGATOIREMENT DANS LES 72H :\n"
            "Formation IAG : https://formation.gestioniag.fr\n"
            f"Code IAG : {code}\n"
            "Demande casier judiciaire : "
            "https://casier-judiciaire.justice.gouv.fr\n"
            "---\nCdt"
        )
        sujet = f"Identifiant IAG {nom} {prenom}"
        html = (
            "<p>Bonjour,</p>"
            "<p>Votre inscription IAG est faite.</p>"
            "<p><b>A FAIRE OBLIGATOIREMENT DANS LES 72H :</b></p>"
            "<p>Formation IAG : "
            "<a href='https://formation.gestioniag.fr'>formation.gestioniag.fr</a></p>"
            "<ul>"
            f"<li><b>Code IAG :</b> {code}</li>"
            "</ul>"
            "<p>Demande de casier judiciaire : "
            "<a href='https://casier-judiciaire.justice.gouv.fr/'>"
            "casier-judiciaire.justice.gouv.fr</a></p>"
            "<p>Cordialement.</p>"
        )
    elif lib_upper == "ENI":
        texte = (
            "Votre inscription ENI est faite.\n"
            "Vous devez valider IMPERATIVEMENT dans les 24h le lien envoye "
            "sur votre mail.\n"
            "Sinon vous devrez attendre 72h pour un nouveau lien.\n"
            "---\nCdt"
        )
        sujet = f"Identifiant ENI {nom} {prenom}"
        html = (
            "<p>Bonjour,</p>"
            "<p>Votre inscription ENI est faite. Vous devez valider "
            "<b>IMPERATIVEMENT dans les 24h</b> le lien envoyé sur "
            f"<b>{mail_candidat}</b>.</p>"
            "<p>Sinon il faudra attendre 72h pour un nouveau lien.</p>"
            "<p>Cordialement.</p>"
        )
    else:
        texte = (
            f"Votre inscription {lib_partenaire} est faite.\n"
            f"Code : {code}\nLogin : {login}\nMDP : {mdp}\n"
            "---\nCdt"
        )
        sujet = f"Identifiant {lib_partenaire} {nom} {prenom}"
        html = (
            f"<p>Bonjour {prenom_cap},</p>"
            f"<p>Votre inscription <b>{lib_partenaire}</b> est faite :</p>"
            "<ul>"
            f"<li><b>Code :</b> {code}</li>"
            f"<li><b>Login :</b> {login}</li>"
            f"<li><b>MDP :</b> {mdp}</li>"
            "</ul>"
            "<p>Cordialement.</p>"
        )

    # SMS
    res_sms = ""
    if gsm:
        res_sms = envoi_sms(texte, gsm)

    # Mail (si candidat a un mail)
    res_mail = ""
    if mail_candidat:
        attachments = []
        if pdf_filename:
            pdf_content = docs_svc.download_file(id_salarie, "internes", pdf_filename)
            if pdf_content:
                attachments.append((pdf_filename, pdf_content))
        try:
            envoi_mail(
                sujet=sujet,
                html=html,
                destinataires=[mail_candidat],
                cc=mails_da or None,
                cci=["intranet@omaya.fr"],
                attachments=attachments or None,
            )
            res_mail = "envoye"
        except Exception as e:
            res_mail = f"erreur: {e}"

    return {
        "ok": True,
        "sms": res_sms,
        "mail": res_mail,
        "gsm": gsm,
        "mail_dest": mail_candidat,
        "cc_da": mails_da,
        "pj": pdf_filename if pdf_filename else "",
    }
