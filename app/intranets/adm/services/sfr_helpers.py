"""Helpers communs SFR (transposition WinDev).

Regroupe les 4 procedures WinDev utilisees dans les imports SFR :
- ajout_fiche_client_sfr    (cf. ajoutFicheClient)
- ajout_fiche_contrat_sfr   (cf. ajoutFicheContrat)
- modif_fiche_client_sfr    (cf. ModifFicheClient)
- valide_tk_call_sfr        (cf. ValideTkCall)
"""

from datetime import date, datetime
from typing import Any, Optional

from app.core.database.pg import get_pg_connection


# ============================================================================
# Helpers internes
# ============================================================================

def _new_id() -> int:
    """8 octets from date/time (equivalent idEntierDateHeureSys WinDev)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


# ============================================================================
# ajoutFicheClient
# ============================================================================

def ajout_fiche_client_sfr(
    nom: str, prenom: str, date_naiss: Any, adresse1: str,
    adresse2: str, cp: str, ville: str, tel: str, gsm: str,
    mail: str, opt_partenaire: bool, op_id: int,
) -> int:
    """Cf. WinDev ajoutFicheClient : cherche par mail, cree ou met a
    jour selon.

    Regles :
    - Si un client existe deja avec ce mail (non vide) : retourne
      son id_client. Si son NOM est vide et qu'on a une adresse,
      complete les infos.
    - Sinon : cree une nouvelle ligne dans adv.pgt_client avec
      pays='FRANCE' par defaut.

    Retourne id_client (int).
    """
    db = get_pg_connection("adv")
    mail_c = _clean(mail).lower()

    # Recherche par mail (uniquement si mail non vide)
    if mail_c:
        existing = db.query_one(
            """SELECT id_client, nom FROM adv.pgt_client
                WHERE LOWER(mail) = ?
                  AND mail <> ''
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                ORDER BY nom DESC
                LIMIT 1""",
            (mail_c,),
        )
        if existing:
            id_client_existant = int(existing["id_client"])
            # Complete si le NOM est vide + on a une adresse
            if not existing.get("nom") and _clean(adresse1):
                db.query(
                    """UPDATE adv.pgt_client
                          SET nom = ?, prenom = ?, date_naiss = ?,
                              adresse1 = ?, adresse2 = ?, cp = ?, ville = ?,
                              pays = 'FRANCE', tel = ?, gsm = ?, mail = ?,
                              opt_partenaire = ?,
                              modif_op = ?, modif_date = NOW(),
                              modif_elem = 'modif'
                        WHERE id_client = ?""",
                    (_clean(nom), _clean(prenom), date_naiss,
                     _clean(adresse1), _clean(adresse2),
                     _clean(cp), _clean(ville), _clean(tel), _clean(gsm),
                     _clean(mail), bool(opt_partenaire),
                     int(op_id), id_client_existant),
                )
            return id_client_existant

    # Creation
    id_new = _new_id()
    db.query(
        """INSERT INTO adv.pgt_client
              (id_client_auto, id_client, civilite, nom, prenom,
               date_naiss, adresse1, adresse2, cp, ville, pays,
               tel, gsm, mail, opt_partenaire,
               op_saisie, date_saisie,
               modif_op, modif_date, modif_elem)
           VALUES (?, ?, 1, ?, ?,
                   ?, ?, ?, ?, ?, 'FRANCE',
                   ?, ?, ?, ?,
                   ?, NOW(),
                   ?, NOW(), 'new')""",
        (id_new, id_new, _clean(nom), _clean(prenom),
         date_naiss, _clean(adresse1), _clean(adresse2),
         _clean(cp), _clean(ville),
         _clean(tel), _clean(gsm), _clean(mail),
         bool(opt_partenaire),
         int(op_id), int(op_id)),
    )
    return id_new


# ============================================================================
# ajoutFicheContrat
# ============================================================================

def ajout_fiche_contrat_sfr(ctt: dict, op_id: int) -> int:
    """Cf. WinDev ajoutFicheContrat(ctt is ST_CONTRAT_SFR) : INSERT
    contrat SFR + recalcul nb_points avec bonus FIB CQ >= 2026-02-01.

    Le dict `ctt` doit contenir les cles equivalentes aux champs WinDev
    (id_client, id_salarie, id_ste, num_bs, date_signature, etc.).
    Les champs absents sont mis a leur valeur par defaut (0, '', None).

    Retourne id_contrat (int) du contrat cree.
    """
    db = get_pg_connection("adv")
    # Genere un id unique (retry si conflit)
    id_new = _new_id()
    while True:
        r = db.query_one(
            "SELECT 1 FROM adv.pgt_sfr_contrat WHERE id_contrat = ? LIMIT 1",
            (id_new,),
        )
        if not r: break
        id_new = _new_id()

    def _g(k: str, default: Any = None) -> Any:
        return ctt.get(k, default)

    # INSERT complet (40+ colonnes cf. WinDev)
    db.query(
        """INSERT INTO adv.pgt_sfr_contrat (
              id_contrat_auto, id_contrat, id_client, id_salarie, id_ste,
              num_bs, id_produit, id_etat_contrat, id_etat_sfr,
              date_signature, date_validation, date_racc_activ,
              portabilite, date_portabilite, date_rdv_tech,
              periode_rdv_tech, date_resil,
              id_sfr_cluster, id_sfr_statut_rdv,
              technologie, self_install, type_vente,
              box8, box8_verif, option_dec, option_verif,
              mois_p_option, motif_annulation, info_vente_sfr,
              info_interne, op_saisie, date_saisie,
              mois_p_va, nb_pts_payes_va,
              mois_p_ra, nb_pts_payes_ra,
              paye_va_distri, mois_p_va_distri,
              paye_ra_distri, mois_p_ra_distri,
              internet_garanti, mail_bo_envoye, mail_bo_date_envoi,
              non_call, remise, offre_speciale,
              booster_active, nb_points, import_j, hors_cible,
              notation, notation_info, id_etat_call_ret, obs_call_ret,
              id_contrat_ret,
              issu_tk_diff, parcours_chaine, parcours_degroupes,
              prise_existante, prise_saisie,
              num_prise_sfr, num_prise_vend,
              activ_control, processing_state,
              modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   ?, ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?,
                   ?, ?,
                   ?, ?,
                   ?, ?, ?,
                   ?, ?, ?, ?,
                   '', ?, ?,
                   ?, ?, NOW(),
                   '', ?,
                   '', ?,
                   FALSE, '',
                   FALSE, '',
                   ?, FALSE, NULL,
                   ?, ?, ?,
                   FALSE, ?, ?, ?,
                   0, '', 0, '',
                   0,
                   ?, ?, ?,
                   ?, ?,
                   ?, '',
                   ?, ?,
                   ?, NOW(), 'new')""",
        (id_new, id_new,
         int(_g("id_client", 0) or 0),
         int(_g("id_salarie", 0) or 0),
         int(_g("id_ste", 0) or 0),
         _clean(_g("num_bs")),
         int(_g("id_produit", 0) or 0),
         int(_g("id_etat_contrat", 0) or 0),
         int(_g("id_etat_sfr", 0) or 0),
         _g("date_signature"), _g("date_validation"), _g("date_racc_activ"),
         bool(_g("portabilite")), _g("date_portabilite"), _g("date_rdv_tech"),
         _clean(_g("periode_rdv_tech")), _g("date_resil"),
         int(_g("id_sfr_cluster", 0) or 0),
         int(_g("id_sfr_statut_rdv", 0) or 0),
         int(_g("technologie", 0) or 0),
         bool(_g("self_install")),
         int(_g("type_vente", 0) or 0),
         bool(_g("box8")), bool(_g("box8_verif")),
         bool(_g("option_dec")), bool(_g("option_verif")),
         _clean(_g("motif_annulation")),
         _clean(_g("info_vente_sfr")),
         _clean(_g("info_interne")),
         int(op_id),
         float(_g("nb_pts_payes_va", 0) or 0),
         float(_g("nb_pts_payes_ra", 0) or 0),
         bool(_g("internet_garanti")),
         bool(_g("non_call", True)),
         bool(_g("remise")),
         bool(_g("offre_speciale")),
         float(_g("nb_points", 0) or 0),
         int(_g("import_j", 0) or 0),
         bool(_g("hors_cible")),
         int(_g("issu_tk_diff", 0) or 0),
         bool(_g("parcours_chaine")),
         bool(_g("parcours_degroupes")),
         bool(_g("prise_existante")),
         bool(_g("prise_saisie")),
         _clean(_g("num_prise_sfr")),
         _clean(_g("activ_control")),
         _clean(_g("processing_state")),
         int(op_id)),
    )

    # Recalcul nb_points (cf. WinDev)
    try:
        _recalcul_nb_points_sfr(id_new)
    except Exception:
        pass
    return id_new


def _recalcul_nb_points_sfr(id_contrat: int) -> None:
    """Cf. WinDev fin de ajoutFicheContrat : recalcule nb_points via
    calculPointContrat + bonus FIB CQ >= 2026-02-01."""
    db = get_pg_connection("adv")
    ctt = db.query_one(
        """SELECT c.id_produit, c.type_vente, c.date_signature,
                  c.date_racc_activ, c.portabilite, c.prise_saisie,
                  c.notation, c.nb_points,
                  p.famille, p.sous_fam
             FROM adv.pgt_sfr_contrat c
             LEFT JOIN adv.pgt_sfr_produit p ON p.id_produit = c.id_produit
            WHERE c.id_contrat = ? LIMIT 1""",
        (id_contrat,),
    )
    if not ctt: return

    from app.shared.sdtc.bareme import calcul_point_contrat
    fam = _donne_fam_prod_sfr(ctt.get("famille") or "", int(ctt.get("type_vente") or 0))
    sous_fam = ctt.get("sous_fam") or ""
    date_sign = ctt.get("date_signature")
    try:
        nbpt = calcul_point_contrat(
            fam=fam, ss_fam=sous_fam, palier=0,
            date_sign=str(date_sign) if date_sign else "",
            info_cplt=str(id_contrat), palier2=0,
        )
    except Exception:
        nbpt = 0.0

    # Bonus FIB CQ >= 2026-02-01
    if fam == "FIB CQ" and date_sign and date_sign >= date(2026, 2, 1):
        if ctt.get("portabilite"): nbpt += 0.2
        if ctt.get("prise_saisie"): nbpt += 0.2
        if (float(ctt.get("notation") or 0) * 2) >= 8.6: nbpt += 0.1

    # Update seulement si diff + date signature ou racc >= 2022-02-01
    dr = ctt.get("date_racc_activ")
    if ((date_sign and date_sign >= date(2022, 2, 1))
        or (dr and dr >= date(2022, 2, 1))):
        if float(ctt.get("nb_points") or 0) != nbpt:
            db.query(
                """UPDATE adv.pgt_sfr_contrat SET nb_points = ?,
                      modif_date = NOW()
                    WHERE id_contrat = ?""",
                (float(nbpt), id_contrat),
            )


def _donne_fam_prod_sfr(famille: str, type_vente: int) -> str:
    """Cf. WinDev DonneFamProdSFR : mapping famille produit + type
    vente vers famille bareme (FIB CQ, FIB, MOB, etc.).

    Regle simplifiee (a affiner selon regles metier reelles) :
    - famille contient 'FIBRE' + type_vente = 1 (Conquete) -> 'FIB CQ'
    - famille contient 'FIBRE' -> 'FIB'
    - famille contient 'MOBILE' -> 'MOB'
    - autre -> famille tel quelle
    """
    f_up = (famille or "").upper()
    if "FIBRE" in f_up:
        return "FIB CQ" if type_vente == 1 else "FIB"
    if "MOBILE" in f_up:
        return "MOB"
    return famille or ""


# ============================================================================
# ModifFicheClient
# ============================================================================

def modif_fiche_client_sfr(
    id_client: int, nom: str, prenom: str, date_naiss: Any,
    adresse1: str, adresse2: str, cp: str, ville: str,
    tel: str, gsm: str, mail: str, op_id: int,
) -> int:
    """Cf. WinDev ModifFicheClient : UPDATE de la fiche client avec
    tous les champs fournis. Ne fait rien si id_client est 0."""
    if not id_client: return 0
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_client
              SET nom = ?, prenom = ?, date_naiss = ?,
                  adresse1 = ?, adresse2 = ?, cp = ?, ville = ?,
                  pays = 'FRANCE', tel = ?, gsm = ?, mail = ?,
                  op_saisie = ?, date_saisie = NOW(),
                  modif_op = ?, modif_date = NOW(),
                  modif_elem = 'modif'
            WHERE id_client = ?""",
        (_clean(nom), _clean(prenom), date_naiss,
         _clean(adresse1), _clean(adresse2),
         _clean(cp), _clean(ville),
         _clean(tel), _clean(gsm), _clean(mail),
         int(op_id), int(op_id), int(id_client)),
    )
    return id_client


# ============================================================================
# ValideTkCall
# ============================================================================

def valide_tk_call_sfr(id_tk_liste: int, num_bs: str, op_id: int) -> bool:
    """Cf. WinDev ValideTkCall : cloture le ticket + statut='Contrat créé' (16).

    Le SMS de felicitation vendeur est commente dans le WinDev source
    -> non transpose ici.
    """
    if not id_tk_liste: return False
    try:
        db = get_pg_connection("ticket")
        db.query(
            """UPDATE ticket.pgt_tk_liste
                  SET id_tk_statut = 16,
                      cloturee = TRUE, date_cloture = NOW(),
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_tk_liste = ?""",
            (int(op_id), int(id_tk_liste)),
        )
        return True
    except Exception:
        return False
