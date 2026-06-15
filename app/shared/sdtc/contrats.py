"""
SDTC - chargement et dispatch des contrats du salarié (afficherContrat).

Transposition de la procédure WinDev `afficherContrat()` de Fen_SDTC.
Pour chaque partenaire actif :
  1. Charge les contrats du salarié (cross-table jointures produit/etat/client)
  2. Pour SFR : `DonneFamProdSFR(famille, type_vente)` -> FamSFR pour le bareme
  3. Recalcule `nb_points` via `calcul_point_contrat()` (fidèle WinDev)
  4. UPDATE en base si différent (cf. WinDev `si MonCtt.nbPoints <> nbpt`)
  5. Dispatch en 2 listes :
     - traités : IDTypeEtat ∈ {1,3,4,6} OU (5 + MoisP non vide)
     - à traiter : tous les autres
  6. Enrichit avec colonnes spécifiques SFR (Box8, Cluster, dates) et
     options ENI (RIB/MAIL/...)
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.database.pg import get_pg_connection

from .bareme import calcul_point_contrat
from .helpers import (
    _capitalize,
    _int,
    _iso,
    _num,
    _str,
    _winrgb_to_hex,
    _yyyymm,
    donne_fam_prod_sfr,
)


# Cf. WinDev test ligne ~144 : 1=Temporaire, 3=Rejet, 4=Anomalie,
# 6=Décommission, 5=Validé/Payé (si MoisP rempli).
_TYPES_ETATS_FINALISES = {1, 3, 4, 6}


def load_contrats(id_salarie: int) -> dict:
    """Charge l'ensemble des contrats du salarié + recalcule nb_points.

    Retourne :
      {
        "traites":   list[dict]  # IDTypeEtat ∈ {1,3,4,6} ou (5 + MoisP)
        "a_traiter": list[dict]
        "type_etats": {id_type_etat: {lib_type, couleur}}
      }
    """
    db_adv = get_pg_connection("adv")

    # 1) Partenaires actifs (prefixe_bdd alphabetique)
    parts = db_adv.query(
        """SELECT prefixe_bdd FROM adv.pgt_partenaire
            WHERE is_actif = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND COALESCE(prefixe_bdd, '') <> ''"""
    )
    prefixes = sorted({_str(p.get("prefixe_bdd")).strip() for p in (parts or [])})
    prefixes = [p for p in prefixes if p]

    # 2) Type d'etat (couleurs + lib_type)
    type_etat_rows = db_adv.query(
        """SELECT id_type_etat, lib_type, couleur_r, couleur_v, couleur_b
             FROM adv.pgt_type_etat_contrat
            WHERE modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%'"""
    )
    type_etat_map: dict[int, dict] = {}
    for r in type_etat_rows or []:
        tid = _int(r.get("id_type_etat"))
        type_etat_map[tid] = {
            "lib_type": _str(r.get("lib_type")),
            "couleur": _winrgb_to_hex(
                r.get("couleur_r"), r.get("couleur_v"), r.get("couleur_b")
            ),
        }

    # 3) Chargement parallèle par partenaire
    def fetch(prefix: str) -> list[dict]:
        lp = prefix.lower()
        db = get_pg_connection("adv")
        # Cf. WinDev (MaFenetre Fen_SDTC) : pour SFR, le mois de paiement
        # de reference est mois_p_ra (Raccordement). Pour les autres
        # partenaires, c'est mois_p.
        mois_p_col = "c.mois_p_ra" if lp == "sfr" else "c.mois_p"
        try:
            return db.query(
                f"""SELECT
                    c.id_contrat, c.id_salarie, c.num_bs, c.info_interne,
                    c.id_produit, c.id_etat_contrat, c.date_signature,
                    c.nb_points, {mois_p_col} AS mois_p,
                    cl.nom AS client_nom, cl.prenom AS client_prenom,
                    cl.adresse1 AS client_adresse, cl.cp AS client_cp,
                    cl.ville AS client_ville, cl.mail AS client_mail,
                    cl.gsm AS client_gsm,
                    p.lib_produit, p.famille, p.sous_fam,
                    e.id_etat AS e_id_etat, e.lib_etat, e.lib_etat_vend,
                    e.id_type_etat
                FROM adv.pgt_{lp}_contrat c
                LEFT JOIN adv.pgt_{lp}_produit p ON p.id_produit = c.id_produit
                LEFT JOIN adv.pgt_{lp}_etat_contrat e ON e.id_etat = c.id_etat_contrat
                LEFT JOIN adv.pgt_client cl ON cl.id_client = c.id_client
                WHERE c.id_salarie = ?
                  AND (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
                ORDER BY c.date_signature DESC""",
                (int(id_salarie),),
            )
        except Exception as e:
            import sys
            import traceback
            print(
                f"[SDTC contrats] Echec partenaire {prefix}: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            return []

    rows_by_prefix: dict[str, list[dict]] = {}
    if prefixes:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for prefix, rows in zip(prefixes, pool.map(fetch, prefixes)):
                if rows:
                    rows_by_prefix[prefix] = rows

    traites: list[dict] = []
    a_traiter: list[dict] = []

    for prefix, rows in rows_by_prefix.items():
        part = prefix.upper()
        # Pré-charge des colonnes spécifiques (SFR + ENI + OEN)
        contrats_ids = [_int(r.get("id_contrat")) for r in rows]
        sfr_extra = _load_sfr_extra(contrats_ids) if part == "SFR" else {}
        eni_extra = _load_eni_extra(contrats_ids) if part == "ENI" else {}
        oen_extra = _load_oen_extra(contrats_ids) if part == "OEN" else {}

        for r in rows:
            id_contrat = _int(r.get("id_contrat"))
            id_type_etat = _int(r.get("id_type_etat"))
            mois_p_raw = r.get("mois_p")
            mois_p_iso = _yyyymm(mois_p_raw)
            te_meta = type_etat_map.get(id_type_etat, {})
            type_etat_lib = te_meta.get("lib_type", "")

            famille = _str(r.get("famille"))
            sous_fam = _str(r.get("sous_fam"))
            type_prod = sous_fam if (part == "ENI" and sous_fam) else famille

            lib_etat = _str(r.get("lib_etat_vend")) or _str(r.get("lib_etat"))

            client_nom = (
                f"{_str(r.get('client_nom'))} {_capitalize(_str(r.get('client_prenom')))}"
            ).strip()

            # ----- Spécifique SFR -----
            sfr_data = sfr_extra.get(id_contrat, {})
            sfr_pack = {
                "box8": bool(sfr_data.get("box8")),
                "box8_verif": bool(sfr_data.get("box8_verif")),
                "id_sfr_cluster": _str(sfr_data.get("id_sfr_cluster")),
                "date_portabilite": _iso(sfr_data.get("date_portabilite")),
                "date_racc_activ": _iso(sfr_data.get("date_racc_activ")),
                "date_rdv_tech": _iso(sfr_data.get("date_rdv_tech")),
                "date_resil": _iso(sfr_data.get("date_resil")),
                "date_validation": _iso(sfr_data.get("date_validation")),
                "id_etat_sfr": _int(sfr_data.get("id_etat_sfr")),
                "internet_garanti": bool(sfr_data.get("internet_garanti")),
                "type_vente": _int(sfr_data.get("type_vente")),
                "remise": bool(sfr_data.get("remise")),
                "self_install": bool(sfr_data.get("self_install")),
                "technologie": _int(sfr_data.get("technologie")),
            } if part == "SFR" else {}

            # ----- Spécifique ENI -----
            eni_data = eni_extra.get(id_contrat, {})
            eni_pack = {
                "gaz_car_declaree": _int(eni_data.get("gaz_car_declaree")),
                "gaz_car_relevee": _int(eni_data.get("gaz_car_relevee")),
                "elec_puissance": _int(eni_data.get("elec_puissance")),
                "gaz_actif": bool(eni_data.get("gaz_actif")),
                "elec_actif": bool(eni_data.get("elec_actif")),
            } if part == "ENI" else {}

            # ----- Spécifique OEN -----
            oen_data = oen_extra.get(id_contrat, {})
            oen_pack = {
                "gaz_car_relevee": _int(oen_data.get("gaz_car_relevee")),
                "elec_puissance": _int(oen_data.get("elec_puissance")),
                "id_etat_oen": _int(oen_data.get("id_etat_oen")),
            } if part == "OEN" else {}

            # ----- Calcul nb_points fidèle WinDev (defensif : fallback
            # sur la valeur stockee si le recalcul plante) -----
            nb_points_actuels = _num(r.get("nb_points"))
            date_sign = _iso(r.get("date_signature"))
            nb_points = nb_points_actuels
            try:
                nb_points_calcules = _recalcul_nb_points(
                    part=part,
                    fam=famille,
                    ss_fam=sous_fam,
                    date_sign=date_sign,
                    num_bs=_str(r.get("num_bs")),
                    lib_produit=_str(r.get("lib_produit")),
                    id_contrat=id_contrat,
                    sfr_extra=sfr_data,
                    eni_extra=eni_data,
                    oen_extra=oen_data,
                )
                if abs(nb_points_calcules - nb_points_actuels) > 0.001:
                    try:
                        _update_nb_points(part, id_contrat, nb_points_calcules)
                    except Exception:
                        pass  # lecture-seule autorisee
                nb_points = nb_points_calcules
            except Exception as e:
                import sys
                print(
                    f"[SDTC] Recalcul nb_points KO ({part} {id_contrat}): "
                    f"{type(e).__name__}: {e}",
                    file=sys.stderr,
                )

            item = {
                "id_contrat": str(id_contrat),
                "partenaire": part,
                "num_bs": _str(r.get("num_bs")),
                "info_interne": _str(r.get("info_interne")),
                "lib_produit": _str(r.get("lib_produit")),
                "famille": famille,
                "sous_fam": sous_fam,
                "type_prod": type_prod,
                "date_signature": date_sign,
                "mois_paiement": mois_p_iso,
                "id_etat_contrat": _int(r.get("id_etat_contrat")),
                "etat_contrat_lib": lib_etat,
                "etat_contrat_lib_op": _str(r.get("lib_etat")),
                "id_type_etat": id_type_etat,
                "type_etat_lib": type_etat_lib,
                "couleur_fond": te_meta.get("couleur", "#FFFFFF"),
                "nb_points": nb_points,
                "client_nom": client_nom,
                "client_adresse": _str(r.get("client_adresse")),
                "client_cp": _str(r.get("client_cp")),
                "client_ville": _str(r.get("client_ville")),
                "client_mail": _str(r.get("client_mail")),
                "client_gsm": _str(r.get("client_gsm")),
            }
            if sfr_pack:
                item["sfr"] = sfr_pack
            if eni_pack:
                item["eni"] = eni_pack
            if oen_pack:
                item["oen"] = oen_pack

            # Dispatch traites vs a_traiter (cf. WinDev IDTypeEtat in {1,3,4,6}
            # ou (5 et MoisP <> '')).
            in_finalises = id_type_etat in _TYPES_ETATS_FINALISES
            est_valide_paye = (id_type_etat == 5 and bool(mois_p_iso))
            if in_finalises or est_valide_paye:
                # Cf. WinDev : masquer mois_paiement pour Tempo/Rejet/Anomalie/
                # En Attente Op (cf. test "si MonCtt.IDTypeEtat = 3 ou 4 ou
                # 1 ou 7 alors TableContrat.Mois_Paiement = ''").
                if id_type_etat in (1, 3, 4, 7):
                    item["mois_paiement"] = ""
                traites.append(item)
            else:
                a_traiter.append(item)

    # Agregats pour l'onglet Resume (cf. WinDev TableEtat + TableValideDecomm)
    table_etat: dict[str, int] = {}
    table_vd: dict[tuple[str, str], dict] = {}
    for item in traites + a_traiter:
        lib_type = item.get("type_etat_lib") or ""
        table_etat[lib_type] = table_etat.get(lib_type, 0) + 1
        # TableValideDecomm : uniquement pour Valide-Paye (5) et Decomm (6) avec mois_p
        id_te = item.get("id_type_etat") or 0
        if id_te not in (5, 6):
            continue
        mois_p = item.get("mois_paiement") or ""
        if not mois_p:
            continue
        # Format MM-AAAA cf. WinDev
        try:
            mois_aff = f"{mois_p[5:7]}-{mois_p[0:4]}" if len(mois_p) >= 7 else mois_p
        except Exception:
            mois_aff = mois_p
        partenaire = item.get("partenaire") or ""
        key = (mois_p, partenaire)
        cell = table_vd.get(key)
        if cell is None:
            cell = {
                "mois_p": mois_p,
                "mois_aff": mois_aff,
                "partenaire": partenaire,
                "valides": 0,
                "decomm": 0,
            }
            table_vd[key] = cell
        if id_te == 5:
            cell["valides"] += 1
        elif id_te == 6:
            cell["decomm"] += 1

    table_etat_rows = sorted(
        [{"lib_type": k, "qte": v} for k, v in table_etat.items() if k],
        key=lambda r: -r["qte"],
    )
    table_vd_rows = sorted(
        table_vd.values(),
        key=lambda r: (r["mois_p"], r["partenaire"]),
        reverse=True,
    )

    return {
        "traites": traites,
        "a_traiter": a_traiter,
        "type_etats": type_etat_map,
        "table_etat": table_etat_rows,
        "table_valide_decomm": table_vd_rows,
    }


# ---------------------------------------------------------------------------
# Recalcul nb_points + UPDATE (fidèle WinDev `MonCtt.nbPoints <> nbpt`)
# ---------------------------------------------------------------------------


def _recalcul_nb_points(
    *,
    part: str,
    fam: str,
    ss_fam: str,
    date_sign: str,
    num_bs: str,
    lib_produit: str,
    id_contrat: int,
    sfr_extra: dict,
    eni_extra: dict,
    oen_extra: dict,
) -> float:
    """Sélectionne les bons paramètres à passer à calcul_point_contrat selon
    le partenaire (cf. switch WinDev dans `MaProcedurePourChaqueEnregistrement`).
    """
    if part == "SFR":
        type_vente = _int(sfr_extra.get("type_vente"))
        fam_sfr = donne_fam_prod_sfr(fam, type_vente)
        # Fibre : info_cplt = id_contrat (pour bonus FIB CQ >= 20260201)
        # Autres : info_cplt = lib_produit
        if (fam or "").upper().startswith("FIBRE"):
            info_cplt = str(id_contrat)
        else:
            info_cplt = lib_produit
        date_eff = sfr_extra.get("date_racc_activ") or date_sign
        date_eff_iso = _iso(date_eff)
        # Si DateRaccActiv >= 20220201 : utilise cette date à la place
        if (
            date_eff_iso
            and date_eff_iso >= "2022-02-01"
            and sfr_extra.get("date_racc_activ")
        ):
            return calcul_point_contrat(fam_sfr, ss_fam, 0, date_eff_iso, "")
        return calcul_point_contrat(fam_sfr, ss_fam, 0, date_sign, info_cplt)

    if part == "ENI":
        # Car : gaz_car_relevee si > 0 sinon gaz_car_declaree
        car = (
            _int(eni_extra.get("gaz_car_relevee"))
            if _int(eni_extra.get("gaz_car_relevee")) > 0
            else _int(eni_extra.get("gaz_car_declaree"))
        )
        elec_puissance = _int(eni_extra.get("elec_puissance"))
        # nb_options + info options : chargés via _eni_options (TODO si besoin)
        info_cplt = "0"
        return calcul_point_contrat(fam, ss_fam, car, date_sign, info_cplt, elec_puissance)

    if part == "OEN":
        car = _int(oen_extra.get("gaz_car_relevee"))
        elec_puissance = _int(oen_extra.get("elec_puissance"))
        return calcul_point_contrat(fam, ss_fam, car, date_sign, "0", elec_puissance)

    # Autres partenaires (STR/VAL/IAG/TLC) : info_cplt = num_bs
    return calcul_point_contrat(fam, ss_fam, "", date_sign, num_bs)


def _update_nb_points(part: str, id_contrat: int, nb_points: float) -> None:
    """UPDATE adv.pgt_<part>_contrat SET nb_points = ?, modif_date = NOW()
    WHERE id_contrat = ?."""
    lp = part.lower()
    db = get_pg_connection("adv")
    db.execute(
        f"""UPDATE adv.pgt_{lp}_contrat
              SET nb_points = ?, modif_date = NOW()
            WHERE id_contrat = ?""",
        (float(nb_points), int(id_contrat)),
    )


# ---------------------------------------------------------------------------
# Préchargements par partenaire (colonnes spécifiques)
# ---------------------------------------------------------------------------


def _load_sfr_extra(ids: list[int]) -> dict[int, dict]:
    """Charge les colonnes spécifiques SFR par lot."""
    if not ids:
        return {}
    db = get_pg_connection("adv")
    placeholders = ",".join(["?"] * len(ids))
    rows = db.query(
        f"""SELECT id_contrat, box8, box8_verif, id_sfr_cluster,
                   date_portabilite, date_racc_activ, date_rdv_tech,
                   date_resil, date_validation, id_etat_sfr,
                   internet_garanti, type_vente, remise, self_install,
                   technologie
              FROM adv.pgt_sfr_contrat
             WHERE id_contrat IN ({placeholders})""",
        tuple(ids),
    )
    return {_int(r.get("id_contrat")): r for r in (rows or [])}


def _load_eni_extra(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    db = get_pg_connection("adv")
    placeholders = ",".join(["?"] * len(ids))
    rows = db.query(
        f"""SELECT id_contrat, gaz_car_declaree, gaz_car_relevee,
                   elec_puissance, gaz_actif, elec_actif
              FROM adv.pgt_eni_contrat
             WHERE id_contrat IN ({placeholders})""",
        tuple(ids),
    )
    return {_int(r.get("id_contrat")): r for r in (rows or [])}


def _load_oen_extra(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    db = get_pg_connection("adv")
    placeholders = ",".join(["?"] * len(ids))
    rows = db.query(
        f"""SELECT id_contrat, gaz_car_relevee, elec_puissance,
                   id_etat_oen
              FROM adv.pgt_oen_contrat
             WHERE id_contrat IN ({placeholders})""",
        tuple(ids),
    )
    return {_int(r.get("id_contrat")): r for r in (rows or [])}


# ---------------------------------------------------------------------------
# Helpers SFR : libellé TypeVente (utilisé pour Lib_Produit dans le récap)
# ---------------------------------------------------------------------------


_TYPE_VENTE_SFR_LIB = {
    1: "CQ",
    2: "CQ Premium",
    3: "MIG",
    4: "MIG Premium",
}


def lib_type_vente_sfr(type_vente: Any) -> str:
    return _TYPE_VENTE_SFR_LIB.get(_int(type_vente), "")
