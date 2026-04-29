"""
Service d'extraction production — portage du code WinDev
Fen_ChoixProd (construction ListeId par scope) + Fen_suiviProdAsynchrone (extraction).

MVP : extraction des lignes contrats uniquement, tous partenaires confondus.
Les KPIs par partenaire (SFR/OEN/ENI…) seront ajoutés en étape 2.

Algorithme général :
  1. Reconstruire la liste des segments d'affectation (ListeId WinDev)
     selon le scope demandé : Vendeur / Équipe / Réseau / Réseau Hors Distrib
  2. Pour chaque partenaire coché, exécuter la requête sur {PREFIX}_contrat
     JOIN {PREFIX}_produit JOIN {PREFIX}_etatContrat
  3. Enrichir chaque ligne :
     - TypeEtatContrat (libellé + couleur)
     - Affectation vendeur à la date signature (organigramme + parent)
     - Infos client (cvtheque client)
     - Infos vendeur (nom/prénom/poste)
  4. Écrire en Parquet

Le callback `progress_cb(pct, msg)` permet au worker de publier l'avancement
dans la base pendant le traitement.
"""

from __future__ import annotations

import base64
import json
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Callable, Optional

from app.core.config import PRODUCTION_EXTRACTS_DIR
from app.core.database import get_connection


ProgressCb = Callable[[int, str], None]


# ================================================================
# Helpers
# ================================================================

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


def _clean_id(n: int) -> int:
    """Filtre les IDs corrompus (> 9e18 = max uint64 HFSQL NULL)."""
    return n if 0 < n < 9_000_000_000_000_000_000 else 0


def _to_ymd(v) -> str:
    """
    Normalise une date HFSQL au format YYYYMMDD.
    Supporte ISO (YYYY-MM-DD...) et format WinDev (YYYYMMDD...).
    """
    if v is None or v == "":
        return ""
    s = str(v).strip()
    if not s:
        return ""
    # ISO
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:4] + s[5:7] + s[8:10]
    # WinDev
    if len(s) >= 8 and s[:8].isdigit():
        return s[:8]
    return ""


def _iso(v) -> str:
    """Date HFSQL → YYYY-MM-DD pour l'affichage."""
    ymd = _to_ymd(v)
    if len(ymd) == 8:
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return ""


# Préfixes NumBS dont la date+heure de signature est embarquée :
# <PREFIX><AAAAMMJJ><HHMMSS><CCC?>
_NUMBS_TIME_PREFIXES = ("TK", "THD", "CBL")


def _heure_from_numbs(num_bs: str) -> str:
    """Extrait HH:MM depuis un NumBS du type TK/THD/CBL + AAAAMMJJ + HHMMSS + …
    Retourne '' si le NumBS ne suit pas ce format."""
    if not num_bs:
        return ""
    nb_up = num_bs.upper()
    for px in _NUMBS_TIME_PREFIXES:
        n = len(px)
        if (
            len(num_bs) >= n + 14
            and nb_up.startswith(px)
            and num_bs[n:n + 14].isdigit()
        ):
            hh = num_bs[n + 8:n + 10]
            mm = num_bs[n + 10:n + 12]
            return f"{hh}:{mm}"
    return ""


def _first_day_of_month(ymd: str) -> str:
    return ymd[:6] + "01" if len(ymd) >= 6 else ymd


def _last_day_of_month(ymd: str) -> str:
    if len(ymd) < 6:
        return ymd
    y = int(ymd[:4])
    m = int(ymd[4:6])
    # Jour 1 du mois suivant - 1 jour
    if m == 12:
        nm, ny = 1, y + 1
    else:
        nm, ny = m + 1, y
    d = date(ny, nm, 1) - timedelta(days=1)
    return d.strftime("%Y%m%d")


def _winrgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{(r or 0) & 0xFF:02X}{(g or 0) & 0xFF:02X}{(b or 0) & 0xFF:02X}"


def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


# ================================================================
# Segments d'affectation (ListeId WinDev)
# ================================================================

@dataclass
class AffSegment:
    id_salarie: int = 0
    id_orga: int = 0
    date_debut: str = ""          # YYYYMMDD
    date_fin: str = ""            # YYYYMMDD (inclus)


def _req_equipe_terrain_by_salarie(db_rh, id_salarie: int, date_c_ymd: str) -> Optional[dict]:
    """
    Équivalent ReqEquipeTerrainBySalarieByDate WinDev.
    Retourne l'affectation salarie_organigramme active à la date donnée.
    """
    rows = db_rh.query(
        """SELECT TOP 1
            so.idorganigramme, so.DateDébut, so.DateFin,
            o.IdPARENT, o.Lib_ORGA, o.IDTypeOrga, o.IDTypeProduit
        FROM salarie_organigramme so
        INNER JOIN organigramme o ON o.idorganigramme = so.idorganigramme
        WHERE so.IDSalarie = ?
          AND so.ModifELEM NOT LIKE '%suppr%'
          AND LEFT(so.DateDébut, 8) <= ?
          AND (so.DateFin = '' OR LEFT(so.DateFin, 8) >= ?)
        ORDER BY so.DateDébut DESC""",
        (id_salarie, date_c_ymd, date_c_ymd),
    )
    return rows[0] if rows else None


def build_liste_affectations(
    db_rh, params: dict, prod_deb: str, prod_fin: str
) -> tuple[list[AffSegment], int]:
    """
    Construit la liste des segments d'affectation selon le scope.

    Retourne (segments, prod_tot) où prod_tot est le flag WinDev :
      - 0 pour Vendeur/Équipe (scope par salarié/orga)
      - 1 pour Réseau global
      - 2 pour Réseau Hors Distrib
    """
    scope = params.get("scope", 1)

    # Scope 3 : Réseau global → liste vide, pas de filtre
    if scope == 3:
        return ([], 1)

    # Scope 4 : Réseau Hors Distrib → toutes orgas racines sauf IdSte=4
    if scope == 4:
        rows = db_rh.query(
            """SELECT idorganigramme
            FROM organigramme
            WHERE IdPARENT = 0
              AND IdSte <> 4
              AND ModifELEM <> 'suppr'"""
        )
        segs = []
        for r in rows:
            oid = _clean_id(_to_int(r.get("idorganigramme")))
            if oid:
                segs.append(AffSegment(
                    id_salarie=0, id_orga=oid,
                    date_debut=prod_deb, date_fin=prod_fin,
                ))
        return (segs, 2)

    # Scope 2 : Équipe → 1 seul segment
    if scope == 2:
        id_orga = _clean_id(_to_int(params.get("id_organigramme", 0)))
        return ([AffSegment(
            id_salarie=0, id_orga=id_orga,
            date_debut=prod_deb, date_fin=prod_fin,
        )], 0)

    # Scope 1 : Vendeur
    id_sal = _clean_id(_to_int(params.get("id_salarie", 0)))
    prod_groupe = bool(params.get("prod_groupe"))

    # Prod Perso : segment unique sans contrainte orga
    if not prod_groupe:
        return ([AffSegment(
            id_salarie=id_sal, id_orga=0,
            date_debut=prod_deb, date_fin=prod_fin,
        )], 0)

    # Prod Groupe avec dérogation : parcours de l'historique d'affectation
    segs: list[AffSegment] = []

    # Cas spécial WinDev : IDSalarie=4 → segment global sans orga
    if id_sal == 4:
        segs.append(AffSegment(
            id_salarie=id_sal, id_orga=0,
            date_debut=prod_deb, date_fin=prod_fin,
        ))
        return (segs, 0)

    # Première affectation au début de la période
    aff = _req_equipe_terrain_by_salarie(db_rh, id_sal, prod_deb)
    if aff:
        id_eq = _clean_id(_to_int(aff.get("idorganigramme")))
        d_deb = _to_ymd(aff.get("DateDébut")) or prod_deb
        d_fin = _to_ymd(aff.get("DateFin")) or prod_fin
        segs.append(AffSegment(
            id_salarie=id_sal, id_orga=id_eq,
            date_debut=d_deb, date_fin=d_fin or prod_fin,
        ))

        # Suivre les changements d'équipe pendant la période
        date_ref = _to_ymd(aff.get("DateFin"))
        last_eq = id_eq
        while date_ref and date_ref <= prod_fin:
            # +1 jour
            d = datetime.strptime(date_ref, "%Y%m%d") + timedelta(days=1)
            date_ref_next = d.strftime("%Y%m%d")
            aff_next = _req_equipe_terrain_by_salarie(db_rh, id_sal, date_ref_next)
            if not aff_next:
                break
            new_eq = _clean_id(_to_int(aff_next.get("idorganigramme")))
            if new_eq != last_eq:
                d_deb_n = _to_ymd(aff_next.get("DateDébut")) or date_ref_next
                d_fin_n = _to_ymd(aff_next.get("DateFin")) or prod_fin
                segs.append(AffSegment(
                    id_salarie=id_sal, id_orga=new_eq,
                    date_debut=d_deb_n, date_fin=d_fin_n,
                ))
                last_eq = new_eq
            next_fin = _to_ymd(aff_next.get("DateFin"))
            if not next_fin or next_fin == date_ref:
                break
            date_ref = next_fin

    # Dérogations (table DerogationOrga)
    dero_rows = db_rh.query(
        """SELECT idorganigramme, DateDEBUT, DATEFIN
        FROM DerogationOrga
        WHERE ModifELEM NOT LIKE '%suppr%'
          AND IDSalarie = ?""",
        (id_sal,),
    )
    for d in dero_rows:
        d_deb = _to_ymd(d.get("DateDEBUT"))
        d_fin = _to_ymd(d.get("DATEFIN"))
        if d_deb and d_deb > prod_fin:
            continue
        if d_fin and d_fin < prod_deb:
            continue
        id_o = _clean_id(_to_int(d.get("idorganigramme")))
        segs.append(AffSegment(
            id_salarie=id_sal, id_orga=id_o,
            date_debut=d_deb or prod_deb,
            date_fin=d_fin or prod_fin,
        ))

    return (segs, 0)


# ================================================================
# Lookups en batch (salariés, orgas, clients)
# ================================================================

# Taille max de chunk pour les WHERE IN (...) — évite de dépasser la limite
# de 32768 chars de la ligne de commande Windows CreateProcess.
# Avec des IDs 8 octets (~19 chars + virgule), 1000 IDs = ~20 kchars.
_IN_CHUNK = 1000


def _chunked(items: list, size: int):
    """Découpe une liste en chunks de taille `size`."""
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _load_salaries_info(db_rh, ids_salaries: set[int]) -> dict[int, dict]:
    """
    Charge les infos minimales (nom, prénom, poste, activité, date sortie)
    pour un batch de salariés.
    """
    all_ids = [i for i in ids_salaries if i]
    if not all_ids:
        return {}

    out: dict[int, dict] = {}
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        rows = db_rh.query(
            f"""SELECT s.IDSalarie, s.Nom, s.Prenom,
                se.EnActivité, se.DateAncienneté, se.IdTypePoste,
                tp.Lib_Poste
            FROM salarie s
            INNER JOIN salarie_embauche se ON se.IDSalarie = s.IDSalarie
            LEFT JOIN TypePoste tp ON tp.IdTypePoste = se.IdTypePoste
            WHERE s.IDSalarie IN ({ids_sql})"""
        )
        for r in rows:
            sid = _clean_id(_to_int(r.get("IDSalarie")))
            out[sid] = {
                "nom": r.get("Nom") or "",
                "prenom": r.get("Prenom") or "",
                "en_activite": bool(r.get("EnActivité")),
                "date_embauche": _iso(r.get("DateAncienneté")),
                "poste": r.get("Lib_Poste") or "",
            }

    # Date sortie pour les inactifs
    inactifs = [sid for sid, v in out.items() if not v["en_activite"]]
    for chunk in _chunked(inactifs, _IN_CHUNK):
        ids_sql_i = ",".join(str(i) for i in chunk)
        sortie_rows = db_rh.query(
            f"""SELECT IDSalarie, DateSortieDemandée
            FROM salarie_sortie
            WHERE IDSalarie IN ({ids_sql_i})
              AND ModifELEM <> 'suppr'"""
        )
        for r in sortie_rows:
            sid = _clean_id(_to_int(r.get("IDSalarie")))
            if sid in out:
                out[sid]["date_sortie"] = _iso(r.get("DateSortieDemandée"))

    for v in out.values():
        v.setdefault("date_sortie", "")
    return out


def _load_orgas_info(db_rh, ids_orgas: set[int]) -> dict[int, dict]:
    """
    Charge le Lib_ORGA + Lib_ORGA du parent pour un batch d'orgas.
    Équivaut à affectationVendeurByDate (retourne '{parent} =>{orga}').
    """
    if not ids_orgas:
        return {}
    ids_sql = ",".join(str(i) for i in ids_orgas if i)
    if not ids_sql:
        return {}

    # Couche 1 : orga directe
    rows = db_rh.query(
        f"""SELECT idorganigramme, Lib_ORGA, IdPARENT
        FROM organigramme
        WHERE idorganigramme IN ({ids_sql})"""
    )
    out: dict[int, dict] = {}
    parent_ids: set[int] = set()
    for r in rows:
        oid = _clean_id(_to_int(r.get("idorganigramme")))
        pid = _clean_id(_to_int(r.get("IdPARENT")))
        out[oid] = {
            "lib": r.get("Lib_ORGA") or "",
            "parent_id": pid,
            "parent_lib": "",
        }
        if pid:
            parent_ids.add(pid)

    # Couche 2 : orga parents
    if parent_ids:
        ids_sql_p = ",".join(str(i) for i in parent_ids)
        prows = db_rh.query(
            f"""SELECT idorganigramme, Lib_ORGA
            FROM organigramme
            WHERE idorganigramme IN ({ids_sql_p})"""
        )
        plibs = {
            _clean_id(_to_int(p.get("idorganigramme"))): p.get("Lib_ORGA") or ""
            for p in prows
        }
        for v in out.values():
            v["parent_lib"] = plibs.get(v["parent_id"], "")

    return out


