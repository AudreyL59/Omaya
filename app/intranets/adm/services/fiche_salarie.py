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
            se.en_activite, se.en_pause, se.id_ste, se.id_type_poste,
            se.date_debut,
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


def set_en_pause(id_salarie: int, value: bool) -> dict:
    """Bascule le statut En pause (salarie_embauche.en_pause)."""
    db = get_pg_connection("rh")
    db.query(
        f"""UPDATE rh.pgt_salarie_embauche
        SET en_pause = {'TRUE' if value else 'FALSE'},
            modif_date = NOW()
        WHERE id_salarie = {_int(id_salarie)}"""
    )
    return {"ok": True}


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
