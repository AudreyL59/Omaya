"""Service Fen_DistribCttCourtage (Docs Dematerialises d'une societe).

Cf code WinDev : depuis Fen_FicheSociete bouton 'Docs Dematerialises' :
    OuvreSoeur(Fen_DistribCttCourtage, IdSte)

La fenetre affiche pour un distributeur donne (id_ste) :
  - Header : Raison sociale du distrib + Nom du gerant
  - Tableau haut : Groupes de remuneration (pgt_groupe_rem JOIN
    pgt_partenaire) groupes visuellement par Famille
  - Tableau bas : Editions de contrat (pgt_societe_doc_courtage
    JOIN salarie + doc_courtage)
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


def _date_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, (date, datetime)): return v.strftime("%Y-%m-%d")
    return str(v)


class DistribInfos(BaseModel):
    id_ste: str
    raison_sociale: str = ""
    id_gerant: int = 0
    gerant_display: str = ""


class GroupeRemItem(BaseModel):
    id_groupe_rem: str
    famille: str = ""              # lib_partenaire (Fibre, Mobile, ...)
    famille_id: int = 0            # id_partenaire
    ss_fam: str = ""
    lib_groupe: str = ""
    date_deb: str = ""
    date_fin: str = ""
    is_actif: bool = True


class EditionCttItem(BaseModel):
    id_societe_doc_courtage: str
    id_salarie: int
    nom_gerant: str = ""
    id_groupe_operateur: int = 0     # 'Operateur' col WinDev
    col_secteur: str = ""            # Secteur
    date_edition: str = ""
    recu: bool = False
    recu_date: str = ""


def get_distrib_infos(id_ste: int) -> DistribInfos | None:
    """Charge raison_sociale + gerant (Nom Prenom capitalise)
    cf reqinfoSte WinDev. Match par id_ste (pas id_societe_auto)."""
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT s.raison_sociale, s.id_gerant, sa.nom, sa.prenom
             FROM rh.pgt_societe s
             LEFT JOIN rh.pgt_salarie sa ON sa.id_salarie = s.id_gerant
            WHERE s.id_ste = ? LIMIT 1""",
        (int(id_ste),),
    )
    if not r: return None
    nom = (r.get("nom") or "").strip()
    prenom = (r.get("prenom") or "").strip().lower()
    prenom = prenom[:1].upper() + prenom[1:] if prenom else ""
    gerant = f"{nom} {prenom}".strip()
    return DistribInfos(
        id_ste=str(id_ste),
        raison_sociale=r.get("raison_sociale") or "",
        id_gerant=int(r.get("id_gerant") or 0),
        gerant_display=gerant,
    )


def list_groupes_rem(id_distrib: int) -> list[GroupeRemItem]:
    """cf ReqGroupeRem WinDev :
       JOIN groupe_rem + partenaire, tri Famille/SsFam/IsActif/DateDeb DESC.
       'Famille' cote SQL = colonne famille (id_partenaire numerique)."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT g.id_groupe_rem, g.id_distrib, g.famille AS id_famille,
                  g.ss_fam, g.lib_groupe, g.date_deb, g.date_fin, g.is_actif,
                  p.lib_partenaire
             FROM adv.pgt_groupe_rem g
             LEFT JOIN adv.pgt_partenaire p ON p.id_partenaire = g.famille
            WHERE g.id_distrib = ?
              AND (g.modif_elem IS NULL OR g.modif_elem NOT LIKE '%suppr%')
            ORDER BY p.lib_partenaire, g.ss_fam, g.is_actif DESC,
                     g.date_deb DESC""",
        (int(id_distrib),),
    ) or []
    return [GroupeRemItem(
        id_groupe_rem=str(r["id_groupe_rem"]),
        famille=r.get("lib_partenaire") or "",
        famille_id=int(r.get("id_famille") or 0),
        ss_fam=r.get("ss_fam") or "",
        lib_groupe=r.get("lib_groupe") or "",
        date_deb=_date_str(r.get("date_deb")),
        date_fin=_date_str(r.get("date_fin")),
        is_actif=bool(r.get("is_actif")),
    ) for r in rows]