def _load_nb_jour_pres(
    db_rh,
    ids_salaries: set[int],
    date_debut_ymd: str,
    date_fin_ymd: str,
    weekends_ymd_by_salarie: dict[int, set[str]],
) -> dict[int, int]:
    """
    Charge le nombre de jours de présence par salarié sur la période.

    Règle WinDev (reqDecl + reqVeriDecl) :
    - Lundi-vendredi : toutes les dates avec Presence=1 sont comptées
    - Samedi-dimanche : comptés uniquement si le salarié a signé
      un contrat ce jour-là (cf. ListeDateWE dans WinDev)
    """
    if not ids_salaries:
        return {}

    all_ids = [i for i in ids_salaries if i]
    if not all_ids:
        return {}

    out: dict[int, int] = {i: 0 for i in all_ids}

    # 1. Jours de semaine (lundi-vendredi) : requête groupée par salarié
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        rows = db_rh.query(
            f"""SELECT IDSalarie, COUNT(*) AS NbPres
            FROM salarie_decl_presence
            WHERE IDSalarie IN ({ids_sql})
              AND DATE BETWEEN ? AND ?
              AND ModifELEM <> 'suppr'
              AND Presence = 1
              AND DAYOFWEEK(DATE) BETWEEN 2 AND 6
            GROUP BY IDSalarie""",
            (date_debut_ymd, date_fin_ymd),
        )
        for r in rows:
            sid = _clean_id(_to_int(r.get("IDSalarie")))
            out[sid] = out.get(sid, 0) + _to_int(r.get("NbPres"))

    # 2. Week-ends : pour chaque salarié × chaque WE où il a signé,
    # vérifier s'il a Presence=1 ce jour-là.
    for id_sal, weekends in weekends_ymd_by_salarie.items():
        if id_sal not in out:
            continue
        for d in weekends:
            row = db_rh.query_one(
                """SELECT COUNT(*) AS NbPres FROM salarie_decl_presence
                WHERE IDSalarie = ? AND DATE = ?
                  AND ModifELEM <> 'suppr' AND Presence = 1""",
                (id_sal, d),
            )
            if row and _to_int(row.get("NbPres")) > 0:
                out[id_sal] = out.get(id_sal, 0) + 1

    return out


def _load_etat_operateur(
    db_adv, prefix: str, id_etat_col: str, ids_etats: set[int],
) -> dict[int, dict]:
    """
    Charge la jointure {prefix}_etatContrat (IDetat, Lib_Etat, IDTypeEtat)
    pour un batch d'IDs — utilisé pour l'Etat Opérateur (SFR/OEN).
    """
    all_ids = [i for i in ids_etats if i]
    if not all_ids:
        return {}
    out: dict[int, dict] = {}
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        rows = db_adv.query(
            f"""SELECT IDetat, Lib_Etat, IDTypeEtat
            FROM {prefix}_etatContrat
            WHERE IDetat IN ({ids_sql})"""
        )
        for r in rows:
            eid = _to_int(r.get("IDetat"))
            out[eid] = {
                "lib_etat": r.get("Lib_Etat") or "",
                "id_type_etat": _to_int(r.get("IDTypeEtat")),
            }
    return out


def _load_sfr_clusters(db_adv, ids_clusters: set[int]) -> dict[int, dict]:
    """Charge CodeVAD + NomCluster par IDSFR_Cluster."""
    all_ids = [i for i in ids_clusters if i]
    if not all_ids:
        return {}
    out: dict[int, dict] = {}
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        rows = db_adv.query(
            f"""SELECT IDSFR_Cluster, CodeVAD, NomCluster
            FROM SFR_Cluster
            WHERE IDSFR_Cluster IN ({ids_sql})"""
        )
        for r in rows:
            cid = _clean_id(_to_int(r.get("IDSFR_Cluster")))
            out[cid] = {
                "code_vad": r.get("CodeVAD") or "",
                "nom_cluster": r.get("NomCluster") or "",
            }
    return out


def _load_contrat_options(
    db_adv, prefix: str, ids_contrats: set[int],
) -> dict[int, dict]:
    """
    Charge les options contrat pour ENI/OEN (tables {prefix}_contrat_Option).
    Retourne {IDcontrat: {OPT_Entretien, OPT_EnergieVerteGaz, OPT_Reforestation,
    OPT_Protection, OPT_eFacture, OPT_PDC, ...}}
    """
    all_ids = [i for i in ids_contrats if i]
    if not all_ids:
        return {}
    out: dict[int, dict] = {}
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        try:
            rows = db_adv.query(
                f"""SELECT IDcontrat, OPT_Entretien, OPT_EnergieVerteGaz,
                    OPT_Reforestation, OPT_Protection, OPT_eFacture, OPT_PDC
                FROM {prefix}_contrat_Option
                WHERE IDcontrat IN ({ids_sql})
                  AND ModifELEM <> 'suppr'"""
            )
        except Exception:
            # Partenaire sans table _contrat_Option → on retourne vide
            return {}
        for r in rows:
            cid = _clean_id(_to_int(r.get("IDcontrat")))
            out[cid] = {
                "opt_entretien": bool(r.get("OPT_Entretien")),
                "opt_energie_verte_gaz": bool(r.get("OPT_EnergieVerteGaz")),
                "opt_reforestation": bool(r.get("OPT_Reforestation")),
                "opt_protection": bool(r.get("OPT_Protection")),
                "opt_efacture": bool(r.get("OPT_eFacture")),
                "opt_pdc": bool(r.get("OPT_PDC")),
            }
    return out


def _load_heure_from_tk(num_bs_list: list[str]) -> dict[str, str]:
    """
    Pour une liste de NumBS, retourne dict NumBS → 'HH:MM' depuis TK_Liste.DATECREA.
    Joint via :
      - TK_CallSFR_Panier.NUM (= NumBS) pour les contrats SFR
      - TK_Call_Panier.NumBS  pour les contrats des autres partenaires (OEN/ENI/…)
    Tables paniers en `ticket_bo`, TK_Liste en `ticket`.
    Reproduit le pattern WinDev (TK_Liste.DATECREA = date+heure réelle de signature).
    """
    nums = [str(n) for n in num_bs_list if n]
    if not nums:
        return {}

    db_bo = get_connection("ticket_bo")
    db_tk = get_connection("ticket")
    import logging
    logger = logging.getLogger(__name__)

    num_to_idtk: dict[str, int] = {}

    def _query_panier(table: str, num_col: str) -> None:
        for chunk in _chunked(nums, _IN_CHUNK):
            nums_sql = ",".join("'" + n.replace("'", "''") + "'" for n in chunk)
            try:
                rows = db_bo.query(
                    f"SELECT {num_col}, IDTK_Liste FROM {table} WHERE {num_col} IN ({nums_sql})"
                )
            except Exception as e:
                logger.warning(f"[heure_tk] {table} failed: {e}")
                continue
            for r in rows:
                num = str(r.get(num_col) or "")
                idtk = _to_int(r.get("IDTK_Liste"))
                # Premier hit gagne (SFR prioritaire si la même réf est dans les 2)
                if num and idtk and num not in num_to_idtk:
                    num_to_idtk[num] = idtk

    # 1) Lookup dans les 2 paniers
    _query_panier("TK_CallSFR_Panier", "NUM")
    _query_panier("TK_Call_Panier", "NumBS")

    if not num_to_idtk:
        return {}

    # 2) IDTK_Liste → DATECREA via TK_Liste
    idtk_to_datecrea: dict[int, str] = {}
    for chunk in _chunked(list(set(num_to_idtk.values())), _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        try:
            rows = db_tk.query(
                f"SELECT IDTK_Liste, DATECREA FROM TK_Liste WHERE IDTK_Liste IN ({ids_sql})"
            )
        except Exception as e:
            logger.warning(f"[heure_tk] TK_Liste failed: {e}")
            continue
        for r in rows:
            idtk = _to_int(r.get("IDTK_Liste"))
            dc = str(r.get("DATECREA") or "")
            if idtk and dc:
                idtk_to_datecrea[idtk] = dc

    # 3) NumBS → HH:MM (depuis ISO 'YYYY-MM-DDTHH:MM:SS.sss')
    out: dict[str, str] = {}
    for num, idtk in num_to_idtk.items():
        dc = idtk_to_datecrea.get(idtk, "")
        if len(dc) >= 16 and dc[10] in ("T", " "):
            out[num] = dc[11:16]
    return out


def _load_numbs_in_tk_call_panier(num_bs_list: list[str]) -> set[str]:
    """Retourne l'ensemble des NumBS présents dans TK_Call_Panier (`ticket_bo`).

    Pour OEN (et les autres partenaires non-SFR) — TK_CallSFR_Panier est
    réservé aux contrats SFR. Sert à filtrer la base de calcul du tx de
    consentement OEN : seuls les contrats remontés via un panier Call
    comptent (cf. WinDev StatsOEN).
    """
    nums = [str(n) for n in num_bs_list if n]
    if not nums:
        return set()

    db_bo = get_connection("ticket_bo")
    found: set[str] = set()
    import logging
    logger = logging.getLogger(__name__)
    for chunk in _chunked(nums, _IN_CHUNK):
        nums_sql = ",".join("'" + n.replace("'", "''") + "'" for n in chunk)
        try:
            rows = db_bo.query(
                f"SELECT NumBS FROM TK_Call_Panier WHERE NumBS IN ({nums_sql})"
            )
        except Exception as e:
            logger.warning(f"[tk_call_panier] failed: {e}")
            continue
        for r in rows:
            n = str(r.get("NumBS") or "")
            if n:
                found.add(n)
    return found


def _load_clients_info(db_adv, ids_clients: set[int]) -> dict[int, dict]:
    """Charge les infos client en batch (table client dans ADV)."""
    all_ids = [i for i in ids_clients if i]
    if not all_ids:
        return {}

    out: dict[int, dict] = {}
    today = date.today()
    for chunk in _chunked(all_ids, _IN_CHUNK):
        ids_sql = ",".join(str(i) for i in chunk)
        rows = db_adv.query(
            f"""SELECT IDclient, NOM, PRENOM, ADRESSE1, ADRESSE2, CP, VILLE,
                MAIL, GSM, TEL, DATENAISS, Opt_Partenaire
            FROM client
            WHERE IDclient IN ({ids_sql})"""
        )
        for r in rows:
            cid = _clean_id(_to_int(r.get("IDclient")))
            naiss_ymd = _to_ymd(r.get("DATENAISS"))
            age = 0
            if len(naiss_ymd) == 8:
                try:
                    naiss = date(int(naiss_ymd[:4]), int(naiss_ymd[4:6]), int(naiss_ymd[6:8]))
                    age = today.year - naiss.year - (
                        (today.month, today.day) < (naiss.month, naiss.day)
                    )
                except Exception:
                    age = 0
            gsm = (r.get("GSM") or "").strip() or (r.get("TEL") or "").strip()
            out[cid] = {
                "nom": r.get("NOM") or "",
                "prenom": r.get("PRENOM") or "",
                "adresse1": r.get("ADRESSE1") or "",
                "adresse2": r.get("ADRESSE2") or "",
                "cp": r.get("CP") or "",
                "ville": r.get("VILLE") or "",
                "mail": r.get("MAIL") or "",
                "mobile": gsm,
                "age": age,
                "opt_partenaire": bool(r.get("Opt_Partenaire")),
            }
    return out


def _load_orga_descendants(db_rh, root_ids: set[int]) -> set[int]:
    """
    Retourne l'ensemble des orgas descendantes (incluant les racines) de root_ids.
    BFS sur organigramme (IdPARENT).
    """
    if not root_ids:
        return set()

    # Charger toutes les orgas (petite table)
    all_orgas = db_rh.query(
        """SELECT idorganigramme, IdPARENT
        FROM organigramme
        WHERE ModifELEM <> 'suppr'"""
    )

    # Index parent -> enfants
    children_of: dict[int, list[int]] = {}
    for r in all_orgas:
        oid = _clean_id(_to_int(r.get("idorganigramme")))
        pid = _clean_id(_to_int(r.get("IdPARENT")))
        if oid:
            children_of.setdefault(pid, []).append(oid)

    # BFS
    result = set(root_ids)
    frontier = list(root_ids)
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, []):
            if child not in result:
                result.add(child)
                frontier.append(child)
    return result


def _load_type_etats(db_adv) -> dict[int, dict]:
    """Charge TypeEtatContrat en mémoire (petite table)."""
    rows = db_adv.query(
        """SELECT IDTypeEtat, LibType, Couleur_R, Couleur_V, Couleur_B
        FROM TypeEtatContrat
        WHERE ModifELEM <> 'suppr'"""
    )
    out: dict[int, dict] = {}
    for r in rows:
        tid = _to_int(r.get("IDTypeEtat"))
        out[tid] = {
            "lib": r.get("LibType") or "",
            "couleur": _winrgb_to_hex(
                _to_int(r.get("Couleur_R")),
                _to_int(r.get("Couleur_V")),
                _to_int(r.get("Couleur_B")),
            ),
        }
    return out


# ================================================================
# Requête principale par partenaire
# ================================================================

