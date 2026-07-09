"""
Service Fen_ScoolStagiaire_Fiche - Fiche detaillee d'un stagiaire.

Cf. WinDev Fen_ScoolStagiaire_Fiche(IDformation, idStagiaire, TypeProd).

Compose la fiche complete :
  - Header (Formation_salarie + Formation + Salarie)
  - Onglet Declaratif Presence : merge programme + salarie_decl_presence
  - Onglet Production ENI/SFR : programme + presences + ADF + contrats + coopt
  - Calcul objectifs et ratios cf. CalculObjectifEni/CalculObjectifFibre
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.scool_stagiaire_fiche import (
    AjoutLigneProdPayload, MotifAbsenceCombo, PresenceRow,
    ProdEniRow, ProdSfrRow, RecapPresence,
    ScoolStagiaireFiche, StagiaireHeaderPayload,
)


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _iso_date(v) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000"):
        return ""
    return s


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper()


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


# --------------------------------------------------------------------
# Combos
# --------------------------------------------------------------------

def list_motifs_absence() -> list[MotifAbsenceCombo]:
    """Combo motif absence (pgt_type_absence)."""
    db = get_pg_connection("rh")
    try:
        rows = db.query(
            """SELECT id_type_absence, lib_absence
                 FROM pgt_type_absence
                WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY id_type_absence ASC""",
        ) or []
    except Exception:
        logger.exception("list_motifs_absence")
        return []
    return [
        MotifAbsenceCombo(
            id_type_absence=int(r.get("id_type_absence") or 0),
            lib_absence=(r.get("lib_absence") or "").strip(),
        )
        for r in rows
    ]


# --------------------------------------------------------------------
# Header : Formation_salarie + Formation + Salarie
# --------------------------------------------------------------------

def _load_header(
    id_formation: int, id_salarie: int, type_prod: str,
) -> ScoolStagiaireFiche | None:
    """Cf. WinDev Code init : HLitRecherche Formation_salarié + Formation
    + DonneInfoSalarié.
    """
    scool = get_pg_connection("scool")
    rh = get_pg_connection("rh")

    try:
        fs = scool.query_one(
            """SELECT date_debut, date_fin, livrable
                 FROM scool.pgt_formation_salarie
                WHERE id_formation = ? AND id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_formation, id_salarie),
        )
    except Exception:
        logger.exception("_load_header formation_salarie")
        fs = None
    if not fs:
        return None

    try:
        f = scool.query_one(
            """SELECT intitule, categorie, heure_jour_salle, heure_jour_terrain
                 FROM scool.pgt_formation
                WHERE id_formation = ?""",
            (id_formation,),
        )
    except Exception:
        logger.exception("_load_header formation")
        f = None

    try:
        s = rh.query_one(
            """SELECT nom, prenom
                 FROM pgt_salarie
                WHERE id_salarie = ?""",
            (id_salarie,),
        )
    except Exception:
        s = None

    # Axes de travail : salarie_adf pour la formation (une ligne / date)
    # On prend le dernier renseigne dans la periode formation
    axe1 = ""
    axe2 = ""
    try:
        adf = rh.query_one(
            """SELECT axe_travail1, axe_travail2
                 FROM pgt_salarie_adf
                WHERE id_salarie = ?
                  AND date BETWEEN ? AND ?
                  AND (COALESCE(axe_travail1, '') <> ''
                       OR COALESCE(axe_travail2, '') <> '')
                ORDER BY date DESC
                LIMIT 1""",
            (id_salarie, fs.get("date_debut"), fs.get("date_fin")),
        )
        if adf:
            axe1 = (adf.get("axe_travail1") or "").strip()
            axe2 = (adf.get("axe_travail2") or "").strip()
    except Exception:
        pass

    nom = (s or {}).get("nom") or ""
    prenom = _cap_prenom(((s or {}).get("prenom") or "").strip())

    return ScoolStagiaireFiche(
        id_formation=str(id_formation),
        id_salarie=str(id_salarie),
        nom_prenom=f"{nom.strip()} {prenom}".strip(),
        lib_formation=((f or {}).get("intitule") or "").strip(),
        date_debut=_iso_date(fs.get("date_debut")),
        date_fin=_iso_date(fs.get("date_fin")),
        niveau_form=((f or {}).get("categorie") or "").strip(),
        heure_jour_salle=float((f or {}).get("heure_jour_salle") or 8),
        heure_jour_terrain=float((f or {}).get("heure_jour_terrain") or 8),
        type_prod=type_prod,
        axe_travail_1=axe1,
        axe_travail_2=axe2,
        livrable=bool(fs.get("livrable")),
    )


