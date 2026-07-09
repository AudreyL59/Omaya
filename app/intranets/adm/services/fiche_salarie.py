"""
Service Fiche Salarie ADM — transposition de Fen_FicheSalarie WinDev.

Source de donnees : PostgreSQL (schema rh) via get_pg_connection("rh").

La page WinDev se compose d'un header (nom, prenom, statuts) + un menu
sidebar 14 items + une zone droite ChangeFenetreSource. Chaque item du menu
correspond a un sous-onglet (Identite, Coordonnees, Embauche, ...).

Cette session : header + onglet 1 (Identite). Les autres viendront iterativement.
"""

from datetime import date, datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str_id(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s if s and s != "0" else ""


def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _iso(v: Any) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, (date, datetime)):
        if v.year < 1900:
            return ""
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s or s.startswith("0000") or s.startswith("1900"):
        return ""
    return s[:10]


def _sql_str(v: Any) -> str:
    """Echappe les apostrophes pour SQL inline."""
    return str(v or "").replace("'", "''")


def load_photo(id_salarie: int) -> tuple[bytes, str] | None:
    """Retourne (bytes, content_type) ou None si pas de photo.

    Detecte le type d'image via les magic bytes (JPEG/PNG/GIF/WebP).
    Defaut : image/jpeg.
    """
    db = get_pg_connection("rh")
    row = db.query_one(
        "SELECT photo FROM rh.pgt_salarie WHERE id_salarie = ?",
        (id_salarie,),
    )
    if not row:
        return None
    blob = row.get("photo")
    if not blob:
        return None
    # psycopg2 renvoie bytea comme `memoryview` ou `bytes`
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return None
    if len(blob) < 8:
        return None

    # Magic bytes
    ct = "image/jpeg"
    if blob[:3] == b"\xff\xd8\xff":
        ct = "image/jpeg"
    elif blob[:8] == b"\x89PNG\r\n\x1a\n":
        ct = "image/png"
    elif blob[:6] in (b"GIF87a", b"GIF89a"):
        ct = "image/gif"
    elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        ct = "image/webp"
    elif blob[:2] == b"BM":
        ct = "image/bmp"

    return bytes(blob), ct


def load_header(id_salarie: int) -> dict:
    """Header de la fiche : id + identite + statut + societe + poste + embauche/sortie."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT
            s.id_salarie, s.civilite, s.nom, s.prenom,
            s.datecrea, s.op_crea, s.modif_date, s.modif_op,
            s.agenda_actif,
            se.en_activite, se.en_pause, se.id_absence,
            se.id_ste, se.id_type_poste, se.date_debut,
            soc.rs_interne, soc.raison_sociale,
            tp.lib_poste,
            ss.date_sortie_demandee, ss.date_sortie_reelle, ss.id_type_sortie,
            tss.lib_sortie
        FROM rh.pgt_salarie s
        LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
        LEFT JOIN rh.pgt_societe soc ON soc.id_ste = se.id_ste
        LEFT JOIN rh.pgt_type_poste tp ON tp.id_type_poste = se.id_type_poste
        LEFT JOIN rh.pgt_salarie_sortie ss ON ss.id_salarie = s.id_salarie
        LEFT JOIN rh.pgt_type_sortie_salarie tss ON tss.id_type_sortie = ss.id_type_sortie
        WHERE s.id_salarie = ?
          AND s.modif_elem NOT LIKE '%suppr%'""",
        (id_salarie,),
    )
    if not row:
        return {}
    return {
        "id_salarie": _str_id(row.get("id_salarie")),
        "nom": _str(row.get("nom")),
        "prenom": _str(row.get("prenom")),
        "civilite": _int(row.get("civilite")),
        # Photo servie via /api/adm/fiche-salarie/{id}/photo (404 si pas de photo).
        "photo_url": f"/api/adm/fiche-salarie/{id_salarie}/photo",
        "en_activite": bool(row.get("en_activite")),
        "en_pause": bool(row.get("en_pause")),
        "id_absence": _str_id(row.get("id_absence")),
        "agenda_actif": bool(row.get("agenda_actif")),
        "id_ste": _str_id(row.get("id_ste")),
        "rs_societe": _str(row.get("rs_interne")) or _str(row.get("raison_sociale")),
        "id_type_poste": _int(row.get("id_type_poste")),
        "lib_poste": _str(row.get("lib_poste")),
        # Embauche / sortie pour le bandeau (cf. WinDev CallbackInfoEmbauche)
        "date_debut": _iso(row.get("date_debut")),
        "date_sortie_demandee": _iso(row.get("date_sortie_demandee")),
        "date_sortie_reelle": _iso(row.get("date_sortie_reelle")),
        "lib_sortie": _str(row.get("lib_sortie")),
        # Tooltip "Fiche creee le ... / Derniere modif le ..."
        "datecrea": _iso(row.get("datecrea")),
        "op_crea": _str_id(row.get("op_crea")),
        "modif_date": _iso(row.get("modif_date")),
        "modif_op": _str_id(row.get("modif_op")),
    }


def load_identite(id_salarie: int) -> dict:
    """Onglet 1 : Infos Principales (FI_SalarieIdentite)."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT
            id_salarie, civilite, nom, nom_marital, prenom,
            sexe, nationalite, date_naiss, lieu_naiss, dep_naiss,
            num_ss, cpam, num_cin,
            situation_fam, avec_enfant, nb_enfants,
            travailleur_handi, matricule_tr, agenda_actif
        FROM rh.pgt_salarie
        WHERE id_salarie = ?
          AND modif_elem NOT LIKE '%suppr%'""",
        (id_salarie,),
    )
    if not row:
        return {}
    return {
        "id_salarie": _str_id(row.get("id_salarie")),
        "civilite": _int(row.get("civilite")),
        "nom": _str(row.get("nom")),
        "nom_marital": _str(row.get("nom_marital")),
        "prenom": _str(row.get("prenom")),
        "sexe": _str(row.get("sexe")),
        "nationalite": _str(row.get("nationalite")),
        "date_naiss": _iso(row.get("date_naiss")),
        "lieu_naiss": _str(row.get("lieu_naiss")),
        "dep_naiss": _int(row.get("dep_naiss")),
        "num_ss": _str(row.get("num_ss")),
        "cpam": _str(row.get("cpam")),
        "num_cin": _str(row.get("num_cin")),
        "situation_fam": _int(row.get("situation_fam")),
        "avec_enfant": bool(row.get("avec_enfant")),
        "nb_enfants": _int(row.get("nb_enfants")),
        "travailleur_handi": bool(row.get("travailleur_handi")),
        "matricule_tr": _str(row.get("matricule_tr")),
        "agenda_actif": bool(row.get("agenda_actif")),
    }