def _build_partenaire_sql(
    prefix: str,
    cond_salaries: str,
    crit_date: str,
    id_type_etat: int,
) -> str:
    """
    Construit la requête SQL d'extraction pour un partenaire.
    Reprend le pattern WinDev (Fen_suiviProdAsynchrone) avec les colonnes
    spécifiques par partenaire.
    """
    etat_filter = ""
    if id_type_etat and id_type_etat > 0:
        etat_filter = f" AND pe.IDTypeEtat = {int(id_type_etat)}"

    # SFR_contrat n'a pas de colonne MoisP classique — c'est MoisP_Ra
    mois_p_col = "MoisP_Ra" if prefix == "SFR" else "MoisP"

    # Colonnes communes (toujours présentes)
    cols = [
        "pc.IDcontrat", "pc.IDSalarie", "pc.NumBS", "pc.InfoInterne",
        "pc.DateSAISIE", "pc.IDproduit", "pc.IDetatContrat",
        "pc.DateSignature", "pc.nbPoints", "pc.IDclient",
        "pc.Notation", "pc.NotationInfo",
        f"pc.{mois_p_col} AS MoisP",
        "pp.Lib_produit", "pp.PréfixeBDD", "pp.Famille", "pp.SousFAM",
        "pe.Lib_Etat", "pe.IDTypeEtat", "pe.Lib_EtatVend",
    ]

    # Colonnes spécifiques par partenaire
    if prefix == "SFR":
        cols += [
            "pc.TypeVente", "pc.Technologie", "pc.Box8", "pc.Box8Vérif",
            "pc.HorsCible", "pc.DateRDVTech", "pc.DateRaccActiv",
            "pc.DateValidation", "pc.DateRésil",
            "pc.Portabilité", "pc.DatePortabilité",
            "pc.IDSFR_Cluster", "pc.IDetatSFR",
            "pc.MoisP_Option", "pc.MoisP_RaDistri", "pc.MoisP_Va", "pc.MoisP_VaDistri",
            "pc.PayeRaDistri", "pc.PayeVaDistri",
            "pc.InternetGaranti", "pc.OffreSpeciale", "pc.ParcoursChainé",
            "pc.PriseExistante", "pc.PriseSaisie",
            "pc.NumPrise_SFR", "pc.NumPrise_Vend",
            "pc.MobPropoVend", "pc.InterventionVend",
            "pc.IssuTkDiff", "pc.RepAppSFR", "pc.Remise", "pc.SelfInstall",
            "pc.ActivControl", "pc.ProcessingState",
            "pc.InfoVenteSFR AS InfoPartagee",
        ]
    else:
        # Non-SFR : InfoPartagée + CodeENR
        cols += [
            "pc.InfoPartagée AS InfoPartagee",
            "pc.CodeENR",
        ]

    if prefix == "OEN":
        cols += [
            "pc.DateActivation", "pc.IdEtatOEN",
            "pc.GazCarDeclaree", "pc.GazCarRelevée", "pc.ElecPuissance",
            "pc.RefClient",
        ]
    elif prefix == "ENI":
        cols += [
            "pc.GazCarDeclaree", "pc.GazCarRelevée", "pc.ElecPuissance",
            "pc.GazActif", "pc.ElecActif",
        ]
    elif prefix == "STR":
        cols += ["pc.Opt_Mandat AS OptNum"]
    elif prefix == "VAL":
        cols += ["pc.FormatNumérique AS OptNum"]
    elif prefix == "PRO":
        cols += ["pc.DateRésil", "pc.DatePrem AS DateValidation"]
    elif prefix == "GEP":
        cols += [
            "pc.ModePaiement", "pc.Pack", "pc.DuréeAb", "pc.RIB_Fourni",
        ]

    select_block = ",\n    ".join(cols)

    return f"""
SELECT
    {select_block}
FROM {prefix}_produit pp, {prefix}_etatContrat pe, {prefix}_contrat pc
WHERE pc.IDproduit = pp.IDproduit
  AND pc.IDetatContrat = pe.IDetat
  AND pc.ModifELEM NOT LIKE '%suppr%'
  AND ({cond_salaries})
  AND {crit_date}
  {etat_filter}
"""


def _cond_salaries_from_segments(segs: list[AffSegment]) -> str:
    """
    Construit la clause WHERE pour filtrer les contrats par salariés.
    Si scope=Réseau (segs vide), renvoie '1=1' (pas de filtre).
    Si scope=Équipe/Réseau HD (id_salarie=0), renvoie '1=1' car on filtrera
    par orga via la jointure d'affectation côté Python.
    """
    ids = {s.id_salarie for s in segs if s.id_salarie}
    if not ids:
        return "1=1"
    if len(ids) == 1:
        return f"pc.IDSalarie = {next(iter(ids))}"
    ids_sql = ",".join(str(i) for i in ids)
    return f"pc.IDSalarie IN ({ids_sql})"


# ================================================================
# Extraction principale
# ================================================================

