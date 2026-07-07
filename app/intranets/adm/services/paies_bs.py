"""
Service Fen_PaiesBS - 'Module paies'.

Transposition Btn 'Lister les contrats' :
1. Pour chaque partenaire actif : SELECT dynamique sur pgt_{part}_contrat
   filtre sur (date_signature dans periode signee) OR
   (date_signature dans hors delai ET mois_p dans mois cible) OR
   (mois_p dans mois cible).
2. Enrichissement par partenaire :
   - SFR : date_racc_activ, type_vente, mois_p_ra, id_etat_sfr, technologie,
     portabilite, notation, prise_saisie
   - ENI : gaz_car_declaree/relevee, elec_puissance, gaz_actif/elec_actif,
     opt_energie_verte_elec/gaz, opt_mail, opt_reforestation, opt_protection,
     opt_entretien
3. Skip contrats deja payes (type_etat 5/6) avec MoisP different du mois cible.
4. Calcul TableJourNonProd : jours ouvres non feries de la periode sans contrat.
5. Copie contrats 'Decommission' dans une liste separee (onglet 2).
6. Detecte couleurs :
   - Hors delai (jaune #F8EDA5) si date_signature dans periode hors delai et non SFR
   - Rejet/Resil (rouge #FED2D2) si type_etat = 3 ou 4
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel
from app.intranets.adm.schemas.paies_bs import (
    ContratMaj, ContratMajResult, ContratRow, JourNonProd,
    ListerContratsParams, ListerContratsResult, NbCttParJourRow,
    PartenairePeriode, ValiderPaiesParams, ValiderPaiesResult,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Constants & helpers
# --------------------------------------------------------------------

_KNOWN_PARTENAIRES = {"ENI", "IAG", "OEN", "PRO", "SFR", "STR", "VAL", "TLC"}


def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _to_iso(v) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)[:10]
    return s if not is_sentinel(s) else ""


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return "-".join(x[:1].upper() + x[1:].lower() for x in p.split("-"))


def _premier_jour(mois: str) -> str:
    """'YYYY-MM' -> 'YYYY-MM-01'."""
    return f"{mois}-01" if len(mois) == 7 else mois[:10]


def _dernier_jour(mois: str) -> str:
    """'YYYY-MM' -> 'YYYY-MM-31' (31 pour tout mois -> PG le calcule)."""
    if len(mois) != 7:
        return mois[:10]
    y, m = int(mois[:4]), int(mois[5:7])
    if m == 12:
        d = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(y, m + 1, 1) - timedelta(days=1)
    return d.isoformat()


def _jours_feries_fr(annee: int) -> set[date]:
    """Jours feries francais fixes + calcul de Paques (Lundi Paques,
    Ascension, Pentecote).

    cf. WinDev JourFerieAjoute() : 01/01, LundiPaques, 01/05, 08/05,
    Ascension, LundiPentecote, 14/07, 15/08, 01/11, 11/11, 25/12.
    """
    # Calcul de Paques (algorithme de Meeus/Jones/Butcher)
    a = annee % 19
    b = annee // 100
    c = annee % 100
    d_ = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_ - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    mois_p = (h + ll - 7 * m + 114) // 31
    jour_p = ((h + ll - 7 * m + 114) % 31) + 1
    paques = date(annee, mois_p, jour_p)

    return {
        date(annee, 1, 1),            # Jour de l'An
        paques + timedelta(days=1),   # Lundi de Paques
        date(annee, 5, 1),            # Fete du Travail
        date(annee, 5, 8),            # Victoire 1945
        paques + timedelta(days=39),  # Jeudi Ascension
        paques + timedelta(days=50),  # Lundi Pentecote
        date(annee, 7, 14),           # Fete nationale
        date(annee, 8, 15),           # Assomption
        date(annee, 11, 1),           # Toussaint
        date(annee, 11, 11),          # Armistice 1918
        date(annee, 12, 25),          # Noel
    }


def _client_abbrev(nom: str, prenom: str) -> str:
    """Cf. WinDev : Gauche(NOM,3)+'. '+capitalise(Gauche(PRENOM,3))+'.'."""
    n = (nom or "").strip()[:3]
    p = (prenom or "").strip()[:3]
    return f"{n}. {_cap_prenom(p)}.".strip()


# --------------------------------------------------------------------
# Affectation historique (vendeur -> agence + equipe a une date donnee)
# --------------------------------------------------------------------

def _load_affectations_batch(
    id_salarie: int, date_debut: str, date_fin: str,
) -> list[dict]:
    """Charge tous les segments d'affectation d'un salarie sur une periode.

    Retour : liste de {date_debut, date_fin, agence, equipe}.
    Reutilise le pattern de affectationVendeurByDate mais en batch.
    """
    rh = get_pg_connection("rh")
    try:
        segs = rh.query(
            """SELECT so.date_debut, so.date_fin, o.lib_orga,
                      o.id_type_niveau_orga, o.idparent
                 FROM pgt_salarie_organigramme so
                 JOIN pgt_organigramme o
                      ON o.idorganigramme = so.idorganigramme
                WHERE so.id_salarie = ?
                  AND (so.modif_elem IS NULL
                       OR so.modif_elem NOT LIKE '%suppr%')
                  AND (so.date_debut IS NULL OR so.date_debut <= ?)
                  AND (so.date_fin IS NULL OR so.date_fin >= ?)
                ORDER BY so.date_debut DESC NULLS LAST""",
            (int(id_salarie), date_fin, date_debut),
        ) or []
    except Exception:
        segs = []
    return segs


def _affectation_at(
    segments: list[dict], date_ref: str,
) -> tuple[str, str]:
    """Retourne (agence, equipe) a la date_ref en cherchant dans les
    segments precharges.
    """
    if not date_ref:
        return ("", "")
    date_ref_d = date.fromisoformat(date_ref[:10])
    agence = ""
    equipe = ""
    id_agence = 0
    for s in segments:
        d1 = s.get("date_debut")
        d2 = s.get("date_fin")
        d1_d = d1 if isinstance(d1, date) else (
            date.fromisoformat(str(d1)[:10]) if d1 else date.min
        )
        d2_d = d2 if isinstance(d2, date) else (
            date.fromisoformat(str(d2)[:10]) if d2 else date.max
        )
        if not (d1_d <= date_ref_d <= d2_d):
            continue
        lvl = s.get("id_type_niveau_orga")
        lib = (s.get("lib_orga") or "").strip()
        if lvl == 3 and not agence:
            agence = lib
        elif lvl == 4 and not equipe:
            equipe = lib
            id_agence = int(s.get("idparent") or 0)
    # Si equipe trouvee et agence pas encore, on lookup l'idparent
    if equipe and not agence and id_agence:
        rh = get_pg_connection("rh")
        try:
            r = rh.query_one(
                """SELECT lib_orga FROM pgt_organigramme
                    WHERE idorganigramme = ?""",
                (id_agence,),
            )
            if r:
                agence = (r.get("lib_orga") or "").strip()
        except Exception:
            pass
    return (agence, equipe)


# --------------------------------------------------------------------
# Query dynamique par partenaire
# --------------------------------------------------------------------

def _build_query(
    part: str, id_salarie: int, mois_cible: str, p: PartenairePeriode,
) -> tuple[str, tuple]:
    """Construit la requete SELECT pour un partenaire.

    Cf. WinDev reqProd genere avec Remplace(part_, {PART}_) puis WHERE
    date_signature/mois_p en fonction du partenaire.
    """
    prefix = part.lower()
    mois_deb = _premier_jour(mois_cible)
    mois_fin = _dernier_jour(mois_cible)
    du = p.signe_du or "1900-01-01"
    au = p.signe_au or "2100-12-31"
    du1 = p.hors_delai_du or du
    au1 = p.hors_delai_au or au

    # Colonnes specifiques par partenaire (SFR utilise mois_p_ra, ENI options)
    if part == "SFR":
        cond = (
            "(c.date_signature BETWEEN ? AND ?) "
            "OR (c.mois_p_ra BETWEEN ? AND ?)"
        )
        cond_params: tuple = (du, au, mois_deb, mois_fin)
        select_specific = (
            "c.mois_p_ra AS mois_p_query, "
            "c.date_racc_activ, c.type_vente, "
        )
    else:
        # Autres partenaires : date_signature dans periode OU
        # (date_signature dans hors delai ET mois_p dans mois cible) OU
        # mois_p dans mois cible
        cond = (
            "(c.date_signature BETWEEN ? AND ?) "
            "OR (c.date_signature BETWEEN ? AND ? "
            "    AND c.mois_p BETWEEN ? AND ?) "
            "OR (c.mois_p BETWEEN ? AND ?)"
        )
        cond_params = (du, au, du1, au1, mois_deb, mois_fin, mois_deb, mois_fin)
        # Colonnes specifiques (evite les colonnes qui n'existent pas
        # sur les autres partenaires)
        select_specific = "c.mois_p AS mois_p_query, "
        if part == "ENI":
            select_specific += (
                "c.gaz_car_declaree, c.gaz_car_relevee, c.elec_puissance, "
                "c.gaz_actif, c.elec_actif, "
            )

    sql = f"""
        SELECT c.id_contrat, c.id_salarie, c.num_bs,
               c.id_produit, c.id_etat_contrat, c.date_signature,
               c.nb_points,
               {select_specific}
               cli.nom AS client_nom, cli.prenom AS client_prenom,
               cli.cp AS client_cp, cli.ville AS client_ville,
               prod.lib_produit, prod.famille, prod.sous_fam,
               etat.lib_etat, etat.id_type_etat
          FROM adv.pgt_{prefix}_contrat c
          JOIN adv.pgt_{prefix}_produit prod
               ON c.id_produit = prod.id_produit
          JOIN adv.pgt_{prefix}_etat_contrat etat
               ON c.id_etat_contrat = etat.id_etat
          JOIN adv.pgt_client cli
               ON c.id_client = cli.id_client
         WHERE c.id_salarie = ?
           AND ({cond})
           AND (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
    """
    params = (int(id_salarie),) + cond_params
    return sql, params


# --------------------------------------------------------------------
# Enrichissement options ENI + SFR
# --------------------------------------------------------------------

def _enrichir_eni_options(rows: list[ContratRow]) -> None:
    """cf. WinDev AfficherOptionENI : lookup batch dans
    pgt_eni_contrat_option pour ajouter opt_energie_verte_*,
    opt_mail, opt_reforestation, opt_protection, opt_entretien.
    """
    ids = [int(r.id_contrat) for r in rows if r.partenaire == "ENI" and r.id_contrat]
    if not ids:
        return
    db = get_pg_connection("adv")
    ids_sql = ",".join(str(i) for i in ids)
    try:
        opts = db.query(
            f"""SELECT id_contrat, opt_energie_verte_elec, opt_energie_verte_gaz,
                       opt_mail, opt_reforestation, opt_protection, opt_entretien
                 FROM adv.pgt_eni_contrat_option
                WHERE id_contrat IN ({ids_sql})
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        ) or []
    except Exception:
        opts = []
    by_id = {int(o["id_contrat"]): o for o in opts}
    for r in rows:
        if r.partenaire != "ENI":
            continue
        o = by_id.get(int(r.id_contrat) if r.id_contrat else 0)
        if not o:
            continue
        r.opt_e_verte_elec = bool(o.get("opt_energie_verte_elec"))
        r.opt_e_verte_gaz = bool(o.get("opt_energie_verte_gaz"))
        r.opt_mail = bool(o.get("opt_mail"))
        r.opt_reforestation = bool(o.get("opt_reforestation"))
        r.opt_protection = bool(o.get("opt_protection"))
        r.opt_entretien = bool(o.get("opt_entretien"))