def save_identite(id_salarie: int, payload: dict) -> dict:
    """UPDATE pgt_salarie avec les modifs de l'onglet Identite (PATCH partiel)."""
    db = get_pg_connection("rh")
    sets = ["modif_date = NOW()"]

    def _quoted(key_pg: str, key_py: str):
        v = payload.get(key_py)
        sets.append(f"{key_pg} = '{_sql_str(v)}'")

    def _int_col(key_pg: str, key_py: str):
        sets.append(f"{key_pg} = {_int(payload.get(key_py))}")

    def _bool_col(key_pg: str, key_py: str):
        sets.append(f"{key_pg} = {'TRUE' if payload.get(key_py) else 'FALSE'}")

    if "civilite" in payload:
        _int_col("civilite", "civilite")
    if "nom" in payload:
        _quoted("nom", "nom")
    if "nom_marital" in payload:
        _quoted("nom_marital", "nom_marital")
    if "prenom" in payload:
        _quoted("prenom", "prenom")
    if "sexe" in payload:
        _quoted("sexe", "sexe")
    if "nationalite" in payload:
        _quoted("nationalite", "nationalite")
    if "date_naiss" in payload:
        d = payload.get("date_naiss") or ""
        if d:
            sets.append(f"date_naiss = '{d[:10]}'")
        else:
            sets.append("date_naiss = NULL")
    if "lieu_naiss" in payload:
        _quoted("lieu_naiss", "lieu_naiss")
    if "dep_naiss" in payload:
        _int_col("dep_naiss", "dep_naiss")
    if "num_ss" in payload:
        _quoted("num_ss", "num_ss")
    if "cpam" in payload:
        _quoted("cpam", "cpam")
    if "num_cin" in payload:
        _quoted("num_cin", "num_cin")
    if "situation_fam" in payload:
        _int_col("situation_fam", "situation_fam")
    if "avec_enfant" in payload:
        _bool_col("avec_enfant", "avec_enfant")
    if "nb_enfants" in payload:
        _int_col("nb_enfants", "nb_enfants")
    if "travailleur_handi" in payload:
        _bool_col("travailleur_handi", "travailleur_handi")
    if "matricule_tr" in payload:
        _quoted("matricule_tr", "matricule_tr")

    sql = f"""UPDATE rh.pgt_salarie SET {', '.join(sets)}
        WHERE id_salarie = {_int(id_salarie)}"""
    db.query(sql)
    return {"ok": True}


def set_en_activite(id_salarie: int, value: bool) -> dict:
    """Bascule le statut Actif/Inactif (salarie_embauche.en_activite)."""
    db = get_pg_connection("rh")
    db.query(
        f"""UPDATE rh.pgt_salarie_embauche
        SET en_activite = {'TRUE' if value else 'FALSE'},
            modif_date = NOW()
        WHERE id_salarie = {_int(id_salarie)}"""
    )
    return {"ok": True}


# Flags booleens directement modifiables sur pgt_salarie_embauche (whitelist)
_TOGGLABLE_EMBAUCHE_FLAGS = {"resp_equipe", "resp_adjoint", "chauffeur", "en_pause"}


def toggle_flag_embauche(
    id_salarie: int, field: str, value: bool, op_id: int,
) -> dict:
    """Bascule un des 4 flags booleens de pgt_salarie_embauche :
    resp_equipe, resp_adjoint, chauffeur, en_pause.

    Cf. WinDev menu contextuel salarie (Fen_Organigramme) : options
    activees/desactivees directement depuis la popup, sans autre dialogue.
    """
    if field not in _TOGGLABLE_EMBAUCHE_FLAGS:
        return {"ok": False, "err": f"Champ non modifiable : {field}"}
    db = get_pg_connection("rh")
    # Si en_pause -> False, on remet id_absence a 0 (cf. set_en_pause).
    extra = ""
    if field == "en_pause" and not value:
        extra = ", id_absence = 0"
    db.query(
        f"""UPDATE rh.pgt_salarie_embauche
               SET {field} = {'TRUE' if value else 'FALSE'}{extra},
                   modif_date = NOW(),
                   modif_op = {_int(op_id)},
                   modif_elem = 'modif'
             WHERE id_salarie = {_int(id_salarie)}""",
    )
    return {"ok": True, "field": field, "value": bool(value)}


