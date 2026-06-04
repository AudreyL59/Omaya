"""
Service Registre RH — transposition de la fenetre WinDev Fen_RegistreRH.

Source de donnees : PostgreSQL (schema rh) via get_pg_connection("rh").

La page WinDev affiche une combo Societe (filtre IDTypeOrga=1) + un tableau
jointure (salarie + coordonnees + embauche + sortie + type_poste) filtre
par IdSte. Tri par DateDebut DESC.
"""

from datetime import date, datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str_id(v: Any) -> str:
    """IDs 8 octets exposes en str (cf. feedback_ids_8octets_string)."""
    if v is None:
        return ""
    s = str(v).strip()
    return s if s and s != "0" else ""


def _iso(v: Any) -> str:
    """Date ou timestamp PG -> ISO 'YYYY-MM-DD' (vide si null/zero)."""
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


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def list_societes() -> list[dict]:
    """Combo Societe : filtre IDTypeOrga=1 (Internes), tri par RaisonSociale."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_ste, rs_interne, raison_sociale
        FROM rh.pgt_societe
        WHERE modif_elem NOT LIKE '%suppr%'
          AND id_type_orga = 1
        ORDER BY raison_sociale ASC NULLS LAST"""
    )
    return [
        {
            "id_ste": _str_id(r.get("id_ste")),
            "rs_interne": _str(r.get("rs_interne")) or _str(r.get("raison_sociale")),
        }
        for r in rows
    ]


def list_refs() -> dict:
    """Combos colonnes : type_ctt, type_horaire, type_sortie."""
    db = get_pg_connection("rh")

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


def list_salaries(id_ste: int) -> list[dict]:
    """
    Liste des salaries d'une societe.

    Transposition de la requete WinDev Table_ReqRegistreRH avec les jointures :
      salarie
      LEFT JOIN salarie_coordonnees ON id_salarie
      LEFT JOIN salarie_embauche    ON id_salarie
      LEFT JOIN type_poste          ON salarie_embauche.id_type_poste
      LEFT JOIN salarie_sortie      ON id_salarie
    WHERE salarie_embauche.id_ste = :id_ste AND salarie.modif_elem NOT LIKE '%suppr%'
    ORDER BY date_debut DESC.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
            s.id_salarie,
            s.civilite, s.nom, s.prenom, s.sexe, s.nationalite,
            s.date_naiss, s.lieu_naiss, s.dep_naiss,
            s.num_ss, s.cpam, s.num_cin, s.travailleur_handi,
            sc.adresse1, sc.adresse2, sc.cp, sc.ville,
            sc.tel_mob, sc.mail, sc.iban,
            sc.urg_nom, sc.urg_lien, sc.urg_tel,
            se.id_ste, se.date_debut, se.date_fin_per_essai,
            se.dpae_num, se.dpae_date,
            se.id_type_poste, tp.lib_poste,
            se.id_type_ctt, se.id_type_horaire,
            se.en_activite, se.coopte, se.coopteur,
            ss.date_sortie_demandee, ss.date_sortie_reelle,
            ss.demandeur_sortie, ss.id_type_sortie
        FROM rh.pgt_salarie s
        LEFT JOIN rh.pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
        LEFT JOIN rh.pgt_salarie_embauche se    ON se.id_salarie = s.id_salarie
        LEFT JOIN rh.pgt_type_poste tp          ON tp.id_type_poste = se.id_type_poste
        LEFT JOIN rh.pgt_salarie_sortie ss      ON ss.id_salarie = s.id_salarie
        WHERE se.id_ste = ?
          AND s.modif_elem NOT LIKE '%suppr%'
        ORDER BY se.date_debut DESC NULLS LAST""",
        (id_ste,),
    )
    return [
        {
            "id_salarie": _str_id(r.get("id_salarie")),
            "civilite": _int(r.get("civilite")),
            "nom": _str(r.get("nom")),
            "prenom": _str(r.get("prenom")),
            "sexe": _str(r.get("sexe")),
            "nationalite": _str(r.get("nationalite")),
            "date_naiss": _iso(r.get("date_naiss")),
            "lieu_naiss": _str(r.get("lieu_naiss")),
            "dep_naiss": _int(r.get("dep_naiss")),
            "num_ss": _str(r.get("num_ss")),
            "cpam": _str(r.get("cpam")),
            "num_cin": _str(r.get("num_cin")),
            "travailleur_handi": bool(r.get("travailleur_handi")),
            "adresse1": _str(r.get("adresse1")),
            "adresse2": _str(r.get("adresse2")),
            "cp": _str(r.get("cp")),
            "ville": _str(r.get("ville")),
            "tel_mob": _str(r.get("tel_mob")),
            "mail": _str(r.get("mail")),
            "iban": _str(r.get("iban")),
            "urg_nom": _str(r.get("urg_nom")),
            "urg_lien": _str(r.get("urg_lien")),
            "urg_tel": _str(r.get("urg_tel")),
            "id_ste": _str_id(r.get("id_ste")),
            "date_debut": _iso(r.get("date_debut")),
            "date_fin_per_essai": _iso(r.get("date_fin_per_essai")),
            "dpae_num": _str(r.get("dpae_num")),
            "dpae_date": _iso(r.get("dpae_date")),
            "id_type_poste": _int(r.get("id_type_poste")),
            "lib_poste": _str(r.get("lib_poste")),
            "id_type_ctt": _int(r.get("id_type_ctt")),
            "id_type_horaire": _int(r.get("id_type_horaire")),
            "en_activite": bool(r.get("en_activite")),
            "coopte": bool(r.get("coopte")),
            "coopteur": _str_id(r.get("coopteur")),
            "date_sortie_demandee": _iso(r.get("date_sortie_demandee")),
            "date_sortie_reelle": _iso(r.get("date_sortie_reelle")),
            "demandeur_sortie": _str_id(r.get("demandeur_sortie")),
            "id_type_sortie": _int(r.get("id_type_sortie")),
        }
        for r in rows
    ]
