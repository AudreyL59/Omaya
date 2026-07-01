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
