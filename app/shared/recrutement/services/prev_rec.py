"""Service Fen_PrevRec (Prevision de Recrutement) — shared.

Affiche les sessions de prevision de recrutement pour un orga (et ses
descendants) avec filtre 'en cours' (date_butoire >= DateRef).

Pour cette etape : juste la lecture (liste racine, enfants, previsions).
Les actions (nouvelle session, edit, supprimer) viendront ensuite.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from datetime import datetime, timedelta

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str
from app.shared.tickets.forms.sortie_rh import _date_dernier_ctt


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrgaNode(BaseModel):
    idorganigramme: str
    lib_orga: str
    has_children: bool          # affiche le chevron / triangle


class OrgaInfo(BaseModel):
    idorganigramme: str
    lib_orga: str
    capacite: int = 0
    ville: str = ""
    cp: str = ""
    nb_productifs: int = 0          # calcule via DateDernierCttVendeur


class CooptSourcingStats(BaseModel):
    coopt: int = 0
    sourcing: int = 0
    nb_communes: int = 0
    nb_cv_analyses: int = 0


class VendeurOrgaRow(BaseModel):
    id_vendeur: str
    nom_prenom: str
    date_embauche: str = ""       # ISO
    dernier_ctt: str = ""         # ISO ou '' si jamais
    lib_equipe: str = ""
    id_equipe: str = ""
    has_ctt: bool = False         # False = ligne rouge foncee


class SessionPayload(BaseModel):
    idorganigramme: str
    id_recruteur: str = ""
    id_prev_recrut_etat: str = "1"  # En Prevision par defaut
    id_cv_lieu_rdv: str = ""
    id_communes_france: str = ""
    date_session: str = ""
    date_butoire: str = ""
    date_debut: str = ""
    date_fin: str = ""
    taille_session: int = 0
    potentiel_accueil: int = 0
    nb_prod: int = 0
    nb_coopt_mini: int = 30
    nb_sourcing_mini: int = 50
    obj_coopt: int = 0
    obj_sourcing: int = 0
    coopt_smoins1: int = 0
    coopt_jmoins2: int = 0
    sourcing_smoins1: int = 0
    sourcing_jmoins2: int = 0
    commentaire: str = ""


class EtatItem(BaseModel):
    id_prev_recrut_etat: str
    lib_etat: str


class PrevRecRow(BaseModel):
    id_prevision_recrut: str
    id_prev_recrut_etat: str
    lib_etat: str
    idorganigramme: str
    lib_orga: str
    id_cv_lieu_rdv: str
    lib_lieu: str = ""
    id_communes_france: str
    localisation: str = ""       # 'NomVille (CP)'
    date_session: str = ""       # ISO
    date_butoire: str = ""       # ISO
    date_debut: str = ""
    date_fin: str = ""
    commentaire: str = ""
    taille_session: int = 0
    potentiel_accueil: int = 0
    nb_prod: int = 0
    nb_coopt_mini: int = 0
    nb_sourcing_mini: int = 0
    obj_coopt: int = 0
    obj_sourcing: int = 0
    coopt_smoins1: int = 0
    coopt_jmoins2: int = 0
    sourcing_smoins1: int = 0
    sourcing_jmoins2: int = 0


# ---------------------------------------------------------------------------
# Arbre orga (chargement lazy via has_children)
# ---------------------------------------------------------------------------


def _has_children_sql(db) -> str:
    """Sous-requete pour determiner has_children."""
    return """EXISTS (
        SELECT 1 FROM rh.pgt_organigramme c
         WHERE c.id_parent = o.idorganigramme
           AND c.idorganigramme <> 0
           AND (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
    )"""


def list_orgas_racine() -> list[OrgaNode]:
    """Niveau 1 de l'arbre : orgas dont id_parent=0."""
    db = get_pg_connection("rh")
    sub = _has_children_sql(db)
    rows = db.query(
        f"""SELECT o.idorganigramme, o.lib_orga, {sub} AS hc
              FROM rh.pgt_organigramme o
             WHERE o.id_parent = 0
               AND o.idorganigramme <> 0
               AND (o.modif_elem IS NULL OR o.modif_elem NOT LIKE '%suppr%')
          ORDER BY o.lib_orga ASC"""
    ) or []
    return [OrgaNode(
        idorganigramme=str(_int(r["idorganigramme"])),
        lib_orga=_str(r["lib_orga"]),
        has_children=bool(r["hc"]),
    ) for r in rows]


def list_orgas_enfants(id_parent: int) -> list[OrgaNode]:
    """Enfants directs d'un orga."""
    if not id_parent:
        return []
    db = get_pg_connection("rh")
    sub = _has_children_sql(db)
    rows = db.query(
        f"""SELECT o.idorganigramme, o.lib_orga, {sub} AS hc
              FROM rh.pgt_organigramme o
             WHERE o.id_parent = ?
               AND o.idorganigramme <> 0
               AND (o.modif_elem IS NULL OR o.modif_elem NOT LIKE '%suppr%')
          ORDER BY o.lib_orga ASC""",
        (int(id_parent),),
    ) or []
    return [OrgaNode(
        idorganigramme=str(_int(r["idorganigramme"])),
        lib_orga=_str(r["lib_orga"]),
        has_children=bool(r["hc"]),
    ) for r in rows]


def _descendants(id_orga: int) -> list[int]:
    """Retourne id_orga + tous ses descendants (CTE recursive PG)."""
    if not id_orga:
        return []
    db = get_pg_connection("rh")
    rows = db.query(
        """WITH RECURSIVE tree AS (
              SELECT idorganigramme FROM rh.pgt_organigramme
               WHERE idorganigramme = ?
            UNION ALL
              SELECT c.idorganigramme FROM rh.pgt_organigramme c
                JOIN tree t ON c.id_parent = t.idorganigramme
               WHERE (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
                 AND c.idorganigramme <> 0
            )
            SELECT idorganigramme FROM tree""",
        (int(id_orga),),
    ) or []
    return [_int(r["idorganigramme"]) for r in rows]


# ---------------------------------------------------------------------------
# Listing previsions
# ---------------------------------------------------------------------------


def list_etats() -> list[EtatItem]:
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_prev_recrut_etat, lib_etat
             FROM recrutement.pgt_prev_recrut_etat
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY id_prev_recrut_etat ASC"""
    ) or []
    return [EtatItem(
        id_prev_recrut_etat=str(_int(r["id_prev_recrut_etat"])),
        lib_etat=_str(r["lib_etat"]),
    ) for r in rows]


def list_previsions(
    id_orga: int,
    date_ref: Optional[date] = None,
) -> list[PrevRecRow]:
    """Sessions de prevision en cours pour un orga (ou tout si id=0).
    En cours = date_butoire >= date_ref (ou date_butoire NULL = encore en
    pure prevision sans date butoir).

    Joint rh.pgt_organigramme (lib_orga), recrutement.pgt_prev_recrut_etat
    (lib_etat), recrutement.pgt_cv_lieu_rdv (lib_lieu), divers.pgt_communes_france
    (localisation).
    """
    db = get_pg_connection("recrutement")

    if id_orga:
        ids = _descendants(id_orga)
        if not ids:
            return []
        in_clause = ",".join(str(i) for i in ids)
        where_orga = f"AND p.idorganigramme IN ({in_clause})"
    else:
        where_orga = ""

    params: list = []
    where_date = ""
    if date_ref:
        where_date = "AND (p.date_butoire IS NULL OR p.date_butoire >= ?)"
        params.append(date_ref)

    sql = f"""
        SELECT p.id_prevision_recrut, p.id_prev_recrut_etat, p.idorganigramme,
               p.id_cv_lieu_rdv, p.id_communes_france,
               p.date_session, p.date_butoire, p.date_debut, p.date_fin,
               p.commentaire, p.taille_session, p.potentiel_accueil, p.nb_prod,
               p.nb_coopt_mini, p.nb_sourcing_mini, p.obj_coopt, p.obj_sourcing,
               p.coopt_smoins1, p.coopt_jmoins2,
               p.sourcing_smoins1, p.sourcing_jmoins2,
               o.lib_orga,
               e.lib_etat,
               l.lib_lieu,
               c.nom_ville, c.code_postal
          FROM recrutement.pgt_prev_recrut p
          LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = p.idorganigramme
          LEFT JOIN recrutement.pgt_prev_recrut_etat e
                 ON e.id_prev_recrut_etat = p.id_prev_recrut_etat
          LEFT JOIN recrutement.pgt_cv_lieu_rdv l ON l.id_cv_lieu_rdv = p.id_cv_lieu_rdv
          LEFT JOIN divers.pgt_communes_france c ON c.id_communes_france = p.id_communes_france
         WHERE (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
           {where_orga}
           {where_date}
      ORDER BY p.date_session ASC NULLS LAST, p.date_butoire ASC NULLS LAST
    """
    rows = db.query(sql, tuple(params)) or []

    def _iso(d) -> str:
        return d.isoformat() if d else ""

    out: list[PrevRecRow] = []
    for r in rows:
        ville = _str(r.get("nom_ville"))
        cp = _str(r.get("code_postal"))
        loc = f"{ville} ({cp})" if ville else ""
        out.append(PrevRecRow(
            id_prevision_recrut=str(_int(r["id_prevision_recrut"])),
            id_prev_recrut_etat=str(_int(r.get("id_prev_recrut_etat"))),
            lib_etat=_str(r.get("lib_etat")),
            idorganigramme=str(_int(r["idorganigramme"])),
            lib_orga=_str(r.get("lib_orga")),
            id_cv_lieu_rdv=str(_int(r.get("id_cv_lieu_rdv"))),
            lib_lieu=_str(r.get("lib_lieu")),
            id_communes_france=str(_int(r.get("id_communes_france"))),
            localisation=loc,
            date_session=_iso(r.get("date_session")),
            date_butoire=_iso(r.get("date_butoire")),
            date_debut=_iso(r.get("date_debut")),
            date_fin=_iso(r.get("date_fin")),
            commentaire=_str(r.get("commentaire")),
            taille_session=_int(r.get("taille_session")),
            potentiel_accueil=_int(r.get("potentiel_accueil")),
            nb_prod=_int(r.get("nb_prod")),
            nb_coopt_mini=_int(r.get("nb_coopt_mini")),
            nb_sourcing_mini=_int(r.get("nb_sourcing_mini")),
            obj_coopt=_int(r.get("obj_coopt")),
            obj_sourcing=_int(r.get("obj_sourcing")),
            coopt_smoins1=_int(r.get("coopt_smoins1")),
            coopt_jmoins2=_int(r.get("coopt_jmoins2")),
            sourcing_smoins1=_int(r.get("sourcing_smoins1")),
            sourcing_jmoins2=_int(r.get("sourcing_jmoins2")),
        ))
    return out


# ---------------------------------------------------------------------------
# Info orga + comptage productifs (pour Fen_PrevRec_Ajout)
# ---------------------------------------------------------------------------


def _salaries_actifs_orga(id_orga: int) -> list[int]:
    """Liste les id_salarie actifs d'un orga (et descendants).

    Critere : salarie.agenda_actif = TRUE
              + salarie_embauche.en_activite IN (TRUE, ParamActif)
              + pas supprime
    """
    if not id_orga:
        return []
    db = get_pg_connection("rh")
    ids = _descendants(id_orga)
    if not ids:
        return []
    in_clause = ",".join(str(i) for i in ids)
    # 'en_activite' peut etre une variable d'etat (probable enum / int).
    # WinDev : EnActivité = 1 OR EnActivité = ParamActif. On garde une
    # logique large : actif et non supprime.
    rows = db.query(
        f"""SELECT DISTINCT s.id_salarie
              FROM rh.pgt_salarie s
              JOIN rh.pgt_salarie_organigramme so ON so.id_salarie = s.id_salarie
             WHERE so.idorganigramme IN ({in_clause})
               AND s.agenda_actif = TRUE
               AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
               AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')"""
    ) or []
    return [_int(r["id_salarie"]) for r in rows]


def get_orga_info(id_orga: int) -> OrgaInfo:
    """Info orga + comptage productifs.

    nb_productifs = salaries actifs ayant un contrat vendeur (date != sentinelle
    20070101). Reuse _date_dernier_ctt() partage.
    """
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT idorganigramme, lib_orga,
                  COALESCE(capacite, 0) AS capacite,
                  COALESCE(ville, '') AS ville
             FROM rh.pgt_organigramme
            WHERE idorganigramme = ?""",
        (int(id_orga),),
    )
    if not r:
        return OrgaInfo(idorganigramme=str(id_orga), lib_orga="?")
    capacite = _int(r.get("capacite"))
    ville = _str(r.get("ville"))
    lib = _str(r.get("lib_orga"))

    # Bonus WinDev : si pas de ville mais lib contient 'PL', tente d'extraire.
    # ex: 'Equipe ALLAIN/BREST/SFR/5PL' -> place=5, ville=SFR (segment -2)
    if not ville and "PL" in lib.upper():
        segs = lib.split("/")
        if len(segs) >= 2:
            last = segs[-1].upper().replace("PL", "").strip()
            try:
                capacite += int(last)
            except ValueError:
                pass
            ville = segs[-2].strip().upper()

    # Comptage productifs (peut etre long si grosse orga)
    nb_prod = 0
    for id_sal in _salaries_actifs_orga(id_orga):
        try:
            d = _date_dernier_ctt(id_sal)
        except Exception:
            d = ""
        # Sentinelle WinDev '20070101' = pas de contrat
        if d and d != "2007-01-01":
            nb_prod += 1

    return OrgaInfo(
        idorganigramme=str(id_orga),
        lib_orga=lib,
        capacite=capacite,
        ville=ville,
        nb_productifs=nb_prod,
    )


# ---------------------------------------------------------------------------
# Recherche coopt/sourcing pour les boutons S-1 et J-2
# ---------------------------------------------------------------------------


def cherche_coopt_sourcing(
    id_communes_france: int,
    rayon_km: int,
    type_recherche: int,                 # 1=S-1 (date_crea fixe), 2=J-2 (today)
    date_crea_iso: str,                  # 'YYYY-MM-DD HH:MM:SS' = base
) -> CooptSourcingStats:
    """Cherche le nombre de CV cooptes (id_cv_source=1) et sourcing
    (autres) dans une zone geographique + periode.

    Filtres :
      - cv source IN (1, 3, 7)
      - age 18-36 ans
      - statut courant = 1
      - dans la liste des communes < rayon km du centre
      - date_saisie ou date_reac entre [date_crea -1 mois, date_fin]
        ou date_fin = today si type=2 sinon date_crea
    """
    db = get_pg_connection("recrutement")
    db_divers = get_pg_connection("divers")

    # Bornage age
    today = datetime.now().date()
    age_max = today.replace(year=today.year - 36) + timedelta(days=1)
    age_min = today  # 0 ans = ne change pas (vide accepte aussi)

    # Bornage saisie : date_crea -1 mois -> date_fin
    try:
        dt_crea = datetime.fromisoformat(date_crea_iso)
    except ValueError:
        dt_crea = datetime.now()
    dt_deb = (dt_crea - timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    dt_fin = (datetime.now() if type_recherche == 2 else dt_crea).replace(
        hour=23, minute=59, second=59, microsecond=0,
    )

    # Liste des communes dans le rayon
    cps: list[int] = []
    if id_communes_france and rayon_km > 0:
        try:
            r = db_divers.query_one(
                """SELECT latitude_deg, longitude_deg
                     FROM divers.pgt_communes_france
                    WHERE id_communes_france = ?""",
                (int(id_communes_france),),
            )
            if r and r.get("latitude_deg") and r.get("longitude_deg"):
                # Distance approx (haversine simplifie)
                lat0 = float(r["latitude_deg"])
                lng0 = float(r["longitude_deg"])
                # 1deg lat ~ 111km. Bounding box rapide puis filtre fin.
                drow = db_divers.query(
                    """SELECT id_communes_france
                         FROM divers.pgt_communes_france
                        WHERE latitude_deg BETWEEN ? AND ?
                          AND longitude_deg BETWEEN ? AND ?""",
                    (
                        lat0 - rayon_km / 111.0, lat0 + rayon_km / 111.0,
                        lng0 - rayon_km / 80.0,  lng0 + rayon_km / 80.0,
                    ),
                ) or []
                cps = [_int(x["id_communes_france"]) for x in drow]
        except Exception:
            cps = []

    where_cp = ""
    if cps:
        in_clause = ",".join(str(c) for c in cps)
        where_cp = f"AND cv.id_communes_france IN ({in_clause})"

    sql = f"""
        SELECT cv.id_cvtheque, cv.id_cvsource AS id_cv_source
          FROM recrutement.pgt_cvtheque cv
         WHERE (cv.modif_elem IS NULL OR cv.modif_elem NOT LIKE '%suppr%')
           AND cv.id_cvsource IN (1, 3, 7)
           AND cv.id_cvposte IN (0, 1, 10, 13)
           AND (cv.date_naissance IS NULL OR
                cv.date_naissance BETWEEN ? AND ?)
           AND (
                (cv.date_saisie BETWEEN ? AND ?)
             OR (cv.date_reac IS NOT NULL AND cv.date_reac BETWEEN ? AND ?)
           )
           {where_cp}
    """
    rows = db.query(sql, (
        age_max, age_min, dt_deb, dt_fin, dt_deb, dt_fin,
    )) or []

    # Filtre supplementaire : dernier statut = 1
    coopt = 0
    sourcing = 0
    nb_analyses = 0
    for row in rows:
        nb_analyses += 1
        id_cv = _int(row["id_cvtheque"])
        st = db.query_one(
            """SELECT id_cv_statut FROM recrutement.pgt_cvsuivi
                WHERE id_cvtheque = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
             ORDER BY datecrea DESC NULLS LAST LIMIT 1""",
            (id_cv,),
        )
        if not st or _int(st.get("id_cv_statut")) != 1:
            continue
        if _int(row["id_cv_source"]) == 1:
            coopt += 1
        else:
            sourcing += 1

    return CooptSourcingStats(
        coopt=coopt, sourcing=sourcing,
        nb_communes=len(cps), nb_cv_analyses=nb_analyses,
    )


# ---------------------------------------------------------------------------
# Create / save session
# ---------------------------------------------------------------------------


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def create_session(p: SessionPayload, op_id: int) -> dict:
    """INSERT nouvelle prevision recrut + retour id_prevision_recrut cree."""
    db = get_pg_connection("recrutement")
    id_new = _new_id()
    r = db.query_one(
        """SELECT COALESCE(MAX(id_prevision_recrut_auto), 0) + 1 AS n
             FROM recrutement.pgt_prev_recrut"""
    )
    auto = _int(r["n"]) if r else 1

    def _d(s: str):
        try:
            return datetime.fromisoformat(s).date() if s else None
        except ValueError:
            return None

    db.query(
        """INSERT INTO recrutement.pgt_prev_recrut (
              id_prevision_recrut_auto, id_prevision_recrut,
              idorganigramme, id_recruteur, id_prev_recrut_etat,
              id_cv_lieu_rdv, id_communes_france,
              date_session, date_butoire, date_debut, date_fin,
              taille_session, potentiel_accueil, nb_prod,
              nb_coopt_mini, nb_sourcing_mini, obj_coopt, obj_sourcing,
              coopt_smoins1, coopt_jmoins2,
              sourcing_smoins1, sourcing_jmoins2,
              commentaire,
              modif_date, modif_op, modif_elem
           ) VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
              ?, ?, ?, ?, ?,
              NOW(), ?, 'new'
           )""",
        (
            auto, id_new,
            _int(p.idorganigramme), _int(p.id_recruteur) or None,
            _int(p.id_prev_recrut_etat) or 1,
            _int(p.id_cv_lieu_rdv) or None,
            _int(p.id_communes_france) or None,
            _d(p.date_session), _d(p.date_butoire),
            _d(p.date_debut), _d(p.date_fin),
            p.taille_session, p.potentiel_accueil, p.nb_prod,
            p.nb_coopt_mini, p.nb_sourcing_mini, p.obj_coopt, p.obj_sourcing,
            p.coopt_smoins1, p.coopt_jmoins2,
            p.sourcing_smoins1, p.sourcing_jmoins2,
            p.commentaire,
            int(op_id),
        ),
    )
    return {"ok": True, "id_prevision_recrut": str(id_new)}


# ---------------------------------------------------------------------------
# Edition (Fen_PrevRec_Fiche)
# ---------------------------------------------------------------------------


def get_session(id_prev: int) -> Optional[PrevRecRow]:
    """Charge une prevision pour edition."""
    rows = list_previsions(0)
    # Reuse list_previsions sans filtre date_ref puis filtre id en Python
    for r in rows:
        if r.id_prevision_recrut == str(id_prev):
            return r
    # Fallback : si pas dans la liste (ex. butoire passee), requete directe
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT p.id_prevision_recrut, p.id_prev_recrut_etat, p.idorganigramme,
                  p.id_cv_lieu_rdv, p.id_communes_france,
                  p.date_session, p.date_butoire, p.date_debut, p.date_fin,
                  p.commentaire, p.taille_session, p.potentiel_accueil, p.nb_prod,
                  p.nb_coopt_mini, p.nb_sourcing_mini, p.obj_coopt, p.obj_sourcing,
                  p.coopt_smoins1, p.coopt_jmoins2,
                  p.sourcing_smoins1, p.sourcing_jmoins2,
                  p.id_recruteur,
                  o.lib_orga, e.lib_etat, l.lib_lieu,
                  c.nom_ville, c.code_postal
             FROM recrutement.pgt_prev_recrut p
             LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = p.idorganigramme
             LEFT JOIN recrutement.pgt_prev_recrut_etat e
                    ON e.id_prev_recrut_etat = p.id_prev_recrut_etat
             LEFT JOIN recrutement.pgt_cv_lieu_rdv l
                    ON l.id_cv_lieu_rdv = p.id_cv_lieu_rdv
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = p.id_communes_france
            WHERE p.id_prevision_recrut = ?""",
        (int(id_prev),),
    )
    if not r:
        return None

    def _iso(d) -> str:
        return d.isoformat() if d else ""

    ville = _str(r.get("nom_ville"))
    cp = _str(r.get("code_postal"))
    return PrevRecRow(
        id_prevision_recrut=str(_int(r["id_prevision_recrut"])),
        id_prev_recrut_etat=str(_int(r.get("id_prev_recrut_etat"))),
        lib_etat=_str(r.get("lib_etat")),
        idorganigramme=str(_int(r["idorganigramme"])),
        lib_orga=_str(r.get("lib_orga")),
        id_cv_lieu_rdv=str(_int(r.get("id_cv_lieu_rdv"))),
        lib_lieu=_str(r.get("lib_lieu")),
        id_communes_france=str(_int(r.get("id_communes_france"))),
        localisation=f"{ville} ({cp})" if ville else "",
        date_session=_iso(r.get("date_session")),
        date_butoire=_iso(r.get("date_butoire")),
        date_debut=_iso(r.get("date_debut")),
        date_fin=_iso(r.get("date_fin")),
        commentaire=_str(r.get("commentaire")),
        taille_session=_int(r.get("taille_session")),
        potentiel_accueil=_int(r.get("potentiel_accueil")),
        nb_prod=_int(r.get("nb_prod")),
        nb_coopt_mini=_int(r.get("nb_coopt_mini")),
        nb_sourcing_mini=_int(r.get("nb_sourcing_mini")),
        obj_coopt=_int(r.get("obj_coopt")),
        obj_sourcing=_int(r.get("obj_sourcing")),
        coopt_smoins1=_int(r.get("coopt_smoins1")),
        coopt_jmoins2=_int(r.get("coopt_jmoins2")),
        sourcing_smoins1=_int(r.get("sourcing_smoins1")),
        sourcing_jmoins2=_int(r.get("sourcing_jmoins2")),
    )