def set_en_pause(id_salarie: int, value: bool, id_absence: int = 0) -> dict:
    """Bascule le statut En pause (salarie_embauche.en_pause).

    Cf. WinDev : EnPause et IdAbsence sont mis a jour ensemble.
    Activation : value=True + id_absence = absence venant d'etre creee.
    Desactivation : value=False + id_absence = 0.
    """
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie_embauche
              SET en_pause = ?,
                  id_absence = ?,
                  modif_date = NOW()
            WHERE id_salarie = ?""",
        (bool(value), int(id_absence or 0), int(id_salarie)),
    )
    return {"ok": True}


def set_agenda_actif(id_salarie: int, value: bool, op_id: int) -> dict:
    """Bascule pgt_salarie.agenda_actif (cf. Btn 'Agenda')."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_salarie
              SET agenda_actif = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_salarie = ?""",
        (bool(value), int(op_id), int(id_salarie)),
    )
    return {"ok": True, "agenda_actif": bool(value)}


def duplicate_salarie(id_salarie: int, op_id: int) -> dict:
    """Btn 'Dupliquer' : clone la fiche complete (salarie + embauche +
    coordonnees + sortie + mutuelle) avec un nouvel id.

    Cf. WinDev :
      - salarie : Nom = 'Z ' + Nom, LOGIN += '-old', ActiveLog = 0
      - embauche : meme contenu (copie a l'identique des 30+ champs)
      - coordonnees : meme contenu
      - sortie : creation vide (pour respecter le PK)
      - mutuelle : creation vide
    """
    db = get_pg_connection("rh")
    id_new = _new_ticket_id()  # YYYYMMDDHHMMSSmmm comme dans WinDev

    # 1. Cloner pgt_salarie
    db.query(
        """INSERT INTO rh.pgt_salarie
              (id_salarie, civilite, nom, nom_marital, prenom, sexe,
               nationalite, date_naiss, lieu_naiss, dep_naiss, num_ss,
               cpam, num_cin, situation_fam, avec_enfant, nb_enfants,
               travailleur_handi, matricule_tr, agenda_actif,
               op_crea, datecrea, photo, login, mdp_crypte,
               id_utilisateur, active_log,
               modif_date, modif_op, modif_elem)
           SELECT ?, civilite, ?, nom_marital, prenom, sexe,
                  nationalite, date_naiss, lieu_naiss, dep_naiss, num_ss,
                  cpam, num_cin, situation_fam, avec_enfant, nb_enfants,
                  travailleur_handi, matricule_tr, agenda_actif,
                  ?, NOW(), photo, COALESCE(login, '') || '-old', mdp_crypte,
                  id_utilisateur, FALSE,
                  NOW(), ?, 'new'
             FROM rh.pgt_salarie
            WHERE id_salarie = ?""",
        (
            int(id_new),
            "Z " + (load_header(id_salarie).get("nom") or ""),
            int(op_id),
            int(op_id),
            int(id_salarie),
        ),
    )

    # 2. Cloner pgt_salarie_embauche (sans id_salarie_embauche, PK genere)
    db.query(
        """INSERT INTO rh.pgt_salarie_embauche
              (id_salarie, date_debut, date_fin_per_essai, date_anciennete,
               en_activite, dpae_date, dpae_num, dpae_ope,
               id_type_poste, id_type_ctt, id_type_horaire,
               id_ste, id_ste_dpae_energie, id_ste_dpae_fibre,
               coopte, coopteur, j_odirecte, jo_coopteur,
               resp_equipe, resp_adjoint, chauffeur, multi_prod,
               en_pause, id_absence, id_cvtheque,
               cin_envoyee, cj_envoye,
               formation_iag, formation_iag_date,
               modif_date, modif_op, modif_elem)
           SELECT ?, date_debut, date_fin_per_essai, date_anciennete,
                  en_activite, dpae_date, dpae_num, dpae_ope,
                  id_type_poste, id_type_ctt, id_type_horaire,
                  id_ste, id_ste_dpae_energie, id_ste_dpae_fibre,
                  coopte, coopteur, j_odirecte, jo_coopteur,
                  resp_equipe, resp_adjoint, chauffeur, multi_prod,
                  en_pause, id_absence, id_cvtheque,
                  cin_envoyee, cj_envoye,
                  formation_iag, formation_iag_date,
                  NOW(), ?, 'new'
             FROM rh.pgt_salarie_embauche
            WHERE id_salarie = ?""",
        (int(id_new), int(op_id), int(id_salarie)),
    )

    # 3. Cloner pgt_salarie_coordonnees
    db.query(
        """INSERT INTO rh.pgt_salarie_coordonnees
              (id_salarie, adresse1, adresse2, cp, ville,
               tel_fixe, tel_mob, mail, mail2,
               urg_nom, urg_lien, urg_tel, iban, bic,
               modif_date, modif_op, modif_elem)
           SELECT ?, adresse1, adresse2, cp, ville,
                  tel_fixe, tel_mob, mail, mail2,
                  urg_nom, urg_lien, urg_tel, iban, bic,
                  NOW(), ?, 'new'
             FROM rh.pgt_salarie_coordonnees
            WHERE id_salarie = ?""",
        (int(id_new), int(op_id), int(id_salarie)),
    )

    # 4. Creer pgt_salarie_sortie vide (PK = id_salarie)
    db.query(
        """INSERT INTO rh.pgt_salarie_sortie
              (id_salarie, id_type_sortie, modif_date, modif_op, modif_elem)
           VALUES (?, 0, NOW(), ?, 'new')""",
        (int(id_new), int(op_id)),
    )

    # 5. Creer pgt_salarie_mutuelle vide (PK = id_salarie)
    db.query(
        """INSERT INTO rh.pgt_salarie_mutuelle
              (id_salarie, modif_date, modif_op, modif_elem)
           VALUES (?, NOW(), ?, 'new')""",
        (int(id_new), int(op_id)),
    )

    return {"ok": True, "id_salarie": str(id_new)}


# IDs et constantes WinDev partagees pour sortirSalarie
ID_PARTENAIRE_OHM = 562949953421321
SOCIETES_AVEC_JURISTE_ANNUL_DUE = {301, 312}


def _new_ticket_id() -> int:
    """Equivalent idEntierDateHeureSys WinDev : YYYYMMDDHHMMSSmmm en bigint."""
    now = datetime.now()
    return int(now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}")


def _ste_label(db_rh, id_ste: int) -> str:
    """Libelle d'une societe pour affichage dans le mail."""
    if not id_ste:
        return ""
    row = db_rh.query_one(
        "SELECT rs_interne, raison_sociale FROM rh.pgt_societe WHERE id_ste = ?",
        (id_ste,),
    )
    if not row:
        return ""
    return _str(row.get("rs_interne")) or _str(row.get("raison_sociale"))


def _poste_label(db_rh, id_type_poste: int) -> str:
    if not id_type_poste:
        return ""
    row = db_rh.query_one(
        "SELECT lib_poste FROM rh.pgt_type_poste WHERE id_type_poste = ?",
        (id_type_poste,),
    )
    return _str(row.get("lib_poste")) if row else ""


def _ctt_label(db_rh, id_type_ctt: int) -> str:
    if not id_type_ctt:
        return ""
    row = db_rh.query_one(
        "SELECT intitule FROM rh.pgt_type_ctt_travail WHERE id_type_ctt = ?",
        (id_type_ctt,),
    )
    return _str(row.get("intitule")) if row else ""


def _set_date(field: str, value: str) -> str:
    """SQL SET clause pour une date : NULL si vide, sinon 'YYYY-MM-DD'."""
    if value:
        return f"{field} = '{str(value)[:10]}'"
    return f"{field} = NULL"


def sortir_salarie(id_salarie: int, payload: dict, demandeur_id: int) -> dict:
    """Action de sortie d'un salarie (transposition WinDev sortirSalarie).

    Phase B complete :
    - B1 : UPDATE salarie_embauche + salarie_sortie avec tous les champs du
      formulaire (info_cpl, courrier_*, stc_*).
    - B2 : Creation TK_Liste + TK_DemandeSortieRH si TypeSortie > 1.
      Creation TK_DemandeCodeVendeur + TK_Liste si codes Ohm existent.
    - B3 : Envoi mail RH avec destinataires conditionnels (juriste si CDI/CDD,
      Cci si TypeSortie > 1, etc.).
    """
    type_sortie = _int(payload.get("type_sortie"))
    db_rh = get_pg_connection("rh")

    # Garantit l'existence des lignes
    for tbl in ("rh.pgt_salarie_embauche", "rh.pgt_salarie_sortie"):
        if not db_rh.query_one(f"SELECT 1 FROM {tbl} WHERE id_salarie = ?", (id_salarie,)):
            db_rh.query(
                f"INSERT INTO {tbl} (id_salarie, modif_date, modif_elem) "
                f"VALUES ({_int(id_salarie)}, NOW(), 'new')"
            )

    # --- B1.1 UPDATE salarie_embauche : EnActivite = FALSE -------------
    db_rh.query(
        f"""UPDATE rh.pgt_salarie_embauche SET
            en_activite = FALSE,
            modif_date = NOW(),
            modif_op = {_int(demandeur_id)},
            modif_elem = 'modif'
        WHERE id_salarie = {_int(id_salarie)}"""
    )

    # --- B1.2 UPDATE salarie_sortie ------------------------------------
    sortie_sets = [
        f"id_type_sortie = {type_sortie}",
        "date_sortie_demandee = NOW()",
        f"demandeur_sortie = {_int(demandeur_id)}",
        f"info_cpl = '{_sql_str(payload.get('info_cpl'))}'",
        _set_date("courrier_date_envoi", payload.get("courrier_date_envoi") or ""),
        f"courrier_num_suivi = '{_sql_str(payload.get('courrier_num_suivi'))}'",
        _set_date("courrier_date_recep", payload.get("courrier_date_recep") or ""),
        f"courrier_delai_prev = '{_sql_str(payload.get('courrier_delai_prev'))}'",
        _set_date("stc_date_envoi", payload.get("stc_date_envoi") or ""),
        f"stc_num_suivi = '{_sql_str(payload.get('stc_num_suivi'))}'",
        _set_date("stc_date_recep", payload.get("stc_date_recep") or ""),
        _set_date("stc_retourne_le", payload.get("stc_retourne_le") or ""),
        "modif_date = NOW()",
        f"modif_op = {_int(demandeur_id)}",
        "modif_elem = 'modif'",
    ]

    # Annul DUE : date_sortie_reelle = date_debut (cf. WinDev)
    emb = db_rh.query_one(
        """SELECT date_debut, date_fin_per_essai, dpae_num, id_type_poste,
            id_type_ctt, id_ste
        FROM rh.pgt_salarie_embauche WHERE id_salarie = ?""",
        (id_salarie,),
    )
    date_debut = emb.get("date_debut") if emb else None
    if type_sortie == 1 and date_debut:
        sortie_sets.append(f"date_sortie_reelle = '{_iso(date_debut)}'")

    db_rh.query(
        f"""UPDATE rh.pgt_salarie_sortie SET {', '.join(sortie_sets)}
        WHERE id_salarie = {_int(id_salarie)}"""
    )

    # --- B1.3 UPDATE salarie.modif_date --------------------------------
    db_rh.query(
        f"""UPDATE rh.pgt_salarie SET modif_date = NOW()
        WHERE id_salarie = {_int(id_salarie)}"""
    )

    # --- Recup salarie info pour le mail ------------------------------
    sal = db_rh.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
        (id_salarie,),
    )
    nom_salarie = f"{_str(sal.get('nom'))} {_capitalize_first(_str(sal.get('prenom')))}".strip() if sal else str(id_salarie)

    # Lib_Sortie pour le sujet
    type_sortie_row = db_rh.query_one(
        "SELECT lib_sortie FROM rh.pgt_type_sortie_salarie WHERE id_type_sortie = ?",
        (type_sortie,),
    )
    lib_sortie = _str(type_sortie_row.get("lib_sortie")) if type_sortie_row else f"Type {type_sortie}"

    id_ticket_codes_ohm = ""
    id_ticket_sortie = ""

    # --- B2.1 Si codes Ohm existent : TK_DemandeCodeVendeur + TK_Liste -
    try:
        sp = db_rh.query_one(
            f"""SELECT code, login, mdp
            FROM rh.pgt_salarie_partenaire
            WHERE id_partenaire = {ID_PARTENAIRE_OHM}
              AND id_salarie = ?
              AND mdp IS NOT NULL AND mdp <> ''
              AND modif_elem <> 'supp'""",
            (id_salarie,),
        )
        if sp:
            id_new = _new_ticket_id()
            id_ticket_codes_ohm = str(id_new)
            db_bo = get_pg_connection("ticket_bo")
            db_bo.query(
                f"""INSERT INTO ticket_bo.pgt_tk_demande_code_vendeur
                    (id_tk_demande_code_vendeur, id_tk_liste, type_ori,
                     id_elem, id_partenaire, code, login, mdp,
                     modif_date, modif_elem, modif_op)
                VALUES ({id_new}, {id_new}, 'DPAE',
                        {_int(id_salarie)}, {ID_PARTENAIRE_OHM},
                        '{_sql_str(sp.get('code'))}',
                        '{_sql_str(sp.get('login'))}',
                        '{_sql_str(sp.get('mdp'))}',
                        NOW(), 'new', {_int(demandeur_id)})"""
            )
            db_ticket = get_pg_connection("ticket")
            db_ticket.query(
                f"""INSERT INTO ticket.pgt_tk_liste
                    (id_tk_liste, id_tk_liste_auto, date_crea, op_crea, op_dest,
                     service, id_tk_type_demande, id_tk_statut,
                     cloturee, modif_date, modif_op, modif_elem,
                     op_traitement_staff, ordre_traitement_staff)
                VALUES ({id_new}, {id_new}, NOW(), {_int(demandeur_id)}, {_int(demandeur_id)},
                        'BO', 39, 1,
                        FALSE, NOW(), {_int(demandeur_id)}, 'new',
                        0, 0)"""
            )
    except Exception:
        traceback.print_exc(file=sys.stderr)

    # --- B2.2 Si TypeSortie > 1 : TK_Liste + TK_DemandeSortieRH -------
    if type_sortie > 1:
        try:
            id_ticket = _new_ticket_id()
            id_ticket_sortie = str(id_ticket)
            service = "BO" if type_sortie <= 4 else "JU"
            id_type_demande = 36 if type_sortie <= 4 else 37

            db_ticket = get_pg_connection("ticket")
            db_ticket.query(
                f"""INSERT INTO ticket.pgt_tk_liste
                    (id_tk_liste, id_tk_liste_auto, date_crea, op_crea, op_dest,
                     service, id_tk_type_demande, id_tk_statut,
                     cloturee, modif_date, modif_op, modif_elem,
                     op_traitement_staff, ordre_traitement_staff)
                VALUES ({id_ticket}, {id_ticket}, NOW(), {_int(demandeur_id)}, {_int(id_salarie)},
                        '{service}', {id_type_demande}, 1,
                        FALSE, NOW(), {_int(demandeur_id)}, 'new',
                        0, 0)"""
            )
            db_tkrh = get_pg_connection("ticket_rh")
            db_tkrh.query(
                f"""INSERT INTO ticket_rh.pgt_tk_demande_sortie_rh
                    (id_tk_demande_sortie_rh, id_tk_demande_sortie_rh_auto,
                     id_tk_liste, id_salarie, type_sortie,
                     info_cplt, doc_sortie,
                     modif_op, modif_date, modif_elem)
                VALUES ({id_ticket}, {id_ticket},
                        {id_ticket}, {_int(id_salarie)}, '{type_sortie}',
                        '', FALSE,
                        {_int(demandeur_id)}, NOW(), 'new')"""
            )
        except Exception:
            traceback.print_exc(file=sys.stderr)

    # --- B3 Envoi mail RH ----------------------------------------------
    mail_envoye = False
    try:
        from app.core.config import (
            MAIL_TECH, MAIL_SUPPORT, MAIL_RESP_RH,
            MAIL_RESP_JURISTE, MAIL_JURISTE_1, MAIL_JURISTE_2,
        )
        from app.shared.notifications.mail import envoi_mail_rh

        # Recup infos pour le mail
        id_ste = _int(emb.get("id_ste")) if emb else 0
        ste_lib = _ste_label(db_rh, id_ste)
        poste_lib = _poste_label(db_rh, _int(emb.get("id_type_poste"))) if emb else ""
        ctt_lib = _ctt_label(db_rh, _int(emb.get("id_type_ctt"))) if emb else ""
        type_ctt = _int(emb.get("id_type_ctt")) if emb else 0

        # Recup mail du demandeur
        dem_row = db_rh.query_one(
            """SELECT sc.mail FROM rh.pgt_salarie_coordonnees sc
            WHERE sc.id_salarie = ?""",
            (demandeur_id,),
        )
        mail_demandeur = _str(dem_row.get("mail")).lower() if dem_row else ""

        # Sujet
        sujet = f"{lib_sortie} pour {nom_salarie}"
        if type_ctt in (4, 5) and ctt_lib:
            sujet += f" ({ctt_lib})"

        # Destinataires (dedupes, sans le demandeur s'il est deja dans les fixes)
        dest_set = []
        def _add(addr):
            a = (addr or "").strip().lower()
            if a and a not in dest_set:
                dest_set.append(a)
        _add(mail_demandeur)
        if mail_demandeur != MAIL_TECH.lower():
            _add(MAIL_TECH)
        if mail_demandeur != MAIL_SUPPORT.lower():
            _add(MAIL_SUPPORT)
        if mail_demandeur != MAIL_RESP_RH.lower():
            _add(MAIL_RESP_RH)

        cci = []
        if type_ctt in (4, 5):
            if MAIL_JURISTE_1:
                cci.append(MAIL_JURISTE_1)
        if type_sortie > 1:
            cci.append("fpe@exosphere.fr")
            for j in (MAIL_JURISTE_1, MAIL_JURISTE_2, MAIL_RESP_JURISTE):
                if j and j not in cci:
                    cci.append(j)
        if type_sortie == 1 and id_ste in SOCIETES_AVEC_JURISTE_ANNUL_DUE:
            if MAIL_JURISTE_1 and MAIL_JURISTE_1 not in cci:
                cci.append(MAIL_JURISTE_1)

        # HTML du mail
        date_debut_fr = _date_fr(date_debut) if date_debut else ""
        fin_per_essai_fr = _date_fr(emb.get("date_fin_per_essai")) if emb else ""
        dpae_num = _str(emb.get("dpae_num")) if emb else ""

        html = '<font face="arial" style="font-size:10pt;"><p>Bonjour,</p>'
        html += f"<p>{lib_sortie} pour {nom_salarie}</p>"
        html += f"<p><b>Fiche N° :</b> {id_salarie}</p>"
        html += f"<p><b>Demande faite par :</b> {mail_demandeur or demandeur_id}</p>"
        if type_sortie > 1:
            html += "<p><b><u>Information Embauche :</u></b></p>"
            html += f"<p><b>Date embauche :</b> {date_debut_fr}<br/>"
            html += f"<b>Date de fin de période d'essai :</b> {fin_per_essai_fr}<br/>"
            html += f"<b>DPAE Num :</b> {dpae_num}<br/>"
            html += f"<b>Poste :</b> {poste_lib}<br/>"
            html += f"<b>Société :</b> {ste_lib}</p>"
        html += "<p>Cdt</p><p>Service RH EXOSPHERE</p></font>"

        if dest_set:
            mail_envoye = envoi_mail_rh(sujet, html, dest_set, cci or None)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        mail_envoye = False

    return {
        "ok": True,
        "mail_envoye": mail_envoye,
        "id_ticket_sortie": id_ticket_sortie,
        "id_ticket_codes_ohm": id_ticket_codes_ohm,
    }


