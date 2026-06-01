"""
Service CVthèque : recherche dans cvtheque + référentiels.

Tables principales :
  - cvtheque + CvSuivi (Bdd_Omaya_Recrutement)
  - cvstatut, CvSource, CvAnnonceur (Bdd_Omaya_Recrutement)
  - CommunesFrance (Bdd_Omaya_Divers)
  - salarie (Bdd_Omaya_RH) pour le nom du coopteur

Transposition de PAGE_CVtheque + POPUP_Recherche WinDev.
"""

import base64
import struct
from datetime import datetime, date, timedelta
from math import asin, cos, radians, sin, sqrt

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection


def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance géodésique entre 2 points en kilomètres."""
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlam = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlam / 2) ** 2
    return 2 * R * asin(sqrt(a))


# --- Référentiels ---------------------------------------------------------

def lister_statuts() -> list[dict]:
    """Liste des statuts CV (cvstatut)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cv_statut, lib_statut FROM pgt_cvstatut
        WHERE modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_statut ASC"""
    )
    return [
        {
            "id_cv_statut": _to_int(r.get("id_cv_statut")),
            "lib_statut": r.get("lib_statut") or "",
        }
        for r in rows
    ]


def lister_sources() -> list[dict]:
    """Liste des sources CV actives."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cvsource, lib_source FROM pgt_cv_source
        WHERE is_actif = TRUE AND modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_source ASC"""
    )
    return [
        {
            "id_cv_source": _to_int(r.get("id_cvsource")),
            "lib_source": r.get("lib_source") or "",
        }
        for r in rows
    ]


def lister_annonceurs() -> list[dict]:
    """Liste des annonceurs CV actifs."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cv_annonceur, lib_annonceur FROM pgt_cv_annonceur
        WHERE is_actif = TRUE AND modif_elem NOT LIKE '%suppr%'
        ORDER BY lib_annonceur ASC"""
    )
    return [
        {
            "id_cv_annonceur": _to_int(r.get("id_cv_annonceur")),
            "lib_annonceur": r.get("lib_annonceur") or "",
        }
        for r in rows
    ]


def rechercher_communes(ville: str) -> list[dict]:
    """
    Recherche les CP/villes correspondant à un début de nom de ville.
    Fallback API Adresse si pas de résultat en base locale.
    """
    ville = (ville or "").strip()
    if not ville:
        return []

    db = get_pg_connection("divers")
    # Le WinDev remplace les espaces par des tirets avant la requête.
    ville_pattern = f"{ville.replace(' ', '-')}%"

    rows = db.query(
        """SELECT id_communes_france, code_postal, nom_ville, latitude_deg, longitude_deg
        FROM pgt_communes_france
        WHERE modif_elem NOT LIKE '%suppr%'
          AND LOWER(nom_ville) LIKE LOWER(?)
        ORDER BY code_postal ASC""",
        (ville_pattern,),
    )

    # Dédupliquer par CP
    seen_cp: set[str] = set()
    result = []
    for r in rows:
        cp = r.get("code_postal") or ""
        if cp in seen_cp:
            continue
        seen_cp.add(cp)
        result.append({
            "cp": cp,
            "ville": r.get("nom_ville") or "",
            "id_communes_france": str(_to_int(r.get("id_communes_france"))),
            "latitude": float(r.get("latitude_deg") or 0),
            "longitude": float(r.get("longitude_deg") or 0),
        })
    return result


def communes_dans_rayon(
    latitude: float,
    longitude: float,
    rayon_km: int,
) -> list[int]:
    """
    Retourne les IDCommunesFrance situés à moins de rayon_km du point (lat, lon).

    Pré-filtre par bounding box, puis calcul précis haversine.
    """
    if rayon_km <= 0 or latitude == 0 or longitude == 0:
        return []

    # Pré-filtre bounding box (1 deg lat ≈ 111 km)
    dlat = rayon_km / 111.0
    cos_lat = max(0.001, cos(radians(latitude)))
    dlon = rayon_km / (111.0 * cos_lat)
    lat_min = latitude - dlat
    lat_max = latitude + dlat
    lon_min = longitude - dlon
    lon_max = longitude + dlon

    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_communes_france, latitude_deg, longitude_deg
        FROM pgt_communes_france
        WHERE modif_elem NOT LIKE '%suppr%'
          AND latitude_deg BETWEEN ? AND ?
          AND longitude_deg BETWEEN ? AND ?""",
        (lat_min, lat_max, lon_min, lon_max),
    )

    result: list[int] = []
    for r in rows:
        lat = float(r.get("latitude_deg") or 0)
        lon = float(r.get("longitude_deg") or 0)
        if lat == 0 and lon == 0:
            continue
        if _haversine_km(latitude, longitude, lat, lon) <= rayon_km:
            cid = _to_int(r.get("id_communes_france"))
            if cid:
                result.append(cid)
    return result


# --- Recherche principale -------------------------------------------------