# ====================================================================
# Fen_GroupeRemFiche - Nouveau / Editer un groupe de remuneration
# ====================================================================


# ID_PARTENAIRE special SFR (cf code WinDev 'si Famille = 562949953421315')
# -> quand famille=SFR, on lit baremePoint.Famille au lieu de baremePoint.SousFAM
PART_SFR = 562949953421315


class GroupeOperateurItem(BaseModel):
    id_groupe_operateur: int
    lib_groupe: str = ""


class PartenaireItem(BaseModel):
    id_partenaire: int
    lib_partenaire: str = ""


class GroupeRemDetail(BaseModel):
    id_groupe_rem: str = "0"
    id_distrib: str = ""
    id_groupe_operateur: int = 0
    lib_groupe: str = ""
    famille: int = 0
    ss_fam: str = ""
    nb_col: int = 0
    nb_ligne: int = 0
    date_deb: str = ""
    date_fin: str = ""
    is_actif: bool = True


class GroupeRemPayload(BaseModel):
    id_distrib: int
    id_groupe_operateur: int = 0
    lib_groupe: str = ""
    famille: int = 0
    ss_fam: str = ""
    nb_col: int = 0
    nb_ligne: int = 0
    date_deb: str | None = None
    date_fin: str | None = None
    is_actif: bool = True


def _new_id() -> int:
    """ID entier 8 octets = timestamp yyyyMMddHHmmssSSS."""
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def list_groupes_operateur() -> list[GroupeOperateurItem]:
    """Combo 'Groupe Doc' - alimentee par la table GroupeOperateur."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT id_groupe_operateur, lib_groupe
             FROM adv.pgt_groupe_operateur
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY lib_groupe""",
    ) or []
    return [GroupeOperateurItem(
        id_groupe_operateur=int(r["id_groupe_operateur"]),
        lib_groupe=r.get("lib_groupe") or "",
    ) for r in rows]


def list_familles_by_grop(id_groupe_operateur: int) -> list[PartenaireItem]:
    """Combo 'Famille' filtree par le Groupe Operateur choisi
    (cf reqFamille WinDev : JOIN sur GroupeOperateur_Partenaire)."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT DISTINCT p.id_partenaire, p.lib_partenaire
             FROM adv.pgt_partenaire p
             JOIN adv.pgt_groupe_operateur_partenaire gop
                 ON gop.id_partenaire = p.id_partenaire
            WHERE gop.id_groupe_operateur = ?
              AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')
            ORDER BY p.lib_partenaire""",
        (int(id_groupe_operateur),),
    ) or []
    return [PartenaireItem(
        id_partenaire=int(r["id_partenaire"]),
        lib_partenaire=r.get("lib_partenaire") or "",
    ) for r in rows]


def list_ss_fam(famille_id: int) -> list[str]:
    """Combo 'Ss Fam' filtree par Famille (cf RemplirComboSsFam WinDev) :
    - Si Famille = SFR (562949953421315) : baremePoint.Famille
    - Sinon : baremePoint.SousFAM
    Prepend 'Tous' + 'Divers' quelle que soit la famille."""
    out: list[str] = ["Tous", "Divers"]
    db = get_pg_connection("adv")
    col = "famille" if int(famille_id) == PART_SFR else "sous_fam"
    rows = db.query(
        f"""SELECT DISTINCT {col} AS v FROM adv.pgt_bareme_point
             WHERE id_partenaire = ?
               AND {col} IS NOT NULL AND {col} <> ''
             ORDER BY {col}""",
        (int(famille_id),),
    ) or []
    for r in rows:
        v = (r.get("v") or "").strip()
        if v and v not in out: out.append(v)
    return out