def sortir_distrib(id_salarie: int, demandeur_id: int) -> dict:
    """Sortie DISTRIB (cf. WinDev sortirDistrib).

    Difference avec sortir_salarie :
    - IDTypeSortie = 0 (au lieu d'un type reel)
    - PAS d'envoi de mail
    - PAS de ticket TK_DemandeSortieRH
    - Mais garde : EnActivite=FALSE + ticket demande code Ohm si applicable
    """
    db_rh = get_pg_connection("rh")

    # Garantit l'existence des lignes
    for tbl in ("rh.pgt_salarie_embauche", "rh.pgt_salarie_sortie"):
        if not db_rh.query_one(
            f"SELECT 1 FROM {tbl} WHERE id_salarie = ?", (id_salarie,),
        ):
            db_rh.query(
                f"INSERT INTO {tbl} (id_salarie, modif_date, modif_elem) "
                f"VALUES ({_int(id_salarie)}, NOW(), 'new')",
            )

    # EnActivite = FALSE
    db_rh.query(
        f"""UPDATE rh.pgt_salarie_embauche SET
                en_activite = FALSE,
                modif_date = NOW(),
                modif_op = {_int(demandeur_id)},
                modif_elem = 'modif'
            WHERE id_salarie = {_int(id_salarie)}""",
    )

    # salarie_sortie : id_type_sortie = 0
    db_rh.query(
        f"""UPDATE rh.pgt_salarie_sortie SET
                id_type_sortie = 0,
                date_sortie_demandee = NOW(),
                demandeur_sortie = {_int(demandeur_id)},
                modif_date = NOW(),
                modif_op = {_int(demandeur_id)},
                modif_elem = 'modif'
            WHERE id_salarie = {_int(id_salarie)}""",
    )
    db_rh.query(
        f"""UPDATE rh.pgt_salarie SET modif_date = NOW()
            WHERE id_salarie = {_int(id_salarie)}""",
    )

    # Ticket demande code Ohm si le salarie a un code
    id_ticket_codes_ohm = ""
    try:
        sp = db_rh.query_one(
            f"""SELECT code, login, mdp
                 FROM rh.pgt_salarie_partenaire
                WHERE id_partenaire = {ID_PARTENAIRE_OHM}
                  AND id_salarie = ?
                  AND mdp IS NOT NULL AND mdp <> ''
                  AND modif_elem <> 'supp'""",
            (id_salarie,),
        )
        if sp:
            id_new = _new_ticket_id()
            id_ticket_codes_ohm = str(id_new)
            db_bo = get_pg_connection("ticket_bo")
            db_bo.query(
                f"""INSERT INTO ticket_bo.pgt_tk_demande_code_vendeur
                        (id_tk_demande_code_vendeur, id_tk_liste, type_ori,
                         id_elem, id_partenaire, code, login, mdp,
                         modif_date, modif_elem, modif_op)
                    VALUES ({id_new}, {id_new}, 'DPAE',
                            {_int(id_salarie)}, {ID_PARTENAIRE_OHM},
                            '{_sql_str(sp.get('code'))}',
                            '{_sql_str(sp.get('login'))}',
                            '{_sql_str(sp.get('mdp'))}',
                            NOW(), 'new', {_int(demandeur_id)})""",
            )
            db_ticket = get_pg_connection("ticket")
            db_ticket.query(
                f"""INSERT INTO ticket.pgt_tk_liste
                        (id_tk_liste, id_tk_liste_auto, date_crea,
                         op_crea, op_dest, service,
                         id_tk_type_demande, id_tk_statut,
                         cloturee, modif_date, modif_op, modif_elem,
                         op_traitement_staff, ordre_traitement_staff)
                    VALUES ({id_new}, {id_new}, NOW(),
                            {_int(demandeur_id)}, {_int(demandeur_id)},
                            'BO', 39, 1, FALSE,
                            NOW(), {_int(demandeur_id)}, 'new', 0, 0)""",
            )
    except Exception:
        traceback.print_exc(file=sys.stderr)

    return {
        "ok": True,
        "id_ticket_codes_ohm": id_ticket_codes_ohm,
    }