def get_fiche(id_cvtheque: int) -> dict | None:
    """
    Retourne la fiche complète d'un CV + historique (CvSuivi).
    """
    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")
    db_divers = get_pg_connection("divers")

    row = db_rec.query_one(
        """SELECT id_cvtheque, origine, nom, prenom, pays, adresse,
            id_communes_france, date_naissance, permis_b, vehicule, mail, gsm,
            fic_cv, id_cvposte, id_cvsource, id_elem_source, id_ste, observ,
            traite_en_cours, op_traite
        FROM pgt_cvtheque WHERE id_cvtheque = ?""",
        (id_cvtheque,),
    )
    if not row:
        return None

    # Commune
    id_commune = _to_int(row.get("id_communes_france"))
    cp = ""
    ville = ""
    if id_commune:
        c = db_divers.query_one(
            "SELECT code_postal, nom_ville FROM pgt_communes_france WHERE id_communes_france = ?",
            (id_commune,),
        )
        if c:
            cp = c.get("code_postal") or ""
            ville = c.get("nom_ville") or ""

    # Coopteur (si source = 1)
    nom_coopteur = ""
    id_cv_source = _to_int(row.get("id_cvsource"))
    id_elem_source = _to_int(row.get("id_elem_source"))
    if id_cv_source == 1 and id_elem_source:
        s = db_rh.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
            (id_elem_source,),
        )
        if s:
            nom_coopteur = f"{s.get('nom') or ''} {(s.get('prenom') or '').capitalize()}".strip()

    # Age
    age = 0
    date_naiss = row.get("date_naissance") or ""
    if date_naiss:
        try:
            parsed = date_naiss[:10].replace("T", " ")
            if "-" in parsed:
                y, m, d = int(parsed[0:4]), int(parsed[5:7]), int(parsed[8:10])
            else:
                y, m, d = int(parsed[0:4]), int(parsed[4:6]), int(parsed[6:8])
            dn = date(y, m, d)
            today = date.today()
            age = today.year - dn.year - ((today.month, today.day) < (dn.month, dn.day))
        except Exception:
            age = 0

    # Lien CV
    fic_cv = (row.get("fic_cv") or "").strip()
    cv_url = ""
    if fic_cv:
        if fic_cv.lower().startswith("http"):
            cv_url = fic_cv.split(",")[0].strip()
        else:
            from app.core.config import DOCS_URL
            cv_url = f"{DOCS_URL.rstrip('/')}/cvtheque/{fic_cv}"

    # Historique
    suivi_rows = db_rec.query(
        """SELECT id_cv_suivi, datecrea, op_crea, id_cv_statut, type_elem, id_elem, observation
        FROM pgt_cvsuivi
        WHERE id_cvtheque = ?
          AND modif_elem NOT LIKE '%suppr%'
          AND modif_elem NOT LIKE '%DOUB%'
        ORDER BY datecrea DESC""",
        (id_cvtheque,),
    )

    # Résoudre opérateurs + statuts
    op_ids = {_to_int(s.get("op_crea")) for s in suivi_rows}
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        ids_sql = ",".join(str(i) for i in op_ids)
        orows = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for o in orows:
            nom = o.get("nom") or ""
            prenom = (o.get("prenom") or "").capitalize()
            op_map[_to_int(o.get("id_salarie"))] = f"{nom} {prenom}".strip()

    statuts_rows = db_rec.query("SELECT id_cv_statut, lib_statut FROM pgt_cvstatut")
    statuts_map = {_to_int(s.get("id_cv_statut")): s.get("lib_statut") or "" for s in statuts_rows}

    suivi = []
    for s in suivi_rows:
        op_id = _to_int(s.get("op_crea"))
        suivi.append({
            "id_cv_suivi": str(_to_int(s.get("id_cv_suivi"))),
            "datecrea": s.get("datecrea") or "",
            "op_crea": op_id,
            "op_crea_nom": op_map.get(op_id, ""),
            "id_cv_statut": _to_int(s.get("id_cv_statut")),
            "statut_lib": statuts_map.get(_to_int(s.get("id_cv_statut")), ""),
            "type_elem": s.get("type_elem") or "",
            "id_elem": str(_to_int(s.get("id_elem"))),
            "observation": s.get("observation") or "",
        })

    # Dernier statut
    id_cv_statut = suivi[0]["id_cv_statut"] if suivi else 0

    fiche = {
        "id_cvtheque": str(_to_int(row.get("id_cvtheque"))),
        "origine": _to_int(row.get("origine")),
        "nom": row.get("nom") or "",
        "prenom": row.get("prenom") or "",
        "pays": row.get("pays") or "",
        "adresse": row.get("adresse") or "",
        "cp": cp,
        "ville": ville,
        "id_communes_france": id_commune,
        "date_naissance": date_naiss,
        "age": age,
        "permis_b": bool(row.get("permis_b")),
        "vehicule": bool(row.get("vehicule")),
        "mail": row.get("mail") or "",
        "gsm": row.get("gsm") or "",
        "fic_cv": fic_cv,
        "cv_url": cv_url,
        "id_cv_poste": _to_int(row.get("id_cvposte")),
        "id_cv_source": id_cv_source,
        "id_elem_source": id_elem_source,
        "nom_coopteur": nom_coopteur,
        "id_ste": _to_int(row.get("id_ste")),
        "observation": row.get("observ") or "",
        "id_cv_statut": id_cv_statut,
        "traite_en_cours": bool(row.get("traite_en_cours")),
        "op_traite": _to_int(row.get("op_traite")),
    }
    return {"fiche": fiche, "suivi": suivi}