def get_groupe_rem(id_groupe_rem: int) -> GroupeRemDetail | None:
    db = get_pg_connection("adv")
    r = db.query_one(
        """SELECT id_groupe_rem, id_distrib, id_groupe_operateur,
                  lib_groupe, famille, ss_fam, nb_col, nb_ligne,
                  date_deb, date_fin, is_actif
             FROM adv.pgt_groupe_rem
            WHERE id_groupe_rem = ? LIMIT 1""",
        (int(id_groupe_rem),),
    )
    if not r: return None
    return GroupeRemDetail(
        id_groupe_rem=str(r["id_groupe_rem"]),
        id_distrib=str(r.get("id_distrib") or ""),
        id_groupe_operateur=int(r.get("id_groupe_operateur") or 0),
        lib_groupe=r.get("lib_groupe") or "",
        famille=int(r.get("famille") or 0),
        ss_fam=r.get("ss_fam") or "",
        nb_col=int(r.get("nb_col") or 0),
        nb_ligne=int(r.get("nb_ligne") or 0),
        date_deb=_date_str(r.get("date_deb")),
        date_fin=_date_str(r.get("date_fin")),
        is_actif=bool(r.get("is_actif")),
    )


def create_groupe_rem(p: GroupeRemPayload, op_id: int) -> int:
    """Cree un groupe_rem + nb_col colonnes X + nb_ligne lignes Y +
    (nb_col * nb_ligne) cellules Tab (Montant=0). cf btn 'Enregistrer'
    WinDev bloc idGroupe=0."""
    db = get_pg_connection("adv")
    id_new = _new_id()
    db.query(
        """INSERT INTO adv.pgt_groupe_rem
              (id_groupe_rem, id_distrib, id_groupe_operateur, lib_groupe,
               famille, ss_fam, nb_col, nb_ligne, ordre,
               date_deb, date_fin, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, NOW(), ?, 'new')""",
        (id_new, int(p.id_distrib), int(p.id_groupe_operateur or 0),
         p.lib_groupe, int(p.famille or 0), p.ss_fam,
         int(p.nb_col or 0), int(p.nb_ligne or 0),
         p.date_deb if p.date_deb else None,
         p.date_fin if p.date_fin else None,
         bool(p.is_actif), int(op_id)),
    )

    # Cree les colonnes X + lignes Y + cellules Tab
    mes_x: list[int] = []
    for i in range(1, int(p.nb_col or 0) + 1):
        id_x = _new_id() + i
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_x
                  (id_groupe_rem_x, id_groupe_rem, lib, code_interne,
                   date_deb, date_fin, is_actif, ordre,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, '', ?, ?, ?, ?, NOW(), ?, 'new')""",
            (id_x, id_new, f"Colonne {i}",
             p.date_deb if p.date_deb else None,
             p.date_fin if p.date_fin else None,
             bool(p.is_actif), i, int(op_id)),
        )
        mes_x.append(id_x)

    for j in range(1, int(p.nb_ligne or 0) + 1):
        id_y = _new_id() + 1000 + j
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_y
                  (id_groupe_rem_y, id_groupe_rem, lib, code_interne,
                   date_deb, date_fin, is_actif, ordre,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, '', ?, ?, ?, ?, NOW(), ?, 'new')""",
            (id_y, id_new, f"Ligne {j}",
             p.date_deb if p.date_deb else None,
             p.date_fin if p.date_fin else None,
             bool(p.is_actif), j, int(op_id)),
        )
        # Croise avec toutes les X pour creer les cellules
        for x in mes_x:
            db.query(
                """INSERT INTO adv.pgt_groupe_rem_tab
                      (id_groupe_rem_tab, id_groupe_rem, id_groupe_rem_x,
                       id_groupe_rem_y, montant, date_deb, date_fin,
                       is_actif, modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, 0, ?, ?, ?, NOW(), ?, 'new')""",
                (_new_id() + x + id_y, id_new, x, id_y,
                 p.date_deb if p.date_deb else None,
                 p.date_fin if p.date_fin else None,
                 bool(p.is_actif), int(op_id)),
            )

    return id_new


