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

def _load_salaries_info(db_rh, ids_salaries: set[int]) -> dict[int, dict]:
    """
    Charge les infos minimales (nom, prénom, poste, activité, date sortie)
    pour un batch de salariés.
    """
    if not ids_salaries:
        return {}
    ids_sql = ",".join(str(i) for i in ids_salaries if i)
    if not ids_sql:
        return {}

    rows = db_rh.query(
        f"""SELECT s.IDSalarie, s.Nom, s.Prenom,
            se.EnActivité, se.DateAncienneté, se.IdTypePoste,
            tp.Lib_Poste
        FROM salarie s
        INNER JOIN salarie_embauche se ON se.IDSalarie = s.IDSalarie
        LEFT JOIN TypePoste tp ON tp.IdTypePoste = se.IdTypePoste
        WHERE s.IDSalarie IN ({ids_sql})"""
    )
    out: dict[int, dict] = {}
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
    if inactifs:
        ids_sql_i = ",".join(str(i) for i in inactifs)
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


def _load_clients_info(db_adv, ids_clients: set[int]) -> dict[int, dict]:
    """Charge les infos client en batch (table client dans ADV)."""
    if not ids_clients:
        return {}
    ids_sql = ",".join(str(i) for i in ids_clients if i)
    if not ids_sql:
        return {}

    rows = db_adv.query(
        f"""SELECT IDclient, NOM, PRENOM, ADRESSE1, ADRESSE2, CP, VILLE,
            MAIL, GSM, TEL, DATENAISS, Opt_Partenaire
        FROM client
        WHERE IDclient IN ({ids_sql})"""
    )
    out: dict[int, dict] = {}
    today = date.today()
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
    Reprend exactement le pattern WinDev mais avec les préfixes substitués.
    """
    etat_filter = ""
    if id_type_etat and id_type_etat > 0:
        etat_filter = f" AND pe.IDTypeEtat = {int(id_type_etat)}"

    return f"""
SELECT
    pc.IDcontrat, pc.IDSalarie, pc.NumBS, pc.InfoInterne,
    pc.DateSAISIE, pc.IDproduit, pc.IDetatContrat,
    pc.DateSignature, pc.nbPoints, pc.IDclient,
    pc.Notation, pc.NotationInfo,
    pc.MoisP,
    pp.Lib_produit, pp.PréfixeBDD, pp.Famille, pp.SousFAM,
    pe.Lib_Etat, pe.IDTypeEtat, pe.Lib_EtatVend
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
            # Partenaire sans table = on ignore et on continue
            progress_cb(pct_start, f"⚠ {prefix} ignoré ({e})")
            continue

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

    for r in all_rows:
        prefix = r["_prefix"]
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

        rows_out.append({
            "id_contrat": str(_clean_id(_to_int(r.get("IDcontrat")))),
            "partenaire": prefix,
            "num_bs": num_bs,
            "date_signature": _iso(r.get("DateSignature")),
            "date_saisie": _iso(r.get("DateSAISIE")),
            "mois_p": _iso(r.get("MoisP")),
            "heure_sign": "",
            "lib_produit": r.get("Lib_produit") or "",
            "type_prod": type_prod,
            "id_type_etat": id_te,
            "lib_type_etat": te.get("lib", ""),
            "couleur_etat": te.get("couleur", ""),
            "lib_etat": r.get("Lib_Etat") or "",
            "lib_etat_vend": lib_etat_vend,
            "id_salarie": str(id_salarie),
            "vendeur_nom": sinfo.get("nom", ""),
            "vendeur_prenom": sinfo.get("prenom", ""),
            "agence": affect.get("agence", ""),
            "equipe": affect.get("equipe", ""),
            "poste": sinfo.get("poste", ""),
            "en_activite": sinfo.get("en_activite", True),
            "date_sortie": sinfo.get("date_sortie", ""),
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
            "nb_points": _to_int(r.get("nbPoints")),
            "notation": float(r.get("Notation") or 0),
            "notation_info": r.get("NotationInfo") or "",
            "info_interne": r.get("InfoInterne") or "",
            "info_partagee": "",
            "code_enr": "",
            "nb_ctt_brut": nb_ctt_brut,
            "nb_ctt_hors_rejet": nb_ctt_hors_rejet,
            "nb_ctt_paye": nb_ctt_paye,
        })

    # Étape 6 : écriture Parquet
    progress_cb(95, f"Écriture Parquet ({len(rows_out)} lignes)")
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

    duree_s = int(time.time() - t0)
    progress_cb(100, "Terminé")
    return {
        "path": str(out_path),
        "nb_lignes": len(rows_out),
        "duree_s": duree_s,
        "message_erreur": "",
    }


def _parquet_path(id_user: int, id_job: int) -> Path:
    return PRODUCTION_EXTRACTS_DIR / str(id_user) / f"{id_job}.parquet"


# ================================================================
# Lecture paginée du résultat (pour l'API)
# ================================================================

def read_contrats_page(
    path: str,
    page: int = 1,
    page_size: int = 50,
    sort: str = "",
    filters: dict | None = None,
) -> dict:
    """
    Lit un fichier Parquet et retourne une page de résultats filtrés/triés.
    filters : dict {col: value} - pour un filtre texte, match contient (insensible casse)
                 pour les colonnes numériques, match exact
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
    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "rows": rows,
    }