def _new_id() -> int:
    """ID WinDev (idEntierDateHeureSys)."""
    from datetime import datetime as _dt
    n = _dt.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _format_tel(tel: str) -> str:
    import re
    return re.sub(r"\D", "", tel or "")


def enregistrer_fiche(
    id_cvtheque: int,
    data: dict,
    id_salarie_user: int,
    prenom_user: str,
    ancien_statut: int,
) -> dict:
    """
    Enregistre la fiche CV : update cvtheque + éventuel nouveau CvSuivi si statut changé.

    Retourne {"ok": bool, "need_confirm_statut6": bool}.
    """
    from datetime import datetime as _dt

    db_hf = get_connection("recrutement")  # HFSQL pour les ecritures
    db_pg = get_pg_connection("recrutement")  # PG pour les lectures

    # Vérification existence (lecture -> PG)
    cv = db_pg.query_one(
        "SELECT id_cvtheque, observ FROM pgt_cvtheque WHERE id_cvtheque = ?",
        (id_cvtheque,),
    )
    if not cv:
        raise ValueError("CV introuvable")

    # Append saisir_obser à OBSERV
    observ = data.get("observation") or ""
    saisir = (data.get("saisir_obser") or "").strip()
    if saisir:
        now_fr = _dt.now().strftime("%d/%m/%Y %H:%M")
        addition = f"{now_fr} par {prenom_user.capitalize()} : {saisir}"
        observ = f"{observ}\n{addition}" if observ else addition

    # Formatage tel/mail
    gsm = _format_tel(data.get("gsm") or "")
    mail = (data.get("mail") or "").strip().lower().replace(" ", "")

    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    pays = (data.get("pays") or "").strip()
    adresse = (data.get("adresse") or "").strip()
    id_commune = int(data.get("id_communes_france") or 0)
    date_naiss = (data.get("date_naissance") or "").strip()
    permis_b = bool(data.get("permis_b"))
    vehicule = bool(data.get("vehicule"))
    id_cv_poste = int(data.get("id_cv_poste") or 0)
    id_cv_source = int(data.get("id_cv_source") or 0)
    id_elem_source = int(data.get("id_elem_source") or 0)
    id_ste = int(data.get("id_ste") or 0)

    nouveau_statut = int(data.get("id_cv_statut") or 0)
    confirm_6 = bool(data.get("confirm_statut_6"))

    # Si statut = 6 et pas confirmé → renvoyer need_confirm
    if nouveau_statut == 6 and nouveau_statut != ancien_statut and not confirm_6:
        return {"ok": False, "need_confirm_statut6": True}

    now_wd = _new_id()
    now_str = str(now_wd)

    # Échapper les quotes
    def esc(s: str) -> str:
        return (s or "").replace("'", "''")

    db_hf.query(
        f"""UPDATE cvtheque SET
            NOM = '{esc(nom)}',
            PRENOM = '{esc(prenom)}',
            PAYS = '{esc(pays)}',
            Adresse = '{esc(adresse)}',
            IDCommunesFrance = {id_commune},
            DateNaissance = '{esc(date_naiss)}',
            PermisB = {1 if permis_b else 0},
            Véhicule = {1 if vehicule else 0},
            MAIL = '{esc(mail)}',
            GSM = '{esc(gsm)}',
            IDcvposte = {id_cv_poste},
            IDcvsource = {id_cv_source},
            IdElemSource = {id_elem_source},
            IdSte = {id_ste},
            OBSERV = '{esc(observ)}',
            ModifOP = {id_salarie_user},
            ModifDate = '{now_str}',
            ModifELEM = 'new'
        WHERE IDcvtheque = {id_cvtheque}"""
    )

    # Nouveau CvSuivi si changement de statut
    if nouveau_statut and nouveau_statut != ancien_statut:
        observ_suivi = ""
        if nouveau_statut == 6:
            observ_suivi = "Statué en direct sans prise de RDV"
        observ_suivi_safe = observ_suivi.replace("'", "''")

        id_suivi = _new_id()
        db_hf.query(
            f"""INSERT INTO CvSuivi (
                IDCvSuivi, IDcvtheque, Datecrea, OPCREA, IdCvStatut,
                TypeElem, IdElem, Observation, ModifDate, ModifOp, ModifElem
            ) VALUES (
                {id_suivi}, {id_cvtheque}, '{now_str}', {id_salarie_user}, {nouveau_statut},
                '', 0, '{observ_suivi_safe}', '{now_str}', {id_salarie_user}, 'new'
            )"""
        )

    return {"ok": True, "need_confirm_statut6": False}