# --------------------------------------------------------------------
# ProgrammeFormation : cree les lignes prod par date
# --------------------------------------------------------------------

def _load_programme(
    id_formation: int, date_debut: str, date_fin: str,
) -> list[dict]:
    """Cf. WinDev reqProgForm."""
    if not date_debut or not date_fin:
        return []
    scool = get_pg_connection("scool")
    try:
        rows = scool.query(
            """SELECT date, salle, terrain, duree,
                      num_semaine, horaires, objectif
                 FROM scool.pgt_formation_programme
                WHERE id_formation = ?
                  AND (modif_elem IS NULL
                       OR modif_elem NOT LIKE '%suppr%')
                  AND date BETWEEN ? AND ?
                ORDER BY num_semaine ASC, date ASC""",
            (id_formation, date_debut, date_fin),
        ) or []
    except Exception:
        logger.exception("_load_programme")
        return []
    return rows


# --------------------------------------------------------------------
# DeclaratifPresence : populate Table_Presence + recap
# --------------------------------------------------------------------

def _load_presences(
    id_salarie: int, date_debut: str, date_fin: str,
) -> tuple[dict[str, PresenceRow], RecapPresence]:
    """Cf. WinDev DeclaratifPresence.
    Retourne dict{date: PresenceRow} + recap.
    """
    presences: dict[str, PresenceRow] = {}
    recap = RecapPresence()
    if not date_debut or not date_fin:
        return presences, recap

    rh = get_pg_connection("rh")
    try:
        # + jointure type_absence pour recuperer le libelle motif
        rows = rh.query(
            """SELECT sdp.date, sdp.presence, sdp.motifabsence,
                      sdp.periode_absence, sdp.type_journee,
                      LENGTH(COALESCE(sdp.emargement_matin, '')) AS emarg_m,
                      LENGTH(COALESCE(sdp.emargement_aprem, '')) AS emarg_a,
                      ta.lib_absence
                 FROM pgt_salarie_decl_presence sdp
                 LEFT JOIN pgt_type_absence ta
                        ON ta.id_type_absence = sdp.motifabsence
                WHERE sdp.id_salarie = ?
                  AND sdp.date BETWEEN ? AND ?
                  AND (sdp.modif_elem IS NULL
                       OR sdp.modif_elem NOT LIKE '%suppr%')""",
            (id_salarie, date_debut, date_fin),
        ) or []
    except Exception:
        logger.exception("_load_presences")
        return presences, recap

    for r in rows:
        d = _iso_date(r.get("date"))
        if not d:
            continue
        pres = 1 if r.get("presence") else 0
        motif = int(r.get("motifabsence") or 0)
        periode = int(r.get("periode_absence") or 0)
        # WinDev : motif 6 = "present" en realite
        if motif == 6:
            pres = 1
            motif = 0

        lib_motif = ""
        jour_pres = 0.0
        if pres == 0:
            lib_motif = (r.get("lib_absence") or "").strip()
            # Periode < 3 = demi-journee
            if periode < 3:
                pres = -1
                jour_pres = 0.5
        else:
            jour_pres = 1.0

        row = PresenceRow(
            date=d,
            type_journee=int(r.get("type_journee") or 1),
            presence=pres,
            id_motif=motif,
            motif_absence=lib_motif,
            periode=periode,
            emarg_matin=int(r.get("emarg_m") or 0) > 0,
            emarg_aprem=int(r.get("emarg_a") or 0) > 0,
        )
        presences[d] = row

        recap.total_jours += jour_pres
        if row.type_journee == 1:
            recap.nb_jours_salle += jour_pres
        else:
            recap.nb_jours_terrain += jour_pres

    return presences, recap