def extract_job_to_parquet(
    id_job: int,
    id_salarie_user: int,
    params: dict,
    progress_cb: ProgressCb = lambda p, m: None,
) -> dict:
    """
    Exécute l'extraction complète d'un job et écrit le résultat en Parquet.
    Retourne un dict avec les métadonnées de fin :
      {path, nb_lignes, duree_s, message_erreur}

    Cette fonction est appelée par le worker ; elle ne touche pas directement
    à la table ProductionExtractionJob (c'est le worker qui MAJ le statut).
    """
    t0 = time.time()

    # Normalisation période
    prod_deb = _to_ymd(params.get("date_du", ""))
    prod_fin = _to_ymd(params.get("date_au", ""))
    mode_date = int(params.get("mode_date", 1))
    if mode_date == 2:
        # Mode "par mois de paiement" : on étend à tous les mois complets
        prod_deb = _first_day_of_month(prod_deb)
        prod_fin = _last_day_of_month(prod_fin)

    if not prod_deb or not prod_fin or prod_deb > prod_fin:
        raise ValueError(f"Période invalide : {prod_deb} -> {prod_fin}")

    partenaires: list[str] = [p.strip() for p in params.get("partenaires", []) if p.strip()]
    if not partenaires:
        raise ValueError("Aucun partenaire choisi")

    id_type_etat = int(params.get("id_type_etat", 0) or 0)

    # Préparer les connexions
    db_rh = get_connection("rh")
    db_adv = get_connection("adv")

    # Étape 1 : construire la liste des segments d'affectation
    progress_cb(5, "Calcul des affectations")
    segments, prod_tot = build_liste_affectations(db_rh, params, prod_deb, prod_fin)

    # Étape 2 : charger les référentiels (TypeEtat)
    progress_cb(10, "Chargement des référentiels")
    type_etats = _load_type_etats(db_adv)

    # Étape 3 : boucle partenaires
    all_rows: list[dict] = []
    cond_salaries = _cond_salaries_from_segments(segments)
    n_parts = len(partenaires)

    for idx, prefix in enumerate(partenaires):
        pct_start = 15 + int((idx / n_parts) * 70)
        progress_cb(pct_start, f"Extraction {prefix} ({idx + 1}/{n_parts})")

        # Critère de date : SFR spécial (MoisP_Ra), autres (MoisP) en mode 2 ;
        # mode 1 : DateSignature
        if mode_date == 2:
            if prefix == "SFR":
                crit_date = f"pc.MoisP_Ra BETWEEN '{prod_deb}' AND '{prod_fin}'"
            else:
                crit_date = f"pc.MoisP BETWEEN '{prod_deb}' AND '{prod_fin}'"
        else:
            crit_date = f"pc.DateSignature BETWEEN '{prod_deb}' AND '{prod_fin}'"

        sql = _build_partenaire_sql(prefix, cond_salaries, crit_date, id_type_etat)
        try:
            rows = db_adv.query(sql)
        except Exception as e:
            # Plutôt que d'ignorer silencieusement (masque les bugs de colonnes
            # manquantes), on fait remonter l'erreur pour que le job passe en
            # 'error' avec un message explicite identifiant le partenaire.
            raise RuntimeError(f"Echec extraction partenaire {prefix} : {e}") from e

        progress_cb(pct_start, f"{prefix} : {len(rows)} contrats bruts")

        for r in rows:
            r["_prefix"] = prefix
        all_rows.extend(rows)

    progress_cb(85, f"Enrichissement ({len(all_rows)} contrats)")

    # Étape 4 : batch lookups
    ids_salaries = {_clean_id(_to_int(r.get("IDSalarie"))) for r in all_rows}
    ids_salaries.discard(0)
    ids_clients = {_clean_id(_to_int(r.get("IDclient"))) for r in all_rows}
    ids_clients.discard(0)

    salaries_info = _load_salaries_info(db_rh, ids_salaries)
    clients_info = _load_clients_info(db_adv, ids_clients)

    # Lookups spécifiques par partenaire
    # - SFR : état opérateur (via IDetatSFR) + SFR_Cluster
    # - OEN : état opérateur (via IdEtatOEN)
    # - ENI/OEN : contrat_Option
    sfr_rows = [r for r in all_rows if r["_prefix"] == "SFR"]
    oen_rows = [r for r in all_rows if r["_prefix"] == "OEN"]
    eni_rows = [r for r in all_rows if r["_prefix"] == "ENI"]

    sfr_etats_ope = _load_etat_operateur(
        db_adv, "SFR", "IDetatSFR",
        {_to_int(r.get("IDetatSFR")) for r in sfr_rows},
    )
    oen_etats_ope = _load_etat_operateur(
        db_adv, "OEN", "IdEtatOEN",
        {_to_int(r.get("IdEtatOEN")) for r in oen_rows},
    )
    sfr_clusters = _load_sfr_clusters(
        db_adv,
        {_clean_id(_to_int(r.get("IDSFR_Cluster"))) for r in sfr_rows},
    )
    eni_opts = _load_contrat_options(
        db_adv, "ENI",
        {_clean_id(_to_int(r.get("IDcontrat"))) for r in eni_rows},
    )
    oen_opts = _load_contrat_options(
        db_adv, "OEN",
        {_clean_id(_to_int(r.get("IDcontrat"))) for r in oen_rows},
    )

    # Heure de signature via TK_Liste.DATECREA (cf. WinDev) pour :
    # - SFR MOBILE / Box 5G : NumBS n'embarque pas l'heure de signature
    # - Tout partenaire non-SFR (OEN/ENI/...) : DateSAISIE n'est pas fiable
    nums_for_tk: list[str] = []
    for r in all_rows:
        nb = r.get("NumBS")
        if not nb:
            continue
        if r["_prefix"] == "SFR":
            famille = (r.get("Famille") or "").upper()
            sous_fam = (r.get("SousFAM") or "").upper()
            if famille == "MOBILE" or "BOX5G" in sous_fam:
                nums_for_tk.append(str(nb))
        else:
            nums_for_tk.append(str(nb))
    heure_tk: dict[str, str] = _load_heure_from_tk(nums_for_tk)

    # Pour OEN/ENI : set des NumBS présents dans TK_Call_Panier — sert à
    # filtrer la base clients du tx de consentement (cf. WinDev StatsOEN/ENI).
    nums_call = [str(r.get("NumBS")) for r in all_rows
                 if r["_prefix"] in ("OEN", "ENI") and r.get("NumBS")]
    in_tk_call: set[str] = _load_numbs_in_tk_call_panier(nums_call)

    # Calcul affectation vendeur à la date signature (requête par salarié+date)
    # On cache les résultats pour (id_salarie, date_ymd).
    affect_cache: dict[tuple[int, str], dict] = {}

    def get_affect(id_s: int, date_ymd: str) -> dict:
        if not id_s or not date_ymd:
            return {}
        key = (id_s, date_ymd)
        if key in affect_cache:
            return affect_cache[key]
        row = _req_equipe_terrain_by_salarie(db_rh, id_s, date_ymd)
        if not row:
            affect_cache[key] = {}
            return {}
        orga_id = _clean_id(_to_int(row.get("idorganigramme")))
        parent_id = _clean_id(_to_int(row.get("IdPARENT")))
        lib = row.get("Lib_ORGA") or ""
        parent_lib = ""
        if parent_id:
            prow = db_rh.query_one(
                "SELECT Lib_ORGA FROM organigramme WHERE idorganigramme = ?",
                (parent_id,),
            )
            if prow:
                parent_lib = prow.get("Lib_ORGA") or ""
        info = {
            "orga_id": orga_id,
            "equipe": lib,
            "agence": parent_lib,
        }
        affect_cache[key] = info
        return info

    # Étape 5 : filtrer par segments et enrichir
    progress_cb(90, "Construction des lignes")
    rows_out: list[dict] = []
    scope = int(params.get("scope", 1))

    # Pour scope Équipe/Réseau HD : on récupère l'ensemble des orgas descendantes
    # des orgas cibles (un vendeur peut être dans une sous-équipe, pas directement
    # à la racine du réseau). Transitive closure sur organigramme.IdPARENT.
    orgas_racines: set[int] = {s.id_orga for s in segments if s.id_orga}
    orgas_cibles: set[int] = _load_orga_descendants(db_rh, orgas_racines) if orgas_racines else set()

    # Compteurs pour diagnostic (combien filtrés par scope vs conservés par partenaire)
    stat_brut: dict[str, int] = {}
    stat_keep: dict[str, int] = {}
    for r in all_rows:
        prefix = r["_prefix"]
        stat_brut[prefix] = stat_brut.get(prefix, 0) + 1
        id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
        date_sign_ymd = _to_ymd(r.get("DateSignature"))
        # Pour mode "par mois de paiement", on considère la fin du mois de paiement
        date_c_ymd = date_sign_ymd
        if mode_date == 2:
            mp = _to_ymd(r.get("MoisP"))
            if mp:
                date_c_ymd = _last_day_of_month(mp)

        affect = get_affect(id_salarie, date_c_ymd or prod_fin)

        # Filtrage par segment (scope Équipe/Réseau HD)
        if scope in (2, 4) and orgas_cibles:
            orga_id = affect.get("orga_id", 0)
            if orga_id not in orgas_cibles:
                continue

        # Filtrage par segment (scope Vendeur + Prod Groupe)
        if scope == 1 and params.get("prod_groupe") and segments:
            # Vérifier que la date signature tombe dans un segment du vendeur
            matched = False
            for seg in segments:
                if seg.id_salarie and seg.id_salarie != id_salarie:
                    continue
                if not date_sign_ymd:
                    matched = True
                    break
                if seg.date_debut <= date_sign_ymd <= seg.date_fin:
                    # Vérifier orga si segment le précise
                    if seg.id_orga == 0 or seg.id_orga == affect.get("orga_id", 0):
                        matched = True
                        break
            if not matched:
                continue

        sinfo = salaries_info.get(id_salarie, {})
        cid = _clean_id(_to_int(r.get("IDclient")))
        cinfo = clients_info.get(cid, {})
        id_te = _to_int(r.get("IDTypeEtat"))
        te = type_etats.get(id_te, {})
        famille = r.get("Famille") or ""
        sous_fam = r.get("SousFAM") or ""
        type_prod = sous_fam if prefix in ("ENI", "OEN") else famille

        num_bs = r.get("NumBS") or ""
        is_ticket = num_bs[:2].upper() == "TK" if num_bs else False

        nb_ctt_brut = 0 if is_ticket else 1
        nb_ctt_hors_rejet = 0
        nb_ctt_paye = 0
        if not is_ticket:
            if id_te != 3:
                nb_ctt_hors_rejet = 1
            elif prefix == "SFR" and _to_int(r.get("IDetatContrat")) == 73:
                nb_ctt_hors_rejet = 1
            if id_te in (5, 8):
                nb_ctt_paye = 1

        lib_etat_vend = r.get("Lib_EtatVend") or r.get("Lib_Etat") or ""

        # Heure signature :
        # - SFR Fibre (Famille != MOBILE et SousFAM ne contient pas BOX5G) :
        #   NumBS embarque la date+heure (TK/THD/CBL + 14 digits) → on extrait.
        # - SFR MOBILE / Box 5G + tous les autres partenaires (OEN/ENI/…) :
        #   on lookup TK_Liste.DATECREA via heure_tk (panier SFR ou Call).
        # - Fallback final : heure de DateSAISIE.
        ss_up = (sous_fam or "").upper()
        is_sfr_mob_b5g = prefix == "SFR" and (
            (famille or "").upper() == "MOBILE" or "BOX5G" in ss_up
        )
        heure_sign = ""
        if prefix == "SFR" and not is_sfr_mob_b5g:
            heure_sign = _heure_from_numbs(num_bs)
        else:
            heure_sign = heure_tk.get(num_bs, "")
        if not heure_sign:
            ds = r.get("DateSAISIE") or ""
            if ds:
                s = str(ds)
                iso_h = s[11:16] if len(s) >= 16 and s[10] in "T " else ""
                wd_h = s[8:12] if len(s) >= 12 and s[:8].isdigit() else ""
                h = iso_h or (f"{wd_h[:2]}:{wd_h[2:4]}" if wd_h else "")
                heure_sign = h

        # Etat opérateur (SFR/OEN) via jointure _etatContrat
        etat_ope_lib = ""
        etat_ope_type_id = 0
        etat_ope_type_lib = ""
        if prefix == "SFR":
            eo = sfr_etats_ope.get(_to_int(r.get("IDetatSFR")), {})
            etat_ope_lib = eo.get("lib_etat", "")
            etat_ope_type_id = eo.get("id_type_etat", 0)
            etat_ope_type_lib = type_etats.get(etat_ope_type_id, {}).get("lib", "")
        elif prefix == "OEN":
            eo = oen_etats_ope.get(_to_int(r.get("IdEtatOEN")), {})
            etat_ope_lib = eo.get("lib_etat", "")
            etat_ope_type_id = eo.get("id_type_etat", 0)
            etat_ope_type_lib = type_etats.get(etat_ope_type_id, {}).get("lib", "")

        # SFR Cluster
        cluster_code = ""
        cluster_nom = ""
        if prefix == "SFR":
            cl = sfr_clusters.get(_clean_id(_to_int(r.get("IDSFR_Cluster"))), {})
            cluster_code = cl.get("code_vad", "")
            cluster_nom = cl.get("nom_cluster", "")

        # Options ENI/OEN
        opts = {}
        if prefix == "ENI":
            opts = eni_opts.get(_clean_id(_to_int(r.get("IDcontrat"))), {})
        elif prefix == "OEN":
            opts = oen_opts.get(_clean_id(_to_int(r.get("IDcontrat"))), {})

        # Consommation gaz/électricité (ENI/OEN)
        car = 0
        if prefix in ("ENI", "OEN"):
            car = _to_int(r.get("GazCarDeclaree"))
            car_relev = _to_int(r.get("GazCarRelevée"))
            if car_relev > 0:
                car = car_relev
        puissance = _to_int(r.get("ElecPuissance")) if prefix in ("ENI", "OEN") else 0

        # Date Racc / Activation (SFR = DateRaccActiv ; OEN = DateActivation)
        date_racc_activ = ""
        if prefix == "SFR":
            date_racc_activ = _iso(r.get("DateRaccActiv"))
        elif prefix == "OEN":
            date_racc_activ = _iso(r.get("DateActivation"))

        rows_out.append({
            # Identité + commun
            "id_contrat": str(_clean_id(_to_int(r.get("IDcontrat")))),
            "partenaire": prefix,
            "num_bs": num_bs,
            "date_signature": _iso(r.get("DateSignature")),
            "date_saisie": _iso(r.get("DateSAISIE")),
            "mois_p": _iso(r.get("MoisP")),
            "heure_sign": heure_sign,
            "lib_produit": r.get("Lib_produit") or "",
            "type_prod": type_prod,
            "sous_fam": sous_fam,
            "id_etat_contrat": _to_int(r.get("IDetatContrat")),
            "id_type_etat": id_te,
            "lib_type_etat": te.get("lib", ""),
            "couleur_etat": te.get("couleur", ""),
            "lib_etat": r.get("Lib_Etat") or "",
            "lib_etat_vend": lib_etat_vend,
            # OEN/ENI : NumBS présent dans TK_Call_Panier ? (sert au tx consent)
            "in_tk_call_panier": (prefix in ("OEN", "ENI") and num_bs in in_tk_call),
            # Etat opérateur (SFR/OEN uniquement)
            "id_type_etat_ope": etat_ope_type_id,
            "lib_type_etat_ope": etat_ope_type_lib,
            "lib_etat_ope": etat_ope_lib,
            # Vendeur
            "id_salarie": str(id_salarie),
            "vendeur_nom": sinfo.get("nom", ""),
            "vendeur_prenom": sinfo.get("prenom", ""),
            "agence": affect.get("agence", ""),
            "equipe": affect.get("equipe", ""),
            "poste": sinfo.get("poste", ""),
            "en_activite": sinfo.get("en_activite", True),
            "date_embauche": sinfo.get("date_embauche", ""),
            "date_sortie": sinfo.get("date_sortie", ""),
            # Client
            "id_client": str(cid),
            "client_nom": cinfo.get("nom", ""),
            "client_prenom": _capitalize(cinfo.get("prenom", "")),
            "client_adresse1": cinfo.get("adresse1", ""),
            "client_adresse2": cinfo.get("adresse2", ""),
            "client_cp": cinfo.get("cp", ""),
            "client_ville": cinfo.get("ville", ""),
            "client_mail": cinfo.get("mail", ""),
            "client_mobile": cinfo.get("mobile", ""),
            "client_age": cinfo.get("age", 0),
            "client_rap_part": cinfo.get("opt_partenaire", False),
            # Valeurs + notation
            "nb_points": _to_int(r.get("nbPoints")),
            # SFR stocke la notation /5 en BDD, on l'expose /10 (cf. WinDev StatsSFR : Notation*2)
            "notation": (
                float(r.get("Notation") or 0) * 2
                if prefix == "SFR"
                else float(r.get("Notation") or 0)
            ),
            "notation_info": r.get("NotationInfo") or "",
            "info_interne": r.get("InfoInterne") or "",
            "info_partagee": r.get("InfoPartagee") or "",
            "code_enr": r.get("CodeENR") or "",
            # SFR specifique
            "activ_control": r.get("ActivControl") or "" if prefix == "SFR" else "",
            "processing_state": r.get("ProcessingState") or "" if prefix == "SFR" else "",
            "sfr_type_vente": _to_int(r.get("TypeVente")) if prefix == "SFR" else 0,
            "sfr_technologie": _to_int(r.get("Technologie")) if prefix == "SFR" else 0,
            "sfr_box8": bool(r.get("Box8")) if prefix == "SFR" else False,
            "sfr_box8_verif": bool(r.get("Box8Vérif")) if prefix == "SFR" else False,
            "sfr_hors_cible": bool(r.get("HorsCible")) if prefix == "SFR" else False,
            "sfr_date_rdv_tech": _iso(r.get("DateRDVTech")) if prefix == "SFR" else "",
            "sfr_date_racc_activ": date_racc_activ,
            "sfr_date_validation": (
                _iso(r.get("DateValidation")) if prefix in ("SFR", "PRO") else ""
            ),
            "sfr_date_resil": (
                _iso(r.get("DateRésil")) if prefix in ("SFR", "PRO") else ""
            ),
            "sfr_portabilite": bool(r.get("Portabilité")) if prefix == "SFR" else False,
            "sfr_date_portab": _iso(r.get("DatePortabilité")) if prefix == "SFR" else "",
            "sfr_cluster_code": cluster_code,
            "sfr_cluster_nom": cluster_nom,
            "sfr_mois_p_distrib": _iso(r.get("MoisP_RaDistri")) if prefix == "SFR" else "",
            "sfr_internet_garanti": bool(r.get("InternetGaranti")) if prefix == "SFR" else False,
            "sfr_offre_speciale": bool(r.get("OffreSpeciale")) if prefix == "SFR" else False,
            "sfr_parcours_chaine": bool(r.get("ParcoursChainé")) if prefix == "SFR" else False,
            "sfr_prise_existante": bool(r.get("PriseExistante")) if prefix == "SFR" else False,
            "sfr_prise_saisie": bool(r.get("PriseSaisie")) if prefix == "SFR" else False,
            "sfr_num_prise_sfr": r.get("NumPrise_SFR") or "" if prefix == "SFR" else "",
            "sfr_num_prise_vend": r.get("NumPrise_Vend") or "" if prefix == "SFR" else "",
            # ENI/OEN consommation
            "car": car,
            "puissance": puissance,
            "gaz_actif": bool(r.get("GazActif")) if prefix == "ENI" else False,
            "elec_actif": bool(r.get("ElecActif")) if prefix == "ENI" else False,
            # ENI/OEN options (cf table _contrat_Option)
            "opt_demat": bool(opts.get("opt_efacture", False)),  # OPT Démat ≈ OPT_eFacture (à confirmer)
            "opt_maintenance": bool(opts.get("opt_entretien", False)),
            "opt_energie_verte_gaz": bool(opts.get("opt_energie_verte_gaz", False)),
            "opt_reforestation": bool(opts.get("opt_reforestation", False)),
            "opt_protection": bool(opts.get("opt_protection", False)),
            # STR/VAL
            "opt_num": r.get("OptNum") or "" if prefix in ("STR", "VAL") else "",
            # Compteurs
            "nb_ctt_brut": nb_ctt_brut,
            "nb_ctt_hors_rejet": nb_ctt_hors_rejet,
            "nb_ctt_paye": nb_ctt_paye,
        })
        stat_keep[prefix] = stat_keep.get(prefix, 0) + 1

    # Diagnostic : résumé brut/gardé par partenaire dans la progression
    diag = " ".join(
        f"{p}={stat_keep.get(p, 0)}/{stat_brut.get(p, 0)}"
        for p in sorted(stat_brut)
    )
    progress_cb(92, f"Gardes : {diag}")

    # Étape 6 : écriture Parquet
    progress_cb(93, f"Écriture Parquet ({len(rows_out)} lignes)")
    out_path = _parquet_path(id_salarie_user, id_job)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Import pandas ici pour ne pas le charger si le service n'est pas appelé
    import pandas as pd
    df = pd.DataFrame(rows_out)
    # Types explicites pour les colonnes numériques, au cas où df soit vide
    if df.empty:
        df = pd.DataFrame(columns=[
            "id_contrat", "partenaire", "num_bs", "date_signature",
        ])
    df.to_parquet(out_path, compression="snappy", index=False)

    # Étape 7 : calcul des stats (onglets dashboard) et écriture meta.json
    progress_cb(96, "Chargement des jours de présence")
    # Nb Jours Présence pour les vendeurs SFR (actifs) — utilisé par le dashboard SFR
    sfr_vendeur_ids: set[int] = set()
    weekends_by_sal: dict[int, set[str]] = {}
    for r in rows_out:
        if r.get("partenaire") != "SFR":
            continue
        if not r.get("en_activite", True):
            continue
        try:
            sid = int(r.get("id_salarie") or 0)
        except (TypeError, ValueError):
            sid = 0
        if not sid:
            continue
        sfr_vendeur_ids.add(sid)
        ds = r.get("date_signature") or ""
        if len(ds) >= 10:
            try:
                dt = date(int(ds[:4]), int(ds[5:7]), int(ds[8:10]))
                # weekday : 5 = samedi, 6 = dimanche
                if dt.weekday() >= 5:
                    weekends_by_sal.setdefault(sid, set()).add(ds.replace("-", ""))
            except Exception:
                pass

    nb_jour_pres = _load_nb_jour_pres(
        db_rh, sfr_vendeur_ids, prod_deb, prod_fin, weekends_by_sal,
    )

    progress_cb(97, "Calcul des stats")
    partenaires_couleurs = _load_partenaires_couleurs(db_adv)
    stats = _compute_stats(rows_out, partenaires_couleurs, nb_jour_pres)
    meta_path = _meta_path(id_salarie_user, id_job)
    meta_path.write_text(
        json.dumps(stats, ensure_ascii=False),
        encoding="utf-8",
    )

    duree_s = int(time.time() - t0)
    progress_cb(100, "Terminé")
    return {
        "path": str(out_path),
        "nb_lignes": len(rows_out),
        "duree_s": duree_s,
        "message_erreur": "",
    }


def _load_partenaires_couleurs(db_adv) -> dict[str, str]:
    """Retourne un mapping PréfixeBDD -> couleur hex (depuis la table Partenaire)."""
    rows = db_adv.query(
        """SELECT PréfixeBDD, Couleur_R, Couleur_V, Couleur_B
        FROM Partenaire
        WHERE ModifELEM <> 'suppr' AND PréfixeBDD <> ''"""
    )
    out: dict[str, str] = {}
    for r in rows:
        prefix = (r.get("PréfixeBDD") or "").strip()
        if prefix:
            out[prefix] = _winrgb_to_hex(
                _to_int(r.get("Couleur_R")),
                _to_int(r.get("Couleur_V")),
                _to_int(r.get("Couleur_B")),
            )
    return out


