"""
Service Clusters SFR : liste des clusters avec objectifs/réalisé et calcul des ratios.

Transposition de PAGE_Cluster (WinDev).

Sources :
  - Bdd_Omaya_ADV : SFR_Cluster, SFR_ClusterObjectif
  - Bdd_Omaya_RH  : organigramme, societe (enrichissement batch)

Agrégation :
  - Vue principale      : agrège par département = LEFT(CodeVAD, 2)
  - Vue sous-clusters   : une carte par CodeVAD complet (ex: "14-01", "14-02")

IDResp = 0 → label "Réseau" (objectifs globaux, pas rattachés à un responsable).
À renommer IDResp → IdOrganigramme lors de la migration SQL Server.
"""

import base64
import struct

from app.core.database import get_connection


# -- Helpers ------------------------------------------------------------

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


# -- Référentiels ------------------------------------------------------

DEPARTEMENTS: dict[str, str] = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron",
    "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal", "16": "Charente",
    "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "20": "Corse",
    "2A": "Corse-du-Sud", "2B": "Haute-Corse", "21": "Côte-d'Or", "22": "Côtes-d'Armor",
    "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure",
    "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute Garonne",
    "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine",
    "36": "Indre", "37": "Indre-et-Loire", "38": "Isère", "39": "Jura", "40": "Landes",
    "41": "Loir-et-Cher", "42": "Loire", "43": "Haute Loire", "44": "Loire-Atlantique",
    "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère",
    "49": "Maine-et-Loire", "50": "Manche", "51": "Marne", "52": "Haute Marne",
    "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan",
    "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne",
    "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas Rhin",
    "68": "Haut Rhin", "69": "Rhône", "70": "Haute Saône", "71": "Saône-et-Loire",
    "72": "Sarthe", "73": "Savoie", "74": "Haute Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines",
    "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne",
    "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne",
    "87": "Haute Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne", "95": "Val-d'Oise",
    "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "976": "Mayotte",
}


# Liste hardcodée des orgas "internes" utilisées comme filtres de groupement.
# À rendre dynamique via une interface d'admin plus tard.
GROUPEMENTS_ORGAS: list[int] = [
    18,                         # Région Cécile
    19,                         # Région Julien
    64,                         # Agence CD
    20260402170805658,          # Agence Duval Caen
    20191203164626234,          # Agence JR
    20210906121249525,          # Agence Le Mans
    20260402142812484,          # Agence Brosset Tours
    20260402165637765,          # Agence Mohammed Boutayed Poitiers
    20180131091629815,          # OrgaPower
    20230105145730716,          # OrgaFox
]


def _nom_dep(code: str) -> str:
    return DEPARTEMENTS.get(code, "")


# -- Calcul couleurs ---------------------------------------------------

def _compute_colors(ratio: float, tx_rac: float) -> tuple[str, str]:
    """
    Reproduit les couleurs WinDev (PI_SfrClusterObj).

    Jauge (ratio = nbCtt/obj) :
      - noir      si ratio <= 0.15
      - rouge     si ratio < 0.5
      - bleu      si ratio >= 1
      - vert      si ratio > 0.8
      - jaune or  si ratio > 0.7
      - orange    sinon

    Racc (txRac) :
      - vert foncé  si txRac >= 70
      - rouge clair si txRac < 60
      - orange foncé sinon
    """
    # Attention à l'ordre : WinDev teste dans l'ordre de la structure SELON
    if ratio <= 0.15:
        cj = "#111827"          # noir
    elif ratio < 0.5:
        cj = "#F87171"          # rouge clair
    elif ratio >= 1:
        cj = "#007EC6"          # bleu RVB(0,126,198)
    elif ratio > 0.8:
        cj = "#31896B"          # vert RVB(49,137,107)
    elif ratio > 0.7:
        cj = "#EAB308"          # jaune or
    else:
        cj = "#FDBA74"          # orange pastel

    if tx_rac >= 70:
        cr = "#166534"          # vert foncé
    elif tx_rac < 60:
        cr = "#F87171"          # rouge clair
    else:
        cr = "#C2410C"          # orange foncé

    return cj, cr


# -- Service principal -------------------------------------------------

def _periodes_mois(mois_du: int, annee_du: int, mois_au: int, annee_au: int) -> list[tuple[int, int]]:
    """Retourne la liste [(mois, année)] inclusive entre Du et Au."""
    out: list[tuple[int, int]] = []
    m, a = mois_du, annee_du
    while (a, m) <= (annee_au, mois_au):
        out.append((m, a))
        m += 1
        if m > 12:
            m = 1
            a += 1
    return out


def _passe_filtre(jetons: list[str], exp_lib: str, exp_rs: str, dep_code: str) -> bool:
    """
    Reproduit le filtre SAI_Jeton : si au moins un jeton matche dans
    exp_lib OU exp_rs OU code département, alors la ligne passe.
    Si pas de jeton → pas de filtre.
    """
    if not jetons:
        return True
    for j in jetons:
        jl = (j or "").strip().lower()
        if not jl:
            continue
        if (
            jl in (exp_lib or "").lower()
            or jl in (exp_rs or "").lower()
            or jl in (dep_code or "").lower()
        ):
            return True
    return False