# --------------------------------------------------------------------
# DeclaratifProduction : ADF par jour
# --------------------------------------------------------------------

def _load_adf_by_date(
    id_salarie: int, date_debut: str, date_fin: str,
) -> dict[str, int]:
    """Cf. WinDev ReqDeclADFByStagiaireByDate (SUM nbADF grp date)."""
    out: dict[str, int] = {}
    if not date_debut or not date_fin:
        return out
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT date, SUM(nb_adf) AS s_adf
                 FROM pgt_salarie_decl_production
                WHERE id_salarie = ?
                  AND date BETWEEN ? AND ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                GROUP BY date""",
            (id_salarie, date_debut, date_fin),
        ) or []
    except Exception:
        logger.exception("_load_adf_by_date")
        return out
    for r in rows:
        d = _iso_date(r.get("date"))
        if d:
            out[d] = int(r.get("s_adf") or 0)
    return out


# --------------------------------------------------------------------
# Cooptations par date
# --------------------------------------------------------------------

def _load_coopt_by_date(
    id_salarie: int, date_debut: str, date_fin: str,
) -> dict[str, int]:
    """Cf. WinDev ReqProdCoopt : cvtheque avec id_cvsource=1
    et id_elem_source = stagiaire."""
    out: dict[str, int] = {}
    if not date_debut or not date_fin:
        return out
    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT date_saisie, COUNT(*) AS n
                 FROM recrutement.pgt_cvtheque
                WHERE id_cvsource = 1
                  AND id_elem_source = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                  AND date_saisie BETWEEN ? AND ?
                GROUP BY date_saisie""",
            (id_salarie, date_debut, date_fin),
        ) or []
    except Exception:
        logger.exception("_load_coopt_by_date")
        return out
    for r in rows:
        d = _iso_date(r.get("date_saisie"))
        if d:
            out[d] = int(r.get("n") or 0)
    return out


# --------------------------------------------------------------------
# ProdReelleENI : contrats 4 societes (ENI + IAG + STR + TLC)
# --------------------------------------------------------------------

_ENI_OPT_COLS = (
    ", SUM(o.opt_mail) AS s_mail"
    ", SUM(o.opt_energie_verte_gaz) AS s_gv"
    ", SUM(o.opt_energie_verte_elec) AS s_ev"
)


def _load_contrats_eni(
    id_salarie: int, date_debut: str, date_fin: str,
) -> list[dict]:
    """Cf. WinDev ProdReelleENI : 4 societes, groupe par famille/sous_fam.
    Chaque row a : date, part ('ENI'/'IAG'/'STR'/'TLC'), famille, sous_fam,
    n, s_mail, s_gv, s_ev.
    """
    if not date_debut or not date_fin:
        return []
    adv = get_pg_connection("adv")
    out: list[dict] = []
    for part in ("eni", "iag", "str", "tlc"):
        if part == "eni":
            sql = f"""SELECT c.date_signature AS d,
                             p.famille, p.sous_fam,
                             COUNT(c.id_contrat) AS n
                             {_ENI_OPT_COLS}
                        FROM adv.pgt_{part}_produit p
                        JOIN adv.pgt_{part}_contrat c
                          ON c.id_produit = p.id_produit
                        JOIN adv.pgt_{part}_contrat_option o
                          ON o.id_contrat = c.id_contrat
                       WHERE (c.modif_elem IS NULL
                              OR c.modif_elem NOT LIKE '%suppr%')
                         AND c.id_salarie = ?
                         AND c.date_signature BETWEEN ? AND ?
                       GROUP BY c.date_signature, p.famille, p.sous_fam
                       ORDER BY d ASC"""
        else:
            sql = f"""SELECT c.date_signature AS d,
                             p.famille, p.sous_fam,
                             COUNT(c.id_contrat) AS n
                        FROM adv.pgt_{part}_produit p
                        JOIN adv.pgt_{part}_contrat c
                          ON c.id_produit = p.id_produit
                       WHERE (c.modif_elem IS NULL
                              OR c.modif_elem NOT LIKE '%suppr%')
                         AND c.id_salarie = ?
                         AND c.date_signature BETWEEN ? AND ?
                       GROUP BY c.date_signature, p.famille, p.sous_fam
                       ORDER BY d ASC"""
        try:
            rows = adv.query(sql, (id_salarie, date_debut, date_fin)) or []
        except Exception:
            logger.exception("_load_contrats_eni part=%s", part)
            rows = []
        for r in rows:
            r["part"] = part.upper()
            out.append(r)
    return out