def ajouter_observation(
    id_cvtheque: int,
    observation_add: str,
    prenom_user: str,
) -> str:
    """
    Ajoute une observation datée au champ OBSERV et retourne le nouveau contenu.
    """
    from datetime import datetime as _dt

    observation_add = (observation_add or "").strip()
    if not observation_add:
        raise ValueError("Observation vide")

    db_hf = get_connection("recrutement")  # HFSQL pour les ecritures
    db_pg = get_pg_connection("recrutement")  # PG pour les lectures
    cv = db_pg.query_one(
        "SELECT observ FROM pgt_cvtheque WHERE id_cvtheque = ?",
        (id_cvtheque,),
    )
    if not cv:
        raise ValueError("CV introuvable")

    observ = cv.get("observ") or ""
    now_fr = _dt.now().strftime("%d/%m/%Y %H:%M")
    line = f"{now_fr} par {prenom_user.capitalize()} : {observation_add}"
    new_observ = f"{observ}\n{line}" if observ else line

    now_wd = _new_id()
    observ_safe = new_observ.replace("'", "''")
    db_hf.query(
        f"""UPDATE cvtheque
        SET OBSERV = '{observ_safe}', ModifDate = '{now_wd}'
        WHERE IDcvtheque = {id_cvtheque}"""
    )
    return new_observ


def get_traitement_bulk(cv_ids: list[int]) -> list[dict]:
    """
    Retourne l'état courant (traitement + dernier statut + dernier op)
    pour une liste de CV IDs. Pour le polling temps réel.
    """
    if not cv_ids:
        return []

    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")

    ids_sql = ",".join(str(i) for i in cv_ids)
    rows = db_rec.query(
        f"""SELECT id_cvtheque, traite_en_cours, op_traite
        FROM pgt_cvtheque WHERE id_cvtheque IN ({ids_sql})"""
    )

    # Dernier CvSuivi par CV : on fait une query globale et on garde le premier par date desc
    suivis = db_rec.query(
        f"""SELECT id_cvtheque, id_cv_statut, op_crea, datecrea
        FROM pgt_cvsuivi
        WHERE modif_elem NOT LIKE '%suppr%'
          AND modif_elem NOT LIKE '%DOUB%'
          AND id_cvtheque IN ({ids_sql})
        ORDER BY datecrea DESC"""
    )
    latest_by_cv: dict[int, dict] = {}
    for s in suivis:
        idcv = _to_int(s.get("id_cvtheque"))
        if idcv not in latest_by_cv:
            latest_by_cv[idcv] = {
                "id_cv_statut": _to_int(s.get("id_cv_statut")),
                "op_crea": _to_int(s.get("op_crea")),
            }

    # Libellés statuts
    statut_rows = db_rec.query("SELECT id_cv_statut, lib_statut FROM pgt_cvstatut")
    statuts_map = {_to_int(s.get("id_cv_statut")): s.get("lib_statut") or "" for s in statut_rows}

    # Noms des opé (traitement + OPCrea)
    op_ids = {_to_int(r.get("op_traite")) for r in rows if r.get("traite_en_cours")}
    for v in latest_by_cv.values():
        op_ids.add(v["op_crea"])
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        op_ids_sql = ",".join(str(i) for i in op_ids)
        op_rows = db_rh.query(
            f"SELECT id_salarie, prenom FROM pgt_salarie WHERE id_salarie IN ({op_ids_sql})"
        )
        for o in op_rows:
            op_map[_to_int(o.get("id_salarie"))] = (o.get("prenom") or "").capitalize()

    result = []
    for r in rows:
        idcv = _to_int(r.get("id_cvtheque"))
        latest = latest_by_cv.get(idcv, {"id_cv_statut": 0, "op_crea": 0})
        result.append({
            "id_cvtheque": str(idcv),
            "op_traitement": op_map.get(_to_int(r.get("op_traite")), "") if r.get("traite_en_cours") else "",
            "statut_actuel": latest["id_cv_statut"],
            "statut_actuel_lib": statuts_map.get(latest["id_cv_statut"], ""),
            "last_change_op": latest["op_crea"],
        })
    return result


def modifier_traitement(id_cvtheque: int, id_op: int, is_traite: bool) -> None:
    """Marque/libère un CV en cours de traitement."""
    db = get_connection("recrutement")
    from datetime import datetime as _dt
    now = _dt.now().strftime("%Y%m%d%H%M%S") + f"{_dt.now().microsecond // 1000:03d}"
    db.query(
        f"""UPDATE cvtheque
        SET TraiteEnCours = {1 if is_traite else 0},
            opTraite = {id_op},
            DateTraite = '{now}',
            ModifDate = '{now}'
        WHERE IDcvtheque = {id_cvtheque}"""
    )


