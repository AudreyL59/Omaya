"""
SDTC : chargement des contrats du salarie (cross-partner).

Transposition de la procedure WinDev `afficherContrat()` de Fen_SDTC.
Charge les contrats de tous les partenaires actifs (pgt_partenaire), les
trie en 2 listes :
  - traites : id_type_etat in (1,3,4,6) ou (5 avec mois_paiement non vide)
  - a_traiter : tous les autres

Pour le MVP, on n'embarque pas toutes les options ENI/SFR/OEN (qui
demandent encore plus de requetes vers les tables pgt_*_contrat_option).
Si besoin, on ajoutera dans un commit dedie.
"""

from concurrent.futures import ThreadPoolExecutor

from app.core.database.pg import get_pg_connection


def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _str(v) -> str:
    return "" if v is None else str(v)


def _iso(v) -> str:
    if v is None:
        return ""
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _yyyymm(v) -> str:
    """Date / datetime / 'YYYYMMDD' -> 'YYYYMM' pour les mois de paiement."""
    if v is None or v == "":
        return ""
    s = str(v)
    if len(s) >= 7 and s[4] == "-":
        return s[:7]
    if len(s) >= 6 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}"
    return ""


def _winrgb_to_hex(r: int, g: int, b: int) -> str:
    """WinDev RVB(R,V,B) -> '#RRGGBB' (R/V/B en 0..255)."""
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def _capitalize(s: str) -> str:
    return s[0].upper() + s[1:].lower() if s else ""


# Mapping id_type_etat (cf. pgt_type_etat_contrat WinDev) :
# 1=Temporaire, 3=En Rejet, 4=Anomalie, 5=Valide-Paye, 6=Decommission,
# 7=En Attente operateur, 8=Raccorde/Active. La liste "traites" reproduit
# le test WinDev "IDTypeEtat = 3 ou 4 ou 1 ou 6 ou (5 et MoisP <> '')".
_TYPES_TRAITES = {1, 3, 4, 6}