def update_groupe_rem(
    id_groupe_rem: int, p: GroupeRemPayload, op_id: int,
) -> bool:
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem
              SET id_groupe_operateur=?, lib_groupe=?, famille=?, ss_fam=?,
                  date_deb=?, date_fin=?, is_actif=?,
                  modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_groupe_rem=?""",
        (int(p.id_groupe_operateur or 0), p.lib_groupe,
         int(p.famille or 0), p.ss_fam,
         p.date_deb if p.date_deb else None,
         p.date_fin if p.date_fin else None,
         bool(p.is_actif), int(op_id), int(id_groupe_rem)),
    )
    return True


# ====================================================================
# GRILLE X/Y/Tab du groupe REM (partie 2 + 3)
# ====================================================================


class GrilleXItem(BaseModel):
    id_groupe_rem_x: str
    lib: str = ""
    code_interne: str = ""
    ordre: int = 0


class GrilleYItem(BaseModel):
    id_groupe_rem_y: str
    lib: str = ""
    code_interne: str = ""
    ordre: int = 0


class CelluleItem(BaseModel):
    id_groupe_rem_tab: str
    id_groupe_rem_x: str
    id_groupe_rem_y: str
    montant: float = 0.0


class GrilleGroupeRem(BaseModel):
    id_groupe_rem: str
    colonnes: list[GrilleXItem] = []
    lignes: list[GrilleYItem] = []
    cellules: list[CelluleItem] = []


class EditColonnePayload(BaseModel):
    lib: str = ""
    code_interne: str = ""


def get_grille(id_groupe_rem: int) -> GrilleGroupeRem:
    """Charge la grille complete (X + Y + cellules Tab) d'un groupe REM."""
    db = get_pg_connection("adv")
    cols = db.query(
        """SELECT id_groupe_rem_x, lib, code_interne, ordre
             FROM adv.pgt_groupe_rem_x
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY ordre""",
        (int(id_groupe_rem),),
    ) or []
    lignes = db.query(
        """SELECT id_groupe_rem_y, lib, code_interne, ordre
             FROM adv.pgt_groupe_rem_y
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY ordre""",
        (int(id_groupe_rem),),
    ) or []
    cellules = db.query(
        """SELECT id_groupe_rem_tab, id_groupe_rem_x, id_groupe_rem_y, montant
             FROM adv.pgt_groupe_rem_tab
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_groupe_rem),),
    ) or []
    return GrilleGroupeRem(
        id_groupe_rem=str(id_groupe_rem),
        colonnes=[GrilleXItem(
            id_groupe_rem_x=str(r["id_groupe_rem_x"]),
            lib=r.get("lib") or "",
            code_interne=r.get("code_interne") or "",
            ordre=int(r.get("ordre") or 0),
        ) for r in cols],
        lignes=[GrilleYItem(
            id_groupe_rem_y=str(r["id_groupe_rem_y"]),
            lib=r.get("lib") or "",
            code_interne=r.get("code_interne") or "",
            ordre=int(r.get("ordre") or 0),
        ) for r in lignes],
        cellules=[CelluleItem(
            id_groupe_rem_tab=str(r["id_groupe_rem_tab"]),
            id_groupe_rem_x=str(r["id_groupe_rem_x"]),
            id_groupe_rem_y=str(r["id_groupe_rem_y"]),
            montant=float(r.get("montant") or 0),
        ) for r in cellules],
    )


def _get_groupe_rem_dates(db, id_groupe_rem: int) -> tuple:
    """Recupere date_deb/date_fin/is_actif du groupe (utilise a l'ajout
    d'une colonne/ligne pour copier ces valeurs par defaut)."""
    r = db.query_one(
        """SELECT date_deb, date_fin, is_actif FROM adv.pgt_groupe_rem
            WHERE id_groupe_rem = ? LIMIT 1""",
        (int(id_groupe_rem),),
    ) or {}
    return (r.get("date_deb"), r.get("date_fin"), bool(r.get("is_actif")))


def add_colonne(id_groupe_rem: int, op_id: int) -> str:
    """Ajoute une colonne X + cellules Tab pour chaque ligne Y."""
    db = get_pg_connection("adv")
    dd, df, act = _get_groupe_rem_dates(db, id_groupe_rem)
    # Nouvel ordre = MAX + 1
    max_r = db.query_one(
        """SELECT COALESCE(MAX(ordre), 0) + 1 AS n FROM adv.pgt_groupe_rem_x
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_groupe_rem),),
    )
    new_ordre = int((max_r or {}).get("n") or 1)
    id_x = _new_id()
    db.query(
        """INSERT INTO adv.pgt_groupe_rem_x
              (id_groupe_rem_x, id_groupe_rem, lib, code_interne,
               date_deb, date_fin, is_actif, ordre,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, '', ?, ?, ?, ?, NOW(), ?, 'new')""",
        (id_x, int(id_groupe_rem), f"Colonne {new_ordre}",
         dd, df, act, new_ordre, int(op_id)),
    )
    # Cellules pour chaque ligne Y active
    lignes = db.query(
        """SELECT id_groupe_rem_y FROM adv.pgt_groupe_rem_y
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_groupe_rem),),
    ) or []
    for y in lignes:
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_tab
                  (id_groupe_rem_tab, id_groupe_rem, id_groupe_rem_x,
                   id_groupe_rem_y, montant, date_deb, date_fin,
                   is_actif, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, 0, ?, ?, ?, NOW(), ?, 'new')""",
            (_new_id() + int(y["id_groupe_rem_y"]),
             int(id_groupe_rem), id_x, int(y["id_groupe_rem_y"]),
             dd, df, act, int(op_id)),
        )
    _remise_ordre(db, id_groupe_rem, op_id)
    return str(id_x)


def add_ligne(id_groupe_rem: int, op_id: int) -> str:
    """Ajoute une ligne Y + cellules Tab pour chaque colonne X."""
    db = get_pg_connection("adv")
    dd, df, act = _get_groupe_rem_dates(db, id_groupe_rem)
    max_r = db.query_one(
        """SELECT COALESCE(MAX(ordre), 0) + 1 AS n FROM adv.pgt_groupe_rem_y
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_groupe_rem),),
    )
    new_ordre = int((max_r or {}).get("n") or 1)
    id_y = _new_id()
    db.query(
        """INSERT INTO adv.pgt_groupe_rem_y
              (id_groupe_rem_y, id_groupe_rem, lib, code_interne,
               date_deb, date_fin, is_actif, ordre,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, '', ?, ?, ?, ?, NOW(), ?, 'new')""",
        (id_y, int(id_groupe_rem), f"Ligne {new_ordre}",
         dd, df, act, new_ordre, int(op_id)),
    )
    colonnes = db.query(
        """SELECT id_groupe_rem_x FROM adv.pgt_groupe_rem_x
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_groupe_rem),),
    ) or []
    for x in colonnes:
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_tab
                  (id_groupe_rem_tab, id_groupe_rem, id_groupe_rem_x,
                   id_groupe_rem_y, montant, date_deb, date_fin,
                   is_actif, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, 0, ?, ?, ?, NOW(), ?, 'new')""",
            (_new_id() + int(x["id_groupe_rem_x"]),
             int(id_groupe_rem), int(x["id_groupe_rem_x"]), id_y,
             dd, df, act, int(op_id)),
        )
    _remise_ordre(db, id_groupe_rem, op_id)
    return str(id_y)


