"""Liste des process visibles pour un user.

Filtre :
  - le user est createur, OU
  - au moins un droit actif matche (id_salarie OR profil_hierarchique)
    + societe (id_ste = 0 ou = user.id_ste)
"""

from __future__ import annotations

import logging

from app.core.database.pg import get_pg_connection
from app.shared.process.schemas.process import ProcessListItem
from app.shared.process.services._helpers import (
    _iso_datetime, _str_id, nom_salarie, profil_user, profils_visibles_pour,
    societe_user,
)

logger = logging.getLogger(__name__)


def liste_process(user_id: int, search: str = "") -> list[ProcessListItem]:
    """Retourne les process visibles pour le user, tries par
    derniere_modif desc.

    `search` est un filtre client sur titre + mots_cles (ILIKE %s%).
    """
    if not user_id:
        return []
    user_profil = profil_user(user_id)
    user_ste = societe_user(user_id)
    profils_ok = profils_visibles_pour(user_profil)

    # Construction dynamique de la clause d'acces (sans placeholder pour
    # les listes IN, les IDs sont deja des int contrôles).
    parts = [f"p.ope_crea = {int(user_id)}"]  # createur voit toujours
    conds_droit = [f"pd.id_salarie = {int(user_id)}"]
    if profils_ok:
        profils_sql = ",".join(f"'{p}'" for p in profils_ok)
        conds_droit.append(f"pd.type_profil IN ({profils_sql})")
    droit_where = " OR ".join(conds_droit)
    ste_filter = f"(pd.id_ste = 0 OR pd.id_ste = {int(user_ste or 0)})"
    parts.append(
        f"""EXISTS (
            SELECT 1 FROM divers.pgt_process_droit pd
             WHERE pd.id_process = p.id_process
               AND COALESCE(pd.droit_actif, FALSE) = TRUE
               AND (pd.modif_elem IS NULL OR pd.modif_elem <> 'suppr')
               AND ({droit_where})
               AND {ste_filter}
        )""",
    )
    acces = " OR ".join(f"({p})" for p in parts)

    search_where = ""
    params: list = []
    q = (search or "").strip()
    if q:
        search_where = " AND (p.titre ILIKE ? OR p.mots_cles ILIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])

    sql = f"""SELECT p.id_process, p.titre, p.service, p.mots_cles,
                     p.date_crea, p.derniere_modif, p.ope_crea,
                     (SELECT COUNT(*) FROM divers.pgt_process_fichier f
                        WHERE f.id_process = p.id_process
                          AND (f.modif_elem IS NULL OR f.modif_elem <> 'suppr')
                     ) AS nb_fichiers
                FROM divers.pgt_process p
               WHERE (p.modif_elem IS NULL OR p.modif_elem <> 'suppr')
                 AND ({acces})
                 {search_where}
               ORDER BY COALESCE(p.derniere_modif, p.date_crea) DESC"""

    db = get_pg_connection("divers")
    try:
        rows = db.query(sql, tuple(params)) or []
    except Exception:
        logger.exception("liste_process user=%s", user_id)
        return []

    # Cache noms operateurs
    op_ids = {int(r.get("ope_crea") or 0) for r in rows}
    op_ids.discard(0)
    op_noms: dict[int, str] = {i: nom_salarie(i) for i in op_ids}

    out: list[ProcessListItem] = []
    for r in rows:
        ope_crea = int(r.get("ope_crea") or 0)
        out.append(ProcessListItem(
            IDProcess=_str_id(r.get("id_process")),
            Titre=r.get("titre") or "",
            Service=r.get("service") or "",
            MotsCles=r.get("mots_cles") or "",
            DateCrea=_iso_datetime(r.get("date_crea")),
            DerniereModif=_iso_datetime(r.get("derniere_modif")),
            OpeCrea=_str_id(ope_crea) if ope_crea else "",
            NomOpeCrea=op_noms.get(ope_crea, ""),
            NbFichiers=int(r.get("nb_fichiers") or 0),
        ))
    return out


def liste_societes() -> list[dict]:
    """Referentiel des societes actives (pour le dropdown 'Societe' des
    droits d'acces). Retourne [{'IdSte': str, 'Lib': str}]."""
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT id_ste, rs_interne, raison_sociale
                 FROM rh.pgt_societe
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY COALESCE(NULLIF(TRIM(rs_interne), ''),
                                  raison_sociale, '') ASC""",
        ) or []
    except Exception:
        logger.exception("liste_societes")
        return []
    out = []
    for r in rows:
        id_ste = int(r.get("id_ste") or 0)
        if not id_ste:
            continue
        lib = ((r.get("rs_interne") or r.get("raison_sociale") or "").strip())
        if not lib:
            continue
        out.append({"IdSte": str(id_ste), "Lib": lib})
    return out


def liste_services_distincts() -> list[str]:
    """Codes services distincts existant en base (pour l'autocomplete UI)."""
    db = get_pg_connection("divers")
    try:
        rows = db.query(
            """SELECT DISTINCT UPPER(TRIM(service)) AS s
                 FROM divers.pgt_process
                WHERE service IS NOT NULL AND TRIM(service) <> ''
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')
                ORDER BY 1""",
        ) or []
    except Exception:
        logger.exception("liste_services_distincts")
        return []
    return [r["s"] for r in rows if r.get("s")]