def update_session(id_prev: int, p: SessionPayload, op_id: int) -> dict:
    """UPDATE prevision_recrut. Logging des changements date_session /
    date_butoire (cf WinDev creaLogOmaya)."""
    db = get_pg_connection("recrutement")
    if not id_prev:
        return {"ok": False, "error": "id_required"}

    def _d(s: str):
        try:
            return datetime.fromisoformat(s).date() if s else None
        except ValueError:
            return None

    db.query(
        """UPDATE recrutement.pgt_prev_recrut SET
              id_recruteur = ?, id_prev_recrut_etat = ?,
              id_cv_lieu_rdv = ?, id_communes_france = ?,
              date_session = ?, date_butoire = ?,
              date_debut = ?, date_fin = ?,
              taille_session = ?, potentiel_accueil = ?, nb_prod = ?,
              nb_coopt_mini = ?, nb_sourcing_mini = ?,
              obj_coopt = ?, obj_sourcing = ?,
              coopt_smoins1 = ?, coopt_jmoins2 = ?,
              sourcing_smoins1 = ?, sourcing_jmoins2 = ?,
              commentaire = ?,
              modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_prevision_recrut = ?""",
        (
            _int(p.id_recruteur) or None,
            _int(p.id_prev_recrut_etat) or 1,
            _int(p.id_cv_lieu_rdv) or None,
            _int(p.id_communes_france) or None,
            _d(p.date_session), _d(p.date_butoire),
            _d(p.date_debut), _d(p.date_fin),
            p.taille_session, p.potentiel_accueil, p.nb_prod,
            p.nb_coopt_mini, p.nb_sourcing_mini,
            p.obj_coopt, p.obj_sourcing,
            p.coopt_smoins1, p.coopt_jmoins2,
            p.sourcing_smoins1, p.sourcing_jmoins2,
            p.commentaire,
            int(op_id), int(id_prev),
        ),
    )
    return {"ok": True, "id_prevision_recrut": str(id_prev)}