def update_x(id_x: int, p: EditColonnePayload, op_id: int) -> bool:
    """Modifie lib + code_interne d'une colonne."""
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem_x
              SET lib=?, code_interne=?, modif_date=NOW(),
                  modif_op=?, modif_elem='modif'
            WHERE id_groupe_rem_x=?""",
        (p.lib, p.code_interne, int(op_id), int(id_x)),
    )
    return True


def update_y(id_y: int, p: EditColonnePayload, op_id: int) -> bool:
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem_y
              SET lib=?, code_interne=?, modif_date=NOW(),
                  modif_op=?, modif_elem='modif'
            WHERE id_groupe_rem_y=?""",
        (p.lib, p.code_interne, int(op_id), int(id_y)),
    )
    return True


def delete_x(id_x: int, id_groupe_rem: int, op_id: int) -> bool:
    """Soft-delete colonne + toutes ses cellules Tab (cf WinDev reqUp + reqUpTab)."""
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem_x
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem_x=?""",
        (int(op_id), int(id_x)),
    )
    db.query(
        """UPDATE adv.pgt_groupe_rem_tab
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem_x=?""",
        (int(op_id), int(id_x)),
    )
    _remise_ordre(db, id_groupe_rem, op_id)
    return True


def delete_y(id_y: int, id_groupe_rem: int, op_id: int) -> bool:
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem_y
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem_y=?""",
        (int(op_id), int(id_y)),
    )
    db.query(
        """UPDATE adv.pgt_groupe_rem_tab
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem_y=?""",
        (int(op_id), int(id_y)),
    )
    _remise_ordre(db, id_groupe_rem, op_id)
    return True


