"""
Service Fen_DPAE_Recherche (ADM, btn Loupe).

Recherche par nom/prenom OU mobile dans la cvtheque et le registre RH.
Renvoie une liste unifiee triee par date d'entree/RDV decroissante.

Logique transposee du WinDev (cf. code Btn Loupe Fen_DPAE_Recherche).
"""

from __future__ import annotations

import re
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
    """Date PG (datetime/date/str) -> 'YYYY-MM-DD' ou ''."""
    if v is None or v == "":
        return ""
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _capitalize(s: str) -> str:
    return (s[:1].upper() + s[1:].lower()) if s else ""


def _format_tel(tel: str) -> str:
    """Equivalent FormateNumTel WinDev : ne garde que les chiffres
    (la requete LIKE %xxx% se charge du wildcard)."""
    return re.sub(r"\D", "", tel or "")


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------


def search(nom: str, prenom: str, gsm: str) -> list[dict]:
    """Cherche dans cvtheque + registre RH (cf. WinDev Btn Loupe).

    Si gsm est renseigne : prio sur les telephones.
    Sinon : filtre par nom + prenom (LIKE %x%).
    """
    nom = (nom or "").strip()
    prenom = (prenom or "").strip()
    gsm_clean = _format_tel(gsm)

    db_rh = get_pg_connection("rh")
    db_rec = get_pg_connection("recrutement")
    db_div = get_pg_connection("divers")

    # --- 1. Registre RH (salaries) ---------------------------------------
    if gsm_clean:
        where_sal = "AND (sc.tel_mob LIKE ? OR sc.tel_fixe LIKE ?)"
        params_sal: tuple = (f"%{gsm_clean}%", f"%{gsm_clean}%")
    else:
        where_sal = "AND s.nom ILIKE ? AND s.prenom ILIKE ?"
        params_sal = (f"%{nom}%", f"%{prenom}%")

    sql_sal = f"""
        SELECT s.id_salarie, s.nom, s.prenom,
               sc.tel_mob, sc.tel_fixe, sc.cp, sc.ville,
               se.en_activite, se.date_debut
          FROM rh.pgt_salarie s
          JOIN rh.pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
          JOIN rh.pgt_salarie_embauche    se ON se.id_salarie = s.id_salarie
         WHERE (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
           {where_sal}
    """
    rows_sal = db_rh.query(sql_sal, params_sal) or []

    out: list[dict] = []
    for r in rows_sal:
        id_sal = _int(r.get("id_salarie"))
        en_activite = bool(r.get("en_activite"))
        infos = ""
        if en_activite:
            infos = "ATTENTION, toujours en activité"
        else:
            sortie = db_rh.query_one(
                """SELECT ss.date_sortie_demandee, ts.lib_sortie
                     FROM rh.pgt_salarie_sortie ss
                LEFT JOIN rh.pgt_type_sortie_salarie ts
                       ON ts.id_type_sortie = ss.id_type_sortie
                    WHERE ss.id_salarie = ?
                 ORDER BY ss.date_sortie_demandee DESC
                    LIMIT 1""",
                (id_sal,),
            )
            if sortie:
                ds = _iso_date(sortie.get("date_sortie_demandee"))
                ds_fr = f"{ds[8:10]}/{ds[5:7]}/{ds[0:4]}" if ds else ""
                lib = _str(sortie.get("lib_sortie"))
                infos = f"Sortie le {ds_fr}, {lib}".rstrip(", ")

        out.append({
            "origine": "Registre RH",
            "id_elem": str(id_sal),
            "id_cv_suivi": "",
            "identite": f"{_str(r.get('nom'))} {_capitalize(_str(r.get('prenom')))}".strip(),
            "cp": _str(r.get("cp")),
            "ville": _str(r.get("ville")),
            "date_entree_rdv": _iso_date(r.get("date_debut")),
            "en_activite": en_activite,
            "infos_cplt": infos,
            "ligne_rdv": False,
        })

    # --- 2. CVtheque ------------------------------------------------------
    if gsm_clean:
        where_cv = "AND cv.gsm LIKE ?"
        params_cv: tuple = (f"%{gsm_clean}%",)
    else:
        where_cv = "AND cv.nom ILIKE ? AND cv.prenom ILIKE ?"
        params_cv = (f"%{nom}%", f"%{prenom}%")

    sql_cv = f"""
        SELECT cv.id_cvtheque, cv.id_communes_france, cv.nom, cv.prenom,
               cv.gsm, cv.id_cvsource, cv.id_elem_source, cv.date_saisie,
               cs.lib_source
          FROM recrutement.pgt_cvtheque cv
          JOIN recrutement.pgt_cv_source cs ON cs.id_cvsource = cv.id_cvsource
         WHERE (cv.modif_elem IS NULL OR cv.modif_elem <> 'suppr')
           {where_cv}
    """
    rows_cv = db_rec.query(sql_cv, params_cv) or []

    for r in rows_cv:
        id_cvtheque = _int(r.get("id_cvtheque"))
        id_commune = _int(r.get("id_communes_france"))
        cp = ville = ""
        if id_commune:
            cmn = db_div.query_one(
                """SELECT code_postal, nom_ville
                     FROM divers.pgt_communes_france
                    WHERE id_communes_france = ? LIMIT 1""",
                (id_commune,),
            )
            if cmn:
                cp = _str(cmn.get("code_postal"))
                ville = _str(cmn.get("nom_ville"))

        lib_source = _str(r.get("lib_source"))
        infos = lib_source
        if _int(r.get("id_cvsource")) == 1:
            id_coop = _int(r.get("id_elem_source"))
            if id_coop:
                coop = db_rh.query_one(
                    "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                    (id_coop,),
                )
                if coop:
                    infos += f" de {_str(coop.get('nom'))} {_capitalize(_str(coop.get('prenom')))}"

        date_saisie_iso = _iso_date(r.get("date_saisie"))
        if date_saisie_iso:
            infos += f" ({date_saisie_iso[8:10]}/{date_saisie_iso[5:7]}/{date_saisie_iso[0:4]})"

        # ReqCvDateDernierRDV : dernier RDV non supprime du candidat
        rdv = db_rec.query_one(
            """SELECT ae.id_agenda_evenement, ae.id_salarie,
                      ae.id_cv_suivi, cs.id_cvtheque,
                      ae.date_debut
                 FROM recrutement.pgt_cvsuivi cs
                 JOIN recrutement.pgt_agenda_evenement ae
                   ON ae.id_cv_suivi = cs.id_cv_suivi
                WHERE cs.id_cvtheque = ?
                  AND (ae.modif_elem IS NULL OR ae.modif_elem NOT LIKE '%suppr%')
             ORDER BY ae.date_debut DESC
                LIMIT 1""",
            (id_cvtheque,),
        )

        date_rdv = ""
        id_cv_suivi = ""
        ligne_rdv = False
        if rdv:
            date_rdv = _iso_date(rdv.get("date_debut"))
            id_cv_suivi = str(_int(rdv.get("id_cv_suivi")) or "")
            ligne_rdv = True
            id_op = _int(rdv.get("id_salarie"))
            if id_op:
                op = db_rh.query_one(
                    "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                    (id_op,),
                )
                if op:
                    infos += f" - RDV avec {_str(op.get('nom'))} {_capitalize(_str(op.get('prenom')))}"

        out.append({
            "origine": "CV",
            "id_elem": str(id_cvtheque),
            "id_cv_suivi": id_cv_suivi,
            "identite": f"{_str(r.get('nom'))} {_capitalize(_str(r.get('prenom')))}".strip(),
            "cp": cp,
            "ville": ville,
            "date_entree_rdv": date_rdv,
            "en_activite": False,
            "infos_cplt": infos,
            "ligne_rdv": ligne_rdv,
        })

    # Tri par date d'entree/RDV decroissante
    out.sort(key=lambda x: x.get("date_entree_rdv") or "", reverse=True)
    return out
