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