def _load_contrats_sfr(
    id_salarie: int, date_debut: str, date_fin: str,
) -> list[dict]:
    """Cf. WinDev ProdReelleFibre : 4 societes (SFR + IAG + STR + TLC).
    Chaque row : date, famille, sous_fam, n, type_vente (SFR seul).
    """
    if not date_debut or not date_fin:
        return []
    adv = get_pg_connection("adv")
    out: list[dict] = []
    for part in ("sfr", "iag", "str", "tlc"):
        if part == "sfr":
            sql = f"""SELECT c.date_signature AS d,
                             p.famille, p.sous_fam,
                             c.type_vente,
                             COUNT(c.id_contrat) AS n
                        FROM adv.pgt_{part}_produit p
                        JOIN adv.pgt_{part}_contrat c
                          ON c.id_produit = p.id_produit
                       WHERE (c.modif_elem IS NULL
                              OR c.modif_elem NOT LIKE '%suppr%')
                         AND c.id_salarie = ?
                         AND c.date_signature BETWEEN ? AND ?
                       GROUP BY c.date_signature, p.famille, p.sous_fam,
                                c.type_vente
                       ORDER BY d ASC"""
        else:
            sql = f"""SELECT c.date_signature AS d,
                             p.famille, p.sous_fam,
                             COUNT(c.id_contrat) AS n
                        FROM adv.pgt_{part}_produit p
                        JOIN adv.pgt_{part}_contrat c
                          ON c.id_produit = p.id_produit
                       WHERE (c.modif_elem IS NULL
                              OR c.modif_elem NOT LIKE '%suppr%')
                         AND c.id_salarie = ?
                         AND c.date_signature BETWEEN ? AND ?
                       GROUP BY c.date_signature, p.famille, p.sous_fam
                       ORDER BY d ASC"""
        try:
            rows = adv.query(sql, (id_salarie, date_debut, date_fin)) or []
        except Exception:
            logger.exception("_load_contrats_sfr part=%s", part)
            rows = []
        for r in rows:
            r["part"] = part.upper()
            out.append(r)
    return out


# --------------------------------------------------------------------
# Calcul objectif ENI (cf. CalculObjectifEni)
# --------------------------------------------------------------------

def _calc_obj_bs_jour(
    rank_terrain: int, niveau_form: str, terrain: float,
) -> float:
    """Cf. WinDev : N1 -> palier 5 jours (2/3/4/5), sinon 5*terrain."""
    if terrain <= 0:
        return 0.0
    if niveau_form != "N1":
        return 5 * terrain
    if rank_terrain <= 5:
        return 2 * terrain
    if rank_terrain <= 10:
        return 3 * terrain
    if rank_terrain <= 15:
        return 4 * terrain
    return 5 * terrain