def _enrichir_sfr_options(rows: list[ContratRow]) -> None:
    """cf. WinDev AfficherOptionSFR : lookup batch dans pgt_sfr_contrat
    pour ajouter DateRDVTech, DateValidation, IDetatSFR, Technologie,
    Portabilite, Notation, PriseSaisie + calcul points auxiliaires.
    """
    ids = [int(r.id_contrat) for r in rows if r.partenaire == "SFR" and r.id_contrat]
    if not ids:
        return
    db = get_pg_connection("adv")
    ids_sql = ",".join(str(i) for i in ids)
    try:
        opts = db.query(
            f"""SELECT id_contrat, date_rdv_tech, date_validation,
                       id_etat_sfr, technologie, portabilite, notation,
                       prise_saisie
                 FROM adv.pgt_sfr_contrat
                WHERE id_contrat IN ({ids_sql})""",
        ) or []
    except Exception:
        opts = []
    by_id = {int(o["id_contrat"]): o for o in opts}
    for r in rows:
        if r.partenaire != "SFR":
            continue
        o = by_id.get(int(r.id_contrat) if r.id_contrat else 0)
        if not o:
            continue
        r.date_rdv_tech = _to_iso(o.get("date_rdv_tech"))
        r.date_validation = _to_iso(o.get("date_validation"))
        r.id_etat_sfr = int(o.get("id_etat_sfr") or 0)
        r.techno = int(o.get("technologie") or 0)
        r.portabilite = bool(o.get("portabilite"))
        note = float(o.get("notation") or 0)
        r.notation_client = note * 2
        r.prise_saisie = bool(o.get("prise_saisie"))
        r.pts_porta = 0.2 if o.get("portabilite") else 0.0
        r.pts_prises = 0.2 if o.get("prise_saisie") else 0.0
        r.pts_notation = 0.1 if r.notation_client >= 8.6 else 0.0