def list_clusters(
    mois_du: int,
    annee_du: int,
    mois_au: int,
    annee_au: int,
    acces_global: bool,
    id_affectation_user: int,
    id_ste_user: int,
    lib_societe_user: str,
    lib_affectation_user: str,
    logo_ste_user: str = "",
    code_vad_parent: str = "",
    jetons: list[str] | None = None,
) -> list[dict]:
    """
    Liste les clusters (agrégés par département) ou sous-clusters (d'un département).

    Args:
        mois_du/annee_du, mois_au/annee_au : intervalle de période (inclusive)
        acces_global : True si droit 'ProdRezo' → scope tous les responsables
        id_affectation_user : ID de l'orga de l'utilisateur (si pas ProdRezo)
        id_ste_user / lib_societe_user / lib_affectation_user / logo_ste_user :
            infos à afficher à la place de la jointure organigramme/societe
            quand l'utilisateur n'a pas ProdRezo
        code_vad_parent : si fourni (ex: "14"), retourne les sous-clusters
            du département (pas d'agrégation) ; sinon agrège par département
        jetons : filtres texte (chips) ; match sur ExpLib/ExpRS/CodeVAD

    Returns:
        Liste de dicts compatibles avec le schema ClusterCard.
    """
    jetons = jetons or []
    periodes = _periodes_mois(mois_du, annee_du, mois_au, annee_au)
    if not periodes:
        return []

    db_adv = get_connection("adv")
    db_rh = get_connection("rh")

    # Accumulateur : key = "dep" (agrégation) ou "codeVAD complet" (détail)
    #   value = dict avec compteurs cumulés + infos d'affichage
    acc: dict[str, dict] = {}

    # Paramètre IDResp :
    #   - ProdRezo : tous (pas de filtre)
    #   - sinon    : restreindre à son affectation (ou 0=Réseau global)
    for (mois, annee) in periodes:
        sql = [
            "SELECT ObjCtt, NbCttBrut, nbRaccSFR, nbS1, nbFibHorsAtt,",
            "       CodeVAD, IDResp",
            "FROM SFR_ClusterObjectif",
            "WHERE ObjMois = ? AND ObjAnnée = ?",
            "  AND ModifELEM <> 'suppr'",
        ]
        params: list = [mois, annee]

        # Filtre département si on est en vue détail
        if code_vad_parent:
            sql.append("  AND LEFT(CodeVAD, 2) = ?")
            params.append(code_vad_parent[:2])

        # Filtre responsable si user non-ProdRezo
        if not acces_global:
            # Scope : son affectation OU lignes Réseau (IDResp=0)
            sql.append("  AND (IDResp = ? OR IDResp = 0)")
            params.append(id_affectation_user)

        rows = db_adv.query("\n".join(sql), tuple(params))

        # Collecte des IDResp rencontrés pour batch lookup organigramme + societe
        resp_ids: set[int] = set()
        for r in rows:
            resp_ids.add(_to_int(r.get("IDResp")))
        resp_ids.discard(0)

        # Batch lookup organigramme → IdSte/Lib_ORGA
        orga_info: dict[int, dict] = {}
        if resp_ids:
            ids_sql = ",".join(str(i) for i in resp_ids)
            orga_rows = db_rh.query(
                f"""SELECT idorganigramme, Lib_ORGA, IdSte
                FROM organigramme
                WHERE idorganigramme IN ({ids_sql})"""
            )
            for o in orga_rows:
                orga_info[_to_int(o.get("idorganigramme"))] = {
                    "lib_orga": o.get("Lib_ORGA") or "",
                    "id_ste": _to_int(o.get("IdSte")),
                }

        # Batch lookup societe → RaisonSociale/Logo (GUIMMICK)
        ste_ids: set[int] = {v["id_ste"] for v in orga_info.values() if v["id_ste"]}
        ste_info: dict[int, dict] = {}
        if ste_ids:
            ids_sql = ",".join(str(i) for i in ste_ids)
            ste_rows = db_rh.query(
                f"""SELECT IdSte, RaisonSociale, GUIMMICK
                FROM societe
                WHERE IdSte IN ({ids_sql})"""
            )
            for s in ste_rows:
                ste_info[_to_int(s.get("IdSte"))] = {
                    "rs": s.get("RaisonSociale") or "",
                    "logo": s.get("GUIMMICK") or "",
                }

        # Agrégation
        for r in rows:
            code_vad = (r.get("CodeVAD") or "").strip()
            if not code_vad or code_vad == "00-00":
                continue

            dep = code_vad[:2]
            id_resp = _to_int(r.get("IDResp"))

            # Clé d'agrégation : dep en vue principale, codeVAD complet en vue détail
            key = code_vad if code_vad_parent else dep

            # Labels ExpLib / ExpRS / logo
            if acces_global:
                # Scope Réseau
                if id_resp == 0:
                    exp_lib = "Réseau"
                    exp_rs = _nom_dep(dep) or dep
                    logo = ""
                else:
                    oi = orga_info.get(id_resp, {})
                    exp_lib = oi.get("lib_orga") or "Réseau"
                    si = ste_info.get(oi.get("id_ste", 0), {})
                    exp_rs = si.get("rs") or _nom_dep(dep) or dep
                    logo = si.get("logo") or ""
            else:
                # Scope user : ses infos
                if id_resp == 0:
                    exp_lib = "Réseau"
                    exp_rs = lib_societe_user or _nom_dep(dep) or dep
                    logo = ""
                else:
                    exp_lib = lib_affectation_user or "Réseau"
                    exp_rs = lib_societe_user or _nom_dep(dep) or dep
                    logo = logo_ste_user or ""

            # Filtre jetons
            if not _passe_filtre(jetons, exp_lib, exp_rs, dep):
                continue

            if key not in acc:
                if code_vad_parent:
                    nom = code_vad  # pour un sous-cluster, on affichera le nom SFR_Cluster
                    code_vad_full = code_vad
                else:
                    nom = f"{dep} - {_nom_dep(dep)}".strip(" -")
                    code_vad_full = dep

                acc[key] = {
                    "code_vad": code_vad_full,
                    "code_vad_full": code_vad,
                    "nom": nom,
                    "exp_lib": exp_lib,
                    "exp_rs": exp_rs,
                    "logo_ste": logo,
                    "obj_ctt": 0,
                    "nb_ctt_brut": 0,
                    "nb_s1": 0,
                    "nb_racc_sfr": 0,
                    "nb_fib_hors_att": 0,
                }

            acc[key]["obj_ctt"] += _to_int(r.get("ObjCtt"))
            acc[key]["nb_ctt_brut"] += _to_int(r.get("NbCttBrut"))
            acc[key]["nb_s1"] += _to_int(r.get("nbS1"))
            acc[key]["nb_racc_sfr"] += _to_int(r.get("nbRaccSFR"))
            acc[key]["nb_fib_hors_att"] += _to_int(r.get("nbFibHorsAtt"))

    # Pour la vue détail (sous-clusters), enrichir avec le NomCluster depuis SFR_Cluster
    if code_vad_parent and acc:
        codes_vad = [v["code_vad_full"] for v in acc.values()]
        codes_quoted = ",".join("'" + c.replace("'", "''") + "'" for c in codes_vad)
        if codes_quoted:
            cluster_rows = db_adv.query(
                f"""SELECT CodeVAD, NomCluster
                FROM SFR_Cluster
                WHERE CodeVAD IN ({codes_quoted})
                  AND ModifELEM NOT LIKE '%suppr%'"""
            )
            nom_par_vad = {
                (c.get("CodeVAD") or "").strip(): (c.get("NomCluster") or "").strip()
                for c in cluster_rows
            }
            for v in acc.values():
                nc = nom_par_vad.get(v["code_vad_full"], "")
                if nc:
                    v["nom"] = f"{v['code_vad_full']} - {nc}"

    # Calcul des ratios + couleurs + sortie triée
    out: list[dict] = []
    for v in acc.values():
        obj = v["obj_ctt"]
        nb_ctt = v["nb_ctt_brut"]
        nb_racc = v["nb_racc_sfr"]
        nb_hors = v["nb_fib_hors_att"]
        nb_s1 = v["nb_s1"]

        ratio_reel = (nb_ctt / obj) if obj > 0 else 0.0
        ratio = min(ratio_reel, 1.0)

        tx_rac = (nb_racc / nb_hors * 100) if nb_hors > 0 else 0.0
        tx_s1 = (nb_racc / (nb_hors + nb_s1) * 100) if (nb_hors + nb_s1) > 0 else 0.0

        cj, cr = _compute_colors(ratio, tx_rac)

        v_out = dict(v)
        v_out["ratio"] = round(ratio, 4)
        v_out["ratio_reel"] = round(ratio_reel, 4)
        v_out["tx_rac"] = round(tx_rac, 2)
        v_out["tx_s1"] = round(tx_s1, 2)
        v_out["couleur_jauge"] = cj
        v_out["couleur_racc"] = cr
        out.append(v_out)

    out.sort(key=lambda x: x["code_vad_full"])
    return out


def list_groupements() -> list[dict]:
    """
    Retourne la liste des orgas internes utilisées comme filtres de groupement
    (barre horizontale de chips).

    Mapping IdOrganigramme -> Lib_ORGA, préserve l'ordre de GROUPEMENTS_ORGAS.
    """
    if not GROUPEMENTS_ORGAS:
        return []

    db_rh = get_connection("rh")
    ids_sql = ",".join(str(i) for i in GROUPEMENTS_ORGAS)
    rows = db_rh.query(
        f"""SELECT idorganigramme, Lib_ORGA
        FROM organigramme
        WHERE idorganigramme IN ({ids_sql})"""
    )
    label_par_id: dict[int, str] = {
        _to_int(r.get("idorganigramme")): (r.get("Lib_ORGA") or "").strip()
        for r in rows
    }

    out: list[dict] = []
    for oid in GROUPEMENTS_ORGAS:
        label = label_par_id.get(oid, "")
        if not label:
            continue
        out.append({"id": str(oid), "label": label})
    return out
