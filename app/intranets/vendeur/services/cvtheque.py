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
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IdCvStatut, LibStatut FROM cvstatut
        WHERE ModifElem NOT LIKE '%suppr%'
        ORDER BY LibStatut ASC"""
    )
    return [
        {
            "id_cv_statut": _to_int(r.get("IdCvStatut")),
            "lib_statut": r.get("LibStatut") or "",
        }
        for r in rows
    ]


def lister_sources() -> list[dict]:
    """Liste des sources CV actives."""
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IDcvsource, Lib_Source FROM CvSource
        WHERE IsActif = 1 AND ModifELEM NOT LIKE '%suppr%'
        ORDER BY Lib_Source ASC"""
    )
    return [
        {
            "id_cv_source": _to_int(r.get("IDcvsource")),
            "lib_source": r.get("Lib_Source") or "",
        }
        for r in rows
    ]


def lister_annonceurs() -> list[dict]:
    """Liste des annonceurs CV actifs."""
    db = get_connection("recrutement")
    rows = db.query(
        """SELECT IDCvAnnonceur, Lib_Annonceur FROM CvAnnonceur
        WHERE IsActif = 1 AND ModifELEM NOT LIKE '%suppr%'
        ORDER BY Lib_Annonceur ASC"""
    )
    return [
        {
            "id_cv_annonceur": _to_int(r.get("IDCvAnnonceur")),
            "lib_annonceur": r.get("Lib_Annonceur") or "",
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

    db = get_connection("divers")
    # Le WinDev remplace les espaces par des tirets avant la requête.
    ville_pattern = f"{ville.replace(' ', '-')}%"

    rows = db.query(
        """SELECT IDCommunesFrance, CodePostal, NomVille, latitude_deg, longitude_deg
        FROM CommunesFrance
        WHERE ModifELEM NOT LIKE '%suppr%'
          AND NomVille LIKE ?
        ORDER BY CodePostal ASC""",
        (ville_pattern,),
    )

    # Dédupliquer par CP
    seen_cp: set[str] = set()
    result = []
    for r in rows:
        cp = r.get("CodePostal") or ""
        if cp in seen_cp:
            continue
        seen_cp.add(cp)
        result.append({
            "cp": cp,
            "ville": r.get("NomVille") or "",
            "id_communes_france": str(_to_int(r.get("IDCommunesFrance"))),
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

    db = get_connection("divers")
    rows = db.query(
        """SELECT IDCommunesFrance, latitude_deg, longitude_deg
        FROM CommunesFrance
        WHERE ModifELEM NOT LIKE '%suppr%'
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
            cid = _to_int(r.get("IDCommunesFrance"))
            if cid:
                result.append(cid)
    return result


# --- Recherche principale -------------------------------------------------

def get_fiche(id_cvtheque: int) -> dict | None:
    """
    Retourne la fiche complète d'un CV + historique (CvSuivi).
    """
    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")
    db_divers = get_connection("divers")

    row = db_rec.query_one(
        """SELECT IDcvtheque, Origine, NOM, PRENOM, PAYS, Adresse,
            IDCommunesFrance, DateNaissance, PermisB, Véhicule, MAIL, GSM,
            Fic_CV, IDcvposte, IDcvsource, IdElemSource, IdSte, OBSERV,
            TraiteEnCours, opTraite
        FROM cvtheque WHERE IDcvtheque = ?""",
        (id_cvtheque,),
    )
    if not row:
        return None

    # Commune
    id_commune = _to_int(row.get("IDCommunesFrance"))
    cp = ""
    ville = ""
    if id_commune:
        c = db_divers.query_one(
            "SELECT CodePostal, NomVille FROM CommunesFrance WHERE IDCommunesFrance = ?",
            (id_commune,),
        )
        if c:
            cp = c.get("CodePostal") or ""
            ville = c.get("NomVille") or ""

    # Coopteur (si source = 1)
    nom_coopteur = ""
    id_cv_source = _to_int(row.get("IDcvsource"))
    id_elem_source = _to_int(row.get("IdElemSource"))
    if id_cv_source == 1 and id_elem_source:
        s = db_rh.query_one(
            "SELECT NOM, PRENOM FROM salarie WHERE IDSalarie = ?",
            (id_elem_source,),
        )
        if s:
            nom_coopteur = f"{s.get('NOM') or ''} {(s.get('PRENOM') or '').capitalize()}".strip()

    # Age
    age = 0
    date_naiss = row.get("DateNaissance") or ""
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
    fic_cv = (row.get("Fic_CV") or "").strip()
    cv_url = ""
    if fic_cv:
        if fic_cv.lower().startswith("http"):
            cv_url = fic_cv.split(",")[0].strip()
        else:
            from app.core.config import DOCS_URL
            cv_url = f"{DOCS_URL.rstrip('/')}/cvtheque/{fic_cv}"

    # Historique
    suivi_rows = db_rec.query(
        """SELECT IDCvSuivi, Datecrea, OPCrea, IdCvStatut, TypeElem, IdElem, Observation
        FROM CvSuivi
        WHERE IDcvtheque = ?
          AND ModifELEM NOT LIKE '%suppr%'
          AND ModifELEM NOT LIKE '%DOUB%'
        ORDER BY Datecrea DESC""",
        (id_cvtheque,),
    )

    # Résoudre opérateurs + statuts
    op_ids = {_to_int(s.get("OPCrea")) for s in suivi_rows}
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        ids_sql = ",".join(str(i) for i in op_ids)
        orows = db_rh.query(
            f"SELECT IDSalarie, NOM, PRENOM FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for o in orows:
            nom = o.get("NOM") or ""
            prenom = (o.get("PRENOM") or "").capitalize()
            op_map[_to_int(o.get("IDSalarie"))] = f"{nom} {prenom}".strip()

    statuts_rows = db_rec.query("SELECT IdCvStatut, LibStatut FROM cvstatut")
    statuts_map = {_to_int(s.get("IdCvStatut")): s.get("LibStatut") or "" for s in statuts_rows}

    suivi = []
    for s in suivi_rows:
        op_id = _to_int(s.get("OPCrea"))
        suivi.append({
            "id_cv_suivi": str(_to_int(s.get("IDCvSuivi"))),
            "datecrea": s.get("Datecrea") or "",
            "op_crea": op_id,
            "op_crea_nom": op_map.get(op_id, ""),
            "id_cv_statut": _to_int(s.get("IdCvStatut")),
            "statut_lib": statuts_map.get(_to_int(s.get("IdCvStatut")), ""),
            "type_elem": s.get("TypeElem") or "",
            "id_elem": str(_to_int(s.get("IdElem"))),
            "observation": s.get("Observation") or "",
        })

    # Dernier statut
    id_cv_statut = suivi[0]["id_cv_statut"] if suivi else 0

    fiche = {
        "id_cvtheque": str(_to_int(row.get("IDcvtheque"))),
        "origine": _to_int(row.get("Origine")),
        "nom": row.get("NOM") or "",
        "prenom": row.get("PRENOM") or "",
        "pays": row.get("PAYS") or "",
        "adresse": row.get("Adresse") or "",
        "cp": cp,
        "ville": ville,
        "id_communes_france": id_commune,
        "date_naissance": date_naiss,
        "age": age,
        "permis_b": bool(row.get("PermisB")),
        "vehicule": bool(row.get("Véhicule")),
        "mail": row.get("MAIL") or "",
        "gsm": row.get("GSM") or "",
        "fic_cv": fic_cv,
        "cv_url": cv_url,
        "id_cv_poste": _to_int(row.get("IDcvposte")),
        "id_cv_source": id_cv_source,
        "id_elem_source": id_elem_source,
        "nom_coopteur": nom_coopteur,
        "id_ste": _to_int(row.get("IdSte")),
        "observation": row.get("OBSERV") or "",
        "id_cv_statut": id_cv_statut,
        "traite_en_cours": bool(row.get("TraiteEnCours")),
        "op_traite": _to_int(row.get("opTraite")),
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

    db = get_connection("recrutement")

    # Vérification existence
    cv = db.query_one(
        "SELECT IDcvtheque, OBSERV FROM cvtheque WHERE IDcvtheque = ?",
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

    db.query(
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
        db.query(
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

    db = get_connection("recrutement")
    cv = db.query_one(
        "SELECT OBSERV FROM cvtheque WHERE IDcvtheque = ?",
        (id_cvtheque,),
    )
    if not cv:
        raise ValueError("CV introuvable")

    observ = cv.get("OBSERV") or ""
    now_fr = _dt.now().strftime("%d/%m/%Y %H:%M")
    line = f"{now_fr} par {prenom_user.capitalize()} : {observation_add}"
    new_observ = f"{observ}\n{line}" if observ else line

    now_wd = _new_id()
    observ_safe = new_observ.replace("'", "''")
    db.query(
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

    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")

    ids_sql = ",".join(str(i) for i in cv_ids)
    rows = db_rec.query(
        f"""SELECT IDcvtheque, TraiteEnCours, opTraite
        FROM cvtheque WHERE IDcvtheque IN ({ids_sql})"""
    )

    # Dernier CvSuivi par CV : on fait une query globale et on garde le premier par date desc
    suivis = db_rec.query(
        f"""SELECT IDcvtheque, IdCvStatut, OPCrea, Datecrea
        FROM CvSuivi
        WHERE ModifELEM NOT LIKE '%suppr%'
          AND ModifELEM NOT LIKE '%DOUB%'
          AND IDcvtheque IN ({ids_sql})
        ORDER BY Datecrea DESC"""
    )
    latest_by_cv: dict[int, dict] = {}
    for s in suivis:
        idcv = _to_int(s.get("IDcvtheque"))
        if idcv not in latest_by_cv:
            latest_by_cv[idcv] = {
                "id_cv_statut": _to_int(s.get("IdCvStatut")),
                "op_crea": _to_int(s.get("OPCrea")),
            }

    # Libellés statuts
    statut_rows = db_rec.query("SELECT IdCvStatut, LibStatut FROM cvstatut")
    statuts_map = {_to_int(s.get("IdCvStatut")): s.get("LibStatut") or "" for s in statut_rows}

    # Noms des opé (traitement + OPCrea)
    op_ids = {_to_int(r.get("opTraite")) for r in rows if r.get("TraiteEnCours")}
    for v in latest_by_cv.values():
        op_ids.add(v["op_crea"])
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        op_ids_sql = ",".join(str(i) for i in op_ids)
        op_rows = db_rh.query(
            f"SELECT IDSalarie, PRENOM FROM salarie WHERE IDSalarie IN ({op_ids_sql})"
        )
        for o in op_rows:
            op_map[_to_int(o.get("IDSalarie"))] = (o.get("PRENOM") or "").capitalize()

    result = []
    for r in rows:
        idcv = _to_int(r.get("IDcvtheque"))
        latest = latest_by_cv.get(idcv, {"id_cv_statut": 0, "op_crea": 0})
        result.append({
            "id_cvtheque": str(idcv),
            "op_traitement": op_map.get(_to_int(r.get("opTraite")), "") if r.get("TraiteEnCours") else "",
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

    db_rh = get_connection("rh")
    rows = db_rh.query(
        """SELECT TOP 1 so.idorganigramme
        FROM salarie_organigramme so
        INNER JOIN salarie s ON s.IDSalarie = so.IDSalarie
        INNER JOIN organigramme o ON o.idorganigramme = so.idorganigramme
        WHERE so.ModifELEM NOT LIKE '%suppr%'
          AND s.ModifELEM NOT LIKE '%suppr%'
          AND so.IDSalarie = ?
          AND LEFT(so.DateDébut, 8) <= ?""",
        (id_vendeur, ymd),
    )
    if not rows:
        return ("", "")

    id_orga = _to_int(rows[0].get("idorganigramme"))
    if not id_orga:
        return ("", "")

    orga = db_rh.query_one(
        "SELECT Lib_ORGA, IdPARENT FROM organigramme WHERE idorganigramme = ?",
        (id_orga,),
    )
    if not orga:
        return ("", "")
    equipe = orga.get("Lib_ORGA") or ""
    id_parent = _to_int(orga.get("IdPARENT"))

    agence = ""
    if id_parent:
        parent = db_rh.query_one(
            "SELECT Lib_ORGA FROM organigramme WHERE idorganigramme = ?",
            (id_parent,),
        )
        if parent:
            agence = parent.get("Lib_ORGA") or ""

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
    db = get_connection("recrutement")

    # Base SQL (sans critères variables)
    base = """SELECT
        cv.IDcvtheque, cv.IDCommunesFrance, cv.Origine, cv.IDcvsource,
        cv.DateNaissance, cv.OBSERV, cv.DateSAISIE, cv.NOM, cv.PRENOM,
        cv.DateREAC, cv.TraiteEnCours, cv.opTraite, cv.IdElemSource,
        cv.GSM, cv.IDcvposte,
        cs.IdCvStatut, cs.Datecrea
    FROM cvtheque cv
    INNER JOIN CvSuivi cs ON cv.IDcvtheque = cs.IDcvtheque
    WHERE cv.ModifElem <> 'suppr'"""

    params: list = []
    where_extra: list[str] = []

    # Bornes dates
    deb, fin = _iso_bounds(date_debut, date_fin)

    if mode == "cp":
        where_extra.append(
            "(cv.DateSAISIE BETWEEN ? AND ? OR cv.DateREAC BETWEEN ? AND ?)"
        )
        params.extend([deb, fin, deb, fin])

        if id_cv_source:
            where_extra.append("cv.IDcvsource = ?")
            params.append(id_cv_source)
            if id_cv_source == 1 and id_coopteur:
                where_extra.append("cv.IdElemSource = ?")
                params.append(int(id_coopteur))
            elif id_cv_source == 2 and id_annonceur:
                where_extra.append("cv.IdElemSource = ?")
                params.append(id_annonceur)

        # Profil
        if profil == 1:
            where_extra.append("(cv.IDcvposte = 1 OR cv.IDcvposte = 0)")
        elif profil == 2:
            where_extra.append("(cv.IDcvposte = 10 OR cv.IDcvposte = 13)")
        elif profil == 3:
            where_extra.append(
                "(cv.IDcvposte = 1 OR cv.IDcvposte = 10 OR cv.IDcvposte = 13 OR cv.IDcvposte = 0)"
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
                "(cv.DateNaissance = '' OR cv.DateNaissance BETWEEN ? AND ?)"
            )
            params.extend([_iso_date(age_min_date), _iso_date(age_max_date)])
        else:
            where_extra.append("cv.DateNaissance BETWEEN ? AND ?")
            params.extend([_iso_date(age_min_date), _iso_date(age_max_date)])

        # Communes dans le rayon — liste d'IDs
        commune_ids = communes_dans_rayon(latitude, longitude, rayon_km)
        if not commune_ids:
            return []

    elif mode == "tel":
        tel_clean = "".join(c for c in tel if c.isdigit())
        if tel_clean:
            where_extra.append("cv.GSM LIKE ?")
            params.append(f"%{tel_clean}%")
        commune_ids = []

    elif mode == "nom":
        if nom:
            where_extra.append("cv.NOM LIKE ?")
            params.append(f"%{nom}%")
        if prenom:
            where_extra.append("cv.PRENOM LIKE ?")
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
                + f" AND cv.IDCommunesFrance IN ({ids_sql})"
                + " ORDER BY cs.Datecrea DESC"
            )
            rows = db.query(sql, tuple(params))
            for r in rows:
                idcv = _to_int(r.get("IDcvtheque"))
                if idcv not in seen_ids:
                    seen_ids.add(idcv)
                    all_rows.append(r)
            # Progress : 10% → 70% sur la boucle
            pct = 10 + int(60 * (i + 1) / n_batches)
            report(pct, f"Communes {i + 1}/{n_batches}")
    else:
        report(30, "Recherche en cours")
        sql = base + " ORDER BY cs.Datecrea DESC"
        rows = db.query(sql, tuple(params))
        for r in rows:
            idcv = _to_int(r.get("IDcvtheque"))
            if idcv not in seen_ids:
                seen_ids.add(idcv)
                all_rows.append(r)
        report(70, "Résultats récupérés")

    # Filtrage post-requête : statut + droit CV_VoirComplet
    if id_cv_statut:
        all_rows = [r for r in all_rows if _to_int(r.get("IdCvStatut")) == id_cv_statut]

    # Si pas de droit CV_VoirComplet, on ne voit que nos propres cooptations (Cooptation → IdElemSource = user)
    if not acces_complet and id_salarie_user:
        filtered: list[dict] = []
        for r in all_rows:
            if _to_int(r.get("IDcvsource")) == 1:
                if _to_int(r.get("IdElemSource")) != id_salarie_user:
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

    db_rec = get_connection("recrutement")
    db_rh = get_connection("rh")
    db_divers = get_connection("divers")

    report(75, "Communes et référentiels...")

    # 1. CP/Ville
    commune_ids = {_to_int(r.get("IDCommunesFrance")) for r in rows}
    commune_ids.discard(0)
    communes_map: dict[int, dict] = {}
    if commune_ids:
        ids_sql = ",".join(str(i) for i in commune_ids)
        crows = db_divers.query(
            f"SELECT IDCommunesFrance, CodePostal, NomVille FROM CommunesFrance "
            f"WHERE IDCommunesFrance IN ({ids_sql})"
        )
        for c in crows:
            communes_map[_to_int(c.get("IDCommunesFrance"))] = {
                "cp": c.get("CodePostal") or "",
                "ville": c.get("NomVille") or "",
            }

    # 2. Statuts
    statut_rows = db_rec.query(
        "SELECT IdCvStatut, LibStatut FROM cvstatut WHERE ModifElem NOT LIKE '%suppr%'"
    )
    statuts_map = {_to_int(s.get("IdCvStatut")): s.get("LibStatut") or "" for s in statut_rows}

    # 3. Sources
    source_rows = db_rec.query("SELECT IDcvsource, Lib_Source FROM CvSource")
    sources_map = {_to_int(s.get("IDcvsource")): s.get("Lib_Source") or "" for s in source_rows}

    # 4. Annonceurs
    annonceur_rows = db_rec.query("SELECT IDCvAnnonceur, Lib_Annonceur FROM CvAnnonceur")
    annonceurs_map = {
        _to_int(a.get("IDCvAnnonceur")): a.get("Lib_Annonceur") or "" for a in annonceur_rows
    }

    report(80, "Coopteurs et annonceurs...")

    # 5. Coopteurs (salariés) — batch
    coopteur_ids = {
        _to_int(r.get("IdElemSource"))
        for r in rows
        if _to_int(r.get("IDcvsource")) == 1
    }
    coopteur_ids.discard(0)
    coopteurs_map: dict[int, str] = {}
    if coopteur_ids:
        ids_sql = ",".join(str(i) for i in coopteur_ids)
        srows = db_rh.query(
            f"SELECT IDSalarie, NOM, PRENOM FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for s in srows:
            nom = s.get("NOM") or ""
            prenom = (s.get("PRENOM") or "").capitalize()
            coopteurs_map[_to_int(s.get("IDSalarie"))] = f"{nom} {prenom}".strip()

    # 6. opTraite (salariés)
    op_ids = {
        _to_int(r.get("opTraite")) for r in rows if r.get("TraiteEnCours")
    }
    op_ids.discard(0)
    op_map: dict[int, str] = {}
    if op_ids:
        ids_sql = ",".join(str(i) for i in op_ids)
        orows = db_rh.query(
            f"SELECT IDSalarie, PRENOM FROM salarie WHERE IDSalarie IN ({ids_sql})"
        )
        for o in orows:
            op_map[_to_int(o.get("IDSalarie"))] = (o.get("PRENOM") or "").capitalize()

    report(85, "Statuts période...")

    # 7. Statut période — par CV, dernier CvSuivi avant date_fin si date_fin < aujourd'hui
    # Optim : on fait une seule requête pour tous les CVs
    _, fin_iso = _iso_bounds(date_debut, date_fin)
    cv_ids = {_to_int(r.get("IDcvtheque")) for r in rows}
    cv_ids.discard(0)
    statut_periode_map: dict[int, int] = {}
    if cv_ids and date_fin and date_fin < datetime.now().strftime("%Y%m%d"):
        ids_sql = ",".join(str(i) for i in cv_ids)
        periode_rows = db_rec.query(
            f"""SELECT IDcvtheque, IdCvStatut, Datecrea FROM CvSuivi
            WHERE ModifELEM NOT LIKE '%suppr%'
              AND IDcvtheque IN ({ids_sql})
              AND ModifDate <= ?
            ORDER BY Datecrea DESC""",
            (fin_iso,),
        )
        for p in periode_rows:
            idcv = _to_int(p.get("IDcvtheque"))
            if idcv not in statut_periode_map:
                statut_periode_map[idcv] = _to_int(p.get("IdCvStatut"))

    report(90, "Affectations coopteurs...")

    # 8. Affectation agence/équipe des coopteurs - batch (optimisation)
    # On récupère tous les salarie_organigramme + organigramme pour les coopteurs
    # puis on mappe en mémoire par date
    affectation_map: dict[tuple[int, str], tuple[str, str]] = {}
    if coopteur_ids:
        ids_sql = ",".join(str(i) for i in coopteur_ids)
        orga_assignations = db_rh.query(
            f"""SELECT so.IDSalarie, so.idorganigramme, so.DateDébut, so.DateFin
            FROM salarie_organigramme so
            WHERE so.ModifELEM NOT LIKE '%suppr%'
              AND so.IDSalarie IN ({ids_sql})"""
        )

        # Récupérer toutes les organigrammes référencées
        orga_ids_lookup = {_to_int(r.get("idorganigramme")) for r in orga_assignations}
        orga_ids_lookup.discard(0)
        orga_info: dict[int, dict] = {}
        if orga_ids_lookup:
            ids_sql2 = ",".join(str(i) for i in orga_ids_lookup)
            orga_rows = db_rh.query(
                f"SELECT idorganigramme, Lib_ORGA, IdPARENT FROM organigramme "
                f"WHERE idorganigramme IN ({ids_sql2})"
            )
            for o in orga_rows:
                orga_info[_to_int(o.get("idorganigramme"))] = {
                    "lib": o.get("Lib_ORGA") or "",
                    "parent": _to_int(o.get("IdPARENT")),
                }
            # Récupérer les parents s'ils ne sont pas déjà là
            parent_ids = {info["parent"] for info in orga_info.values()} - orga_ids_lookup
            parent_ids.discard(0)
            if parent_ids:
                ids_sql3 = ",".join(str(i) for i in parent_ids)
                prows = db_rh.query(
                    f"SELECT idorganigramme, Lib_ORGA FROM organigramme "
                    f"WHERE idorganigramme IN ({ids_sql3})"
                )
                for p in prows:
                    orga_info[_to_int(p.get("idorganigramme"))] = {
                        "lib": p.get("Lib_ORGA") or "",
                        "parent": 0,
                    }

        # Grouper les affectations par salarié
        by_salarie: dict[int, list[dict]] = {}
        for a in orga_assignations:
            sid = _to_int(a.get("IDSalarie"))
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
                deb = _ymd(a.get("DateDébut") or "")
                fin = _ymd(a.get("DateFin") or "")
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
        idcv = _to_int(r.get("IDcvtheque"))
        id_commune = _to_int(r.get("IDCommunesFrance"))
        commune = communes_map.get(id_commune, {})
        localisation = ""
        if commune:
            localisation = f"{commune['cp']} {commune['ville']}".strip()

        # Age
        age = 0
        date_naiss = r.get("DateNaissance") or ""
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
        source_id = _to_int(r.get("IDcvsource"))
        elem_source = _to_int(r.get("IdElemSource"))
        agence = ""
        equipe = ""
        if source_id == 1:
            detail_source = coopteurs_map.get(elem_source, "")
            ds = r.get("DateSAISIE") or ""
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
        if r.get("TraiteEnCours"):
            op_traitement = op_map.get(_to_int(r.get("opTraite")), "")

        # Date saisie : si DateREAC est dans la période, l'utiliser sinon DateSAISIE
        date_saisie = r.get("DateSAISIE") or ""
        date_reac = r.get("DateREAC") or ""
        if date_debut and date_fin and date_reac:
            deb_iso, fin_iso2 = _iso_bounds(date_debut, date_fin)
            if deb_iso <= date_reac <= fin_iso2:
                date_saisie = date_reac

        # Statut actuel + période
        statut_actuel = _to_int(r.get("IdCvStatut"))
        statut_periode = statut_periode_map.get(idcv, statut_actuel)

        # Commentaire (dernière ligne de OBSERV)
        observ = r.get("OBSERV") or ""
        commentaire = observ.split("\n")[-1].strip() if observ else ""

        nom = (r.get("NOM") or "").strip()
        prenom = (r.get("PRENOM") or "").capitalize().strip()
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
            "tel": r.get("GSM") or "",
            "localisation": localisation,            "detail_source": detail_source,
            "agence": agence,
            "equipe": equipe,
            "commentaire": commentaire,
        })

    # Tri final : date saisie desc
    result.sort(key=lambda x: x.get("date_saisie") or "", reverse=True)
    return result