def _capitalize_first(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


def _date_fr(v: Any) -> str:
    """Format DD/MM/YYYY (vide si pas de date ou sentinelle 1900-01-01)."""
    from app.core.utils.sentinel_dates import is_sentinel
    if v is None or v == "" or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return ""


# --- Onglet 2 : Coordonnees ---------------------------------------------

def load_coordonnees(id_salarie: int) -> dict:
    """Charge les coordonnees du salarie. Cree la ligne si elle n'existe pas
    (comportement WinDev : HLitRecherche + HAjoute si pas trouve)."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_salarie, adresse1, adresse2, cp, ville,
            tel_fixe, tel_mob, mail, mail2,
            urg_nom, urg_lien, urg_tel, iban, bic
        FROM rh.pgt_salarie_coordonnees
        WHERE id_salarie = ?""",
        (id_salarie,),
    )
    if not row:
        # Premier acces : on cree une ligne vide pour respecter la contrainte
        # de cle primaire id_salarie. WinDev fait pareil avec HAjoute.
        db.query(
            f"""INSERT INTO rh.pgt_salarie_coordonnees
                (id_salarie, modif_date, modif_elem)
            VALUES ({_int(id_salarie)}, NOW(), 'new')"""
        )
        return {
            "id_salarie": _str_id(id_salarie),
            "adresse1": "", "adresse2": "", "cp": "", "ville": "",
            "tel_fixe": "", "tel_mob": "", "mail": "", "mail2": "",
            "urg_nom": "", "urg_lien": "", "urg_tel": "",
            "iban": "", "bic": "",
        }
    return {
        "id_salarie": _str_id(row.get("id_salarie")),
        "adresse1": _str(row.get("adresse1")),
        "adresse2": _str(row.get("adresse2")),
        "cp": _str(row.get("cp")),
        "ville": _str(row.get("ville")),
        "tel_fixe": _str(row.get("tel_fixe")),
        "tel_mob": _str(row.get("tel_mob")),
        "mail": _str(row.get("mail")),
        "mail2": _str(row.get("mail2")),
        "urg_nom": _str(row.get("urg_nom")),
        "urg_lien": _str(row.get("urg_lien")),
        "urg_tel": _str(row.get("urg_tel")),
        "iban": _str(row.get("iban")),
        "bic": _str(row.get("bic")),
    }