# --------------------------------------------------------------------
# Type etat (LibType via pgt_type_etat_contrat)
# --------------------------------------------------------------------

def _load_type_etats() -> dict[int, str]:
    """Cache statique des libelles TypeEtat (par id_type_etat)."""
    rh = get_pg_connection("adv")
    try:
        rows = rh.query(
            "SELECT id_type_etat, lib_type FROM adv.pgt_type_etat_contrat",
        ) or []
    except Exception:
        rows = []
    return {int(r["id_type_etat"]): (r.get("lib_type") or "").strip()
            for r in rows}


# --------------------------------------------------------------------
# Entree principale : lister_contrats
# --------------------------------------------------------------------

def lister_contrats(
    p: ListerContratsParams,
) -> ListerContratsResult:
    """Cf. WinDev Btn Lister les contrats.

    1. Recupere nom vendeur.
    2. Pour chaque partenaire actif : query dynamique.
    3. Skip contrats deja payes (type_etat 5/6) avec MoisP != mois cible.
    4. Enrichit options ENI + SFR.
    5. Calcule affectation historique par contrat.
    6. Calcule jours non-prod.
    7. Copie contrats decommission dans une liste separee.
    """
    # Validation
    if not p.id_salarie:
        return ListerContratsResult(ok=False, message="Salarie manquant")
    if len(p.mois_paiement) != 7 or p.mois_paiement[4] != "-":
        return ListerContratsResult(
            ok=False, message="Format mois_paiement invalide (YYYY-MM)",
        )
    partenaires_actifs = [
        pp for pp in p.partenaires
        if pp.is_actif and pp.prefixe.upper() in _KNOWN_PARTENAIRES
    ]
    if not partenaires_actifs:
        return ListerContratsResult(
            ok=False, message="Aucun partenaire selectionne",
        )

    # Recupere nom du vendeur pour affichage
    rh = get_pg_connection("rh")
    sal = rh.query_one(
        """SELECT nom, prenom
             FROM pgt_salarie WHERE id_salarie = ?""",
        (int(p.id_salarie),),
    )
    if not sal:
        return ListerContratsResult(
            ok=False, message=f"Salarie {p.id_salarie} introuvable",
        )
    vendeur_nom = (
        f"{(sal.get('nom') or '').strip()} "
        f"{_cap_prenom((sal.get('prenom') or '').strip())}"
    ).strip()

    # Preload : affectation historique + type etats
    date_min = min((pp.signe_du or pp.hors_delai_du or "1900-01-01")
                   for pp in partenaires_actifs)
    date_max = max((pp.signe_au or pp.hors_delai_au or "2100-12-31")
                   for pp in partenaires_actifs)
    date_max = max(date_max, _dernier_jour(p.mois_paiement))
    affectations = _load_affectations_batch(
        p.id_salarie, date_min[:10], date_max[:10],
    )
    type_etats = _load_type_etats()

    # Prepare structures
    contrats_signes: list[ContratRow] = []
    mois_deb = _premier_jour(p.mois_paiement)

    # Traite chaque partenaire
    db = get_pg_connection("adv")
    for pp in partenaires_actifs:
        prefix = pp.prefixe.upper()
        sql, params = _build_query(prefix, p.id_salarie, p.mois_paiement, pp)
        try:
            rows = db.query(sql, params) or []
        except Exception as e:
            logger.exception("Query %s KO", prefix)
            continue

        for r in rows:
            id_type_etat = int(r.get("id_type_etat") or 0)
            mois_p_ctt = _to_iso(r.get("mois_p_query"))

            # Skip contrats deja statue (5/6) avec MoisP != mois cible
            if id_type_etat in (5, 6) and mois_p_ctt:
                if mois_p_ctt[:7] != p.mois_paiement:
                    continue

            date_sign = _to_iso(r.get("date_signature"))
            agence, equipe = _affectation_at(affectations, date_sign)

            # Couleur : hors delai (jaune) si signature dans hors delai
            # et pas SFR ; rejet/resil (rouge) si type_etat 3/4.
            couleur = ""
            if id_type_etat in (3, 4):
                couleur = "rejet_resil"
            elif (prefix != "SFR"
                  and pp.hors_delai_du and pp.hors_delai_au
                  and pp.hors_delai_du <= date_sign <= pp.hors_delai_au):
                couleur = "hors_delai"

            # nb_points forcee a 0 si etat 3/4 (rejet/resil)
            nb_points = 0.0
            if id_type_etat not in (3, 4):
                nb_points = float(r.get("nb_points") or 0)

            row = ContratRow(
                id_contrat=_clean_id(r.get("id_contrat")),
                partenaire=prefix,
                lib_produit=(r.get("lib_produit") or "").strip(),
                type_prod=(
                    r.get("sous_fam") if prefix == "ENI"
                    else r.get("famille") or ""
                ) or "",
                num_bs=(r.get("num_bs") or "").strip(),
                date_signature=date_sign,
                id_type_etat=id_type_etat,
                type_etat=type_etats.get(id_type_etat, ""),
                id_etat=int(r.get("id_etat_contrat") or 0),
                etat_contrat=(r.get("lib_etat") or "").strip(),
                vendeur_nom=vendeur_nom,
                agence=agence, equipe=equipe,
                client_nom=_client_abbrev(
                    r.get("client_nom") or "",
                    r.get("client_prenom") or "",
                ),
                client_cp=(r.get("client_cp") or "").strip(),
                client_ville=(r.get("client_ville") or "").strip(),
                mois_paiement=mois_p_ctt,
                nb_points=nb_points,
                couleur_fond=couleur,
            )
            if prefix == "ENI":
                car_declaree = int(r.get("gaz_car_declaree") or 0)
                car_relevee = int(r.get("gaz_car_relevee") or 0)
                row.car = car_relevee if car_relevee > 0 else car_declaree
                row.elec_actif = bool(r.get("elec_actif"))
                row.gaz_actif = bool(r.get("gaz_actif"))
                row.puissance = int(r.get("elec_puissance") or 0)
            if prefix == "SFR":
                row.date_racc_valid = _to_iso(r.get("date_racc_activ"))
                row.type_vente = int(r.get("type_vente") or 0)
            contrats_signes.append(row)

    # Enrichissement options ENI/SFR
    _enrichir_eni_options(contrats_signes)
    _enrichir_sfr_options(contrats_signes)

    # Tri par date signature
    contrats_signes.sort(key=lambda x: x.date_signature)

    # Contrats decommission (onglet 2)
    contrats_decomm = [
        r for r in contrats_signes
        if "decommission" in r.type_etat.lower()
        or "décommission" in r.type_etat.lower()
    ]

    # Jours non-prod : jours ouvres non feries de chaque periode sans contrat
    jours_non_prod = _compute_jours_non_prod(
        contrats_signes, partenaires_actifs,
    )

    return ListerContratsResult(
        ok=True,
        contrats_signes=contrats_signes,
        contrats_decomm=contrats_decomm,
        jours_non_prod=jours_non_prod,
        has_eni=any(r.partenaire == "ENI" for r in contrats_signes),
        has_sfr=any(r.partenaire == "SFR" for r in contrats_signes),
        message=f"{len(contrats_signes)} contrat(s) trouve(s)",
    )


