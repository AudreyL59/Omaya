"""
Solde De Tout Compte (SDTC) - service partage.

Transposition de Fen_SDTC WinDev (fenetre partagee au projet). Charge les
informations consolidees du salarie en partance : etat civil, embauche,
societe, sortie, mutuelle, date du dernier contrat. Les onglets contrats /
calcul commission / generation PDF-XLS-mail viendront dans des commits
ulterieurs.
"""

from app.core.database.pg import get_pg_connection
from app.shared.tickets.forms.sortie_rh import _date_dernier_ctt


def _str(v) -> str:
    return "" if v is None else str(v)


def _iso(v) -> str:
    """Date / datetime -> ISO 'YYYY-MM-DD'. Vide si None."""
    if v is None:
        return ""
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def _normalize_lib_sortie(lib_sortie: str) -> tuple[str, str]:
    """Transposition WinDev :
       si Contient(finS,'FPE') -> 'FIN DE PERIODE D'ESSAI A L'INITIATIVE DU [SALARIE/EMPLOYEUR]'
       si Contient(finS,'mission') -> 'DEMISSION'
       sinon -> 'LICENCIEMENT'

    Retourne (titre_normalise, kind) ou kind in ('fpe', 'demission', 'licenciement').
    """
    if not lib_sortie:
        return ("", "")
    lib_up = lib_sortie.upper()
    if "FPE" in lib_up:
        if "SALAR" in lib_up:
            return ("FIN DE PERIODE D'ESSAI A L'INITIATIVE DU SALARIE", "fpe")
        return ("FIN DE PERIODE D'ESSAI A L'INITIATIVE DE L'EMPLOYEUR", "fpe")
    if "MISSION" in lib_up:
        return ("DEMISSION", "demission")
    return ("LICENCIEMENT", "licenciement")


def load(id_salarie: int) -> dict:
    """Charge l'ensemble des donnees consolidees pour SDTC."""
    db_rh = get_pg_connection("rh")

    sal = db_rh.query_one(
        """SELECT s.id_salarie, s.nom, s.prenom, s.num_ss, s.date_naiss,
                  s.lieu_naiss, s.dep_naiss,
                  c.adresse1, c.adresse2, c.cp, c.ville,
                  se.date_debut AS date_embauche, se.date_anciennete,
                  se.id_ste,
                  soc.rs_interne, soc.raison_sociale
           FROM rh.pgt_salarie s
           LEFT JOIN rh.pgt_salarie_coordonnees c ON c.id_salarie = s.id_salarie
           LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
           LEFT JOIN rh.pgt_societe soc ON soc.id_ste = se.id_ste
           WHERE s.id_salarie = ?""",
        (int(id_salarie),),
    )
    if not sal:
        return {"found": False}

    nom = _str(sal.get("nom"))
    prenom = _str(sal.get("prenom"))
    lib_nom = f"{nom} {_capitalize(prenom)}".strip()
    lib_societe = _str(sal.get("rs_interne")) or _str(sal.get("raison_sociale"))

    # --- Sortie -----------------------------------------------------------
    sortie_row = db_rh.query_one(
        """SELECT ss.date_sortie_reelle, ss.courrier_date_envoi,
                  ss.courrier_num_suivi, ss.courrier_delai_prev,
                  ss.courrier_date_recep,
                  ss.mail_objet, ss.mail_contenu,
                  tss.lib_sortie
           FROM rh.pgt_salarie_sortie ss
           LEFT JOIN rh.pgt_type_sortie_salarie tss ON tss.id_type_sortie = ss.id_type_sortie
           WHERE ss.id_salarie = ?""",
        (int(id_salarie),),
    )
    sortie_data = {
        "date_sortie_reelle": "",
        "lib_sortie_raw": "",
        "titre_sortie": "",
        "kind": "",
        "courrier_info": "",
        "mail_objet": "",
        "mail_contenu": "",
    }
    if sortie_row:
        date_sortie = _iso(sortie_row.get("date_sortie_reelle"))
        lib_raw = _str(sortie_row.get("lib_sortie"))
        titre, kind = _normalize_lib_sortie(lib_raw)
        # Bloc courrier (FPE = envoi+delai / Dem = recu)
        courrier_info = ""
        if kind == "fpe":
            envoi = _iso(sortie_row.get("courrier_date_envoi"))
            delai = _str(sortie_row.get("courrier_delai_prev"))
            if envoi:
                courrier_info = f"(Courrier envoye le {envoi}"
                if delai:
                    courrier_info += f" + delai de prevenance : {delai}"
                courrier_info += ")"
        elif kind == "demission":
            recu = _iso(sortie_row.get("courrier_date_recep"))
            if recu:
                courrier_info = f"(Courrier recu le {recu})"
        sortie_data = {
            "date_sortie_reelle": date_sortie,
            "lib_sortie_raw": lib_raw,
            "titre_sortie": titre,
            "kind": kind,
            "courrier_info": courrier_info,
            "mail_objet": _str(sortie_row.get("mail_objet")),
            "mail_contenu": _str(sortie_row.get("mail_contenu")),
        }

    # --- Mutuelle ---------------------------------------------------------
    mut = db_rh.query_one(
        """SELECT mutuelle_doc_envoyes, adhesion_date
           FROM rh.pgt_salarie_mutuelle
           WHERE id_salarie = ?""",
        (int(id_salarie),),
    )
    info_mutuelle = "Non"
    if mut and mut.get("mutuelle_doc_envoyes"):
        info_mutuelle = "Oui"
        adh = _iso(mut.get("adhesion_date"))
        if adh:
            info_mutuelle += f", depuis le {adh}"

    # --- Date dernier ctt (tous partenaires) -----------------------------
    try:
        dernier_ctt = _date_dernier_ctt(int(id_salarie))
    except Exception:
        dernier_ctt = ""

    return {
        "found": True,
        "id_salarie": str(id_salarie),
        "salarie": {
            "nom": nom,
            "prenom": prenom,
            "lib_nom": lib_nom,
            "num_ss": _str(sal.get("num_ss")),
            "date_naiss": _iso(sal.get("date_naiss")),
            "lieu_naiss": _str(sal.get("lieu_naiss")),
            "dep_naiss": _str(sal.get("dep_naiss")),
            "adresse1": _str(sal.get("adresse1")),
            "adresse2": _str(sal.get("adresse2")),
            "cp": _str(sal.get("cp")),
            "ville": _str(sal.get("ville")),
            "date_embauche": _iso(sal.get("date_embauche")),
            "date_anciennete": _iso(sal.get("date_anciennete")),
            "id_ste": str(sal.get("id_ste") or ""),
            "lib_societe": lib_societe,
        },
        "sortie": sortie_data,
        "info_mutuelle": info_mutuelle,
        "date_dernier_ctt": dernier_ctt,
    }
