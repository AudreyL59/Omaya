"""
Onglet 'Accès Omaya' (Droit d'accès) de la fiche salarie ADM.

Transposition de FI_SalarieDroitAcces.

Etape 1 :
  - Liste des droits du salarie (JOIN pgt_type_droit_acces /
    pgt_salarie_droit_acces) avec rupture par Categorie.
  - Bouton 'Activer/desactiver la selection' : toggle droit_actif
    pour chaque ligne cochee.
  - Bouton 'Supprimer' : soft delete (modif_elem='suppr').

Etape 2 (commit suivant) :
  - 2 popups d'ajout : Intranet/Appli (ADM=0, FDV=1) et Omaya Software
    (ADM=1, FDV=0, restreint aux droits de l'operateur connecte).
  - Bouton 'Choisir ce profil' (categorie pgt_profil_droit_acces).

Etape 3 :
  - Bouton 'Envoyer code Omaya' : genere/recupere MDP + envoie mail + SMS.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def load_droits(id_salarie: int) -> list[dict]:
    """Liste des droits attribues au salarie, JOIN sur le catalogue."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              sda.id_salarie_droit_acces,
              tda.id_type_droit_acces,
              tda.lib_droit,
              tda.code_interne,
              tda.description,
              tda.adm,
              tda.fdv,
              tda.categorie,
              sda.droit_actif
           FROM rh.pgt_salarie_droit_acces sda
           INNER JOIN rh.pgt_type_droit_acces tda
             ON sda.id_type_droit_acces = tda.id_type_droit_acces
           WHERE sda.id_salarie = ?
             AND sda.modif_elem NOT LIKE '%suppr%'
             AND tda.modif_elem NOT LIKE '%suppr%'
           ORDER BY tda.categorie ASC NULLS LAST, tda.lib_droit ASC""",
        (int(id_salarie),),
    )
    return [
        {
            "id_salarie_droit_acces": str(r.get("id_salarie_droit_acces") or ""),
            "id_type_droit_acces": _int(r.get("id_type_droit_acces")),
            "lib_droit": _str(r.get("lib_droit")),
            "code_interne": _str(r.get("code_interne")),
            "description": _str(r.get("description")),
            "adm": bool(r.get("adm")),
            "fdv": bool(r.get("fdv")),
            "categorie": _str(r.get("categorie")),
            "droit_actif": bool(r.get("droit_actif")),
        }
        for r in rows
    ]


def toggle_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Activer/desactiver la selection' : toggle droit_actif pour
    chaque ligne cochee. Si la combinaison (id_salarie, id_type) n'existe
    pas en base, on l'ignore (cf. WinDev HLitRecherche puis HModifie)."""
    db = get_pg_connection("rh")
    nb_toggled = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces, droit_actif
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        new_actif = not bool(row.get("droit_actif"))
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  droit_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_salarie_droit_acces = ?""",
            (
                new_actif,
                int(op_id),
                int(row.get("id_salarie_droit_acces")),
            ),
        )
        nb_toggled += 1
    return {"ok": True, "nb_toggled": nb_toggled}


def list_droits_disponibles(
    id_salarie: int, adm: bool, fdv: bool, op_user_id: int
) -> list[dict]:
    """Liste des droits disponibles a attribuer.

    Transposition des req SQL de Fen_SalarieDroitAjout (ADM=0, FDV=1)
    et Fen_ChoixDroitPerso (ADM=1, FDV=0, IDSalarie=usersCial).

    Filtrage selon WinDev :
      - Type du droit (adm / fdv).
      - WHERE salarie_droit_acces.id_salarie = ParamIDSalarie.
        - Pour Intranet/Appli (FDV) : ParamIDSalarie = id_salarie de la
          fiche -> retourne les droits attribues, listing principal.
          MAIS la popup d'ajout WinDev semble afficher tous les droits
          non-attribues pour selection (un INNER JOIN sur sda.id_salarie
          retourne les droits deja la, ce qui est etrange pour un
          'ajout'). On suit donc l'esprit : on liste TOUS les droits du
          type, le frontend peut ensuite afficher l'etat (attribue ou
          pas).
        - Pour Omaya Software (ADM) : ParamIDSalarie = usersCial -> on
          ne propose que les droits que l'operateur connecte possede.

    Retourne pour chaque droit : id, lib, code_interne, description,
    categorie, deja_attribue (au salarie cible), droit_actif (au salarie
    cible).
    """
    db = get_pg_connection("rh")
    # 1) Liste des droits du catalogue filtres ADM/FDV
    rows_cat = db.query(
        """SELECT id_type_droit_acces, lib_droit, code_interne,
                  description, categorie
           FROM rh.pgt_type_droit_acces
           WHERE adm = ? AND fdv = ?
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY categorie ASC NULLS LAST, lib_droit ASC""",
        (bool(adm), bool(fdv)),
    )
    if not rows_cat:
        return []

    # 2) Si on est sur le mode 'Omaya Software' (ADM=1), filtrer par
    #    les droits que op_user_id possede deja activement.
    if adm and op_user_id:
        droits_user = db.query(
            """SELECT id_type_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ?
                 AND COALESCE(droit_actif, FALSE) = TRUE
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(op_user_id),),
        )
        ok_ids = {_int(r.get("id_type_droit_acces")) for r in droits_user}
        rows_cat = [r for r in rows_cat if _int(r.get("id_type_droit_acces")) in ok_ids]

    # 3) Etat sur le salarie cible (deja attribue, actif ?)
    droits_sal = db.query(
        """SELECT id_type_droit_acces, droit_actif
           FROM rh.pgt_salarie_droit_acces
           WHERE id_salarie = ?
             AND modif_elem NOT LIKE '%suppr%'""",
        (int(id_salarie),),
    )
    etat_map = {
        _int(r.get("id_type_droit_acces")): bool(r.get("droit_actif"))
        for r in droits_sal
    }

    return [
        {
            "id_type_droit_acces": _int(r.get("id_type_droit_acces")),
            "lib_droit": _str(r.get("lib_droit")),
            "code_interne": _str(r.get("code_interne")),
            "description": _str(r.get("description")),
            "categorie": _str(r.get("categorie")),
            "deja_attribue": _int(r.get("id_type_droit_acces")) in etat_map,
            "droit_actif": etat_map.get(_int(r.get("id_type_droit_acces")), False),
        }
        for r in rows_cat
    ]