def _compute_stats(
    rows: list[dict],
    partenaires_couleurs: dict[str, str],
    nb_jour_pres_par_salarie: dict[int, int] | None = None,
) -> dict:
    """
    Agrège les stats universelles à partir des rows extraites :
      - répartition par partenaire (Brut/Temporaire/Envoyé/Rejet/Résil/Payé/...)
      - liste des vendeurs avec nb contrats, nb payé, nb_points, et répartition
        par partenaire

    Équivalent WinDev : TableRepartContrats + TableVendeur de Fen_suiviProdAsynchrone.
    """
    # Répartition par partenaire : un dict par prefix
    repart: dict[str, dict] = {}
    for r in rows:
        prefix = r.get("partenaire", "")
        if not prefix:
            continue
        if prefix not in repart:
            repart[prefix] = {
                "partenaire": prefix,
                "couleur_hex": partenaires_couleurs.get(prefix, ""),
                "brut": 0, "temporaire": 0, "envoye": 0, "rejet": 0,
                "resil": 0, "payé": 0, "decomm": 0,
                "racc_activ_ko": 0, "racc_active": 0,
            }
        entry = repart[prefix]
        entry["brut"] += 1  # chaque ligne compte pour le brut

        # Mapping IDTypeEtat -> colonne (identique à WinDev)
        id_te = int(r.get("id_type_etat", 0) or 0)
        if id_te == 2:
            entry["envoye"] += 1
        elif id_te == 3:
            entry["rejet"] += 1
        elif id_te == 4:
            entry["resil"] += 1
        elif id_te == 5:
            entry["payé"] += 1
        elif id_te == 6:
            entry["decomm"] += 1
        elif id_te == 7:
            entry["racc_activ_ko"] += 1
        elif id_te == 8:
            entry["racc_active"] += 1
        else:
            # cas "Temporaire" = tout le reste (1, 9, 10...)
            entry["temporaire"] += 1

    repart_rows = sorted(repart.values(), key=lambda x: x["partenaire"])

    # Par vendeur : groupement id_salarie
    vendeurs: dict[str, dict] = {}
    for r in rows:
        id_sal = r.get("id_salarie") or "0"
        if id_sal == "0":
            continue
        if id_sal not in vendeurs:
            vendeurs[id_sal] = {
                "id_salarie": id_sal,
                "nom": r.get("vendeur_nom", ""),
                "prenom": r.get("vendeur_prenom", ""),
                "agence": r.get("agence", ""),
                "equipe": r.get("equipe", ""),
                "poste": r.get("poste", ""),
                "en_activite": bool(r.get("en_activite", True)),
                "date_sortie": r.get("date_sortie", ""),
                "nb_contrats": 0,
                "nb_paye": 0,
                "nb_hors_rejet": 0,
                "nb_points": 0,
                "par_partenaire": {},
            }
        v = vendeurs[id_sal]
        v["nb_contrats"] += 1
        v["nb_paye"] += int(r.get("nb_ctt_paye", 0) or 0)
        v["nb_hors_rejet"] += int(r.get("nb_ctt_hors_rejet", 0) or 0)
        v["nb_points"] += int(r.get("nb_points", 0) or 0)
        prefix = r.get("partenaire", "")
        if prefix:
            v["par_partenaire"][prefix] = v["par_partenaire"].get(prefix, 0) + 1

    vendeur_rows = sorted(
        vendeurs.values(),
        key=lambda x: (-x["nb_contrats"], x["nom"].lower()),
    )

    total_contrats = len(rows)
    total_paye = sum(int(r.get("nb_ctt_paye", 0) or 0) for r in rows)
    total_points = sum(int(r.get("nb_points", 0) or 0) for r in rows)

    # Dashboards par partenaire (onglet Analyse)
    dashboard_sfr = _compute_dashboard_sfr(rows, nb_jour_pres_par_salarie or {})
    dashboard_oen = _compute_dashboard_oen(rows)
    dashboard_eni = _compute_dashboard_eni(rows)

    return {
        "total_contrats": total_contrats,
        "total_paye": total_paye,
        "total_points": total_points,
        "repart_partenaires": repart_rows,
        "vendeurs": vendeur_rows,
        "dashboard_sfr": dashboard_sfr,
        "dashboard_oen": dashboard_oen,
        "dashboard_eni": dashboard_eni,
    }


def _pct(num: float, den: float, decimals: int = 2) -> float:
    if not den:
        return 0.0
    return round((num / den) * 100, decimals)


