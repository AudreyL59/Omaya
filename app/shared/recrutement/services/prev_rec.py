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

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrgaNode(BaseModel):
    idorganigramme: str
    lib_orga: str
    has_children: bool          # affiche le chevron / triangle


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