def attribuer_droits(
    id_salarie: int, id_types: list[int], droit_actif: bool, op_id: int
) -> dict:
    """Btn 'Valider ce(s) droit(s)' : INSERT si nouveau, sinon UPDATE
    avec droit_actif (Activer/Desactiver).

    Cf. Fen_ChoixDroitPerso / Fen_SalarieDroitAjout :
      si HTrouve = Faux -> INSERT droit_actif=Vrai (avec confirm UX)
      sinon -> UPDATE droit_actif=<param> (selon choix 'Activer' ou
      'Desactiver').
    """
    db = get_pg_connection("rh")
    nb_inserted = 0
    nb_updated = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if row:
            db.query(
                """UPDATE rh.pgt_salarie_droit_acces SET
                      droit_actif = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                    WHERE id_salarie_droit_acces = ?""",
                (
                    bool(droit_actif),
                    int(op_id),
                    int(row.get("id_salarie_droit_acces")),
                ),
            )
            nb_updated += 1
        else:
            new_id = _new_id()
            db.query(
                """INSERT INTO rh.pgt_salarie_droit_acces
                      (id_salarie_droit_acces, id_salarie,
                       id_type_droit_acces, droit_actif,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, NOW(), ?, 'new')""",
                (
                    new_id,
                    int(id_salarie),
                    int(id_type),
                    True,  # Cf. WinDev : a la creation, toujours actif
                    int(op_id),
                ),
            )
            nb_inserted += 1
    return {"ok": True, "nb_inserted": nb_inserted, "nb_updated": nb_updated}


def list_profils() -> list[str]:
    """Combo 'Profil' : DISTINCT categorie de pgt_type_poste."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT DISTINCT categorie FROM rh.pgt_type_poste
           WHERE categorie IS NOT NULL AND TRIM(categorie) <> ''
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY categorie ASC"""
    )
    return [_str(r.get("categorie")) for r in rows if r.get("categorie")]


def apply_profil(id_salarie: int, categorie: str, op_id: int) -> dict:
    """Btn 'Choisir ce profil' : applique tous les droits associes a une
    categorie via pgt_profil_droit_acces. INSERT si nouveau, UPDATE
    droit_actif=True si deja la."""
    if not categorie or not categorie.strip():
        return {"ok": False, "error": "Profil requis"}
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_droit_acces FROM rh.pgt_profil_droit_acces
           WHERE categorie = ?
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (categorie.strip(),),
    )
    id_types = [
        _int(r.get("id_type_droit_acces"))
        for r in rows
        if r.get("id_type_droit_acces")
    ]
    if not id_types:
        return {"ok": True, "nb_inserted": 0, "nb_updated": 0, "categorie": categorie}
    return {
        **attribuer_droits(id_salarie, id_types, droit_actif=True, op_id=op_id),
        "categorie": categorie,
    }


def soft_delete_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Supprimer' : soft delete pour chaque (id_salarie, id_type)."""
    db = get_pg_connection("rh")
    nb_deleted = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
                WHERE id_salarie_droit_acces = ?""",
            (int(op_id), int(row.get("id_salarie_droit_acces"))),
        )
        nb_deleted += 1
    return {"ok": True, "nb_deleted": nb_deleted}