def move_x(id_x: int, direction: str, id_groupe_rem: int, op_id: int) -> bool:
    """Deplace la colonne : direction = 'left' (ordre-1) ou 'right' (+1).
    Reproduit WinDev : swap avec la colonne voisine puis remise_ordre."""
    db = get_pg_connection("adv")
    r = db.query_one(
        "SELECT ordre FROM adv.pgt_groupe_rem_x WHERE id_groupe_rem_x = ? LIMIT 1",
        (int(id_x),),
    )
    if not r: return False
    cur = int(r["ordre"] or 0)
    new = cur - 1 if direction == "left" else cur + 1
    if new <= 0: return False
    # Swap : la colonne actuellement a l'ordre `new` recoit `cur`
    db.query(
        """UPDATE adv.pgt_groupe_rem_x SET ordre=?, modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem=? AND ordre=? AND id_groupe_rem_x <> ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (cur, int(op_id), int(id_groupe_rem), new, int(id_x)),
    )
    db.query(
        "UPDATE adv.pgt_groupe_rem_x SET ordre=?, modif_date=NOW(), modif_op=? WHERE id_groupe_rem_x=?",
        (new, int(op_id), int(id_x)),
    )
    _remise_ordre(db, id_groupe_rem, op_id)
    return True


def move_y(id_y: int, direction: str, id_groupe_rem: int, op_id: int) -> bool:
    """direction = 'up' (ordre-1) ou 'down' (+1)."""
    db = get_pg_connection("adv")
    r = db.query_one(
        "SELECT ordre FROM adv.pgt_groupe_rem_y WHERE id_groupe_rem_y = ? LIMIT 1",
        (int(id_y),),
    )
    if not r: return False
    cur = int(r["ordre"] or 0)
    new = cur - 1 if direction == "up" else cur + 1
    if new <= 0: return False
    db.query(
        """UPDATE adv.pgt_groupe_rem_y SET ordre=?, modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem=? AND ordre=? AND id_groupe_rem_y <> ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (cur, int(op_id), int(id_groupe_rem), new, int(id_y)),
    )
    db.query(
        "UPDATE adv.pgt_groupe_rem_y SET ordre=?, modif_date=NOW(), modif_op=? WHERE id_groupe_rem_y=?",
        (new, int(op_id), int(id_y)),
    )
    _remise_ordre(db, id_groupe_rem, op_id)
    return True