def _compute_dashboard_sfr(
    rows: list[dict],
    nb_jour_pres_par_salarie: dict[int, int] | None = None,
) -> dict:
    """
    Dashboard SFR — transposition fidèle de StatsSFR() + AfficheResultatSFR() WinDev.

    Règles clés :
    - Catégorisation par SousFAM et Lib_Produit :
      * Mobile         : type_prod = "MOBILE" (Famille)
      * Secu           : type_prod = "SECU"
      * Box 5G         : SousFAM contient "Box5G"
      * Fibre          : autre cas (hors Mobile / Secu / Box5G), hors BS en TK
    - Hors attente    : id_type_etat > 2 (1=attente saisie, 2=en attente opérateur)
    - Raccordé/Payé  : id_type_etat ∈ {5, 8}
    - Raccordé SFR   : id_type_etat_ope ∈ {5, 8}
    - CQ (Conquête) : sfr_type_vente ≤ 2 ET pas un TK
    - Dépôt garantie : id_etat_contrat = 73
    """
    sfr_all = [r for r in rows if r.get("partenaire") == "SFR"]
    if not sfr_all:
        return {}

    def _is_tk(r: dict) -> bool:
        return str(r.get("num_bs", "") or "")[:2].upper() == "TK"

    def _ss(r: dict) -> str:
        return (r.get("sous_fam", "") or "").upper()

    def _tp(r: dict) -> str:
        return (r.get("type_prod", "") or "").upper()

    # Tous les KPIs (clients, consentement, note, sous-familles) sont calculés
    # HORS TK — WinDev n'appelle StatsSFR que si NumBS ne commence pas par "TK".
    sfr = [r for r in sfr_all if not _is_tk(r)]

    # TableListe4P WinDev : par client_mail, compteurs MobCQ/VLA + FixCQ/VLA.
    t_4p: dict[str, dict] = {}

    def _t4p(email: str) -> dict:
        d = t_4p.get(email)
        if d is None:
            d = {"mob_cq": 0, "mob_vla": 0, "fix_cq": 0, "fix_vla": 0}
            t_4p[email] = d
        return d

    # TableTxRaccVendeur WinDev : 1 ligne par vendeur (id_salarie).
    # Les compteurs ne sont alimentés que pour les vendeurs en activité.
    v_rows: dict[str, dict] = {}

    def _vrow(r: dict) -> dict | None:
        """Retourne la ligne vendeur ou None si inactif (indF = 0 WinDev)."""
        id_s = r.get("id_salarie") or "0"
        if id_s == "0":
            return None
        v = v_rows.get(id_s)
        if v is None:
            v = {
                "id_salarie": id_s,
                "nom": r.get("vendeur_nom", ""),
                "prenom": r.get("vendeur_prenom", ""),
                "agence": r.get("agence", ""),
                "equipe": r.get("equipe", ""),
                "en_activite": bool(r.get("en_activite", True)),
                "nb_thd": 0,
                "nb_cq": 0,
                "nb_ra": 0,
                "nb_port": 0,
                "nb_cq_ra_fixe": 0,
                "nb_res30j_fixe": 0,
                "nb_cq_ra_mob": 0,
                "nb_res30j_mob": 0,
                "nb_consent": 0,
                "nb_client": 0,
                "nb_prise": 0,
                "nb_prise_existante": 0,
                "nb_fibre": 0,
                "nb_box5g": 0,
                "nb_mob": 0,
                "nb_ctt_note": 0,
                "nb_ctt_non_note": 0,
                "nb_note_tot": 0.0,
                "nb_depot_gar": 0,
                "nb_fibre_hors_a": 0,
            }
            v_rows[id_s] = v
        return v if v["en_activite"] else None

    # --- Compteurs généraux (note + consentement par client unique)
    noted = [r for r in sfr if (r.get("notation") or 0) > 0]
    nb_note_sfr = len(noted)
    tot_note_sfr = sum(r.get("notation", 0) for r in noted)

    id_clients_seen: set = set()
    nb_clients = 0
    nb_consent = 0
    for r in sfr:
        cid = r.get("id_client") or "0"
        if cid != "0" and cid not in id_clients_seen:
            id_clients_seen.add(cid)
            nb_clients += 1
            is_consent = bool(r.get("client_rap_part"))
            if is_consent:
                nb_consent += 1
            # Compteur par vendeur : 1 fois par client unique
            v = _vrow(r)
            if v is not None:
                v["nb_client"] += 1
                if is_consent:
                    v["nb_consent"] += 1

    # Notation par vendeur (idem WinDev : sommée pour tous ses contrats notés)
    for r in sfr:
        v = _vrow(r)
        if v is None:
            continue
        note = r.get("notation") or 0
        if note > 0:
            v["nb_ctt_note"] += 1
            v["nb_note_tot"] += float(note)
        else:
            v["nb_ctt_non_note"] += 1

    # --- Sous-familles Premium/Power/Starter
    nb_prem_ssfam = sum(1 for r in sfr if "PREMIUM" in _ss(r))
    nb_power_ssfam = sum(1 for r in sfr if "POWER" in _ss(r))
    nb_starter_ssfam = sum(1 for r in sfr if "STARTER" in _ss(r))

    # --- Parcours Mobile / Fibre / Box5G (excluant les BS en TK)
    nb_sfr_mobile = 0
    nb_sfr_f200 = 0
    nb_sfr_mob_hors_att = 0
    nb_sfr_activ = 0          # Mobile : IdTypeEtatOpé ∈ {5,8}
    nb_sfr_activ_sfr = 0      # Mobile : IdTypeEtatOpé ∈ {5,8} OU testResilChurn
    nb_cq_ra_mob = 0
    nb_res30j_mob = 0

    nb_sfr_secu = 0

    nb_sfr_fibre = 0
    nb_sfr_prem_lib = 0        # Lib_Produit contient "premium"
    nb_sfr_cq = 0              # Type_vente ≤ 2 sur Fibre
    nb_sfr_pc = 0              # Parcours chaînés sur CQ fibre
    nb_sfr_depot_gar = 0
    nb_sfr_fibre_hors_a = 0    # hors anomalie
    nb_cts_resil_fibre = 0
    nb_cts_hors_att = 0        # id_type_etat > 2 sur fibre
    nb_cts_hors_att_av_port = 0
    nb_cts_hors_att_sfr = 0    # id_type_etat_ope > 2 sur fibre
    nb_cts_hors_att_sfr_av_port = 0
    nb_cts_ra = 0              # id_type_etat ∈ {5,8}
    nb_cts_ra_sfr = 0          # id_type_etat_ope ∈ {5,8} OU testResilChurn
    nb_cts_portab = 0          # Portabilité ET CQ (type_vente ≤ 2)
    nb_cq_ra_fixe = 0
    nb_res30j_fixe = 0
    nb_sfr_prise_existante = 0
    nb_sfr_prise_saisie = 0

    nb_sfr_box5g = 0
    nb_sfr_box5g_tv = 0
    nb_sfr_box5g_resil = 0
    nb_sfr_cq_box5g = 0
    nb_cts_hors_att_b5g = 0
    nb_cts_hors_att_sfr_b5g = 0
    nb_cts_b5g_ra = 0
    nb_cts_b5g_ra_sfr = 0
    nb_cq_ra_b5g = 0
    nb_res30j_b5g = 0


    def _churn_jours(r: dict) -> int | None:
        """Nb jours entre DateRaccActiv et DateRésil (ou None si dates invalides)."""
        try:
            d_racc = r.get("sfr_date_racc_activ") or ""
            d_resil = r.get("sfr_date_resil") or ""
            if len(d_racc) < 10 or len(d_resil) < 10:
                return None
            d1 = date(int(d_racc[:4]), int(d_racc[5:7]), int(d_racc[8:10]))
            d2 = date(int(d_resil[:4]), int(d_resil[5:7]), int(d_resil[8:10]))
            return (d2 - d1).days
        except Exception:
            return None

    for r in sfr:
        te = r.get("id_type_etat") or 0
        te_ope = r.get("id_type_etat_ope") or 0
        id_etat = r.get("id_etat_contrat") or 0
        type_vente = r.get("sfr_type_vente") or 0
        is_cq = type_vente <= 2
        activ_control = (r.get("activ_control") or "").upper()
        processing_state = (r.get("processing_state") or "").upper()
        ss = _ss(r)
        tp = _tp(r)
        is_tk = _is_tk(r)

        # Mobile / Secu se calculent même si TK=False (ils ne nourrissent Fibre/Box5G que si non-TK)
        if is_tk:
            # TK → exclus des stats Fibre/Box5G (le WinDev ne compte rien)
            continue

        if tp == "MOBILE":
            nb_sfr_mobile += 1
            v = _vrow(r)
            if v is not None:
                v["nb_mob"] += 1
            # Forfait > 200Go : 1er nombre suivi de "G" dans le libellé
            import re
            lp = (r.get("lib_produit", "") or "").upper()
            m = re.search(r"(\d+)\s*G", lp)
            if m and int(m.group(1)) >= 200:
                nb_sfr_f200 += 1

            # TableListe4P : incrémenter mob_cq/mob_vla selon Type_vente
            email = r.get("client_mail") or ""
            if is_cq and email:
                t = _t4p(email)
                if type_vente == 1:
                    t["mob_cq"] += 1
                elif type_vente == 2:
                    t["mob_vla"] += 1

            test_resil_churn = False
            if is_cq:
                if activ_control == "ACTIVE_BIOS" and processing_state in ("COMPLETED", "CANCELLED"):
                    nb_cq_ra_mob += 1
                    if v is not None:
                        v["nb_cq_ra_mob"] += 1
                if (activ_control in ("ACTIVE_BIOS", "CANCELLED")
                        and processing_state in ("COMPLETED", "CANCELLED")):
                    churn = _churn_jours(r)
                    if churn is not None and churn <= 30:
                        nb_res30j_mob += 1
                        test_resil_churn = True
                        if v is not None:
                            v["nb_res30j_mob"] += 1

            if te_ope in (5, 8):
                nb_sfr_activ += 1
            if te_ope in (5, 8) or test_resil_churn:
                nb_sfr_activ_sfr += 1
            if te_ope > 2:
                nb_sfr_mob_hors_att += 1
            continue

        if tp == "SECU":
            nb_sfr_secu += 1
            continue

        # Fibre / Box5G : on entre dans la branche "testFibre"
        if "BOX5G" in ss:
            nb_sfr_box5g += 1
            v = _vrow(r)
            if v is not None:
                v["nb_box5g"] += 1
            if ss == "BOX5GTV":
                nb_sfr_box5g_tv += 1
            if te == 4:
                nb_sfr_box5g_resil += 1
            if is_cq:
                nb_sfr_cq_box5g += 1
                if activ_control == "ACTIVE_BIOS" and processing_state in ("COMPLETED", "CANCELLED"):
                    nb_cq_ra_b5g += 1
                    # WinDev remplit nb_CQ_RA_Mob pour les B5G (cf. StatsSFR Box5G branche)
                    if v is not None:
                        v["nb_cq_ra_mob"] += 1
                test_resil_churn = False
                if (activ_control in ("ACTIVE_BIOS", "CANCELLED")
                        and processing_state in ("COMPLETED", "CANCELLED")):
                    churn = _churn_jours(r)
                    if churn is not None and churn <= 30:
                        nb_res30j_b5g += 1
                        test_resil_churn = True
                        if v is not None:
                            v["nb_res30j_mob"] += 1
            else:
                test_resil_churn = False

            if te > 2:
                nb_cts_hors_att_b5g += 1
            if te_ope > 2:
                nb_cts_hors_att_sfr_b5g += 1
            if te in (5, 8):
                nb_cts_b5g_ra += 1
            if te_ope in (5, 8) or test_resil_churn:
                nb_cts_b5g_ra_sfr += 1
        else:
            # Fibre pure
            nb_sfr_fibre += 1
            v = _vrow(r)
            if v is not None:
                v["nb_fibre"] += 1

            if "PREMIUM" in (r.get("lib_produit", "") or "").upper():
                nb_sfr_prem_lib += 1
            if te == 4:
                nb_cts_resil_fibre += 1
            if id_etat == 73:
                nb_sfr_depot_gar += 1
                if v is not None:
                    v["nb_depot_gar"] += 1
            if te != 3:  # hors anomalie
                nb_sfr_fibre_hors_a += 1
                if v is not None:
                    v["nb_fibre_hors_a"] += 1
            if r.get("sfr_prise_existante"):
                nb_sfr_prise_existante += 1
                if v is not None:
                    v["nb_prise_existante"] += 1
            if r.get("sfr_prise_saisie"):
                nb_sfr_prise_saisie += 1
                if v is not None:
                    v["nb_prise"] += 1

            # Portabilité compte uniquement sur CQ
            if r.get("sfr_portabilite") and is_cq:
                nb_cts_portab += 1

            # CQ counters + TableListe4P pour Fixe
            test_resil_churn = False
            if is_cq:
                nb_sfr_cq += 1
                if v is not None:
                    v["nb_cq"] += 1
                    if r.get("sfr_portabilite"):
                        v["nb_port"] += 1
                if r.get("sfr_parcours_chaine"):
                    nb_sfr_pc += 1
                email = r.get("client_mail") or ""
                if email:
                    t = _t4p(email)
                    if type_vente == 1:
                        t["fix_cq"] += 1
                    elif type_vente == 2:
                        t["fix_vla"] += 1
                if processing_state == "RACCORDEE RAS":
                    nb_cq_ra_fixe += 1
                    if v is not None:
                        v["nb_cq_ra_fixe"] += 1
                    churn = _churn_jours(r)
                    if churn is not None and churn <= 30:
                        nb_res30j_fixe += 1
                        test_resil_churn = True
                        if v is not None:
                            v["nb_res30j_fixe"] += 1

            if te > 2:
                nb_cts_hors_att += 1
                if v is not None:
                    v["nb_thd"] += 1
                if r.get("sfr_portabilite") and is_cq:
                    nb_cts_hors_att_av_port += 1
            if te_ope > 2:
                nb_cts_hors_att_sfr += 1
                if r.get("sfr_portabilite") and is_cq:
                    nb_cts_hors_att_sfr_av_port += 1
            if te in (5, 8):
                nb_cts_ra += 1
                if v is not None:
                    v["nb_ra"] += 1
            if te_ope in (5, 8) or test_resil_churn:
                nb_cts_ra_sfr += 1

    # Note moyenne sur l'ensemble SFR (la notation est déjà /10 en rows_out)
    note_moy = round(tot_note_sfr / nb_note_sfr, 2) if nb_note_sfr else 0.0
    pct_notes = _pct(nb_note_sfr, nb_sfr_fibre) if nb_sfr_fibre else 0.0

    # Calcul nb_sfr_4p (clients "4 Play" : mobile + fixe chez le même client).
    # Règle WinDev : (nbMobVLA>0 ET nbFixCQ>0) OU (nbMobCQ>0 ET (nbFixCQ + nbFixVLA) > 0)
    nb_sfr_4p = 0
    for c in t_4p.values():
        if (c["mob_vla"] > 0 and c["fix_cq"] > 0) or (
            c["mob_cq"] > 0 and (c["fix_cq"] + c["fix_vla"]) > 0
        ):
            nb_sfr_4p += 1

    # % Parcours Chaînés : capé à 100% (cf. AfficheResultatSFR WinDev)
    tx_pc = _pct(nb_sfr_pc, nb_sfr_4p)
    if tx_pc > 100:
        tx_pc = 100.0

    # Finalisation du tableau vendeur : calculs des taux + Nb_JourPres + Productivité
    jp = nb_jour_pres_par_salarie or {}
    tx_racc_vendeur: list[dict] = []
    for v in v_rows.values():
        nb_jour_pres = int(jp.get(int(v["id_salarie"]), 0))
        nb_thd = v["nb_thd"]
        nb_cq = v["nb_cq"]
        # Productivité = (Fibre hors anomalie + DG) / Nb jours présence
        productivite = 0.0
        if nb_jour_pres > 0:
            productivite = round(
                (v["nb_fibre_hors_a"] + v["nb_depot_gar"]) / nb_jour_pres, 2
            )
        tx_racc_vendeur.append({
            **v,
            "nb_jour_pres": nb_jour_pres,
            "productivite": productivite,
            "tx_racc": _pct(v["nb_ra"], nb_thd),
            "tx_portab": _pct(v["nb_port"], nb_cq),
            "tx_churn_mob": _pct(v["nb_res30j_mob"], v["nb_cq_ra_mob"]),
            "tx_churn_fixe": _pct(v["nb_res30j_fixe"], v["nb_cq_ra_fixe"]),
            "tx_consent": _pct(v["nb_consent"], v["nb_client"]),
            "tx_prise": _pct(v["nb_prise"], v["nb_prise_existante"]),
            "tx_mobile": _pct(v["nb_mob"], v["nb_fibre"]),
            "tx_ctt_note": _pct(
                v["nb_ctt_note"], v["nb_ctt_note"] + v["nb_ctt_non_note"],
            ),
            "note_moy": (
                round(v["nb_note_tot"] / v["nb_ctt_note"], 2)
                if v["nb_ctt_note"] > 0 else 0.0
            ),
        })
    # Tri : par ordre alphabétique sur nom
    tx_racc_vendeur.sort(key=lambda x: (x["nom"].lower(), x["prenom"].lower()))

    # --- Horaires de signatures (ventes finalisées hors TK)
    horaires: dict[str, dict] = {}
    for r in sfr:  # sfr = sfr_all hors TK
        hs = str(r.get("heure_sign") or "")
        if len(hs) < 2 or not hs[:2].isdigit():
            continue
        h = hs[:2]
        b = horaires.setdefault(h, {"h": h, "ventes": 0})
        b["ventes"] += 1
    horaires_sign = sorted(horaires.values(), key=lambda x: x["h"])

    return {
        # SFR global
        "note_moy": note_moy,
        "pct_notes": pct_notes,
        "nb_consent": nb_consent,
        "nb_clients": nb_clients,
        "tx_consent": _pct(nb_consent, nb_clients),

        # Fibre
        "nb_fibre": nb_sfr_fibre,
        "nb_fibre_hors_att": nb_cts_hors_att,
        "nb_fibre_ra": nb_cts_ra,
        "nb_fibre_ra_sfr": nb_cts_ra_sfr,
        "nb_fibre_resil": nb_cts_resil_fibre,
        "nb_fibre_cq": nb_sfr_cq,
        "nb_fibre_porta": nb_cts_portab,
        "nb_fibre_prise_existante": nb_sfr_prise_existante,
        "nb_fibre_prise_saisie": nb_sfr_prise_saisie,
        "nb_fibre_depot_gar": nb_sfr_depot_gar,
        "nb_fibre_pc": nb_sfr_pc,
        "nb_fibre_premium_lib": nb_sfr_prem_lib,  # Lib_Produit contient "premium"
        "nb_prem_ssfam": nb_prem_ssfam,
        "nb_power_ssfam": nb_power_ssfam,
        "nb_starter_ssfam": nb_starter_ssfam,
        "tx_racc": _pct(nb_cts_ra, nb_cts_hors_att),
        "tx_racc_sfr": _pct(nb_cts_ra_sfr, nb_cts_hors_att_sfr),
        "tx_resil": _pct(nb_cts_resil_fibre, nb_sfr_fibre),
        "tx_cq": _pct(nb_sfr_cq, nb_sfr_fibre),
        "tx_premium": _pct(nb_sfr_prem_lib, nb_sfr_fibre),
        "tx_portab": _pct(nb_cts_portab, nb_sfr_cq),
        "tx_prise_saisie": _pct(nb_sfr_prise_saisie, nb_sfr_prise_existante),
        "tx_mobile": _pct(nb_sfr_mobile, nb_sfr_fibre),
        "tx_dg": _pct(nb_sfr_depot_gar, nb_sfr_fibre),
        "nb_sfr_4p": nb_sfr_4p,
        "tx_pc": tx_pc,

        # Mobile
        "nb_mobile": nb_sfr_mobile,
        "nb_mobile_hors_att": nb_sfr_mob_hors_att,
        "nb_mobile_activ": nb_sfr_activ,
        "nb_mobile_activ_sfr": nb_sfr_activ_sfr,
        "nb_mobile_200go": nb_sfr_f200,
        "nb_cq_ra_mob": nb_cq_ra_mob,
        "nb_res30j_mob": nb_res30j_mob,
        "tx_mobile_activ": _pct(nb_sfr_activ, nb_sfr_mob_hors_att),
        "tx_mobile_activ_sfr": _pct(nb_sfr_activ_sfr, nb_sfr_mob_hors_att),
        "tx_forfait_200go": _pct(nb_sfr_f200, nb_sfr_mobile),
        "tx_churn_mob": _pct(nb_res30j_mob, nb_cq_ra_mob),

        # Secu
        "nb_secu": nb_sfr_secu,

        # Box 5G
        "nb_box5g": nb_sfr_box5g,
        "nb_box5g_hors_att": nb_cts_hors_att_b5g,
        "nb_box5g_hors_att_sfr": nb_cts_hors_att_sfr_b5g,
        "nb_box5g_activ": nb_cts_b5g_ra,
        "nb_box5g_activ_sfr": nb_cts_b5g_ra_sfr,
        "nb_box5g_resil": nb_sfr_box5g_resil,
        "nb_box5g_cq": nb_sfr_cq_box5g,
        "nb_box5g_tv": nb_sfr_box5g_tv,
        "nb_cq_ra_b5g": nb_cq_ra_b5g,
        "nb_res30j_b5g": nb_res30j_b5g,
        "tx_box5g_racc": _pct(nb_cts_b5g_ra, nb_cts_hors_att_b5g),
        "tx_box5g_racc_sfr": _pct(nb_cts_b5g_ra_sfr, nb_cts_hors_att_sfr_b5g),
        "tx_box5g_cq": _pct(nb_sfr_cq_box5g, nb_sfr_box5g),
        "tx_box5g_resil": _pct(nb_sfr_box5g_resil, nb_sfr_box5g),
        "tx_box5g_tv": _pct(nb_sfr_box5g_tv, nb_sfr_box5g),
        "tx_churn_b5g": _pct(nb_res30j_b5g, nb_cq_ra_b5g),

        # Tableau par vendeur (TableTxRaccVendeur WinDev)
        "tx_racc_vendeur": tx_racc_vendeur,

        # Graphique horaires de signatures (Graph WinDev)
        "horaires_sign": horaires_sign,
    }