def affectation_vendeur_by_date(id_vendeur: int, ymd: str) -> tuple[str, str]:
    """
    Retourne (agence, equipe) du salarié à la date donnée (format YYYYMMDD).
    Lookup via salarie_organigramme + organigramme + parent.
    """
    if not id_vendeur or not ymd:
        return ("", "")

    db_rh = get_pg_connection("rh")
    rows = db_rh.query(
        """SELECT so.idorganigramme
        FROM pgt_salarie_organigramme so
        INNER JOIN pgt_salarie s ON s.id_salarie = so.id_salarie
        INNER JOIN pgt_organigramme o ON o.idorganigramme = so.idorganigramme
        WHERE so.modif_elem NOT LIKE '%suppr%'
          AND s.modif_elem NOT LIKE '%suppr%'
          AND so.id_salarie = ?
          AND so.date_debut::date <= ?::date
        LIMIT 1""",
        (id_vendeur, ymd),
    )
    if not rows:
        return ("", "")

    id_orga = _to_int(rows[0].get("idorganigramme"))
    if not id_orga:
        return ("", "")

    orga = db_rh.query_one(
        "SELECT lib_orga, id_parent FROM pgt_organigramme WHERE idorganigramme = ?",
        (id_orga,),
    )
    if not orga:
        return ("", "")
    equipe = orga.get("lib_orga") or ""
    id_parent = _to_int(orga.get("id_parent"))

    agence = ""
    if id_parent:
        parent = db_rh.query_one(
            "SELECT lib_orga FROM pgt_organigramme WHERE idorganigramme = ?",
            (id_parent,),
        )
        if parent:
            agence = parent.get("lib_orga") or ""

    # Si l'équipe contient "Agence" (mauvaise arborescence), on inverse
    if "agence" in equipe.lower():
        agence = equipe

    return (agence, equipe)


def _iso_bounds(date_debut: str, date_fin: str) -> tuple[str, str]:
    """
    Convertit YYYYMMDD en bornes datetime ISO YYYY-MM-DD HH:MM:SS.
    Si date_debut vide : 1970-01-01.
    Si date_fin vide : aujourd'hui.
    """
    if not date_debut:
        date_debut = "19700101"
    if not date_fin:
        date_fin = datetime.now().strftime("%Y%m%d")
    deb = f"{date_debut[0:4]}-{date_debut[4:6]}-{date_debut[6:8]} 00:00:00"
    fin = f"{date_fin[0:4]}-{date_fin[4:6]}-{date_fin[6:8]} 23:59:59"
    return deb, fin