def _compute_jours_non_prod(
    contrats: list[ContratRow], partenaires: list[PartenairePeriode],
) -> list[JourNonProd]:
    """Cf. WinDev : liste des jours ouvres non feries de la periode signee
    de chaque partenaire, retire les jours qui ont au moins un contrat signe.

    Retour : liste triee par jour croissant.
    """
    # Determine la periode globale
    dates_min = [pp.signe_du for pp in partenaires if pp.signe_du]
    dates_max = [pp.signe_au for pp in partenaires if pp.signe_au]
    if not dates_min or not dates_max:
        return []
    d_min = min(dates_min)
    d_max = max(dates_max)
    try:
        cur = date.fromisoformat(d_min[:10])
        end = date.fromisoformat(d_max[:10])
    except Exception:
        return []

    # Feries
    feries = set()
    for y in range(cur.year, end.year + 1):
        feries |= _jours_feries_fr(y)

    # Jours ayant au moins un contrat (par partenaire)
    contrats_par_jour_par_part: dict[date, set[str]] = {}
    for c in contrats:
        try:
            d = date.fromisoformat(c.date_signature[:10])
        except Exception:
            continue
        contrats_par_jour_par_part.setdefault(d, set()).add(c.partenaire)

    result: list[JourNonProd] = []
    while cur <= end:
        # Ferie ou weekend (lundi=0, dimanche=6 : on saute 5=samedi, 6=dimanche)
        if cur.weekday() >= 5 or cur in feries:
            cur += timedelta(days=1)
            continue
        parts_du_jour = contrats_par_jour_par_part.get(cur, set())
        # Un partenaire est marque "non-prod" pour ce jour s'il n'a AUCUN
        # contrat signe ce jour-la (dans les partenaires actifs).
        actifs_prefix = {pp.prefixe.upper() for pp in partenaires}
        jour = JourNonProd(
            jour=cur.isoformat(),
            eni=("ENI" in actifs_prefix) and ("ENI" not in parts_du_jour),
            fibre=("SFR" in actifs_prefix) and ("SFR" not in parts_du_jour),
        )
        if jour.eni or jour.fibre:
            result.append(jour)
        cur += timedelta(days=1)

    return result