def _calc_objectifs_eni(rows: list[ProdEniRow], niveau_form: str) -> None:
    """Cf. WinDev CalculObjectifEni. Trie par date, calcule objectifs et
    ratios sur place.
    """
    rows.sort(key=lambda r: r.date)
    nb_jour_terrain = 0
    for r in rows:
        if r.terrain > 0:
            nb_jour_terrain += 1
            r.objectif_bs_jour = _calc_obj_bs_jour(
                nb_jour_terrain, niveau_form, r.terrain,
            )
        if r.objectif_bs_jour > 0:
            r.objectif = r.total_ctt / r.objectif_bs_jour

        nb_gz = r.eni_gaz + r.eni_dual
        if nb_gz > 0:
            r.pourcent_dual = r.eni_dual / nb_gz

        nb_eni = nb_gz + r.eni_elec
        if nb_eni > 0:
            r.pourcent_elec = r.eni_elec / nb_eni
            r.pourcent_mail = r.eni_mail / nb_eni
            r.pourcent_gv = r.eni_gaz_vert / nb_eni
            r.pourcent_ev = r.eni_elec_verte / nb_eni

        if r.total_ctt > 0:
            r.pourcent_adf = r.total_adf / r.total_ctt
            r.pourcent_presse = r.presse / r.total_ctt


def _calc_objectifs_sfr(rows: list[ProdSfrRow], niveau_form: str) -> None:
    """Cf. WinDev CalculObjectifFibre."""
    rows.sort(key=lambda r: r.date)
    nb_jour_terrain = 0
    for r in rows:
        if r.terrain > 0:
            nb_jour_terrain += 1
            r.objectif_bs_jour = _calc_obj_bs_jour(
                nb_jour_terrain, niveau_form, r.terrain,
            )
        if r.objectif_bs_jour > 0:
            r.objectif = r.total_ctt / r.objectif_bs_jour
        if r.total_ctt > 0:
            r.pourcent_adf = r.total_adf / r.total_ctt
            r.pourcent_presse = r.presse / r.total_ctt


# --------------------------------------------------------------------
# Fabrique de lignes ENI (fusion programme + presence + adf + contrats)
# --------------------------------------------------------------------

def _build_prod_eni(
    programme: list[dict],
    presences: dict[str, PresenceRow],
    adf: dict[str, int],
    contrats: list[dict],
    coopt: dict[str, int],
) -> list[ProdEniRow]:
    """Cf. WinDev ProdReelleENI. Fusionne toutes les sources par date."""
    idx: dict[str, ProdEniRow] = {}

    def _ensure(date: str, num_sem: int = 1) -> ProdEniRow:
        if date not in idx:
            idx[date] = ProdEniRow(
                date=date,
                num_sem=num_sem,
                sem_prod=f"Semaine {num_sem}",
            )
        return idx[date]

    # Programme
    for p in programme:
        d = _iso_date(p.get("date"))
        if not d:
            continue
        row = _ensure(d, int(p.get("num_semaine") or 1))
        row.salle = float(p.get("salle") or 0)
        row.terrain = float(p.get("terrain") or 0)
        row.duree = float(p.get("duree") or 0)

    # Presence -> Absent/Present
    for d, pres in presences.items():
        row = _ensure(d)
        if pres.presence == 0:
            row.absent = 1.0
        elif pres.presence == 1:
            row.present = 1.0
        else:
            row.absent = 0.5
            row.present = 0.5

    # ADF
    for d, n in adf.items():
        row = _ensure(d)
        row.total_adf = n

    # Contrats
    for c in contrats:
        d = _iso_date(c.get("d"))
        if not d:
            continue
        row = _ensure(d)
        fam = (c.get("famille") or "").upper().strip()
        sf = (c.get("sous_fam") or "").upper().strip()
        n = int(c.get("n") or 0)
        s_mail = int(c.get("s_mail") or 0)
        s_gv = int(c.get("s_gv") or 0)
        s_ev = int(c.get("s_ev") or 0)

        if fam == "ENI":
            row.eni_mail += s_mail
            if sf == "GAZ":
                row.eni_gaz += n
                row.eni_gaz_vert += s_gv
                row.total_ctt += n
            elif sf == "ELEC":
                row.eni_elec += n
                row.eni_elec_verte += s_ev
            else:
                # Dual
                row.eni_dual += n
                row.eni_gaz_vert += s_gv
                row.eni_elec_verte += s_ev
                row.total_ctt += n
        elif fam == "ASSU":
            row.assu += n
            row.total_ctt += n
        elif fam == "PRESSE":
            row.presse += n

    # Cooptations
    for d, n in coopt.items():
        row = _ensure(d)
        row.cooptation += n

    return list(idx.values())