def _iso_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def rechercher_cvtheque(
    mode: str,
    latitude: float = 0,
    longitude: float = 0,
    rayon_km: int = 30,
    date_debut: str = "",
    date_fin: str = "",
    age_min: int = 0,
    age_max: int = 100,
    id_cv_source: int = 0,
    id_coopteur: str = "",
    id_annonceur: int = 0,
    profil: int = 0,
    id_cv_statut: int = 0,
    tel: str = "",
    nom: str = "",
    prenom: str = "",
    acces_complet: bool = False,
    id_salarie_user: int = 0,
    progress_cb=None,
) -> list[dict]:
    """
    Recherche dans cvtheque avec filtres.

    acces_complet : droit CV_VoirComplet. Si False, on ne voit que les CVs
    dont le coopteur (IdElemSource) est dans Mes_Vendeurs (scope du user).
    """
    db = get_pg_connection("recrutement")

    # Base SQL (sans critères variables)
    base = """SELECT
        cv.id_cvtheque, cv.id_communes_france, cv.origine, cv.id_cvsource,
        cv.date_naissance, cv.observ, cv.date_saisie, cv.nom, cv.prenom,
        cv.date_reac, cv.traite_en_cours, cv.op_traite, cv.id_elem_source,
        cv.gsm, cv.id_cvposte,
        cs.id_cv_statut, cs.datecrea
    FROM pgt_cvtheque cv
    INNER JOIN pgt_cvsuivi cs ON cv.id_cvtheque = cs.id_cvtheque
    WHERE cv.modif_elem <> 'suppr'"""

    params: list = []
    where_extra: list[str] = []

    # Bornes dates
    deb, fin = _iso_bounds(date_debut, date_fin)

    if mode == "cp":
        where_extra.append(
            "(cv.date_saisie BETWEEN ? AND ? OR cv.date_reac BETWEEN ? AND ?)"
        )
        params.extend([deb, fin, deb, fin])

        if id_cv_source:
            where_extra.append("cv.id_cvsource = ?")
            params.append(id_cv_source)
            if id_cv_source == 1 and id_coopteur:
                where_extra.append("cv.id_elem_source = ?")
                params.append(int(id_coopteur))
            elif id_cv_source == 2 and id_annonceur:
                where_extra.append("cv.id_elem_source = ?")
                params.append(id_annonceur)

        # Profil
        if profil == 1:
            where_extra.append("(cv.id_cvposte = 1 OR cv.id_cvposte = 0)")
        elif profil == 2:
            where_extra.append("(cv.id_cvposte = 10 OR cv.id_cvposte = 13)")
        elif profil == 3:
            where_extra.append(
                "(cv.id_cvposte = 1 OR cv.id_cvposte = 10 OR cv.id_cvposte = 13 OR cv.id_cvposte = 0)"
            )

        # Age (min..max)
        today = date.today()
        try:
            age_max_date = date(today.year - age_min, today.month, today.day)
        except ValueError:
            age_max_date = today - timedelta(days=age_min * 365)
        try:
            age_min_date = date(today.year - age_max - 1, today.month, today.day) + timedelta(days=1)
        except ValueError:
            age_min_date = today - timedelta(days=(age_max + 1) * 365)

        if age_min == 0:
            where_extra.append(
                "(cv.date_naissance IS NULL OR cv.date_naissance BETWEEN ? AND ?)"
            )
            params.extend([_iso_date(age_min_date), _iso_date(age_max_date)])
        else:
            where_extra.append("cv.date_naissance BETWEEN ? AND ?")
            params.extend([_iso_date(age_min_date), _iso_date(age_max_date)])

        # Communes dans le rayon — liste d'IDs
        commune_ids = communes_dans_rayon(latitude, longitude, rayon_km)
        if not commune_ids:
            return []

    elif mode == "tel":
        tel_clean = "".join(c for c in tel if c.isdigit())
        if tel_clean:
            where_extra.append("cv.gsm LIKE ?")
            params.append(f"%{tel_clean}%")
        commune_ids = []

    elif mode == "nom":
        if nom:
            where_extra.append("LOWER(cv.nom) LIKE LOWER(?)")
            params.append(f"%{nom}%")
        if prenom:
            where_extra.append("LOWER(cv.prenom) LIKE LOWER(?)")
            params.append(f"%{prenom}%")
        commune_ids = []
    else:
        return []

    where_sql = " AND ".join(where_extra)
    if where_sql:
        base += " AND " + where_sql

    # Si mode cp : on ajoute la liste des communes par batch de 50
    all_rows: list[dict] = []
    seen_ids: set[int] = set()

    def report(pct: int, msg: str = ""):
        if progress_cb:
            progress_cb(pct, msg)

    report(5, "Préparation de la recherche")

    if commune_ids:
        BATCH = 50
        n_batches = (len(commune_ids) + BATCH - 1) // BATCH
        for i in range(n_batches):
            chunk = commune_ids[i * BATCH : (i + 1) * BATCH]
            ids_sql = ",".join(str(cid) for cid in chunk)
            sql = (
                base
                + f" AND cv.id_communes_france IN ({ids_sql})"
                + " ORDER BY cs.datecrea DESC"
            )
            rows = db.query(sql, tuple(params))
            for r in rows:
                idcv = _to_int(r.get("id_cvtheque"))
                if idcv not in seen_ids:
                    seen_ids.add(idcv)
                    all_rows.append(r)
            # Progress : 10% → 70% sur la boucle
            pct = 10 + int(60 * (i + 1) / n_batches)
            report(pct, f"Communes {i + 1}/{n_batches}")
    else:
        report(30, "Recherche en cours")
        sql = base + " ORDER BY cs.datecrea DESC"
        rows = db.query(sql, tuple(params))
        for r in rows:
            idcv = _to_int(r.get("id_cvtheque"))
            if idcv not in seen_ids:
                seen_ids.add(idcv)
                all_rows.append(r)
        report(70, "Résultats récupérés")

    # Filtrage post-requête : statut + droit CV_VoirComplet
    if id_cv_statut:
        all_rows = [r for r in all_rows if _to_int(r.get("id_cv_statut")) == id_cv_statut]

    # Si pas de droit CV_VoirComplet, on ne voit que nos propres cooptations (Cooptation → IdElemSource = user)
    if not acces_complet and id_salarie_user:
        filtered: list[dict] = []
        for r in all_rows:
            if _to_int(r.get("id_cvsource")) == 1:
                if _to_int(r.get("id_elem_source")) != id_salarie_user:
                    continue
            filtered.append(r)
        all_rows = filtered

    # Enrichissement : CP/Ville, coopteur/annonceur, statut_periode, opTraitement
    enriched = _enrich_results(all_rows, date_debut, date_fin, progress_cb)
    report(100, "Terminé")
    return enriched