def _compute_dashboard_oen(rows: list[dict]) -> dict:
    """
    Dashboard OEN — équivalent AfficheResultatOEN() WinDev.

    Règles :
    - Nb PDL = total des lignes brutes (1 par ligne, dual = 2 PDL)
    - Nb Ctt Hors Anomalie = mono + dual/2 (un dual = 1 contrat pour 2 PDL)
    """
    oen = [r for r in rows if r.get("partenaire") == "OEN"]
    if not oen:
        return {}

    # PDL hors anomalies (id_type_etat == 3 = anomalie). Sert de base pour le
    # KPI "Nb PDL Hors anomalie" et les segmentations Base / 6Kva.
    oen_hors_anom = [r for r in oen if r.get("id_type_etat") != 3]
    nb_pdl_brut = len(oen_hors_anom)

    # Segmentation par TypeProd
    def _type(r): return (r.get("type_prod", "") or "").upper()
    oen_gaz = [r for r in oen if _type(r) == "GAZ"]
    oen_elec = [r for r in oen if _type(r) == "ELEC"]
    oen_dual = [r for r in oen if _type(r) not in ("GAZ", "ELEC")]

    # Coefficient par PDL : mono = 1, dual = 0.5 (un dual = 1 contrat pour 2 PDL)
    # On reproduit la logique WinDev StatsOEN où tous les compteurs incluent ce coeff.
    def _coeff(r) -> float:
        return 0.5 if _type(r) not in ("GAZ", "ELEC") else 1.0

    # Nb Ctt = somme des coeffs (dual compte pour 0.5)
    nb_ctt = sum(_coeff(r) for r in oen)
    nb_ctt_mono_gaz = len(oen_gaz)
    nb_ctt_mono_elec = len(oen_elec)
    nb_ctt_dual = len(oen_dual) * 0.5

    # Compteurs d'états appliquant le même coefficient
    nb_anomalie = sum(_coeff(r) for r in oen if r.get("id_type_etat") == 3)
    nb_valide = sum(_coeff(r) for r in oen if r.get("id_type_etat") in (5, 8))
    nb_valide_ope = sum(_coeff(r) for r in oen if r.get("id_type_etat_ope") in (5, 8))
    nb_resil = sum(_coeff(r) for r in oen if r.get("id_type_etat") == 4)
    nb_attente = sum(_coeff(r) for r in oen if r.get("id_type_etat") == 2)
    nb_stand_by = sum(_coeff(r) for r in oen if r.get("id_type_etat") in (1, 9))
    nb_hors_anomalie = nb_ctt - nb_anomalie

    # Règle OEN (sur Lib_produit) :
    #  - contrat avec part Gaz  : Lib_produit contient "gaz"  (mono Gaz + Dual)
    #  - contrat avec part Elec : Lib_produit contient "elec" OU pas "gaz" (mono Elec + Dual)
    #  → un Dual compte dans les deux dénominateurs.
    def _has_gaz(r) -> bool:
        return "gaz" in (r.get("lib_produit") or "").lower()

    def _has_elec(r) -> bool:
        lib = (r.get("lib_produit") or "").lower()
        return "elec" in lib or "gaz" not in lib

    oen_gaz_part = [r for r in oen if _has_gaz(r)]
    oen_elec_part = [r for r in oen if _has_elec(r)]

    nb_gaz = len(oen_gaz_part)
    nb_elec = len(oen_elec_part)

    # Base = contrats avec car ≤ 1000 parmi ceux ayant une part Gaz
    nb_base = sum(
        1 for r in oen_gaz_part
        if (r.get("car") or 0) <= 1000
    )

    # 6kva+ = contrats avec puissance ≥ 6 parmi ceux ayant une part Elec
    nb_6kva = sum(
        1 for r in oen_elec_part
        if (r.get("puissance") or 0) >= 6
    )

    # Clients + consentement (cf. WinDev StatsOEN) :
    # Pour chaque contrat OEN dans l'ordre :
    #   - si NumBS présent dans TK_Call_Panier
    #   - si IDClient pas encore vu : on l'ajoute, on incrémente nb_consent
    #     **uniquement si** ce 1er contrat porte le consent (Opt_Partenaire)
    # → un client n'est compté qu'une fois, sur la base de son 1er contrat Call.
    seen_clients: set = set()
    nb_consent = 0
    for r in oen:
        if not r.get("in_tk_call_panier"):
            continue
        cid = r.get("id_client")
        if not cid or cid == "0":
            continue
        if cid in seen_clients:
            continue
        seen_clients.add(cid)
        if r.get("client_rap_part"):
            nb_consent += 1
    nb_clients = len(seen_clients)

    # Note moyenne
    noted = [r for r in oen if (r.get("notation") or 0) > 0]
    note_moy = (sum(r.get("notation", 0) for r in noted) / len(noted)) if noted else 0.0
    pct_notes = _pct(len(noted), nb_hors_anomalie if nb_hors_anomalie > 0 else 1)

    # Car moyenne sur le gaz (mono Gaz + Dual), anomalies incluses
    car_vals = [
        (r.get("car") or 0) for r in oen_gaz_part
        if (r.get("car") or 0) > 0
    ]
    car_moy = int(sum(car_vals) / len(car_vals)) if car_vals else 0

    # --- Tableau par vendeur (TableTxRaccVendeur OEN — équivalent WinDev)
    # Compteurs alimentés uniquement pour les vendeurs en activité.
    v_rows: dict[str, dict] = {}

    def _vrow(r: dict) -> dict | None:
        id_s = r.get("id_salarie") or "0"
        if id_s == "0":
            return None
        v = v_rows.get(id_s)
        if v is None:
            v = {
                "id_salarie": id_s,
                "nom": r.get("vendeur_nom", ""),
                "prenom": r.get("vendeur_prenom", ""),
                "agence": r.get("agence", ""),
                "equipe": r.get("equipe", ""),
                "en_activite": bool(r.get("en_activite", True)),
                # Compteurs en coeff (dual = 0.5)
                "nb_ctt": 0.0,
                "nb_anomalie": 0.0,
                "nb_resil": 0.0,
                "nb_dual": 0.0,
                # Compteurs PDL (1 par contrat — dual = 1 PDL Gaz + 1 PDL Elec)
                "nb_base": 0,             # car ≤ 1000 sur mono gaz + dual
                "nb_base_total": 0,       # nb Gaz (mono gaz + dual) — dénominateur
                "nb_6kva": 0,             # puissance ≥ 6 sur mono elec + dual
                "nb_6kva_total": 0,       # nb Elec (mono elec + dual) — dénominateur
                # Consentement par client unique
                "_clients_seen": set(),
                "_clients_consent": set(),
                "nb_clients": 0,
                "nb_consent": 0,
            }
            v_rows[id_s] = v
        return v if v["en_activite"] else None

    for r in oen:
        v = _vrow(r)
        if v is None:
            continue
        coeff = _coeff(r)
        v["nb_ctt"] += coeff
        id_te = r.get("id_type_etat") or 0
        if id_te == 3:
            v["nb_anomalie"] += coeff
        if id_te == 4:
            v["nb_resil"] += coeff
        tp = _type(r)
        is_dual = tp not in ("GAZ", "ELEC")
        if is_dual:
            v["nb_dual"] += 0.5
        # Base / 6Kva : un Dual compte dans Gaz ET dans Elec.
        # Détection sur Lib_produit (cf. règle OEN) :
        #   has_gaz  = lib contient "gaz"           (mono Gaz + Dual)
        #   has_elec = lib contient "elec" OU pas "gaz" (mono Elec + Dual)
        lib_prod = (r.get("lib_produit") or "").lower()
        has_gaz = "gaz" in lib_prod
        has_elec = ("elec" in lib_prod) or (not has_gaz)
        car = r.get("car") or 0
        puiss = r.get("puissance") or 0
        if has_gaz:
            v["nb_base_total"] += 1
            if car <= 1000:
                v["nb_base"] += 1
        if has_elec:
            v["nb_6kva_total"] += 1
            if puiss >= 6:
                v["nb_6kva"] += 1
        # Consentement par client unique (uniquement contrats dans
        # TK_Call_Panier — pas de filtre anomalie, cf. KPI global).
        # 1er contrat rencontré pour ce client → décide du consent.
        if r.get("in_tk_call_panier"):
            cid = r.get("id_client") or "0"
            if cid and cid != "0" and cid not in v["_clients_seen"]:
                v["_clients_seen"].add(cid)
                v["nb_clients"] += 1
                if r.get("client_rap_part"):
                    v["_clients_consent"].add(cid)
                    v["nb_consent"] += 1

    tx_racc_vendeur: list[dict] = []
    for v in v_rows.values():
        nb_hors_a = v["nb_ctt"] - v["nb_anomalie"]
        tx_racc_vendeur.append({
            "id_salarie": v["id_salarie"],
            "nom": v["nom"],
            "prenom": v["prenom"],
            "agence": v["agence"],
            "equipe": v["equipe"],
            "en_activite": v["en_activite"],
            "nb_ctt": round(v["nb_ctt"], 1),
            "nb_resil": round(v["nb_resil"], 1),
            "nb_dual": round(v["nb_dual"], 1),
            "nb_base": v["nb_base"],
            "nb_6kva": v["nb_6kva"],
            "nb_clients": v["nb_clients"],
            "nb_consent": v["nb_consent"],
            "tx_resil": _pct(v["nb_resil"], nb_hors_a) if nb_hors_a > 0 else 0.0,
            "tx_dual": _pct(v["nb_dual"], v["nb_ctt"]),
            "tx_base": _pct(v["nb_base"], v["nb_base_total"]),
            "tx_6kva": _pct(v["nb_6kva"], v["nb_6kva_total"]),
            "tx_consent": _pct(v["nb_consent"], v["nb_clients"]),
        })
    tx_racc_vendeur.sort(key=lambda x: (x["nom"].lower(), x["prenom"].lower()))

    return {
        "nb_pdl_brut": nb_pdl_brut,
        "nb_ctt": round(nb_ctt, 1),
        "nb_ctt_mono_gaz": nb_ctt_mono_gaz,
        "nb_ctt_mono_elec": nb_ctt_mono_elec,
        "nb_ctt_dual": round(nb_ctt_dual, 1),  # déjà divisé par 2
        "nb_hors_anomalie": round(nb_hors_anomalie, 1),
        "nb_anomalie": round(nb_anomalie, 1),
        "nb_valide": round(nb_valide, 1),
        "nb_valide_ope": round(nb_valide_ope, 1),
        "nb_resil": round(nb_resil, 1),
        "nb_attente": round(nb_attente, 1),
        "nb_stand_by": round(nb_stand_by, 1),
        "nb_base": nb_base,
        "nb_6kva": nb_6kva,
        "tx_anomalie": _pct(nb_anomalie, nb_ctt),
        "tx_resil": _pct(nb_resil, nb_hors_anomalie) if nb_hors_anomalie > 0 else 0.0,
        "tx_valide": _pct(nb_valide, nb_hors_anomalie) if nb_hors_anomalie > 0 else 0.0,
        "tx_valide_ope": _pct(nb_valide_ope, nb_hors_anomalie) if nb_hors_anomalie > 0 else 0.0,
        "tx_attente": _pct(nb_attente, nb_ctt),
        "tx_dual": _pct(nb_ctt_dual, nb_ctt),
        "tx_base": _pct(nb_base, nb_gaz),
        "tx_6kva": _pct(nb_6kva, nb_elec),
        "nb_consent": nb_consent,
        "nb_clients": nb_clients,
        "tx_consent": _pct(nb_consent, nb_clients),
        "note_moy": round(note_moy, 2),
        "pct_notes": pct_notes,
        "car_moy": car_moy,
        "tx_racc_vendeur": tx_racc_vendeur,
    }


def _compute_dashboard_eni(rows: list[dict]) -> dict:
    """
    Dashboard ENI — miroir OEN, sans coefficient (1 ligne = 1 contrat).

    Type ENI : "GAZ" / "ELEC" / "GAZ-ELEC" (= mono Gaz / mono Elec / Dual).
    """
    eni = [r for r in rows if r.get("partenaire") == "ENI"]
    if not eni:
        return {}

    def _type(r): return (r.get("type_prod", "") or "").upper()

    def _has_gaz(r) -> bool:
        return _type(r) in ("GAZ", "GAZ-ELEC")

    def _has_elec(r) -> bool:
        return _type(r) in ("ELEC", "GAZ-ELEC")

    def _is_dual(r) -> bool:
        return _type(r) == "GAZ-ELEC"

    eni_gaz_part = [r for r in eni if _has_gaz(r)]
    eni_elec_part = [r for r in eni if _has_elec(r)]
    eni_dual = [r for r in eni if _is_dual(r)]

    nb_pdl_brut = len(eni)
    nb_ctt = len(eni)                 # pas de coeff pour ENI
    nb_ctt_dual = len(eni_dual)
    nb_gaz = len(eni_gaz_part)
    nb_elec = len(eni_elec_part)

    # Compteurs d'états (1 par ligne, pas de coeff)
    nb_anomalie = sum(1 for r in eni if r.get("id_type_etat") == 3)
    nb_valide = sum(1 for r in eni if r.get("id_type_etat") in (5, 8))
    nb_resil = sum(1 for r in eni if r.get("id_type_etat") == 4)
    nb_attente = sum(1 for r in eni if r.get("id_type_etat") == 2)
    nb_stand_by = sum(1 for r in eni if r.get("id_type_etat") in (1, 9))
    nb_hors_anomalie = nb_ctt - nb_anomalie

    # Base = contrats avec car ≤ 1000 parmi ceux ayant une part Gaz
    nb_base = sum(
        1 for r in eni_gaz_part
        if (r.get("car") or 0) <= 1000
    )

    # 6kva+ = contrats avec puissance ≥ 6 parmi les Elec
    nb_6kva = sum(
        1 for r in eni_elec_part
        if (r.get("puissance") or 0) >= 6
    )

    # Clients + consentement (cf. OEN) : itère dans l'ordre, NumBS dans
    # TK_Call_Panier obligatoire, 1er contrat décide du consent. Pas de
    # filtre anomalie.
    seen_clients: set = set()
    nb_consent = 0
    for r in eni:
        if not r.get("in_tk_call_panier"):
            continue
        cid = r.get("id_client")
        if not cid or cid == "0":
            continue
        if cid in seen_clients:
            continue
        seen_clients.add(cid)
        if r.get("client_rap_part"):
            nb_consent += 1
    nb_clients = len(seen_clients)

    # Note moyenne
    noted = [r for r in eni if (r.get("notation") or 0) > 0]
    note_moy = (sum(r.get("notation", 0) for r in noted) / len(noted)) if noted else 0.0
    pct_notes = _pct(len(noted), nb_hors_anomalie if nb_hors_anomalie > 0 else 1)

    # Car moyenne sur le gaz (mono Gaz + Dual), anomalies incluses
    car_vals = [
        (r.get("car") or 0) for r in eni_gaz_part
        if (r.get("car") or 0) > 0
    ]
    car_moy = int(sum(car_vals) / len(car_vals)) if car_vals else 0

    # Options (gardées car spécifiques ENI)
    nb_demat = sum(1 for r in eni if r.get("opt_demat"))
    nb_maintenance = sum(1 for r in eni if r.get("opt_maintenance"))
    nb_energie_verte = sum(1 for r in eni if r.get("opt_energie_verte_gaz"))
    nb_reforestation = sum(1 for r in eni if r.get("opt_reforestation"))
    nb_protection = sum(1 for r in eni if r.get("opt_protection"))

    # --- Tableau par vendeur (miroir OEN, sans coeff)
    v_rows: dict[str, dict] = {}

    def _vrow(r: dict) -> dict | None:
        id_s = r.get("id_salarie") or "0"
        if id_s == "0":
            return None
        v = v_rows.get(id_s)
        if v is None:
            v = {
                "id_salarie": id_s,
                "nom": r.get("vendeur_nom", ""),
                "prenom": r.get("vendeur_prenom", ""),
                "agence": r.get("agence", ""),
                "equipe": r.get("equipe", ""),
                "en_activite": bool(r.get("en_activite", True)),
                "nb_ctt": 0, "nb_anomalie": 0, "nb_resil": 0, "nb_dual": 0,
                "nb_base": 0, "nb_base_total": 0,
                "nb_6kva": 0, "nb_6kva_total": 0,
                "_clients_seen": set(),
                "_clients_consent": set(),
                "nb_clients": 0, "nb_consent": 0,
            }
            v_rows[id_s] = v
        return v if v["en_activite"] else None

    for r in eni:
        v = _vrow(r)
        if v is None:
            continue
        v["nb_ctt"] += 1
        id_te = r.get("id_type_etat") or 0
        if id_te == 3:
            v["nb_anomalie"] += 1
        if id_te == 4:
            v["nb_resil"] += 1
        if _is_dual(r):
            v["nb_dual"] += 1
        car = r.get("car") or 0
        puiss = r.get("puissance") or 0
        if _has_gaz(r):
            v["nb_base_total"] += 1
            if car <= 1000:
                v["nb_base"] += 1
        if _has_elec(r):
            v["nb_6kva_total"] += 1
            if puiss >= 6:
                v["nb_6kva"] += 1
        # Consentement : 1er contrat dans TK_Call_Panier décide
        if r.get("in_tk_call_panier"):
            cid = r.get("id_client") or "0"
            if cid and cid != "0" and cid not in v["_clients_seen"]:
                v["_clients_seen"].add(cid)
                v["nb_clients"] += 1
                if r.get("client_rap_part"):
                    v["_clients_consent"].add(cid)
                    v["nb_consent"] += 1

    tx_racc_vendeur: list[dict] = []
    for v in v_rows.values():
        nb_hors_a = v["nb_ctt"] - v["nb_anomalie"]
        tx_racc_vendeur.append({
            "id_salarie": v["id_salarie"],
            "nom": v["nom"],
            "prenom": v["prenom"],
            "agence": v["agence"],
            "equipe": v["equipe"],
            "en_activite": v["en_activite"],
            "nb_ctt": v["nb_ctt"],
            "nb_resil": v["nb_resil"],
            "nb_dual": v["nb_dual"],
            "nb_base": v["nb_base"],
            "nb_6kva": v["nb_6kva"],
            "nb_clients": v["nb_clients"],
            "nb_consent": v["nb_consent"],
            "tx_resil": _pct(v["nb_resil"], nb_hors_a) if nb_hors_a > 0 else 0.0,
            "tx_dual": _pct(v["nb_dual"], v["nb_ctt"]),
            "tx_base": _pct(v["nb_base"], v["nb_base_total"]),
            "tx_6kva": _pct(v["nb_6kva"], v["nb_6kva_total"]),
            "tx_consent": _pct(v["nb_consent"], v["nb_clients"]),
        })
    tx_racc_vendeur.sort(key=lambda x: (x["nom"].lower(), x["prenom"].lower()))

    return {
        "nb_pdl_brut": nb_pdl_brut,
        "nb_ctt": nb_ctt,
        "nb_ctt_dual": nb_ctt_dual,
        "nb_hors_anomalie": nb_hors_anomalie,
        "nb_anomalie": nb_anomalie,
        "nb_valide": nb_valide,
        "nb_resil": nb_resil,
        "nb_attente": nb_attente,
        "nb_stand_by": nb_stand_by,
        "nb_base": nb_base,
        "nb_6kva": nb_6kva,
        "tx_anomalie": _pct(nb_anomalie, nb_ctt),
        "tx_resil": _pct(nb_resil, nb_hors_anomalie) if nb_hors_anomalie > 0 else 0.0,
        "tx_valide": _pct(nb_valide, nb_hors_anomalie) if nb_hors_anomalie > 0 else 0.0,
        "tx_attente": _pct(nb_attente, nb_ctt),
        "tx_dual": _pct(nb_ctt_dual, nb_ctt),
        "tx_base": _pct(nb_base, nb_gaz),
        "tx_6kva": _pct(nb_6kva, nb_elec),
        "nb_consent": nb_consent,
        "nb_clients": nb_clients,
        "tx_consent": _pct(nb_consent, nb_clients),
        "note_moy": round(note_moy, 2),
        "pct_notes": pct_notes,
        "car_moy": car_moy,
        # Options ENI (gardées)
        "nb_demat": nb_demat,
        "nb_maintenance": nb_maintenance,
        "nb_energie_verte": nb_energie_verte,
        "nb_reforestation": nb_reforestation,
        "nb_protection": nb_protection,
        "tx_demat": _pct(nb_demat, nb_ctt),
        "tx_maintenance": _pct(nb_maintenance, nb_ctt),
        "tx_energie_verte": _pct(nb_energie_verte, nb_ctt),
        "tx_reforestation": _pct(nb_reforestation, nb_ctt),
        "tx_protection": _pct(nb_protection, nb_ctt),
        "tx_racc_vendeur": tx_racc_vendeur,
    }