def _format_phone(v: str) -> str:
    """Equivalent ChaineFormate(..., ccSansAccent+ccSansEspace+ccSansPonctuationNiEspace).
    Garde uniquement les chiffres et le '+' de tete."""
    s = (v or "").strip()
    if not s:
        return ""
    keep = []
    for i, ch in enumerate(s):
        if ch.isdigit() or (i == 0 and ch == "+"):
            keep.append(ch)
    return "".join(keep)


def _format_mail(v: str) -> str:
    """Sans espaces, en minuscules."""
    return (v or "").replace(" ", "").lower()


# --- Onglet 3 : Infos Embauche ------------------------------------------

def list_embauche_refs() -> dict:
    """Combos pour l'onglet : societes (internes), postes, type_ctt,
    type_horaire, type_sortie."""
    db = get_pg_connection("rh")
    societes = db.query(
        """SELECT id_ste, rs_interne, raison_sociale
        FROM rh.pgt_societe
        WHERE modif_elem NOT LIKE '%suppr%'
          AND id_type_orga = 1
        ORDER BY raison_sociale ASC NULLS LAST"""
    )
    postes = db.query(
        """SELECT id_type_poste, lib_poste
        FROM rh.pgt_type_poste
        WHERE modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_poste ASC NULLS LAST"""
    )
    type_ctt = db.query(
        """SELECT id_type_ctt, intitule
        FROM rh.pgt_type_ctt_travail
        WHERE modif_elem NOT LIKE '%suppr%'
        ORDER BY intitule ASC NULLS LAST"""
    )
    type_horaire = db.query(
        """SELECT id_type_horaire, lib_horaire
        FROM rh.pgt_type_horaire_travail
        WHERE modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_horaire ASC NULLS LAST"""
    )
    type_sortie = db.query(
        """SELECT id_type_sortie, lib_sortie
        FROM rh.pgt_type_sortie_salarie
        WHERE modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_sortie ASC NULLS LAST"""
    )
    return {
        "societes": [
            {
                "id": _str_id(r.get("id_ste")),
                "label": _str(r.get("rs_interne")) or _str(r.get("raison_sociale")),
            }
            for r in societes
        ],
        "postes": [
            {"id": _int(r.get("id_type_poste")), "label": _str(r.get("lib_poste"))}
            for r in postes
        ],
        "type_ctt": [
            {"id": _int(r.get("id_type_ctt")), "label": _str(r.get("intitule"))}
            for r in type_ctt
        ],
        "type_horaire": [
            {"id": _int(r.get("id_type_horaire")), "label": _str(r.get("lib_horaire"))}
            for r in type_horaire
        ],
        "type_sortie": [
            {"id": _int(r.get("id_type_sortie")), "label": _str(r.get("lib_sortie"))}
            for r in type_sortie
        ],
    }


def _salarie_lib(db, id_salarie_str: str) -> str:
    """Petit helper pour afficher 'Nom Prenom' d'un coopteur."""
    sid = _int(id_salarie_str)
    if not sid:
        return ""
    row = db.query_one(
        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
        (sid,),
    )
    if not row:
        return ""
    return f"{_str(row.get('nom'))} {_str(row.get('prenom'))}".strip()


def load_embauche(id_salarie: int) -> dict:
    """Charge salarie_embauche + salarie_sortie. Cree les lignes si absentes
    (comportement WinDev avec HAjoute si HTrouve = Faux)."""
    db = get_pg_connection("rh")

    emb = db.query_one(
        """SELECT *
        FROM rh.pgt_salarie_embauche
        WHERE id_salarie = ?""",
        (id_salarie,),
    )
    if not emb:
        # Cree la ligne minimale
        db.query(
            f"""INSERT INTO rh.pgt_salarie_embauche
                (id_salarie, modif_date, modif_elem)
            VALUES ({_int(id_salarie)}, NOW(), 'new')"""
        )
        emb = {}

    sor = db.query_one(
        """SELECT *
        FROM rh.pgt_salarie_sortie
        WHERE id_salarie = ?""",
        (id_salarie,),
    )
    if not sor:
        db.query(
            f"""INSERT INTO rh.pgt_salarie_sortie
                (id_salarie, modif_date, modif_elem)
            VALUES ({_int(id_salarie)}, NOW(), 'new')"""
        )
        sor = {}

    coopteur_id = _str_id(emb.get("coopteur"))
    jo_coopteur_id = _str_id(emb.get("jo_coopteur"))

    return {
        "id_salarie": _str_id(id_salarie),
        # Embauche
        "date_debut": _iso(emb.get("date_debut")),
        "date_fin_per_essai": _iso(emb.get("date_fin_per_essai")),
        "date_anciennete": _iso(emb.get("date_anciennete")),
        "en_activite": bool(emb.get("en_activite")),
        "dpae_date": _iso(emb.get("dpae_date")),
        "dpae_num": _str(emb.get("dpae_num")),
        "dpae_ope": _str_id(emb.get("dpae_ope")),
        "id_type_poste": _int(emb.get("id_type_poste")),
        "id_type_ctt": _int(emb.get("id_type_ctt")),
        "id_type_horaire": _int(emb.get("id_type_horaire")),
        "id_ste": _str_id(emb.get("id_ste")),
        "id_ste_dpae_energie": _str_id(emb.get("id_ste_dpae_energie")),
        "id_ste_dpae_fibre": _str_id(emb.get("id_ste_dpae_fibre")),
        "coopte": bool(emb.get("coopte")),
        "coopteur": coopteur_id,
        "coopteur_lib": _salarie_lib(db, coopteur_id) if coopteur_id else "",
        "j_odirecte": bool(emb.get("j_odirecte")),
        "jo_coopteur": jo_coopteur_id,
        "jo_coopteur_lib": _salarie_lib(db, jo_coopteur_id) if jo_coopteur_id else "",
        "resp_equipe": bool(emb.get("resp_equipe")),
        "resp_adjoint": bool(emb.get("resp_adjoint")),
        "chauffeur": bool(emb.get("chauffeur")),
        "multi_prod": bool(emb.get("multi_prod")),
        "cin_envoyee": bool(emb.get("cin_envoyee")),
        "cj_envoye": bool(emb.get("cj_envoye")),
        "formation_iag": bool(emb.get("formation_iag")),
        "formation_iag_date": _iso(emb.get("formation_iag_date")),
        "formation_iag_score": _int(emb.get("formation_iag_score")),
        "id_cvtheque": _str_id(emb.get("id_cvtheque")),
        # Sortie
        "id_type_sortie": _int(sor.get("id_type_sortie")),
        "date_sortie_demandee": _iso(sor.get("date_sortie_demandee")),
        "date_sortie_reelle": _iso(sor.get("date_sortie_reelle")),
        "demandeur_sortie": _str_id(sor.get("demandeur_sortie")),
        "demandeur_sortie_lib": _salarie_lib(db, _str_id(sor.get("demandeur_sortie"))) if sor.get("demandeur_sortie") else "",
        "info_cpl": _str(sor.get("info_cpl")),
        "courrier_date_envoi": _iso(sor.get("courrier_date_envoi")),
        "courrier_num_suivi": _str(sor.get("courrier_num_suivi")),
        "courrier_date_recep": _iso(sor.get("courrier_date_recep")),
        "courrier_delai_prev": _str(sor.get("courrier_delai_prev")),
        "stc_date_envoi": _iso(sor.get("stc_date_envoi")),
        "stc_num_suivi": _str(sor.get("stc_num_suivi")),
        "stc_date_recep": _iso(sor.get("stc_date_recep")),
        "stc_retourne_le": _iso(sor.get("stc_retourne_le")),
    }


