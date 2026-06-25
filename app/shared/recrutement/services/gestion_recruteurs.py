"""Service Fen_Agenda_GestionRecruteur (shared).

Liste les salaries qui ont au moins un evenement dans l'agenda
(= recruteurs potentiels) avec leur etat agenda_actif et en_activite.

Bouton 'Activer/desactiver' : toggle pgt_salarie.agenda_actif.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


class RecruteurRow(BaseModel):
    id_salarie: str
    nom_prenom: str
    agenda_actif: bool
    en_activite: bool


def list_recruteurs_agenda(salarie_actif: bool = True) -> list[RecruteurRow]:
    """Salaries qui ont des evenements agenda + en_activite filtre.

    Equivalent ReqRecruteur WinDev : RIGHT JOIN AgendaEvenement avec
    distinct sur les salaries embauches dont en_activite=ParmaActif.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT DISTINCT s.id_salarie, s.nom, s.prenom, s.agenda_actif,
                  e.en_activite
             FROM rh.pgt_salarie s
             JOIN rh.pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
             JOIN recrutement.pgt_agenda_evenement ae
               ON ae.id_salarie = s.id_salarie
            WHERE (s.modif_elem IS NULL OR s.modif_elem NOT LIKE '%suppr%')
              AND s.id_salarie <> 0
              AND e.en_activite = ?
         ORDER BY s.nom ASC, s.prenom ASC""",
        (bool(salarie_actif),),
    ) or []

    seen: set[int] = set()
    out: list[RecruteurRow] = []
    for r in rows:
        sid = _int(r["id_salarie"])
        if sid in seen:
            continue
        seen.add(sid)
        nom = _str(r.get("nom")).upper()
        prenom = _str(r.get("prenom"))
        pc = prenom[:1].upper() + prenom[1:].lower() if prenom else ""
        out.append(RecruteurRow(
            id_salarie=str(sid),
            nom_prenom=f"{nom} {pc}".strip(),
            agenda_actif=bool(r.get("agenda_actif")),
            en_activite=bool(r.get("en_activite")),
        ))
    return out


def toggle_agenda_actif(ids: list[int], op_id: int) -> dict:
    """Inverse agenda_actif pour chaque salarie de la liste."""
    if not ids:
        return {"ok": False, "error": "empty"}
    db = get_pg_connection("rh")
    in_clause = ",".join(str(int(i)) for i in ids if int(i))
    if not in_clause:
        return {"ok": False, "error": "empty"}
    db.query(
        f"""UPDATE rh.pgt_salarie
              SET agenda_actif = NOT agenda_actif,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_salarie IN ({in_clause})""",
        (int(op_id),),
    )
    return {"ok": True, "count": in_clause.count(",") + 1}