def list_vendeurs_orga(id_orga: int) -> list[VendeurOrgaRow]:
    """Liste les vendeurs actifs d'un orga (et descendants) avec
    date_embauche + dernier_ctt + lib_equipe.

    Couleur rouge fonce = pas de contrat (has_ctt=False).
    """
    if not id_orga:
        return []
    db = get_pg_connection("rh")
    ids = _descendants(id_orga)
    if not ids:
        return []
    in_clause = ",".join(str(i) for i in ids)
    rows = db.query(
        f"""SELECT s.id_salarie, s.nom, s.prenom,
                   e.date_debut,
                   so.idorganigramme AS id_eq,
                   o.lib_orga AS lib_eq
              FROM rh.pgt_salarie s
              JOIN rh.pgt_salarie_organigramme so ON so.id_salarie = s.id_salarie
              LEFT JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
              LEFT JOIN rh.pgt_organigramme o ON o.idorganigramme = so.idorganigramme
             WHERE so.idorganigramme IN ({in_clause})
               AND s.agenda_actif = TRUE
               AND (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
               AND (so.modif_elem IS NULL OR so.modif_elem NOT LIKE '%suppr%')
          ORDER BY s.nom ASC, s.prenom ASC"""
    ) or []

    seen: set[int] = set()
    out: list[VendeurOrgaRow] = []
    for r in rows:
        sid = _int(r["id_salarie"])
        if sid in seen:
            continue
        seen.add(sid)
        try:
            dctt = _date_dernier_ctt(sid)
        except Exception:
            dctt = ""
        has = bool(dctt) and dctt != "2007-01-01"
        nom = _str(r.get("nom")).upper()
        prenom = _str(r.get("prenom"))
        prenom_cap = prenom[:1].upper() + prenom[1:].lower() if prenom else ""
        de = r.get("date_debut")
        out.append(VendeurOrgaRow(
            id_vendeur=str(sid),
            nom_prenom=f"{nom} {prenom_cap}".strip(),
            date_embauche=de.isoformat() if de else "",
            dernier_ctt=dctt if has else "",
            lib_equipe=_str(r.get("lib_eq")),
            id_equipe=str(_int(r.get("id_eq"))),
            has_ctt=has,
        ))
    return out