def load_contrats(id_salarie: int) -> dict:
    """Charge l'ensemble des contrats du salarie tous partenaires confondus."""
    db_adv = get_pg_connection("adv")

    # 1) Liste des partenaires actifs
    parts = db_adv.query(
        "SELECT prefixe_bdd FROM pgt_partenaire WHERE is_actif = TRUE AND modif_elem <> 'suppr'"
    )
    prefixes = [(_str(p.get("prefixe_bdd")).strip()) for p in parts]
    prefixes = [p for p in prefixes if p]

    # 2) Type d'etat (couleurs + lib_type)
    type_etat_rows = db_adv.query(
        """SELECT id_type_etat, lib_type, couleur_r, couleur_v, couleur_b
        FROM pgt_type_etat_contrat WHERE modif_elem <> 'suppr'"""
    )
    type_etat_map: dict[int, dict] = {}
    for r in type_etat_rows:
        tid = _to_int(r.get("id_type_etat"))
        type_etat_map[tid] = {
            "lib_type": _str(r.get("lib_type")),
            "couleur": _winrgb_to_hex(
                _to_int(r.get("couleur_r")),
                _to_int(r.get("couleur_v")),
                _to_int(r.get("couleur_b")),
            ),
        }

    # 3) Chargement parallele des contrats par partenaire
    def fetch_partner(prefix: str) -> list[dict]:
        lprefix = prefix.lower()
        db = get_pg_connection("adv")
        try:
            return db.query(
                f"""SELECT
                    c.id_contrat,
                    c.id_salarie,
                    c.num_bs,
                    c.info_interne,
                    c.id_produit,
                    c.id_etat_contrat,
                    c.date_signature,
                    c.nb_points,
                    c.mois_p AS mois_p,
                    cl.nom AS client_nom,
                    cl.prenom AS client_prenom,
                    cl.adresse1 AS client_adresse,
                    cl.cp AS client_cp,
                    cl.ville AS client_ville,
                    cl.mail AS client_mail,
                    cl.gsm AS client_gsm,
                    p.lib_produit,
                    p.famille,
                    p.sous_fam,
                    p.prefixe_bdd,
                    e.lib_etat,
                    e.lib_etat_vend,
                    e.id_type_etat
                FROM pgt_{lprefix}_contrat c
                LEFT JOIN pgt_{lprefix}_produit p ON p.id_produit = c.id_produit
                LEFT JOIN pgt_{lprefix}_etat_contrat e ON e.id_etat = c.id_etat_contrat
                LEFT JOIN pgt_{lprefix}_client cl ON cl.id_client = c.id_client
                WHERE c.id_salarie = ?
                  AND c.modif_elem NOT LIKE '%suppr%'
                ORDER BY c.date_signature DESC""",
                (int(id_salarie),),
            )
        except Exception:
            # Tables manquantes pour ce partenaire -> on l'ignore
            return []

    rows_by_prefix: dict[str, list[dict]] = {}
    if prefixes:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for prefix, rows in zip(prefixes, pool.map(fetch_partner, prefixes)):
                if rows:
                    rows_by_prefix[prefix] = rows

    traites: list[dict] = []
    a_traiter: list[dict] = []

    for prefix, rows in rows_by_prefix.items():
        for r in rows:
            id_contrat = _str(r.get("id_contrat"))
            id_type_etat = _to_int(r.get("id_type_etat"))
            mois_p_raw = r.get("mois_p")
            mois_p_iso = _yyyymm(mois_p_raw)
            te_meta = type_etat_map.get(id_type_etat, {})
            type_etat_lib = te_meta.get("lib_type", "")

            # Famille (selon ENI : sous_fam ; sinon famille)
            famille = _str(r.get("famille"))
            sous_fam = _str(r.get("sous_fam"))
            type_prod = sous_fam if prefix.upper() == "ENI" and sous_fam else famille

            lib_etat = _str(r.get("lib_etat_vend")) or _str(r.get("lib_etat"))

            client_nom = (
                f"{_str(r.get('client_nom'))} {_capitalize(_str(r.get('client_prenom')))}"
            ).strip()

            item = {
                "id_contrat": id_contrat,
                "partenaire": prefix.upper(),
                "num_bs": _str(r.get("num_bs")),
                "info_interne": _str(r.get("info_interne")),
                "lib_produit": _str(r.get("lib_produit")),
                "type_prod": type_prod,
                "date_signature": _iso(r.get("date_signature")),
                "mois_paiement": mois_p_iso,
                "id_etat_contrat": _to_int(r.get("id_etat_contrat")),
                "etat_contrat_lib": lib_etat,
                "id_type_etat": id_type_etat,
                "type_etat_lib": type_etat_lib,
                "couleur_fond": te_meta.get("couleur", "#FFFFFF"),
                "nb_points": _to_int(r.get("nb_points")),
                "client_nom": client_nom,
                "client_adresse": _str(r.get("client_adresse")),
                "client_cp": _str(r.get("client_cp")),
                "client_ville": _str(r.get("client_ville")),
                "client_mail": _str(r.get("client_mail")),
                "client_gsm": _str(r.get("client_gsm")),
                "info_internes": _str(r.get("info_interne")),
            }

            # Repartition traites / a_traiter (cf. WinDev test ligne 144-146)
            if id_type_etat in _TYPES_TRAITES or (id_type_etat == 5 and mois_p_iso):
                # Si non Valide-Paye -> on masque le mois_paiement (cf. WinDev)
                if id_type_etat in (3, 4, 1, 7):
                    item["mois_paiement"] = ""
                traites.append(item)
            else:
                a_traiter.append(item)

    return {
        "traites": traites,
        "a_traiter": a_traiter,
        "type_etats": type_etat_map,  # utile cote front pour les couleurs
    }