def save_embauche(id_salarie: int, payload: dict) -> dict:
    """UPDATE partiel sur pgt_salarie_embauche + pgt_salarie_sortie."""
    db = get_pg_connection("rh")

    # Garantit l'existence des lignes
    for tbl in ("rh.pgt_salarie_embauche", "rh.pgt_salarie_sortie"):
        if not db.query_one(f"SELECT 1 FROM {tbl} WHERE id_salarie = ?", (id_salarie,)):
            db.query(
                f"INSERT INTO {tbl} (id_salarie, modif_date, modif_elem) "
                f"VALUES ({_int(id_salarie)}, NOW(), 'new')"
            )

    # --- pgt_salarie_embauche ---
    emb_sets: list[str] = ["modif_date = NOW()", "modif_elem = 'modif'"]
    date_fields_emb = [
        "date_debut", "date_fin_per_essai", "date_anciennete", "dpae_date",
        "formation_iag_date",
    ]
    text_fields_emb = ["dpae_num"]
    int_fields_emb = ["id_type_poste", "id_type_ctt", "id_type_horaire",
                      "formation_iag_score"]
    bigint_str_fields_emb = ["dpae_ope", "id_ste", "id_ste_dpae_energie",
                             "id_ste_dpae_fibre", "coopteur", "jo_coopteur",
                             "id_cvtheque"]
    bool_fields_emb = ["en_activite", "coopte", "j_odirecte", "resp_equipe",
                       "resp_adjoint", "chauffeur", "multi_prod",
                       "cin_envoyee", "cj_envoye", "formation_iag"]

    for f in date_fields_emb:
        if f in payload:
            v = payload.get(f)
            if v:
                emb_sets.append(f"{f} = '{str(v)[:10]}'")
            else:
                emb_sets.append(f"{f} = NULL")
    for f in text_fields_emb:
        if f in payload:
            emb_sets.append(f"{f} = '{_sql_str(payload.get(f))}'")
    for f in int_fields_emb:
        if f in payload:
            emb_sets.append(f"{f} = {_int(payload.get(f))}")
    for f in bigint_str_fields_emb:
        if f in payload:
            v = _int(payload.get(f))
            emb_sets.append(f"{f} = {v if v else 'NULL'}")
    for f in bool_fields_emb:
        if f in payload:
            emb_sets.append(f"{f} = {'TRUE' if payload.get(f) else 'FALSE'}")

    db.query(
        f"""UPDATE rh.pgt_salarie_embauche SET {', '.join(emb_sets)}
        WHERE id_salarie = {_int(id_salarie)}"""
    )

    # --- pgt_salarie_sortie ---
    sor_sets: list[str] = ["modif_date = NOW()", "modif_elem = 'modif'"]
    date_fields_sor = [
        "date_sortie_demandee", "date_sortie_reelle",
        "courrier_date_envoi", "courrier_date_recep",
        "stc_date_envoi", "stc_date_recep", "stc_retourne_le",
    ]
    text_fields_sor = ["info_cpl", "courrier_num_suivi", "courrier_delai_prev",
                       "stc_num_suivi"]
    int_fields_sor = ["id_type_sortie"]

    sor_touched = False
    for f in date_fields_sor:
        if f in payload:
            v = payload.get(f)
            if v:
                sor_sets.append(f"{f} = '{str(v)[:10]}'")
            else:
                sor_sets.append(f"{f} = NULL")
            sor_touched = True
    for f in text_fields_sor:
        if f in payload:
            sor_sets.append(f"{f} = '{_sql_str(payload.get(f))}'")
            sor_touched = True
    for f in int_fields_sor:
        if f in payload:
            sor_sets.append(f"{f} = {_int(payload.get(f))}")
            sor_touched = True

    if sor_touched:
        db.query(
            f"""UPDATE rh.pgt_salarie_sortie SET {', '.join(sor_sets)}
            WHERE id_salarie = {_int(id_salarie)}"""
        )

    return {"ok": True}


# --- Overlay "S'Cool" : fiche Formateur ---------------------------------

def load_formateur(id_salarie: int) -> dict:
    """Charge la fiche formateur du salarie (schema scool).

    Retourne exists=False si pas encore enregistree (cas WinDev HTrouve = Faux).
    """
    db = get_pg_connection("scool")
    row = db.query_one(
        """SELECT id_formateur, niveau, formateur_actif
        FROM scool.pgt_formateur
        WHERE id_formateur = ?""",
        (id_salarie,),
    )
    if not row:
        return {
            "id_formateur": _str_id(id_salarie),
            "niveau": 0,
            "formateur_actif": False,
            "exists": False,
        }
    return {
        "id_formateur": _str_id(row.get("id_formateur")),
        "niveau": _int(row.get("niveau")),
        "formateur_actif": bool(row.get("formateur_actif")),
        "exists": True,
    }


def save_formateur(id_salarie: int, payload: dict, op_id: int) -> dict:
    """Enregistre la fiche formateur (INSERT si pas existante, UPDATE sinon)."""
    db = get_pg_connection("scool")
    exists = db.query_one(
        "SELECT 1 FROM scool.pgt_formateur WHERE id_formateur = ?",
        (id_salarie,),
    )
    if not exists:
        # INSERT : niveau = payload.get('niveau') ou 1 par defaut (cf. WinDev)
        niveau = _int(payload.get("niveau", 1)) or 1
        actif = bool(payload.get("formateur_actif", False))
        db.query(
            f"""INSERT INTO scool.pgt_formateur
                (id_formateur, niveau, formateur_actif, modif_date, modif_op, modif_elem)
            VALUES ({_int(id_salarie)}, {niveau}, {'TRUE' if actif else 'FALSE'},
                    NOW(), {_int(op_id)}, 'new')"""
        )
        return {"ok": True}

    # UPDATE partiel
    sets = ["modif_date = NOW()", "modif_elem = 'modif'", f"modif_op = {_int(op_id)}"]
    if "niveau" in payload:
        sets.append(f"niveau = {_int(payload.get('niveau'))}")
    if "formateur_actif" in payload:
        sets.append(
            f"formateur_actif = {'TRUE' if payload.get('formateur_actif') else 'FALSE'}"
        )
    db.query(
        f"""UPDATE scool.pgt_formateur SET {', '.join(sets)}
        WHERE id_formateur = {_int(id_salarie)}"""
    )
    return {"ok": True}


# --- Overlays embauche : Partenaires + DPAE -----------------------------

def list_salarie_portails(id_salarie: int) -> list[dict]:
    """Liste des portails partenaire du salarie (login + mdp par partenaire).

    JOIN avec adv.pgt_partenaire pour avoir le libelle.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
            sp.id_salarie_partenaire, sp.id_partenaire,
            sp.code, sp.login, sp.mdp,
            p.lib_partenaire
        FROM rh.pgt_salarie_partenaire sp
        LEFT JOIN adv.pgt_partenaire p ON p.id_partenaire = sp.id_partenaire
        WHERE sp.modif_elem NOT LIKE '%suppr%'
          AND sp.id_salarie = ?
        ORDER BY p.lib_partenaire ASC NULLS LAST""",
        (id_salarie,),
    )
    return [
        {
            "id_salarie_partenaire": _str_id(r.get("id_salarie_partenaire")),
            "id_partenaire": _str_id(r.get("id_partenaire")),
            "lib_partenaire": _str(r.get("lib_partenaire")),
            "code": _str(r.get("code")),
            "login": _str(r.get("login")),
            "mdp": _str(r.get("mdp")),
        }
        for r in rows
    ]


