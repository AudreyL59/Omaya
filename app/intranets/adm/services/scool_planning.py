"""
Service Fen_ScoolPlanning - Planning S'Cool.

Cf. WinDev Fen_ScoolPlanning\\PlanningScool.txt (~122 lignes).

Pour chaque formateur (option : sortis inclus ou non) :
  1. Charge ses formations dans la periode selectionnee
     (dateDeb <= formation.date_debut OU formation.date_fin AU periode)
     AVEC formateur1..5 = idFormateur
  2. Determine son role sur chaque formation (principal/adjoint/3/4/5)
  3. Ajoute un event 'formation'
  4. Ajoute les events lies (pgt_formation_evenement)

Palette de couleurs identique par idFormation (utilise l'index de
formation dans la liste consolidee, cf. WinDev nCategorie).
"""
from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_planning import (
    PlanningEvent, PlanningParams, PlanningRessource, PlanningResult,
)

logger = logging.getLogger(__name__)


_PALETTE = [
    "#17494E", "#8B7355", "#B45309", "#B91C1C",
    "#7C3AED", "#065F46", "#0369A1", "#D97706",
    "#5B21B6", "#0F766E", "#BE185D", "#4338CA",
]


def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper()


def _iso_date(v) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _list_ressources(avec_sortis: bool) -> list[PlanningRessource]:
    """Cf. WinDev ReqListeFormateur : formateurs actifs (ou tous si
    avec_sortis).
    """
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT f.id_formateur, f.niveau,
                      s.nom, s.prenom,
                      e.en_activite
                 FROM scool.pgt_formateur f
                 JOIN pgt_salarie s ON s.id_salarie = f.id_formateur
                 LEFT JOIN pgt_salarie_embauche e
                        ON e.id_salarie = s.id_salarie
                       AND (e.modif_elem IS NULL
                            OR e.modif_elem NOT LIKE '%suppr%')
                WHERE f.id_formateur > 0
                  AND (f.modif_elem IS NULL
                       OR f.modif_elem NOT LIKE '%suppr%')
                  AND (s.modif_elem IS NULL
                       OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.nom ASC, s.prenom ASC""",
        ) or []
    except Exception:
        logger.exception("_list_ressources")
        return []
    seen: set[int] = set()
    out: list[PlanningRessource] = []
    for r in rows:
        actif = bool(r.get("en_activite"))
        if not avec_sortis and not actif:
            continue
        id_f = int(r.get("id_formateur") or 0)
        if id_f in seen:
            continue
        seen.add(id_f)
        niveau_raw = r.get("niveau")
        niveau = str(niveau_raw).strip() if niveau_raw not in (None, 0) else ""
        out.append(PlanningRessource(
            id_formateur=str(id_f),
            nom=(r.get("nom") or "").strip(),
            prenom=_cap_prenom((r.get("prenom") or "").strip()),
            niveau=niveau,
            is_actif=actif,
        ))
    return out


def _role_formateur(row: dict, id_formateur: int) -> str:
    """Determine le role du formateur sur une formation."""
    for i, lib in enumerate(
        [
            "Formateur principal", "Formateur adjoint",
            "Formateur 3", "Formateur 4", "Formateur 5",
        ],
        start=1,
    ):
        col = f"formateur{i}"
        if int(row.get(col) or 0) == id_formateur:
            return lib
    return ""


def build_planning(p: PlanningParams) -> PlanningResult:
    """Cf. WinDev PlanningScool Code Init."""
    if not p.date_deb or not p.date_fin:
        return PlanningResult()
    if p.date_deb > p.date_fin:
        return PlanningResult()

    ressources = _list_ressources(p.avec_sortis)
    if not ressources:
        return PlanningResult(ressources=[])

    scool = get_pg_connection("scool")
    events: list[PlanningEvent] = []
    formation_couleur: dict[int, str] = {}

    for res in ressources:
        id_f = int(res.id_formateur)
        # Requete WinDev ReqFormationByFormateur
        try:
            forms = scool.query(
                """SELECT f.id_formation, f.intitule, f.categorie,
                          f.ville_formation, f.date_debut, f.date_fin,
                          f.type_produit,
                          f.formateur1, f.formateur2, f.formateur3,
                          f.formateur4, f.formateur5
                     FROM scool.pgt_formation f
                    WHERE (f.modif_elem IS NULL
                           OR f.modif_elem NOT LIKE '%suppr%')
                      AND (
                        (f.date_debut BETWEEN ? AND ?)
                        OR (f.date_fin BETWEEN ? AND ?)
                        OR (f.date_debut <= ? AND f.date_fin >= ?)
                      )
                      AND (f.formateur1 = ? OR f.formateur2 = ?
                           OR f.formateur3 = ? OR f.formateur4 = ?
                           OR f.formateur5 = ?)""",
                (
                    p.date_deb, p.date_fin,
                    p.date_deb, p.date_fin,
                    p.date_deb, p.date_fin,
                    id_f, id_f, id_f, id_f, id_f,
                ),
            ) or []
        except Exception:
            logger.exception("build_planning formation %s", id_f)
            continue

        for f in forms:
            id_form = int(f.get("id_formation") or 0)
            if not id_form:
                continue
            # Couleur : index unique par id_formation
            if id_form not in formation_couleur:
                idx = len(formation_couleur) % len(_PALETTE)
                formation_couleur[id_form] = _PALETTE[idx]
            couleur = formation_couleur[id_form]

            role = _role_formateur(f, id_f)
            categorie = (f.get("categorie") or "").strip()
            intitule = (f.get("intitule") or "").strip()
            ville = (f.get("ville_formation") or "").strip()
            role_suf = f" ({role})" if role else ""
            ville_suf = f", {ville}" if ville else ""
            titre = f"{categorie} {intitule}{role_suf}{ville_suf}".strip()

            events.append(PlanningEvent(
                id=f"form-{id_form}-{id_f}",
                id_formation=str(id_form),
                id_formateur=str(id_f),
                titre=titre,
                date_debut=_iso_date(f.get("date_debut")),
                date_fin=_iso_date(f.get("date_fin")),
                couleur=couleur,
                kind="formation",
            ))

            # Evenements attaches a la formation
            try:
                evenements = scool.query(
                    """SELECT id_formation_evenement, date, intitule
                         FROM scool.pgt_formation_evenement
                        WHERE id_formation = ?
                          AND (modif_elem IS NULL
                               OR modif_elem NOT LIKE '%suppr%')""",
                    (id_form,),
                ) or []
            except Exception:
                evenements = []
            for e in evenements:
                d = _iso_date(e.get("date"))
                if not d or d < p.date_deb or d > p.date_fin:
                    continue
                events.append(PlanningEvent(
                    id=f"evt-{e.get('id_formation_evenement')}-{id_f}",
                    id_formation=str(id_form),
                    id_formateur=str(id_f),
                    titre=(
                        f"{(e.get('intitule') or '').strip()} "
                        f"({intitule})"
                    ).strip(),
                    date_debut=d, date_fin=d,
                    couleur="#B91C1C",
                    kind="evenement",
                ))

    return PlanningResult(ressources=ressources, events=events)