def _meta_path(id_user: int, id_job: int) -> Path:
    return PRODUCTION_EXTRACTS_DIR / str(id_user) / f"{id_job}.meta.json"


def read_job_stats(id_user: int, id_job: int) -> dict:
    """Lit le meta.json des stats précalculées d'un job."""
    _empty = {
        "total_contrats": 0, "total_paye": 0, "total_points": 0,
        "repart_partenaires": [], "vendeurs": [],
        "dashboard_sfr": {}, "dashboard_oen": {}, "dashboard_eni": {},
    }
    p = _meta_path(id_user, id_job)
    if not p.exists():
        return _empty
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Backfill des champs nouveaux pour les jobs anciens
        for k, v in _empty.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return _empty


def _parquet_path(id_user: int, id_job: int) -> Path:
    return PRODUCTION_EXTRACTS_DIR / str(id_user) / f"{id_job}.parquet"


# ================================================================
# Lecture paginée du résultat (pour l'API)
# ================================================================

# Ordre + libellés français pour l'export CSV (mirroir du tableau frontend
# = Excel WinDev "Extraction"). La clé "conso_gaz" est virtuelle, calculée à la volée.
EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("vendeur_nom",          "Vendeur Nom"),
    ("vendeur_prenom",       "Vendeur Prénom"),
    ("num_bs",               "Num BS"),
    ("partenaire",           "Partenaire"),
    ("lib_produit",          "Produit"),
    ("type_prod",            "Type Prod"),
    ("sfr_type_vente",       "Type vente"),
    ("date_signature",       "Date Signature"),
    ("sfr_date_rdv_tech",    "Date RDV Tech"),
    ("sfr_date_racc_activ",  "Date Racc / Activation"),
    ("lib_type_etat",        "Type Etat"),
    ("lib_etat_vend",        "Etat contrat"),
    ("lib_type_etat_ope",    "Type Etat Opérateur"),
    ("lib_etat_ope",         "Etat Opérateur"),
    ("sfr_cluster_nom",      "Cluster Nom"),
    ("poste",                "Poste"),
    ("date_embauche",        "Date Embauche"),
    ("en_activite",          "En activité"),
    ("date_sortie",          "Date Sortie"),
    ("agence",               "Agence"),
    ("equipe",               "Equipe"),
    ("client_nom",           "Client Nom"),
    ("client_prenom",        "Client Prénom"),
    ("client_adresse1",      "Client Adr"),
    ("client_adresse2",      "Client Cplt Adr"),
    ("client_cp",            "CP"),
    ("client_ville",         "Ville"),
    ("client_mail",          "Mail"),
    ("client_mobile",        "Mobile"),
    ("client_rap_part",      "Recueil consentement"),
    ("in_tk_call_panier",    "Call TK"),
    ("opt_num",              "Opt Numérique"),
    ("mois_p",               "Mois Paiement"),
    ("sfr_mois_p_distrib",   "Mois Paiement Distrib"),
    ("nb_points",            "NB Points"),
    ("info_partagee",        "Infos Contrats"),
    ("gaz_actif",            "Gaz Actif"),
    ("elec_actif",           "Elec Actif"),
    ("conso_gaz",            "ConsoGaz"),
    ("car",                  "Car (KWh)"),
    ("puissance",            "Puissance"),
    ("opt_demat",            "OPT Démat"),
    ("opt_maintenance",      "OPT Maintenance"),
    ("opt_energie_verte_gaz","OPT Energie Verte Gaz"),
    ("opt_reforestation",    "OPT Reforestation"),
    ("opt_protection",       "OPT Protection"),
    ("sfr_portabilite",      "Portabilité"),
    ("sfr_date_portab",      "Date Portabilité"),
    ("sfr_date_resil",       "Date Résil"),
    ("sfr_internet_garanti", "Internet Garanti"),
    ("sfr_offre_speciale",   "Offre Spéciale"),
    ("sfr_parcours_chaine",  "Parcours Chainés"),
    ("sfr_prise_existante",  "Prise Existante"),
    ("sfr_num_prise_sfr",    "Num prise SFR"),
    ("sfr_num_prise_vend",   "Num prise vendeur"),
    ("heure_sign",           "Heure Signature"),
    ("notation",             "Note / 5"),
    ("notation_info",        "Notation Info"),
]


def _conso_gaz(car) -> str:
    """ConsoGaz calculée depuis Car (cf. consoGaz frontend / WinDev StatsENI)."""
    try:
        c = int(car or 0)
    except (TypeError, ValueError):
        return ""
    if c <= 0:
        return ""
    if c <= 1000:
        return "Base"
    if c <= 6000:
        return "B0"
    if c <= 30000:
        return "B1"
    return "B2i"


def _date_fr(iso: str) -> str:
    """ISO YYYY-MM-DD → dd/mm/yyyy (vide si invalide)."""
    s = str(iso or "")
    if len(s) < 10 or s[4] != "-" or s[7] != "-":
        return ""
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"


def _mois_fr(iso: str) -> str:
    """ISO YYYY-MM-DD → mm/yyyy (vide si invalide)."""
    s = str(iso or "")
    if len(s) < 7 or s[4] != "-":
        return ""
    return f"{s[5:7]}/{s[0:4]}"


# Colonnes à reformater pour Excel FR
_DATE_COLS = {
    "date_signature", "date_embauche", "date_sortie",
    "sfr_date_rdv_tech", "sfr_date_racc_activ", "sfr_date_portab",
    "sfr_date_resil",
}
_MOIS_COLS = {"mois_p", "sfr_mois_p_distrib"}


# Libellés des codes SFR_contrat.TypeVente (cf. WinDev)
SFR_TYPE_VENTE_LABELS = {
    1: "Conquête",
    2: "Conquête VLA",
    3: "Migration",
    4: "Migration FTTB -> FTTH",
}


def csv_value(row: dict, key: str):
    """Formate une valeur pour le CSV : dates fr, booléens 0/1, ConsoGaz calculée."""
    if key == "conso_gaz":
        return _conso_gaz(row.get("car", 0))
    v = row.get(key, "")
    if v is None or (isinstance(v, float) and v != v):  # NaN
        return ""
    if key == "sfr_type_vente":
        if row.get("partenaire") != "SFR":
            return ""
        try:
            return SFR_TYPE_VENTE_LABELS.get(int(v), "")
        except (TypeError, ValueError):
            return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if key in _DATE_COLS:
        return _date_fr(v)
    if key in _MOIS_COLS:
        return _mois_fr(v)
    return v


# Matrice de censure : droit requis -> colonnes à masquer si droit absent.
# Cf. Fen_suiviProdAsynchrone WinDev (visibilité des colonnes TableContrat).
CENSOR_RULES = {
    "InfoClientCoord": [
        "client_adresse1", "client_adresse2", "client_mail", "client_mobile",
        "sfr_num_prise_sfr", "sfr_num_prise_vend",
    ],
    "ProdRezo": ["id_type_etat_ope", "lib_type_etat_ope", "lib_etat_ope"],
    "InfoNotation": ["notation", "notation_info"],
    "InfoPaieDistrib": ["sfr_mois_p_distrib"],
}


def _apply_censorship(rows: list[dict], droits: list[str]) -> list[dict]:
    """
    Applique la censure à une liste de rows selon les droits de l'utilisateur :
    - Les colonnes listées dans CENSOR_RULES sont vidées si le droit est absent.
    - Si droit InfoClientNom absent, le nom/prénom client est tronqué à 3 chars.
    """
    droits_set = set(droits or [])

    # Colonnes à vider
    cols_to_empty: set[str] = set()
    for droit, cols in CENSOR_RULES.items():
        if droit not in droits_set:
            cols_to_empty.update(cols)

    censure_nom = "InfoClientNom" not in droits_set

    for r in rows:
        for col in cols_to_empty:
            if col not in r:
                continue
            v = r[col]
            if isinstance(v, bool):
                r[col] = False
            elif isinstance(v, (int, float)):
                r[col] = 0
            else:
                r[col] = ""
        if censure_nom:
            nom = str(r.get("client_nom", ""))
            prenom = str(r.get("client_prenom", ""))
            r["client_nom"] = (nom[:3] + ".") if nom else ""
            r["client_prenom"] = (prenom[:3] + ".") if prenom else ""
    return rows


def read_contrats_page(
    path: str,
    page: int = 1,
    page_size: int = 50,
    sort: str = "",
    filters: dict | None = None,
    droits: list[str] | None = None,
) -> dict:
    """
    Lit un fichier Parquet et retourne une page de résultats filtrés/triés.
    filters : dict {col: value} - pour un filtre texte, match contient (insensible casse)
                 pour les colonnes numériques, match exact
    droits  : liste des codes internes de droits de l'utilisateur, pour la censure.
    """
    import pandas as pd

    p = Path(path)
    if not p.exists():
        return {"total": 0, "page": page, "page_size": page_size, "rows": []}

    df = pd.read_parquet(p)
    if df.empty:
        return {"total": 0, "page": page, "page_size": page_size, "rows": []}

    # Filtres
    if filters:
        for col, val in filters.items():
            if col not in df.columns or val in (None, ""):
                continue
            series = df[col]
            if series.dtype == object:
                df = df[series.astype(str).str.contains(str(val), case=False, na=False)]
            else:
                try:
                    df = df[series == type(series.iloc[0])(val)]
                except Exception:
                    pass

    total = len(df)

    # Tri
    if sort:
        desc = sort.startswith("-")
        col = sort[1:] if desc else sort
        if col in df.columns:
            df = df.sort_values(col, ascending=not desc, na_position="last")

    # Pagination
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    page_df = df.iloc[start:end]

    rows = page_df.to_dict(orient="records")
    # Nettoyer les NaN pour la sérialisation JSON
    for r in rows:
        for k, v in list(r.items()):
            if v is None or (isinstance(v, float) and v != v):  # NaN check
                r[k] = "" if isinstance(v, str) or v is None else 0

    # Censure selon les droits du user
    _apply_censorship(rows, droits or [])

    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "rows": rows,
    }