def _enrich_results(
    rows: list[dict],
    date_debut: str,
    date_fin: str,
    progress_cb=None,
) -> list[dict]:
    if not rows:
        return []

    def report(pct: int, msg: str = ""):
        if progress_cb:
            progress_cb(pct, msg)

    db_rec = get_pg_connection("recrutement")
    db_rh = get_pg_connection("rh")
    db_divers = get_pg_connection("divers")

    report(75, "Communes et référentiels...")

    # 1. CP/Ville
    commune_ids = {_to_int(r.get("id_communes_france")) for r in rows}
    commune_ids.discard(0)
    communes_map: dict[int, dict] = {}
    if commune_ids:
        ids_sql = ",".join(str(i) for i in commune_ids)
        crows = db_divers.query(
            f"SELECT id_communes_france, code_postal, nom_ville FROM pgt_communes_france "
            f"WHERE id_communes_france IN ({ids_sql})"
        )
        for c in crows:
            communes_map[_to_int(c.get("id_communes_france"))] = {
                "cp": c.get("code_postal") or "",
                "ville": c.get("nom_ville") or "",
            }

    # 2. Statuts
    statut_rows = db_rec.query(
        "SELECT id_cv_statut, lib_statut FROM pgt_cvstatut WHERE modif_elem NOT LIKE '%suppr%'"
    )
    statuts_map = {_to_int(s.get("id_cv_statut")): s.get("lib_statut") or "" for s in statut_rows}

    # 3. Sources
    source_rows = db_rec.query("SELECT id_cvsource, lib_source FROM pgt_cv_source")
    sources_map = {_to_int(s.get("id_cvsource")): s.get("lib_source") or "" for s in source_rows}

    # 4. Annonceurs
    annonceur_rows = db_rec.query("SELECT id_cv_annonceur, lib_annonceur FROM pgt_cv_annonceur")
    annonceurs_map = {
        _to_int(a.get("id_cv_annonceur")): a.get("lib_annonceur") or "" for a in annonceur_rows
    }

    report(80, "Coopteurs et annonceurs...")

    # 5. Coopteurs (salariés) — batch
    coopteur_ids = {
        _to_int(r.get("id_elem_source"))
        for r in rows
        if _to_int(r.get("id_cvsource")) == 1
    }
    coopteur_ids.discard(0)
    coopteurs_map: dict[int, str] = {}
    if coopteur_ids:
        ids_sql = ",".join(str(i) for i in coopteur_ids)
        srows = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for s in srows:
            nom = s.get("nom") or ""
            prenom = (s.get("prenom") or "").capitalize()
            coopteurs_map[_to_int(s.get("id_salarie"))] = f"{nom} {prenom}".strip()

    # 6. opTraite (salariés)
    op_ids = {
        _to_int(r.get("op_traite")) for r in rows if r.get("traite_en_cours")
    }
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        ids_sql = ",".join(str(i) for i in op_ids)
        orows = db_rh.query(
            f"SELECT id_salarie, prenom FROM pgt_salarie WHERE id_salarie IN ({ids_sql})"
        )
        for o in orows:
            op_map[_to_int(o.get("id_salarie"))] = (o.get("prenom") or "").capitalize()

    report(85, "Statuts période...")

    # 7. Statut période — par CV, dernier CvSuivi avant date_fin si date_fin < aujourd'hui
    # Optim : on fait une seule requête pour tous les CVs
    _, fin_iso = _iso_bounds(date_debut, date_fin)
    cv_ids = {_to_int(r.get("id_cvtheque")) for r in rows}
    cv_ids.discard(0)
    statut_periode_map: dict[int, int] = {}
    if cv_ids and date_fin and date_fin < datetime.now().strftime("%Y%m%d"):
        ids_sql = ",".join(str(i) for i in cv_ids)
        periode_rows = db_rec.query(
            f"""SELECT id_cvtheque, id_cv_statut, datecrea FROM pgt_cvsuivi
            WHERE modif_elem NOT LIKE '%suppr%'
              AND id_cvtheque IN ({ids_sql})
              AND modif_date <= ?
            ORDER BY datecrea DESC""",
            (fin_iso,),
        )
        for p in periode_rows:
            idcv = _to_int(p.get("id_cvtheque"))
            if idcv not in statut_periode_map:
                statut_periode_map[idcv] = _to_int(p.get("id_cv_statut"))

    report(90, "Affectations coopteurs...")

    # 8. Affectation agence/équipe des coopteurs - batch (optimisation)
    # On récupère tous les salarie_organigramme + organigramme pour les coopteurs
    # puis on mappe en mémoire par date
    affectation_map: dict[tuple[int, str], tuple[str, str]] = {}
    if coopteur_ids:
        ids_sql = ",".join(str(i) for i in coopteur_ids)
        orga_assignations = db_rh.query(
            f"""SELECT so.id_salarie, so.idorganigramme, so.date_debut, so.date_fin
            FROM pgt_salarie_organigramme so
            WHERE so.modif_elem NOT LIKE '%suppr%'
              AND so.id_salarie IN ({ids_sql})"""
        )

        # Récupérer toutes les organigrammes référencées
        orga_ids_lookup = {_to_int(r.get("idorganigramme")) for r in orga_assignations}
        orga_ids_lookup.discard(0)
        orga_info: dict[int, dict] = {}
        if orga_ids_lookup:
            ids_sql2 = ",".join(str(i) for i in orga_ids_lookup)
            orga_rows = db_rh.query(
                f"SELECT idorganigramme, lib_orga, id_parent FROM pgt_organigramme "
                f"WHERE idorganigramme IN ({ids_sql2})"
            )
            for o in orga_rows:
                orga_info[_to_int(o.get("idorganigramme"))] = {
                    "lib": o.get("lib_orga") or "",
                    "parent": _to_int(o.get("id_parent")),
                }
            # Récupérer les parents s'ils ne sont pas déjà là
            parent_ids = {info["parent"] for info in orga_info.values()} - orga_ids_lookup
            parent_ids.discard(0)
            if parent_ids:
                ids_sql3 = ",".join(str(i) for i in parent_ids)
                prows = db_rh.query(
                    f"SELECT idorganigramme, lib_orga FROM pgt_organigramme "
                    f"WHERE idorganigramme IN ({ids_sql3})"
                )
                for p in prows:
                    orga_info[_to_int(p.get("idorganigramme"))] = {
                        "lib": p.get("lib_orga") or "",
                        "parent": 0,
                    }

        # Grouper les affectations par salarié
        by_salarie: dict[int, list[dict]] = {}
        for a in orga_assignations:
            sid = _to_int(a.get("id_salarie"))
            by_salarie.setdefault(sid, []).append(a)

        # Helper : extraire YYYYMMDD depuis ISO ou WinDev
        def _ymd(s: str) -> str:
            if not s:
                return ""
            if "-" in s:
                return s[0:4] + s[5:7] + s[8:10]
            return s[0:8]

        def _find_affectation(id_coopteur: int, date_ymd: str) -> tuple[str, str]:
            assignations = by_salarie.get(id_coopteur, [])
            for a in assignations:
                deb = _ymd(a.get("date_debut") or "")
                fin = _ymd(a.get("date_fin") or "")
                if deb and deb <= date_ymd and (not fin or fin >= date_ymd):
                    id_orga = _to_int(a.get("idorganigramme"))
                    info = orga_info.get(id_orga)
                    if not info:
                        return ("", "")
                    equipe = info["lib"]
                    parent_info = orga_info.get(info["parent"])
                    agence = parent_info["lib"] if parent_info else ""
                    if "agence" in equipe.lower():
                        agence = equipe
                    return (agence, equipe)
            return ("", "")

    # Construire le résultat
    report(95, "Finalisation...")
    today = date.today()
    result: list[dict] = []
    n = len(rows)
    for idx, r in enumerate(rows):
        if n > 50 and idx % 20 == 0:
            # Progression fine pendant la boucle : 95 → 99
            report(95 + int(4 * idx / max(1, n - 1)), f"Finalisation ({idx + 1}/{n})")
        idcv = _to_int(r.get("id_cvtheque"))
        id_commune = _to_int(r.get("id_communes_france"))
        commune = communes_map.get(id_commune, {})
        localisation = ""
        if commune:
            localisation = f"{commune['cp']} {commune['ville']}".strip()

        # Age
        age = 0
        date_naiss = r.get("date_naissance") or ""
        if date_naiss:
            try:
                parsed = date_naiss[:10].replace("T", " ")
                if "-" in parsed:
                    y, m, d = int(parsed[0:4]), int(parsed[5:7]), int(parsed[8:10])
                else:
                    y, m, d = int(parsed[0:4]), int(parsed[4:6]), int(parsed[6:8])
                dn = date(y, m, d)
                age = today.year - dn.year - ((today.month, today.day) < (dn.month, dn.day))
            except Exception:
                age = 0

        # Coopteur / Annonceur
        detail_source = ""
        source_id = _to_int(r.get("id_cvsource"))
        elem_source = _to_int(r.get("id_elem_source"))
        agence = ""
        equipe = ""
        if source_id == 1:
            detail_source = coopteurs_map.get(elem_source, "")
            ds = r.get("date_saisie") or ""
            if ds:
                ds_ymd = ds[0:4] + ds[5:7] + ds[8:10] if "-" in ds else ds[0:8]
                cache_key = (elem_source, ds_ymd)
                if cache_key not in affectation_map:
                    affectation_map[cache_key] = _find_affectation(elem_source, ds_ymd)
                agence, equipe = affectation_map[cache_key]
        elif source_id == 2:
            detail_source = annonceurs_map.get(elem_source, "")

        # OpTraitement
        op_traitement = ""
        if r.get("traite_en_cours"):
            op_traitement = op_map.get(_to_int(r.get("op_traite")), "")

        # Date saisie : si DateREAC est dans la période, l'utiliser sinon DateSAISIE
        date_saisie = r.get("date_saisie") or ""
        date_reac = r.get("date_reac") or ""
        if date_debut and date_fin and date_reac:
            deb_iso, fin_iso2 = _iso_bounds(date_debut, date_fin)
            if deb_iso <= date_reac <= fin_iso2:
                date_saisie = date_reac

        # Statut actuel + période
        statut_actuel = _to_int(r.get("id_cv_statut"))
        statut_periode = statut_periode_map.get(idcv, statut_actuel)

        # Commentaire (dernière ligne de OBSERV)
        observ = r.get("observ") or ""
        commentaire = observ.split("\n")[-1].strip() if observ else ""

        nom = (r.get("nom") or "").strip()
        prenom = (r.get("prenom") or "").capitalize().strip()
        identite = f"{nom} {prenom}".strip()

        result.append({
            "id_cvtheque": str(idcv),
            "identite": identite,
            "op_traitement": op_traitement,
            "date_saisie": date_saisie,
            "statut_actuel": statut_actuel,
            "statut_actuel_lib": statuts_map.get(statut_actuel, ""),
            "statut_periode": statut_periode,
            "statut_periode_lib": statuts_map.get(statut_periode, ""),
            "source": source_id,
            "source_lib": sources_map.get(source_id, ""),
            "age": age,
            "tel": r.get("gsm") or "",
            "localisation": localisation,            "detail_source": detail_source,
            "agence": agence,
            "equipe": equipe,
            "commentaire": commentaire,
        })

    # Tri final : date saisie desc
    result.sort(key=lambda x: x.get("date_saisie") or "", reverse=True)
    return result