def list_salarie_part_dpae(id_salarie: int) -> list[dict]:
    """Liste des associations 'societe DPAE par partenaire' pour le salarie."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
            spd.id_salarie_partenaire, spd.id_partenaire, spd.id_ste,
            p.lib_partenaire,
            soc.rs_interne, soc.raison_sociale
        FROM rh.pgt_salarie_part_dpae spd
        LEFT JOIN adv.pgt_partenaire p ON p.id_partenaire = spd.id_partenaire
        LEFT JOIN rh.pgt_societe soc ON soc.id_ste = spd.id_ste
        WHERE spd.modif_elem NOT LIKE '%suppr%'
          AND spd.id_salarie = ?
        ORDER BY p.lib_partenaire ASC NULLS LAST""",
        (id_salarie,),
    )
    return [
        {
            "id_salarie_partenaire": _str_id(r.get("id_salarie_partenaire")),
            "id_partenaire": _str_id(r.get("id_partenaire")),
            "lib_partenaire": _str(r.get("lib_partenaire")),
            "id_ste": _str_id(r.get("id_ste")),
            "rs_societe": _str(r.get("rs_interne")) or _str(r.get("raison_sociale")),
        }
        for r in rows
    ]


def delete_salarie_part_dpae(id_salarie_partenaire: int, op_id: int) -> dict:
    """Suppression logique (ModifElem='suppr') d'une association Partenaire-Ste DPAE."""
    db = get_pg_connection("rh")
    db.query(
        f"""UPDATE rh.pgt_salarie_part_dpae SET
            modif_date = NOW(),
            modif_elem = 'suppr',
            modif_op = {_int(op_id)}
        WHERE id_salarie_partenaire = {_int(id_salarie_partenaire)}"""
    )
    return {"ok": True}


def send_portail_codes(id_salarie_partenaire: int, demandeur_id: int) -> dict:
    """Renvoie les codes d'un portail partenaire au salarie (mail + SMS).

    Transposition du bouton WinDev "Renvoyer les codes" de l'overlay Partenaires
    de la fiche salarie ADM.

    Retourne {ok, mail_envoye, sms_envoye, sms_result, error?}.
    """
    db_rh = get_pg_connection("rh")

    # 1. Recuperer le portail + libelle partenaire + infos salarie
    row = db_rh.query_one(
        """SELECT
            sp.id_salarie_partenaire, sp.id_salarie, sp.id_partenaire,
            sp.code, sp.login, sp.mdp,
            p.lib_partenaire,
            s.nom, s.prenom,
            sc.mail, sc.tel_mob
        FROM rh.pgt_salarie_partenaire sp
        LEFT JOIN adv.pgt_partenaire p ON p.id_partenaire = sp.id_partenaire
        LEFT JOIN rh.pgt_salarie s ON s.id_salarie = sp.id_salarie
        LEFT JOIN rh.pgt_salarie_coordonnees sc ON sc.id_salarie = sp.id_salarie
        WHERE sp.id_salarie_partenaire = ?""",
        (id_salarie_partenaire,),
    )
    if not row:
        return {"ok": False, "error": "Portail introuvable"}

    nom = _str(row.get("nom"))
    prenom = _str(row.get("prenom"))
    nom_prenom = f"{nom} {_capitalize_first(prenom)}".strip()
    mail = _str(row.get("mail")).lower()
    gsm_raw = _str(row.get("tel_mob"))
    lib_partenaire = _str(row.get("lib_partenaire"))
    code = _str(row.get("code"))
    login = _str(row.get("login"))
    mdp = _str(row.get("mdp"))

    # 2. Envoi mail
    mail_envoye = False
    mail_err = ""
    if mail:
        try:
            from app.core.config import MAIL_SUPPORT
            from app.shared.notifications.mail import envoi_mail_rh

            sujet = f"Vos Codes {lib_partenaire}"
            html = (
                '<font face="arial" style="font-size:10pt;">'
                '<p>Bonjour,</p>'
                f'<p>{nom_prenom} :<br/>'
                '<ul>'
                f'<li><b>Partenaire :</b> {lib_partenaire}</li>'
                f'<li><b>Code :</b> {code}</li>'
                f'<li><b>Login :</b> {login}</li>'
                f'<li><b>Mdp :</b> {mdp}</li>'
                '</ul>'
                '</p><br/>---'
                'Cdt.<br/>'
                '<p><i>PS : Ceci est un mail automatique, ne pas répondre. Merci.</i></p>'
                '</font>'
            )
            cci = [MAIL_SUPPORT] if MAIL_SUPPORT else []
            mail_envoye = envoi_mail_rh(sujet, html, [mail], cci)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            mail_err = f"{type(e).__name__}: {e}"

    # 3. Envoi SMS (numero normalise sans separateurs)
    sms_envoye = False
    sms_result = ""
    if gsm_raw:
        try:
            from app.shared.notifications.sms import envoi_sms
            gsm = "".join(c for c in gsm_raw if c.isdigit() or c == "+")
            texte = (
                f"Vos codes {lib_partenaire}\n"
                f"Code : {code}\n"
                f"Login : {login}\n"
                f"MDP : {mdp}"
            )
            sms_result = envoi_sms(texte, gsm, "", "OMAYA-Info")
            # Le service envoi_sms renvoie une chaine ; succes = pas de mot "erreur"
            low = sms_result.lower()
            sms_envoye = "envoy" in low and "erreur" not in low and "non config" not in low
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            sms_result = f"{type(e).__name__}: {e}"

    return {
        "ok": mail_envoye or sms_envoye,
        "mail_envoye": mail_envoye,
        "mail_err": mail_err,
        "sms_envoye": sms_envoye,
        "sms_result": sms_result,
    }


def save_coordonnees(id_salarie: int, payload: dict) -> dict:
    """UPDATE pgt_salarie_coordonnees (PATCH partiel).

    Applique les normalisations WinDev sur tel_fixe / tel_mob / mail
    (les champs absents du payload restent inchanges).
    """
    db = get_pg_connection("rh")

    # Garantit l'existence de la ligne (idem load_coordonnees)
    exists = db.query_one(
        "SELECT 1 FROM rh.pgt_salarie_coordonnees WHERE id_salarie = ?",
        (id_salarie,),
    )
    if not exists:
        db.query(
            f"""INSERT INTO rh.pgt_salarie_coordonnees
                (id_salarie, modif_date, modif_elem)
            VALUES ({_int(id_salarie)}, NOW(), 'new')"""
        )

    sets = ["modif_date = NOW()", "modif_elem = 'modif'"]
    text_fields = ["adresse1", "adresse2", "cp", "ville",
                   "urg_nom", "urg_lien", "urg_tel", "iban", "bic", "mail2"]
    for f in text_fields:
        if f in payload:
            sets.append(f"{f} = '{_sql_str(payload.get(f))}'")
    # Normalisations specifiques
    if "tel_fixe" in payload:
        sets.append(f"tel_fixe = '{_sql_str(_format_phone(payload.get('tel_fixe') or ''))}'")
    if "tel_mob" in payload:
        sets.append(f"tel_mob = '{_sql_str(_format_phone(payload.get('tel_mob') or ''))}'")
    if "mail" in payload:
        sets.append(f"mail = '{_sql_str(_format_mail(payload.get('mail') or ''))}'")

    db.query(
        f"""UPDATE rh.pgt_salarie_coordonnees SET {', '.join(sets)}
        WHERE id_salarie = {_int(id_salarie)}"""
    )
    return {"ok": True}
