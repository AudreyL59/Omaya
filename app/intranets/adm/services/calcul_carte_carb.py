"""
Service Fen_CalculCart (ADM Ulease -> Calcul montant carte carburant).

Calcule, pour un mois/annee donne :
  - Pour chaque CarteAttribution active sur la periode :
      - Conducteur + poste + IsResp.
      - Vehicule attribue (vehicule_conducteur).
      - Equipe + agence (salarie_organigramme).
      - Montants releves carburant + peage (cartecarbrelevefournisseur).
      - Production (nb contrats signes / nb jours ouvres / moyenne).
        -> TODO : depend des contrats partenaires qui ne sont pas
        encore migres en PG. _compute_production renvoie 0/0/0 pour
        l'instant. A brancher au cutover BDD partenaires.
      - Grille de calcul du MontantDetecte :
          - Poste 18 ou 19 (chauffeur/responsable terrain) : 500 fixe.
          - Si IsResp + NB_Place=5 : 500 si moy>=3 sinon 300.
          - Si IsResp + NB_Place autre : 700 si moy>=5 sinon 420.
          - Sinon (pas calcul prod) : 0.
      - Sauve dans pgt_cartecalculatt (INSERT ou UPDATE par mois/annee).
"""

from __future__ import annotations

from datetime import date, timedelta
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


def _float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _new_id() -> int:
    from datetime import datetime
    return int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])


def _next_auto(db, schema: str, table: str, col: str) -> int:
    """Calcule MAX(col)+1 pour les tables HFSQL migrees ou la colonne
    _auto n'a pas de sequence PG (default NULL). Race condition
    acceptable pour les modules batch utilises par 1 user a la fois."""
    r = db.query_one(
        f"SELECT COALESCE(MAX({col}),0)+1 AS n FROM {schema}.{table}",
    )
    return _int(r.get("n")) if r else 1