# --------------------------------------------------------------------
# Btn 'Valider les paies' + calcul TR + histo contrat
# --------------------------------------------------------------------

# Dispatch histo par partenaire (reutilise les helpers deja implementes
# dans chaque service import_{part}). cf. pattern import_masse._ajoute_histo.
def _dispatch_histo_etat(
    partenaire: str, id_contrat: int, old_etat: int,
    new_etat: int, date_paiement: str, op_id: int,
) -> None:
    """Delegue au helper _ajoute_histo_{part}_etat du service import
    correspondant. Categorie 'Vend' (mode vendeur, cf. WinDev).
    """
    p = partenaire.lower()
    try:
        if p == "sfr":
            from app.intranets.adm.services.import_sfr import (
                _ajoute_histo_sfr_etat,
            )
            _ajoute_histo_sfr_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
                categorie="Vend",
            )
        elif p == "eni":
            from app.intranets.adm.services.import_eni import (
                _ajoute_histo_eni_etat,
            )
            _ajoute_histo_eni_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
            )
        elif p == "iag":
            from app.intranets.adm.services.import_iag import (
                _ajoute_histo_iag_etat,
            )
            _ajoute_histo_iag_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
            )
        elif p == "pro":
            from app.intranets.adm.services.import_pro import (
                _ajoute_histo_pro_etat,
            )
            _ajoute_histo_pro_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
            )
        elif p == "oen":
            from app.intranets.adm.services.import_oen import (
                _ajoute_histo_oen_etat,
            )
            _ajoute_histo_oen_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
                categorie="Vend",
            )
        elif p == "str":
            from app.intranets.adm.services.import_str import (
                _ajoute_histo_str_etat,
            )
            _ajoute_histo_str_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
            )
        elif p == "val":
            from app.intranets.adm.services.import_val import (
                _ajoute_histo_val_etat,
            )
            _ajoute_histo_val_etat(
                id_contrat, old_etat, new_etat, date_paiement, op_id,
            )
    except Exception:
        logger.exception("histo etat %s (id=%s)", partenaire, id_contrat)