def _build_prod_sfr(
    programme: list[dict],
    presences: dict[str, PresenceRow],
    adf: dict[str, int],
    contrats: list[dict],
    coopt: dict[str, int],
) -> list[ProdSfrRow]:
    """Cf. WinDev ProdReelleFibre."""
    idx: dict[str, ProdSfrRow] = {}

    def _ensure(date: str, num_sem: int = 1) -> ProdSfrRow:
        if date not in idx:
            idx[date] = ProdSfrRow(
                date=date,
                num_sem=num_sem,
                sem_prod=f"Semaine {num_sem}",
            )
        return idx[date]

    for p in programme:
        d = _iso_date(p.get("date"))
        if not d:
            continue
        row = _ensure(d, int(p.get("num_semaine") or 1))
        row.salle = float(p.get("salle") or 0)
        row.terrain = float(p.get("terrain") or 0)
        row.duree = float(p.get("duree") or 0)

    for d, pres in presences.items():
        row = _ensure(d)
        if pres.presence == 0:
            row.absent = 1.0
        elif pres.presence == 1:
            row.present = 1.0
        else:
            row.absent = 0.5
            row.present = 0.5

    for d, n in adf.items():
        row = _ensure(d)
        row.total_adf = n

    for c in contrats:
        d = _iso_date(c.get("d"))
        if not d:
            continue
        row = _ensure(d)
        fam = (c.get("famille") or "").upper().strip()
        sf = (c.get("sous_fam") or "").strip()
        n = int(c.get("n") or 0)
        type_vente = int(c.get("type_vente") or 0)

        if fam == "FIBRE":
            # Migration : type_vente 3 ou 4
            if type_vente in (3, 4):
                row.migration += n
            else:
                sf_key = sf.replace(" ", "").upper()
                if sf_key == "POWER8":
                    row.power8 += n
                elif sf_key == "FIBRE8":
                    row.fibre8 += n
                elif sf_key == "POWER":
                    row.power += n
                elif sf_key == "PREMIUM":
                    row.premium += n
            row.total_ctt += n
        elif fam == "MOBILE":
            row.mobile += n
            row.total_ctt += n
        elif fam == "ASSU":
            row.assu += n
            row.total_ctt += n
        elif fam == "PRESSE":
            row.presse += n

    for d, n in coopt.items():
        row = _ensure(d)
        row.cooptation += n

    return list(idx.values())


# --------------------------------------------------------------------
# Totaux formation
# --------------------------------------------------------------------

def _compute_totaux_eni(fiche: ScoolStagiaireFiche) -> None:
    fiche.tot_salle = sum(r.salle for r in fiche.prod_eni)
    fiche.tot_terrain = sum(r.terrain for r in fiche.prod_eni)
    fiche.tot_duree = sum(r.duree for r in fiche.prod_eni)
    fiche.tot_absent = sum(r.absent for r in fiche.prod_eni)
    fiche.tot_present = sum(r.present for r in fiche.prod_eni)
    fiche.tot_obj_bs = sum(r.objectif_bs_jour for r in fiche.prod_eni)
    fiche.tot_ctt = sum(r.total_ctt for r in fiche.prod_eni)
    fiche.tot_adf = sum(r.total_adf for r in fiche.prod_eni)
    fiche.tot_presse = sum(r.presse for r in fiche.prod_eni)
    fiche.tot_assu = sum(r.assu for r in fiche.prod_eni)
    fiche.tot_coopt = sum(r.cooptation for r in fiche.prod_eni)