def duplicate_groupe_rem_to(
    id_source: int, id_target_distrib: int, op_id: int,
) -> str:
    """Duplique un groupe REM vers un autre distributeur.
    cf btn 'Dupliquer pour un autre distrib' WinDev :
    copie groupe metadata + toutes les X + Y + Tab avec mapping des IDs."""
    db = get_pg_connection("adv")

    # Charge le groupe source
    src = db.query_one(
        """SELECT id_groupe_operateur, lib_groupe, famille, ss_fam,
                  nb_col, nb_ligne, ordre, date_deb, date_fin, is_actif
             FROM adv.pgt_groupe_rem WHERE id_groupe_rem = ? LIMIT 1""",
        (int(id_source),),
    )
    if not src:
        raise ValueError("Groupe REM source introuvable")

    id_new_gr = _new_id()
    db.query(
        """INSERT INTO adv.pgt_groupe_rem
              (id_groupe_rem, id_distrib, id_groupe_operateur, lib_groupe,
               famille, ss_fam, nb_col, nb_ligne, ordre,
               date_deb, date_fin, is_actif,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (id_new_gr, int(id_target_distrib),
         int(src.get("id_groupe_operateur") or 0),
         src.get("lib_groupe") or "",
         int(src.get("famille") or 0),
         src.get("ss_fam") or "",
         int(src.get("nb_col") or 0),
         int(src.get("nb_ligne") or 0),
         int(src.get("ordre") or 0),
         src.get("date_deb"), src.get("date_fin"),
         bool(src.get("is_actif")), int(op_id)),
    )

    # Copie X avec mapping
    src_xs = db.query(
        """SELECT * FROM adv.pgt_groupe_rem_x
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_source),),
    ) or []
    map_x: dict[int, int] = {}
    for i, x in enumerate(src_xs, start=1):
        id_new_x = _new_id() + i
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_x
                  (id_groupe_rem_x, id_groupe_rem, lib, code_interne,
                   date_deb, date_fin, is_actif, ordre,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (id_new_x, id_new_gr, x.get("lib") or "",
             x.get("code_interne") or "",
             x.get("date_deb"), x.get("date_fin"),
             bool(x.get("is_actif")), int(x.get("ordre") or 0),
             int(op_id)),
        )
        map_x[int(x["id_groupe_rem_x"])] = id_new_x

    # Copie Y avec mapping
    src_ys = db.query(
        """SELECT * FROM adv.pgt_groupe_rem_y
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_source),),
    ) or []
    map_y: dict[int, int] = {}
    for i, y in enumerate(src_ys, start=1):
        id_new_y = _new_id() + 1000 + i
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_y
                  (id_groupe_rem_y, id_groupe_rem, lib, code_interne,
                   date_deb, date_fin, is_actif, ordre,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (id_new_y, id_new_gr, y.get("lib") or "",
             y.get("code_interne") or "",
             y.get("date_deb"), y.get("date_fin"),
             bool(y.get("is_actif")), int(y.get("ordre") or 0),
             int(op_id)),
        )
        map_y[int(y["id_groupe_rem_y"])] = id_new_y

    # Copie Tab (cellules) avec les 2 mappings
    src_tabs = db.query(
        """SELECT * FROM adv.pgt_groupe_rem_tab
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_source),),
    ) or []
    for i, t in enumerate(src_tabs, start=1):
        old_x = int(t.get("id_groupe_rem_x") or 0)
        old_y = int(t.get("id_groupe_rem_y") or 0)
        if old_x not in map_x or old_y not in map_y:
            continue    # cellule orpheline (X ou Y supprime) -> skip
        db.query(
            """INSERT INTO adv.pgt_groupe_rem_tab
                  (id_groupe_rem_tab, id_groupe_rem, id_groupe_rem_x,
                   id_groupe_rem_y, montant, date_deb, date_fin,
                   is_actif, modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
            (_new_id() + i, id_new_gr, map_x[old_x], map_y[old_y],
             float(t.get("montant") or 0),
             t.get("date_deb"), t.get("date_fin"),
             bool(t.get("is_actif")), int(op_id)),
        )

    return str(id_new_gr)


def update_cellule(id_x: int, id_y: int, montant: float, op_id: int) -> bool:
    """Modifie le montant d'une cellule (cf WinDev EditerCellule autre cas)."""
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_groupe_rem_tab
              SET montant=?, modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_groupe_rem_x=? AND id_groupe_rem_y=?""",
        (float(montant), int(op_id), int(id_x), int(id_y)),
    )
    return True


def _remise_ordre(db, id_groupe_rem: int, op_id: int) -> None:
    """Renumerote les colonnes X et lignes Y de 1..N + met a jour
    nb_col et nb_ligne dans pgt_groupe_rem. cf procedure remiseOrdre WinDev."""
    # Renumerote colonnes X
    x_rows = db.query(
        """SELECT id_groupe_rem_x FROM adv.pgt_groupe_rem_x
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY ordre""",
        (int(id_groupe_rem),),
    ) or []
    for i, r in enumerate(x_rows, start=1):
        db.query(
            "UPDATE adv.pgt_groupe_rem_x SET ordre=?, modif_date=NOW() WHERE id_groupe_rem_x=?",
            (i, int(r["id_groupe_rem_x"])),
        )
    # Renumerote lignes Y
    y_rows = db.query(
        """SELECT id_groupe_rem_y FROM adv.pgt_groupe_rem_y
            WHERE id_groupe_rem = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY ordre""",
        (int(id_groupe_rem),),
    ) or []
    for i, r in enumerate(y_rows, start=1):
        db.query(
            "UPDATE adv.pgt_groupe_rem_y SET ordre=?, modif_date=NOW() WHERE id_groupe_rem_y=?",
            (i, int(r["id_groupe_rem_y"])),
        )
    # Maj nb_col / nb_ligne dans le groupe
    db.query(
        """UPDATE adv.pgt_groupe_rem
              SET nb_col=?, nb_ligne=?, modif_date=NOW(), modif_op=?
            WHERE id_groupe_rem=?""",
        (len(x_rows), len(y_rows), int(op_id), int(id_groupe_rem)),
    )


def list_editions_ctt(id_distrib: int) -> list[EditionCttItem]:
    """cf ReqEditCtt WinDev :
       JOIN societe_doc_courtage + salarie + doc_courtage.
       NomGerant = NOM + Initiale + suite prenom en minuscule (cf CONCAT WinDev)."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT sdc.id_societe_doc_courtage, sdc.id_salarie,
                  sdc.date_edition, sdc.recu, sdc.recu_date, sdc.secteur,
                  dc.id_groupe_operateur,
                  sa.nom, sa.prenom
             FROM rh.pgt_societe_doc_courtage sdc
             JOIN rh.pgt_salarie sa ON sa.id_salarie = sdc.id_salarie
             JOIN rh.pgt_doc_courtage dc
                  ON dc.id_doc_courtage = sdc.id_doc_courtage
            WHERE (sdc.modif_elem IS NULL OR sdc.modif_elem NOT LIKE '%suppr%')
              AND sdc.id_distrib = ?
            ORDER BY sdc.date_edition DESC""",
        (int(id_distrib),),
    ) or []
    out = []
    for r in rows:
        nom = (r.get("nom") or "").strip()
        prenom = (r.get("prenom") or "").strip()
        # NomGerant = Nom + Initiale majuscule + suite minuscule
        # (cf CONCAT WinDev : SALARIE.Nom + ' ' + UPPER(LEFT(Prenom,1))
        #  + LOWER(SUBSTRING(Prenom,2,LEN(Prenom))))
        nom_gerant = f"{nom} {prenom[:1].upper()}{prenom[1:].lower()}".strip()
        out.append(EditionCttItem(
            id_societe_doc_courtage=str(r["id_societe_doc_courtage"]),
            id_salarie=int(r.get("id_salarie") or 0),
            nom_gerant=nom_gerant,
            id_groupe_operateur=int(r.get("id_groupe_operateur") or 0),
            col_secteur=r.get("secteur") or "",
            date_edition=_date_str(r.get("date_edition")),
            recu=bool(r.get("recu")),
            recu_date=_date_str(r.get("recu_date")),
        ))
    return out