def _dernier_jour_mois(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def _is_jour_ouvre(d: date, feries: set[date]) -> bool:
    """Lundi-Vendredi et pas un jour ferie."""
    return d.weekday() < 5 and d not in feries


def _jours_feries(annee: int) -> set[date]:
    """11 jours feries communs France + DOM (cf. WinDev JourFerieAjoute)."""
    out = {
        date(annee, 1, 1),   # 1er Janvier
        date(annee, 5, 1),   # 1er Mai
        date(annee, 5, 8),   # 8 Mai
        date(annee, 7, 14),  # 14 Juillet
        date(annee, 8, 15),  # Assomption
        date(annee, 11, 1),  # Toussaint
        date(annee, 11, 11), # 11 Novembre
        date(annee, 12, 25), # Noel
    }
    # Paques + derives (Meeus/Jones/Butcher)
    a = annee % 19
    b = annee // 100; c = annee % 100
    d_ = b // 4; e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_ - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    paques = date(annee, month, day)
    out.add(paques + timedelta(days=1))   # Lundi de Paques
    out.add(paques + timedelta(days=39))  # Jeudi de l'Ascension
    out.add(paques + timedelta(days=50))  # Lundi de Pentecote
    return out


def _compute_production(
    id_salarie: int, du: date, au: date,
) -> dict:
    """Production sur la periode : pour chaque partenaire actif, somme
    les contrats signes (hors 'TK%') par jour, puis :
      - nb_prod_tot = total
      - nb_jours_prod = nb de jours ouvres entre du et au (lun-ven hors
        feries) - cf. WinDev qui pre-initialise TableProdJour avec les
        jours ouvres puis ajoute les jours hors-ouvres au passage
      - moy_prod = nb_prod_tot / nb_jours_prod
    """
    if not id_salarie:
        return {"nb_prod_tot": 0, "nb_jours_prod": 0, "moy_prod": 0.0}

    db_adv = get_pg_connection("adv")
    prefixes_rows = db_adv.query(
        """SELECT LOWER(prefixe_bdd) AS p FROM adv.pgt_partenaire
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
              AND prefixe_bdd <> ''""",
    ) or []
    prefixes = [r["p"] for r in prefixes_rows]

    feries = _jours_feries(du.year) | _jours_feries(au.year)
    nb_jours_ouv = sum(
        1 for n in range((au - du).days + 1)
        if _is_jour_ouvre(du + timedelta(days=n), feries)
    )

    nb_prod_tot = 0
    for p in prefixes:
        table = f"adv.pgt_{p}_contrat"
        try:
            row = db_adv.query_one(
                f"""SELECT COUNT(*) AS c FROM {table}
                     WHERE modif_elem <> 'suppr'
                       AND id_salarie = ?
                       AND date_signature BETWEEN ? AND ?
                       AND (num_bs IS NULL OR num_bs NOT LIKE 'TK%')""",
                (int(id_salarie), du, au),
            )
            if row:
                nb_prod_tot += _int(row.get("c"))
        except Exception:
            # Partenaire sans table ou schema absent -> on saute
            continue

    moy = (nb_prod_tot / nb_jours_ouv) if nb_jours_ouv > 0 else 0.0
    return {
        "nb_prod_tot": nb_prod_tot,
        "nb_jours_prod": nb_jours_ouv,
        "moy_prod": moy,
    }


def _compute_montant_detecte(
    is_resp: bool, id_type_poste: int, nb_place: int, moy_prod: float,
) -> tuple[bool, float]:
    """Retourne (calcul_prod, montant_detecte).
    calcul_prod = True si le calcul de prod a ete utilise pour determiner
    le montant. Cf. WinDev CalculMontant + cas postes 18/19."""
    # Postes 18/19 (chauffeur/responsable) : 500 fixe, pas de calcul prod
    if id_type_poste in (18, 19):
        return False, 500.0
    if not is_resp:
        return False, 0.0
    # IsResp : grille selon NB_Place et MoyenneProd
    if nb_place == 5:
        return True, 500.0 if moy_prod >= 3 else 300.0
    return True, 700.0 if moy_prod >= 5 else 420.0


def _equipe_et_agence(idorganigramme: int) -> dict:
    """Equipe = orga lib_orga + capacite. Agence = lib_orga du parent."""
    if not idorganigramme:
        return {"equipe": "", "agence": "", "nb_place": 0}
    db = get_pg_connection("rh")
    eq = db.query_one(
        """SELECT lib_orga, id_parent, capacite
             FROM rh.pgt_organigramme
            WHERE idorganigramme = ? LIMIT 1""",
        (int(idorganigramme),),
    ) or {}
    ag_lib = ""
    parent_id = _int(eq.get("id_parent"))
    if parent_id:
        ag = db.query_one(
            """SELECT lib_orga FROM rh.pgt_organigramme
                WHERE idorganigramme = ? LIMIT 1""",
            (parent_id,),
        ) or {}
        ag_lib = _str(ag.get("lib_orga"))
    return {
        "equipe": _str(eq.get("lib_orga")),
        "agence": ag_lib,
        "nb_place": _int(eq.get("capacite")),
    }


def _equipe_terrain_id(id_salarie: int, dref: date) -> int:
    """Cherche l'idorganigramme actif du salarie a la date donnee.
    Fallback : derniere affectation."""
    if not id_salarie:
        return 0
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT idorganigramme FROM rh.pgt_salarie_organigramme
            WHERE id_salarie = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND date_debut <= ?
              AND (date_fin IS NULL OR date_fin >= ?)
         ORDER BY date_debut DESC LIMIT 1""",
        (int(id_salarie), dref, dref),
    )
    return _int(r.get("idorganigramme")) if r else 0


def _info_salarie(id_salarie: int) -> dict:
    """Nom + Prenom + idTypePoste + IsResp (= resp_equipe)."""
    if not id_salarie:
        return {}
    db = get_pg_connection("rh")
    r = db.query_one(
        """SELECT s.nom, s.prenom,
                  e.id_type_poste, e.resp_equipe
             FROM rh.pgt_salarie s
        LEFT JOIN rh.pgt_salarie_embauche e
               ON e.id_salarie = s.id_salarie
              AND (e.modif_elem IS NULL OR e.modif_elem NOT LIKE '%suppr%')
              AND (e.en_activite IS NULL OR e.en_activite = TRUE)
            WHERE s.id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if not r:
        return {}
    prenom = _str(r.get("prenom")).strip()
    if prenom:
        prenom = prenom[:1].upper() + prenom[1:].lower()
    return {
        "nom_prenom": f"{_str(r.get('nom'))} {prenom}".strip(),
        "id_type_poste": _int(r.get("id_type_poste")),
        "is_resp": bool(r.get("resp_equipe")),
        "poste_lib": "",
    }


def _vehicule_attribue(id_conducteur: int, du: date, au: date) -> str:
    """Derniere immat attribuee au conducteur sur la periode."""
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT vf.immat
             FROM ulease.pgt_vehicule_conducteur vc
       INNER JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
            WHERE (vc.modif_elem IS NULL OR vc.modif_elem NOT LIKE '%suppr%')
              AND vc.id_conducteur = ?
              AND vc.perception_date <= ?
              AND (vc.restitution_date IS NULL
                   OR vc.restitution_date >= ?)
         ORDER BY vc.perception_date DESC LIMIT 1""",
        (int(id_conducteur), au, du),
    )
    return _str(r.get("immat")) if r else ""


def _sommes_releves(id_carte: int, du: date, au: date) -> dict:
    """Retourne {montant_carb, montant_peage} (sommes TTC sur la periode)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT trf.categorie, SUM(ccrf.montant_ttc) AS s
             FROM ulease.pgt_cartecarbrelevefournisseur ccrf
       INNER JOIN ulease.pgt_typerelevefournisseur trf
               ON trf.id_type_releve_fournisseur = ccrf.id_type_releve_fournisseur
            WHERE (ccrf.modif_elem IS NULL OR ccrf.modif_elem <> 'suppr')
              AND (trf.categorie = 'Carburant' OR trf.categorie = 'Péage')
              AND ccrf.id_carte_carburant = ?
              AND ccrf.date BETWEEN ? AND ?
         GROUP BY trf.categorie""",
        (int(id_carte), du, au),
    ) or []
    out = {"montant_carb": 0.0, "montant_peage": 0.0}
    for r in rows:
        cat = _str(r.get("categorie"))
        s = _float(r.get("s"))
        if cat == "Carburant":
            out["montant_carb"] = s
        elif cat in ("Péage", "Peage"):
            out["montant_peage"] = s
    return out


def _list_attributions(du: date, au: date) -> list[dict]:
    """ReqAtt : attributions actives sur la periode + carte + conducteur."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT ca.id_carte_attribution, ca.id_carte_carburant,
                  ca.id_conducteur, ca.du, ca.au,
                  c.id_salarie,
                  cc.code_carte, cc.num_carte
             FROM ulease.pgt_carteattribution ca
       INNER JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = ca.id_conducteur
       INNER JOIN ulease.pgt_cartecarburant cc
               ON cc.id_carte_carburant = ca.id_carte_carburant
            WHERE (ca.modif_elem IS NULL OR ca.modif_elem <> 'suppr')
              AND ca.du <= ?
              AND (ca.au IS NULL OR ca.au >= ?)""",
        (au, du),
    ) or []
    return rows


def _persist_calcul(ligne: dict, mois: int, annee: int, op_id: int) -> str:
    """INSERT ou UPDATE dans pgt_cartecalculatt (1 ligne par mois/annee/
    id_carte_attribution). Renvoie l'id_carte_calcul_att."""
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_carte_calcul_att FROM ulease.pgt_cartecalculatt
            WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
              AND id_carte_attribution = ?
              AND mois = ? AND annee = ?
            LIMIT 1""",
        (_int(ligne.get("id_carte_attribution")), int(mois), int(annee)),
    )
    if not r:
        new_id = _new_id()
        next_auto = _next_auto(db, "ulease", "pgt_cartecalculatt",
                               "id_carte_calcul_att_auto")
        db.query(
            """INSERT INTO ulease.pgt_cartecalculatt
                 (id_carte_calcul_att_auto, id_carte_calcul_att,
                  id_carte_attribution, id_conducteur,
                  id_carte_carburant, id_type_poste, calcul_prod,
                  id_organigramme, nb_place, nb_prod_tot, nb_jours_prod,
                  moy_prod, montant_detecte, montant_attribue,
                  montant_carb, montant_peage, montant_total,
                  difference, montant_valide, mois, annee,
                  modif_op, modif_date, modif_elem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, NOW(), 'new')""",
            (
                next_auto, new_id,
                _int(ligne.get("id_carte_attribution")),
                _int(ligne.get("id_conducteur")),
                _int(ligne.get("id_carte_carburant")),
                _int(ligne.get("id_type_poste")),
                bool(ligne.get("calcul_prod")),
                _int(ligne.get("id_organigramme")),
                _int(ligne.get("nb_place")),
                _int(ligne.get("nb_prod_tot")),
                _int(ligne.get("nb_jours_prod")),
                _float(ligne.get("moy_prod")),
                _float(ligne.get("montant_detecte")),
                _float(ligne.get("montant_attribue")),
                _float(ligne.get("montant_carb")),
                _float(ligne.get("montant_peage")),
                _float(ligne.get("montant_total")),
                _float(ligne.get("difference")),
                _float(ligne.get("montant_valide")),
                int(mois), int(annee), int(op_id),
            ),
        )
        return str(new_id)
    id_calc = _int(r.get("id_carte_calcul_att"))
    db.query(
        """UPDATE ulease.pgt_cartecalculatt
              SET calcul_prod = ?, id_organigramme = ?,
                  nb_place = ?, nb_prod_tot = ?, nb_jours_prod = ?,
                  moy_prod = ?, montant_detecte = ?, montant_attribue = ?,
                  montant_carb = ?, montant_peage = ?, montant_total = ?,
                  difference = ?, montant_valide = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_carte_calcul_att = ?""",
        (
            bool(ligne.get("calcul_prod")),
            _int(ligne.get("id_organigramme")),
            _int(ligne.get("nb_place")),
            _int(ligne.get("nb_prod_tot")),
            _int(ligne.get("nb_jours_prod")),
            _float(ligne.get("moy_prod")),
            _float(ligne.get("montant_detecte")),
            _float(ligne.get("montant_attribue")),
            _float(ligne.get("montant_carb")),
            _float(ligne.get("montant_peage")),
            _float(ligne.get("montant_total")),
            _float(ligne.get("difference")),
            _float(ligne.get("montant_valide")),
            int(op_id), id_calc,
        ),
    )
    return str(id_calc)


def calcul_montant_cartes(mois: int, annee: int, op_id: int) -> dict:
    """Btn 'Demarrer Calcul' : pipeline complet. Retourne {ok, lignes:[...]}."""
    if mois < 1 or mois > 12 or annee < 2000 or annee > 2100:
        return {"ok": False, "error": "Mois/annee invalide"}

    du = date(annee, mois, 1)
    au = _dernier_jour_mois(du)

    attribs = _list_attributions(du, au)
    out: list[dict] = []

    for a in attribs:
        id_att = _int(a.get("id_carte_attribution"))
        id_carte = _int(a.get("id_carte_carburant"))
        id_cond = _int(a.get("id_conducteur"))
        id_sal = _int(a.get("id_salarie"))

        info = _info_salarie(id_sal)
        is_resp = bool(info.get("is_resp"))
        id_type_poste = _int(info.get("id_type_poste"))

        # Equipe terrain a la date Du, fallback Au
        id_orga = _equipe_terrain_id(id_sal, du) or _equipe_terrain_id(id_sal, au)
        eq = _equipe_et_agence(id_orga) if id_orga else {"equipe": "", "agence": "", "nb_place": 0}

        # Vehicule attribue
        immat = _vehicule_attribue(id_cond, du, au)

        # Bornes de la periode pour les releves (intersection avec att.du/au)
        att_du = _try_date(a.get("du")) or du
        att_au = _try_date(a.get("au")) or au
        d1 = du if du >= att_du else att_du
        d2 = au if au <= att_au or not att_au else att_au
        if d2 is None:
            d2 = au

        sommes = _sommes_releves(id_carte, d1, d2)
        total = sommes["montant_carb"] + sommes["montant_peage"]

        # Production
        prod = _compute_production(id_sal, du, au)

        # Calcul du MontantDetecte
        calcul_prod, montant_detecte = _compute_montant_detecte(
            is_resp, id_type_poste, eq["nb_place"], prod["moy_prod"],
        )

        # Montant Attribue : prend la valeur existante en BDD si presente,
        # sinon = MontantDetecte (cf. WinDev)
        db = get_pg_connection("ulease")
        existing = db.query_one(
            """SELECT id_carte_calcul_att, montant_attribue FROM ulease.pgt_cartecalculatt
                WHERE (modif_elem IS NULL OR modif_elem <> 'suppr')
                  AND id_carte_attribution = ?
                  AND mois = ? AND annee = ?
                LIMIT 1""",
            (id_att, int(mois), int(annee)),
        )
        if existing:
            montant_attribue = _float(existing.get("montant_attribue"))
            id_calcul_existing = str(_int(existing.get("id_carte_calcul_att")))
        else:
            montant_attribue = montant_detecte
            id_calcul_existing = ""

        # Diff + Montant_a_valider
        diff = montant_detecte - total
        if diff < 0:
            montant_valide = montant_attribue + diff
        else:
            montant_valide = montant_attribue

        ligne = {
            "id_carte_attribution": str(id_att),
            "id_conducteur": str(id_cond),
            "id_carte_carburant": str(id_carte),
            "id_salarie": str(id_sal),
            "id_type_poste": id_type_poste,
            "code_carte": _str(a.get("code_carte")),
            "num_carte": _str(a.get("num_carte")),
            "nom_prenom": _str(info.get("nom_prenom")),
            "poste_lib": _str(info.get("poste_lib")),
            "vehicule": immat,
            "calcul_prod": calcul_prod,
            "id_organigramme": id_orga,
            "agence": eq["agence"],
            "equipe": eq["equipe"],
            "nb_place": eq["nb_place"],
            "nb_prod_tot": prod["nb_prod_tot"],
            "nb_jours_prod": prod["nb_jours_prod"],
            "moy_prod": prod["moy_prod"],
            "montant_detecte": montant_detecte,
            "montant_attribue": montant_attribue,
            "montant_carb": sommes["montant_carb"],
            "montant_peage": sommes["montant_peage"],
            "montant_total": total,
            "difference": diff,
            "montant_valide": montant_valide,
        }
        # Persistance
        id_calcul = _persist_calcul(ligne, mois, annee, op_id)
        ligne["id_carte_calcul_att"] = id_calcul or id_calcul_existing
        out.append(ligne)

    # Tri par nom_prenom
    out.sort(key=lambda x: x.get("nom_prenom", ""))
    return {"ok": True, "mois": mois, "annee": annee, "lignes": out}


def _try_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    s = str(v)
    if len(s) >= 10 and s[4] == "-":
        try:
            return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        except Exception:
            return None
    return None


def list_calcul(mois: int, annee: int) -> list[dict]:
    """Relit le tableau de calcul deja persiste (sans recalculer)."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT cc.id_carte_calcul_att, cc.id_carte_attribution,
                  cc.id_conducteur, cc.id_carte_carburant, cc.id_type_poste,
                  cc.calcul_prod, cc.id_organigramme, cc.nb_place,
                  cc.nb_prod_tot, cc.nb_jours_prod, cc.moy_prod,
                  cc.montant_detecte, cc.montant_attribue,
                  cc.montant_carb, cc.montant_peage, cc.montant_total,
                  cc.difference, cc.montant_valide,
                  car.code_carte, car.num_carte,
                  cond.id_salarie
             FROM ulease.pgt_cartecalculatt cc
       INNER JOIN ulease.pgt_cartecarburant car
               ON car.id_carte_carburant = cc.id_carte_carburant
       INNER JOIN ulease.pgt_conducteur cond
               ON cond.id_conducteur = cc.id_conducteur
            WHERE (cc.modif_elem IS NULL OR cc.modif_elem <> 'suppr')
              AND cc.mois = ? AND cc.annee = ?""",
        (int(mois), int(annee)),
    ) or []
    out = []
    for r in rows:
        id_sal = _int(r.get("id_salarie"))
        info = _info_salarie(id_sal)
        id_orga = _int(r.get("id_organigramme"))
        eq = _equipe_et_agence(id_orga) if id_orga else {"equipe": "", "agence": "", "nb_place": 0}
        out.append({
            "id_carte_calcul_att": str(_int(r.get("id_carte_calcul_att"))),
            "id_carte_attribution": str(_int(r.get("id_carte_attribution"))),
            "id_conducteur": str(_int(r.get("id_conducteur"))),
            "id_carte_carburant": str(_int(r.get("id_carte_carburant"))),
            "id_salarie": str(id_sal),
            "id_type_poste": _int(r.get("id_type_poste")),
            "code_carte": _str(r.get("code_carte")),
            "num_carte": _str(r.get("num_carte")),
            "nom_prenom": _str(info.get("nom_prenom")),
            "poste_lib": "",
            "vehicule": "",
            "calcul_prod": bool(r.get("calcul_prod")),
            "id_organigramme": id_orga,
            "agence": eq["agence"],
            "equipe": eq["equipe"],
            "nb_place": _int(r.get("nb_place")) or eq["nb_place"],
            "nb_prod_tot": _int(r.get("nb_prod_tot")),
            "nb_jours_prod": _int(r.get("nb_jours_prod")),
            "moy_prod": _float(r.get("moy_prod")),
            "montant_detecte": _float(r.get("montant_detecte")),
            "montant_attribue": _float(r.get("montant_attribue")),
            "montant_carb": _float(r.get("montant_carb")),
            "montant_peage": _float(r.get("montant_peage")),
            "montant_total": _float(r.get("montant_total")),
            "difference": _float(r.get("difference")),
            "montant_valide": _float(r.get("montant_valide")),
        })
    out.sort(key=lambda x: x.get("nom_prenom", ""))
    return out


def update_montant_attribue(
    id_carte_calcul_att: int, montant_attribue: float, op_id: int,
) -> dict:
    """Permet a l'utilisateur d'ajuster manuellement le MontantAttribue
    apres calcul (cf. WinDev : 1ere passe = MontantDetecte, puis user
    edite, puis EnregistreCalcul est rappele)."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_cartecalculatt
              SET montant_attribue = ?,
                  modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_carte_calcul_att = ?""",
        (_float(montant_attribue), int(op_id), int(id_carte_calcul_att)),
    )
    return {"ok": True}