def _compute_totaux_sfr(fiche: ScoolStagiaireFiche) -> None:
    fiche.tot_salle = sum(r.salle for r in fiche.prod_sfr)
    fiche.tot_terrain = sum(r.terrain for r in fiche.prod_sfr)
    fiche.tot_duree = sum(r.duree for r in fiche.prod_sfr)
    fiche.tot_absent = sum(r.absent for r in fiche.prod_sfr)
    fiche.tot_present = sum(r.present for r in fiche.prod_sfr)
    fiche.tot_obj_bs = sum(r.objectif_bs_jour for r in fiche.prod_sfr)
    fiche.tot_ctt = sum(r.total_ctt for r in fiche.prod_sfr)
    fiche.tot_adf = sum(r.total_adf for r in fiche.prod_sfr)
    fiche.tot_presse = sum(r.presse for r in fiche.prod_sfr)
    fiche.tot_assu = sum(r.assu for r in fiche.prod_sfr)
    fiche.tot_coopt = sum(r.cooptation for r in fiche.prod_sfr)


# --------------------------------------------------------------------
# API principale : get_fiche_stagiaire
# --------------------------------------------------------------------

def get_fiche_stagiaire(
    id_formation: str, id_salarie: str, type_prod: str,
) -> ScoolStagiaireFiche | None:
    """Cf. WinDev Code init + init : construit la fiche complete."""
    if not id_formation or not id_salarie:
        return None
    try:
        id_form = int(id_formation)
        id_sal = int(id_salarie)
    except (TypeError, ValueError):
        return None

    tp = (type_prod or "").upper().strip()
    fiche = _load_header(id_form, id_sal, tp)
    if not fiche:
        return None

    # Sources communes
    programme = _load_programme(id_form, fiche.date_debut, fiche.date_fin)
    presences, recap = _load_presences(
        id_sal, fiche.date_debut, fiche.date_fin,
    )
    adf = _load_adf_by_date(id_sal, fiche.date_debut, fiche.date_fin)
    coopt = _load_coopt_by_date(id_sal, fiche.date_debut, fiche.date_fin)

    fiche.presence = sorted(presences.values(), key=lambda p: p.date)
    fiche.recap_presence = recap

    if tp == "ENI":
        contrats = _load_contrats_eni(
            id_sal, fiche.date_debut, fiche.date_fin,
        )
        fiche.prod_eni = _build_prod_eni(
            programme, presences, adf, contrats, coopt,
        )
        _calc_objectifs_eni(fiche.prod_eni, fiche.niveau_form)
        _compute_totaux_eni(fiche)
    elif tp == "SFR":
        contrats = _load_contrats_sfr(
            id_sal, fiche.date_debut, fiche.date_fin,
        )
        fiche.prod_sfr = _build_prod_sfr(
            programme, presences, adf, contrats, coopt,
        )
        _calc_objectifs_sfr(fiche.prod_sfr, fiche.niveau_form)
        _compute_totaux_sfr(fiche)

    return fiche


# --------------------------------------------------------------------
# Enregistrer : maj Formation_salarie
# --------------------------------------------------------------------