def valider_paies(
    p: ValiderPaiesParams, op_id: int,
) -> ValiderPaiesResult:
    """Cf. WinDev Btn Valider les paies.

    Pour chaque contrat en input :
      1. Cas SFR + type_etat=8 + date_racc_valid <= date_racc_limite ->
         nouvel etat = 6 (Paye par employeur - Raccordement) + UPDATE
         SFR (mois_p_ra + nb_pts_payes_ra) + histo etat.
      2. Autres partenaires + type_etat=3/4 (Rejet/Resil) -> mois_paiement
         = "" (reset, pas d'UPDATE en BDD).
      3. Sinon : rien (contrat inchange).

    Puis calcul TR (Titres Restaurant) :
      - Partenaires eligibles : ENI, IAG, STR, SFR-FIBRE
      - Etats eligibles : type_etat contenant RESI, VALID,
        ou "En ATTENTE Operateur"
      - Type 1 (ENI/IAG/STR) : 3 ctts/jour = 1 TR
      - Type 2 (SFR-Fibre)   : 1 ctt/jour  = 1 TR
    """
    if not p.contrats:
        return ValiderPaiesResult(
            ok=True, message="Aucun contrat a valider",
        )
    mois_deb = _premier_jour(p.mois_paiement)
    date_racc_limite = p.date_racc_limite or "1900-01-01"

    contrats_maj: list[ContratMajResult] = []
    nb_updated = 0
    db = get_pg_connection("adv")
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for c in p.contrats:
        etat_final = c.id_etat
        type_etat_final = c.type_etat
        etat_lib_final = c.etat_contrat
        date_p = c.mois_paiement
        opt_maj = False  # True si UPDATE metier a faire

        # Cas SFR + Raccorde
        if (c.partenaire == "SFR" and c.id_type_etat == 8
                and c.date_racc_valid
                and c.date_racc_valid <= date_racc_limite):
            etat_final = 6  # Paye par employeur - Raccordement
            type_etat_final = "Validé-Payé"
            etat_lib_final = "Payé par employeur - Raccordement"
            date_p = mois_deb
            opt_maj = True

        # Cas Rejet/Resil (autres partenaires)
        elif c.partenaire != "SFR" and c.id_type_etat in (3, 4):
            date_p = ""  # reset mois paiement (pas d'UPDATE, juste affichage)

        updated_this = False

        # UPDATE + histo si non-simu + optMoisPaiement non vide
        if not p.simulation and opt_maj:
            try:
                prefix = c.partenaire.lower()
                if c.partenaire == "SFR":
                    # UPDATE SFR : id_etat + mois_p_ra + nb_pts_payes_ra
                    db.query(
                        f"""UPDATE adv.pgt_{prefix}_contrat
                              SET id_etat_contrat = ?,
                                  mois_p_ra = ?,
                                  nb_pts_payes_ra = ?,
                                  modif_date = ?, modif_op = ?,
                                  modif_elem = 'modif'
                            WHERE id_contrat = ?""",
                        (int(etat_final), date_p or None,
                         float(c.nb_points), now_iso, int(op_id),
                         int(c.id_contrat)),
                    )
                else:
                    # Autres partenaires (pas de cas UPDATE identifie dans
                    # le TXT WinDev - opt_maj reste False sur non-SFR).
                    db.query(
                        f"""UPDATE adv.pgt_{prefix}_contrat
                              SET id_etat_contrat = ?,
                                  modif_date = ?, modif_op = ?,
                                  modif_elem = 'modif'
                            WHERE id_contrat = ?""",
                        (int(etat_final), now_iso, int(op_id),
                         int(c.id_contrat)),
                    )
                # Histo etat
                _dispatch_histo_etat(
                    c.partenaire, int(c.id_contrat),
                    c.id_etat, etat_final, date_p, op_id,
                )
                updated_this = True
                nb_updated += 1
            except Exception:
                logger.exception("UPDATE contrat KO (id=%s)", c.id_contrat)

        contrats_maj.append(ContratMajResult(
            id_contrat=c.id_contrat,
            partenaire=c.partenaire,
            id_etat=etat_final,
            id_type_etat=c.id_type_etat if not opt_maj else 5,
            etat_contrat=etat_lib_final,
            type_etat=type_etat_final,
            mois_paiement=date_p,
            updated=updated_this,
        ))

    # -------- Calcul TR --------
    # Compte par jour (partenaire eligible + etat eligible)
    from collections import defaultdict
    nb_par_jour: dict[str, dict] = defaultdict(
        lambda: {"nb": 0, "type": 1}
    )
    for cm in contrats_maj:
        # Prend le contrat d'origine pour re-verifier le partenaire/type
        orig = next(
            (x for x in p.contrats
             if x.id_contrat == cm.id_contrat
             and x.partenaire == cm.partenaire),
            None,
        )
        if not orig:
            continue
        # Partenaire eligible
        is_eni_like = orig.partenaire in ("ENI", "IAG", "STR")
        is_sfr_fibre = (orig.partenaire == "SFR"
                       and (orig.type_prod or "").upper() == "FIBRE")
        if not (is_eni_like or is_sfr_fibre):
            continue
        # Etat eligible (post-validation - on utilise cm.type_etat qui
        # a ete recalcule)
        te = (cm.type_etat or "").upper()
        # cf. WinDev : Contient(Type_Etat,"RESI") ou Contient(..., "VALID")
        # ou Type_Etat = "En ATTENTE Operateur"
        if not ("RESI" in te or "VALID" in te
                or te == "EN ATTENTE OPERATEUR"
                or te == "EN ATTENTE OPÉRATEUR"):
            continue
        jour = orig.date_signature[:10] if orig.date_signature else ""
        if not jour:
            continue
        nb_par_jour[jour]["nb"] += 1
        nb_par_jour[jour]["type"] = 2 if is_sfr_fibre else 1

    nb_tr = 0
    rows_par_jour: list[NbCttParJourRow] = []
    for jour, info in sorted(nb_par_jour.items()):
        rows_par_jour.append(NbCttParJourRow(
            date_ctt=jour, nb_ctt=info["nb"], type_ctt=info["type"],
        ))
        if info["type"] == 1 and info["nb"] >= 3:
            nb_tr += 1  # ENI/IAG/STR : 3 ctts/j = 1 TR
        elif info["type"] == 2 and info["nb"] >= 1:
            nb_tr += 1  # SFR-Fibre : 1 ctt/j = 1 TR

    return ValiderPaiesResult(
        ok=True,
        contrats_maj=contrats_maj,
        nb_ctt_par_jour=rows_par_jour,
        nb_tr=nb_tr,
        nb_updated=nb_updated,
        message=(
            f"{nb_updated} contrat(s) mis a jour, {nb_tr} TR calcule(s). "
            + ("(SIMULATION)" if p.simulation else "")
        ),
    )