def save_header(p: StagiaireHeaderPayload, op_id: int) -> bool:
    """Cf. WinDev Btn Enregistrer : si idStagiaire non lie ajoute,
    sinon modifie Formation_salarie. Egalement met a jour salarie_adf
    pour Axes de travail (dernier enregistrement dans la periode).
    """
    if not p.id_formation or not p.id_salarie:
        return False
    try:
        id_form = int(p.id_formation)
        id_sal = int(p.id_salarie)
    except (TypeError, ValueError):
        return False

    scool = get_pg_connection("scool")
    try:
        exists = scool.query_one(
            """SELECT 1 FROM scool.pgt_formation_salarie
                WHERE id_formation = ? AND id_salarie = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (id_form, id_sal),
        )
    except Exception:
        exists = None

    du = p.date_debut[:10] if p.date_debut else None
    au = p.date_fin[:10] if p.date_fin else None

    try:
        if exists:
            scool.execute(
                """UPDATE scool.pgt_formation_salarie
                      SET date_debut = ?, date_fin = ?, livrable = ?,
                          modif_date = NOW(), modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_formation = ? AND id_salarie = ?""",
                (du, au, bool(p.livrable), op_id, id_form, id_sal),
            )
        else:
            scool.execute(
                """INSERT INTO scool.pgt_formation_salarie
                      (id_formation_salarie, id_formation, id_salarie,
                       date_debut, date_fin, livrable,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
                (
                    _new_id(), id_form, id_sal, du, au,
                    bool(p.livrable), op_id,
                ),
            )
    except Exception:
        logger.exception("save_header")
        return False

    # Axes de travail : stocke sur la ligne salarie_adf a la date de fin
    # (WinDev remontait cela via requete latest sur ADF)
    if (p.axe_travail_1 or p.axe_travail_2) and au:
        rh = get_pg_connection("rh")
        try:
            existing = rh.query_one(
                """SELECT id_salarie_adf FROM pgt_salarie_adf
                    WHERE id_salarie = ? AND date = ?
                    LIMIT 1""",
                (id_sal, au),
            )
            if existing:
                rh.execute(
                    """UPDATE pgt_salarie_adf
                          SET axe_travail1 = ?, axe_travail2 = ?,
                              modif_date = NOW(), modif_op = ?,
                              modif_elem = 'modif'
                        WHERE id_salarie_adf = ?""",
                    (
                        p.axe_travail_1.strip(), p.axe_travail_2.strip(),
                        op_id, existing.get("id_salarie_adf"),
                    ),
                )
            else:
                rh.execute(
                    """INSERT INTO pgt_salarie_adf
                          (id_salarie_adf, id_salarie, date,
                           axe_travail1, axe_travail2,
                           modif_date, modif_op, modif_elem)
                       VALUES (?, ?, ?, ?, ?, NOW(), ?, 'new')""",
                    (
                        _new_id(), id_sal, au,
                        p.axe_travail_1.strip(),
                        p.axe_travail_2.strip(),
                        op_id,
                    ),
                )
        except Exception:
            logger.exception("save_header axes")
    return True


# --------------------------------------------------------------------
# Ajout d'une ligne au tableau prod (cree une decl_presence par defaut)
# --------------------------------------------------------------------

def ajout_ligne_prod(p: AjoutLigneProdPayload, op_id: int) -> bool:
    """Cf. WinDev Btn 'Ajouter une ligne au tableau' :
    prompt une date, cree une decl presence type 1 (salle) presente.
    """
    if not p.id_salarie or not p.date:
        return False
    try:
        id_sal = int(p.id_salarie)
    except (TypeError, ValueError):
        return False
    d = p.date[:10]
    rh = get_pg_connection("rh")
    try:
        existing = rh.query_one(
            """SELECT id_declaratif_presence
                 FROM pgt_salarie_decl_presence
                WHERE id_salarie = ? AND date = ?
                LIMIT 1""",
            (id_sal, d),
        )
    except Exception:
        existing = None
    if existing:
        return True   # deja present, rien a faire (cf. WinDev)
    try:
        rh.execute(
            """INSERT INTO pgt_salarie_decl_presence
                  (id_declaratif_presence, id_salarie, date,
                   type_journee, presence, periode_absence,
                   motifabsence, emargement_matin, emargement_aprem,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, 1, TRUE, 0, 0, NULL, NULL,
                       NOW(), ?, 'new')""",
            (_new_id(), id_sal, d, op_id),
        )
    except Exception:
        logger.exception("ajout_ligne_prod")
        return False
    return True
