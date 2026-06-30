"""Services pour Fen_SuiviSFR (sous-fonctionnalites ADM > Suivi SFR).

1. Fen_SFRCttaRacc (Ctts à raccorder) :
   - list_ctts_a_raccorder : SELECT JOIN avec preselect Choix
   - send_mails_to_bos : envoi mail aux BO SFR cluster pour les lignes cochees
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


def _new_id() -> int:
    """ID 8 octets timestamp (cf idEntierDateHeureSys WinDev)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


# ====================================================================
# 1. CTTS A RACCORDER (Fen_SFRCttaRacc)
# ====================================================================


class CttARaccorderItem(BaseModel):
    id_contrat: str
    num_bs: str = ""
    nom: str = ""
    prenom: str = ""
    cp: str = ""
    ville: str = ""
    code_vad: str = ""
    nom_cluster: str = ""
    nom_sa: str = ""               # nom commercial
    prenom_sa: str = ""
    date_signature: str = ""
    date_validation: str = ""
    date_raccordement: str = ""
    date_rdv_tech: str = ""
    lib_etat: str = ""
    type_etat: int = 0
    type_install: int = 0           # SelfInstall
    type_offre: int = 0             # IDproduit
    type_vente: int = 0
    technologie: int = 0
    option_dec: str = ""
    box8: bool = False
    nb_pts_payes: float = 0.0
    mail_bo_envoye: bool = False
    mail_bo_date_envoi: str = ""
    choix: int = 0                  # 1 = preselect a envoyer mail


def _capitalize(p: str) -> str:
    return (p[:1].upper() + p[1:].lower()) if p else ""


def _date_str(d) -> str:
    if not d:
        return ""
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def list_ctts_a_raccorder(
    du: date, au: date,
) -> list[CttARaccorderItem]:
    """Charge les contrats SFR entre Du et Au avec un etat 'planifie' ou
    'paye par employeur'. Pre-coche Choix=1 si :
      - lib_etat = 'Le raccordement est planifié dans le créneau - '
      - ET date_rdv_tech vide
      - ET (mail_bo_envoye=False OU mail_bo_date_envoi > 7 jours)
    """
    db = get_pg_connection("adv")
    rows = db.query(
        """
        SELECT c.id_contrat, c.num_bs, c.date_signature, c.date_validation,
               c.date_racc_activ, c.date_rdv_tech, c.id_sfr_cluster,
               c.id_etat_sfr, c.technologie, c.id_produit, c.self_install,
               c.type_vente, c.box8, c.option_dec, c.nb_pts_payes_va,
               c.mail_bo_envoye, c.mail_bo_date_envoi, c.info_interne,
               cli.nom AS cli_nom, cli.prenom AS cli_prenom,
               cli.cp AS cli_cp, cli.ville AS cli_ville,
               clu.code_vad, clu.nom_cluster,
               s.nom AS sa_nom, s.prenom AS sa_prenom,
               e.lib_etat, e.id_type_etat
          FROM adv.pgt_sfr_contrat c
          LEFT JOIN adv.pgt_client cli ON cli.id_client = c.id_client
          LEFT JOIN adv.pgt_sfr_cluster clu ON clu.id_sfr_cluster = c.id_sfr_cluster
          LEFT JOIN adv.pgt_sfr_etat_contrat e ON e.id_etat = c.id_etat_sfr
          LEFT JOIN rh.pgt_salarie s ON s.id_salarie = c.id_salarie
         WHERE c.date_signature BETWEEN ? AND ?
           AND (c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')
           AND (
                e.lib_etat ILIKE '%Le raccordement est planifié%'
             OR e.lib_etat ILIKE '%Payé par employeur - Validation%'
             OR c.date_rdv_tech BETWEEN ? AND ?
           )
         ORDER BY c.date_signature DESC
         LIMIT 5000
        """,
        (du, au, du, au),
    ) or []

    today = date.today()
    out: list[CttARaccorderItem] = []
    for r in rows:
        lib_etat = r.get("lib_etat") or ""
        date_rdv = _date_str(r.get("date_rdv_tech"))
        mail_envoye = bool(r.get("mail_bo_envoye"))
        mail_date = r.get("mail_bo_date_envoi")

        choix = 0
        # Preselect Choix=1 si etat exact 'Le raccordement est planifié...'
        # ET pas de RDV Tech ET (pas encore envoye OU envoye > 7j)
        if "Le raccordement est planifié" in lib_etat and not date_rdv:
            if not mail_envoye:
                choix = 1
            elif mail_date and isinstance(mail_date, (date, datetime)):
                md = mail_date.date() if isinstance(mail_date, datetime) else mail_date
                if (today - md).days > 7:
                    choix = 1

        out.append(CttARaccorderItem(
            id_contrat=str(r["id_contrat"]),
            num_bs=r.get("num_bs") or "",
            nom=(r.get("cli_nom") or "").strip(),
            prenom=_capitalize((r.get("cli_prenom") or "").strip()),
            cp=r.get("cli_cp") or "",
            ville=r.get("cli_ville") or "",
            code_vad=r.get("code_vad") or "",
            nom_cluster=r.get("nom_cluster") or "",
            nom_sa=(r.get("sa_nom") or "").strip(),
            prenom_sa=_capitalize((r.get("sa_prenom") or "").strip()),
            date_signature=_date_str(r.get("date_signature")),
            date_validation=_date_str(r.get("date_validation")),
            date_raccordement=_date_str(r.get("date_racc_activ")),
            date_rdv_tech=date_rdv,
            lib_etat=lib_etat,
            type_etat=int(r.get("id_type_etat") or 0),
            type_install=int(r.get("self_install") or 0),
            type_offre=int(r.get("id_produit") or 0),
            type_vente=int(r.get("type_vente") or 0),
            technologie=int(r.get("technologie") or 0),
            option_dec=r.get("option_dec") or "",
            box8=bool(r.get("box8")),
            nb_pts_payes=float(r.get("nb_pts_payes_va") or 0),
            mail_bo_envoye=mail_envoye,
            mail_bo_date_envoi=_date_str(mail_date),
            choix=choix,
        ))
    return out


# --------------------------------------------------------------------
# Envoi mail BO SFR
# --------------------------------------------------------------------


class SendMailsResult(BaseModel):
    id_contrat: str
    num_bs: str = ""
    ok: bool = False
    message: str = ""


# ====================================================================
# 2. REMUNERATIONS SFR (Fen_RemInterneSFR)
# ====================================================================


class RemunItem(BaseModel):
    id_sfr_remun: str
    categorie: str = ""              # 'FIBRE' ou 'MOBILE'
    id_produit: int = 0
    lib_produit: str = ""
    type_vente: int = 0
    date_debut: str = ""
    date_fin: str = ""
    montant_va: float = 0.0
    montant_va_remise: float = 0.0
    montant_ra: float = 0.0
    montant_ra_remise: float = 0.0
    prime_volumique: float = 0.0
    abonnement_tv: float = 0.0
    type_repart_rem: int = 0


class RemunPayload(BaseModel):
    categorie: str                      # 'FIBRE' ou 'MOBILE'
    id_produit: int
    type_vente: int = 0
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    montant_va: float = 0.0
    montant_va_remise: float = 0.0
    montant_ra: float = 0.0
    montant_ra_remise: float = 0.0
    prime_volumique: float = 0.0
    abonnement_tv: float = 0.0
    type_repart_rem: int = 0


class ProduitSfrItem(BaseModel):
    id_produit: int
    lib_produit: str


def list_remunerations(categorie: str) -> list[RemunItem]:
    """Liste les rémunérations SFR pour une catégorie ('FIBRE' ou 'MOBILE'),
    JOIN sfr_produit pour le libellé. Tri date_debut DESC, lib_produit ASC.
    """
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT r.id_sfr_remun, r.categorie, r.id_produit,
                  p.lib_produit,
                  r.type_vente, r.date_debut, r.date_fin,
                  r.montant_va, r.montant_va_remise,
                  r.montant_ra, r.montant_ra_remise,
                  r.prime_volumique, r.abonnement_tv, r.type_repart_rem
             FROM adv.pgt_sfr_remun r
             LEFT JOIN adv.pgt_sfr_produit p ON p.id_produit = r.id_produit
            WHERE r.categorie = ?
              AND (r.modif_elem IS NULL OR r.modif_elem NOT LIKE '%suppr%')
            ORDER BY r.date_debut DESC NULLS LAST, p.lib_produit""",
        (categorie.upper(),),
    ) or []
    return [RemunItem(
        id_sfr_remun=str(r["id_sfr_remun"]),
        categorie=r.get("categorie") or "",
        id_produit=int(r.get("id_produit") or 0),
        lib_produit=r.get("lib_produit") or "",
        type_vente=int(r.get("type_vente") or 0),
        date_debut=_date_str(r.get("date_debut")),
        date_fin=_date_str(r.get("date_fin")),
        montant_va=float(r.get("montant_va") or 0),
        montant_va_remise=float(r.get("montant_va_remise") or 0),
        montant_ra=float(r.get("montant_ra") or 0),
        montant_ra_remise=float(r.get("montant_ra_remise") or 0),
        prime_volumique=float(r.get("prime_volumique") or 0),
        abonnement_tv=float(r.get("abonnement_tv") or 0),
        type_repart_rem=int(r.get("type_repart_rem") or 0),
    ) for r in rows]


def list_sfr_produits(categorie: Optional[str] = None) -> list[ProduitSfrItem]:
    """Liste les produits SFR, optionnellement filtres par categorie.
    Categorie SFR : 1=Fibre, 2=Mobile (smallint pgt_sfr_produit.categorie)."""
    db = get_pg_connection("adv")
    where = ["(modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')",
             "COALESCE(pro_actif, 0) = 1"]
    params: list = []
    if categorie:
        cat_int = 1 if categorie.upper() == "FIBRE" else 2
        where.append("categorie = ?")
        params.append(cat_int)
    rows = db.query(
        f"""SELECT id_produit, lib_produit FROM adv.pgt_sfr_produit
            WHERE {' AND '.join(where)}
            ORDER BY lib_produit""",
        tuple(params),
    ) or []
    return [ProduitSfrItem(
        id_produit=int(r["id_produit"]),
        lib_produit=r.get("lib_produit") or "",
    ) for r in rows]


def get_remun(id_sfr_remun: int) -> Optional[RemunItem]:
    """Lit une remuneration pour edition."""
    db = get_pg_connection("adv")
    r = db.query_one(
        """SELECT r.id_sfr_remun, r.categorie, r.id_produit, p.lib_produit,
                  r.type_vente, r.date_debut, r.date_fin,
                  r.montant_va, r.montant_va_remise,
                  r.montant_ra, r.montant_ra_remise,
                  r.prime_volumique, r.abonnement_tv, r.type_repart_rem
             FROM adv.pgt_sfr_remun r
             LEFT JOIN adv.pgt_sfr_produit p ON p.id_produit = r.id_produit
            WHERE r.id_sfr_remun = ? LIMIT 1""",
        (int(id_sfr_remun),),
    )
    if not r:
        return None
    return RemunItem(
        id_sfr_remun=str(r["id_sfr_remun"]),
        categorie=r.get("categorie") or "",
        id_produit=int(r.get("id_produit") or 0),
        lib_produit=r.get("lib_produit") or "",
        type_vente=int(r.get("type_vente") or 0),
        date_debut=_date_str(r.get("date_debut")),
        date_fin=_date_str(r.get("date_fin")),
        montant_va=float(r.get("montant_va") or 0),
        montant_va_remise=float(r.get("montant_va_remise") or 0),
        montant_ra=float(r.get("montant_ra") or 0),
        montant_ra_remise=float(r.get("montant_ra_remise") or 0),
        prime_volumique=float(r.get("prime_volumique") or 0),
        abonnement_tv=float(r.get("abonnement_tv") or 0),
        type_repart_rem=int(r.get("type_repart_rem") or 0),
    )


def create_remun(p: RemunPayload, op_id: int) -> int:
    db = get_pg_connection("adv")
    id_new = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_sfr_remun_auto), 0) + 1 AS n FROM adv.pgt_sfr_remun"
    )
    auto_n = int(auto["n"]) if auto else 1
    db.query(
        """INSERT INTO adv.pgt_sfr_remun
              (id_sfr_remun_auto, id_sfr_remun, categorie, id_produit,
               type_vente, date_debut, date_fin,
               montant_va, montant_va_remise, montant_ra, montant_ra_remise,
               prime_volumique, abonnement_tv, type_repart_rem,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (auto_n, id_new, p.categorie.upper(), int(p.id_produit),
         int(p.type_vente), p.date_debut, p.date_fin,
         float(p.montant_va), float(p.montant_va_remise),
         float(p.montant_ra), float(p.montant_ra_remise),
         float(p.prime_volumique), float(p.abonnement_tv),
         int(p.type_repart_rem), int(op_id)),
    )
    return id_new


def update_remun(id_sfr_remun: int, p: RemunPayload, op_id: int) -> bool:
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_sfr_remun
              SET categorie=?, id_produit=?, type_vente=?,
                  date_debut=?, date_fin=?,
                  montant_va=?, montant_va_remise=?,
                  montant_ra=?, montant_ra_remise=?,
                  prime_volumique=?, abonnement_tv=?, type_repart_rem=?,
                  modif_date=NOW(), modif_op=?, modif_elem='modif'
            WHERE id_sfr_remun=?""",
        (p.categorie.upper(), int(p.id_produit), int(p.type_vente),
         p.date_debut, p.date_fin,
         float(p.montant_va), float(p.montant_va_remise),
         float(p.montant_ra), float(p.montant_ra_remise),
         float(p.prime_volumique), float(p.abonnement_tv),
         int(p.type_repart_rem), int(op_id), int(id_sfr_remun)),
    )
    return True


def duplicate_remun(id_sfr_remun: int, op_id: int) -> int:
    """Duplique une remuneration : copie tous les champs sauf l'ID."""
    db = get_pg_connection("adv")
    src = db.query_one(
        """SELECT categorie, id_produit, type_vente, date_debut, date_fin,
                  montant_va, montant_va_remise, montant_ra, montant_ra_remise,
                  prime_volumique, abonnement_tv, type_repart_rem
             FROM adv.pgt_sfr_remun WHERE id_sfr_remun = ?""",
        (int(id_sfr_remun),),
    )
    if not src:
        return 0
    id_new = _new_id()
    auto = db.query_one(
        "SELECT COALESCE(MAX(id_sfr_remun_auto), 0) + 1 AS n FROM adv.pgt_sfr_remun"
    )
    auto_n = int(auto["n"]) if auto else 1
    db.query(
        """INSERT INTO adv.pgt_sfr_remun
              (id_sfr_remun_auto, id_sfr_remun, categorie, id_produit,
               type_vente, date_debut, date_fin,
               montant_va, montant_va_remise, montant_ra, montant_ra_remise,
               prime_volumique, abonnement_tv, type_repart_rem,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (auto_n, id_new, src.get("categorie"), src.get("id_produit"),
         src.get("type_vente"), src.get("date_debut"), src.get("date_fin"),
         src.get("montant_va"), src.get("montant_va_remise"),
         src.get("montant_ra"), src.get("montant_ra_remise"),
         src.get("prime_volumique"), src.get("abonnement_tv"),
         src.get("type_repart_rem"), int(op_id)),
    )
    return id_new


def delete_remun(id_sfr_remun: int, op_id: int) -> bool:
    db = get_pg_connection("adv")
    db.query(
        """UPDATE adv.pgt_sfr_remun
              SET modif_elem='suppr', modif_date=NOW(), modif_op=?
            WHERE id_sfr_remun=?""",
        (int(op_id), int(id_sfr_remun)),
    )
    return True


# ====================================================================
# 3. TICKET CALL SFR (Fen_TicketCallSFR)
# ====================================================================


class TicketCallItem(BaseModel):
    id_tk_call_sfr: str
    id_tk_liste: str
    nb_ctt: int = 0                      # nb lignes panier (NB Ctt dans le panier)
    nb_ctt_avec_num: int = 0             # nb lignes panier avec NumBS (NB Ctt avec Num BS)
    contenu_panier: str = ""             # multi-ligne resume des paniers
    date_crea: str = ""
    nom_vendeur: str = ""
    agence: str = ""                     # affectation cf vendeur (TODO)
    equipe: str = ""
    nom_client: str = ""
    prenom_client: str = ""
    cp: str = ""
    ville: str = ""
    nom_operateur: str = ""              # OPCrea (qui a fait le ticket)
    date_deb_prise_en_charge: str = ""
    date_fin_prise_en_charge: str = ""
    delai_av_prise_charge_min: float = 0.0   # date_deb - date_h_appel en minutes
    lib_statut: str = ""
    cloturee: bool = False
    nb_valide: int = 0                   # nb panier statut=1 ou 3


class AnalyseTrancheItem(BaseModel):
    tranche_horaire: str
    nb_ticket: int = 0
    moins_3min: int = 0
    entre_3_5min: int = 0
    entre_5_7min: int = 0
    plus_de_7min: int = 0


class AnalyseVentesItem(BaseModel):
    delai: str
    ventes_valides: int = 0
    ventes_annulees: int = 0


class AnalyseVentesTotaux(BaseModel):
    pas_encore_statuees: int = 0
    ventes_validees: int = 0
    ventes_annulees: int = 0
    par_delai: list[AnalyseVentesItem] = []


def _delai_label(min_value: float) -> str:
    """Categorie de delai (cf code WinDev) : <3m / 3-5m / 5-7m / >7m."""
    if min_value < 3:
        return "< 3 min"
    if min_value < 5:
        return "Entre 3 et 5 min"
    if min_value < 7:
        return "Entre 5 et 7 min"
    return "> 7 min"


def _load_ticket_call_sfr(
    du: date, au: date, etat: str,
) -> list[dict]:
    """Helper : execute la requete principale TK_CallSFR + JOIN.
    etat : 'ouverts' / 'clotures' / 'tous'."""
    where_cloture = ""
    if etat == "ouverts":
        where_cloture = "AND tl.cloturee = FALSE"
    elif etat == "clotures":
        where_cloture = "AND tl.cloturee = TRUE"

    db = get_pg_connection("ticket_bo")
    rows = db.query(
        f"""
        SELECT DISTINCT
               tc.id_tk_call_sfr, tc.id_tk_liste, tc.id_salarie,
               tc.nom_client, tc.prenom_client,
               tc.cp, tc.ville,
               tc.date_h_appel, tc.ope_appel,
               tc.date_deb_prise_en_charge, tc.date_fin_prise_en_charge,
               tl.date_crea, tl.id_tk_statut, tl.cloturee,
               tl.date_cloture, tl.op_crea,
               ts.lib_statut,
               s.nom AS sa_nom, s.prenom AS sa_prenom
          FROM ticket_bo.pgt_tk_call_sfr tc
          JOIN ticket.pgt_tk_liste tl ON tl.id_tk_liste = tc.id_tk_liste
          LEFT JOIN ticket.pgt_tk_statut ts ON ts.id_tk_statut = tl.id_tk_statut
          LEFT JOIN rh.pgt_salarie s ON s.id_salarie = tl.op_crea
         WHERE (tc.modif_elem IS NULL OR tc.modif_elem NOT LIKE '%suppr%')
           -- date_crea est un timestamp : on filtre [du 00:00, au+1 00:00[
           -- pour inclure toute la journee 'au' (sinon BETWEEN du au ne
           -- match que minuit pile quand du = au).
           AND tl.date_crea >= ?
           AND tl.date_crea <  (?::date + INTERVAL '1 day')
           AND tl.op_crea <> 6
           {where_cloture}
         ORDER BY tl.date_crea DESC
         LIMIT 5000
        """,
        (du, au),
    ) or []
    return rows


def _load_paniers_by_tickets(ids_tickets: list[int]) -> dict[int, list[dict]]:
    """Charge tous les paniers d'un coup, retourne dict {id_tk_call_sfr: [paniers]}."""
    if not ids_tickets:
        return {}
    db = get_pg_connection("ticket_bo")
    ids_sql = ",".join(str(i) for i in ids_tickets)
    rows = db.query(
        f"""SELECT p.id_tk_call_sfr_panier, p.id_tk_call_sfr, p.num,
                   p.id_offres_sfr, p.type, p.statut_prod, p.num_date_saisie,
                   o.lib_offre
              FROM ticket_bo.pgt_tk_call_sfr_panier p
              LEFT JOIN adv.pgt_sfr_offres_provad o
                     ON o.id_offres_sfr = p.id_offres_sfr
             WHERE p.id_tk_call_sfr IN ({ids_sql})
               AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')""",
    ) or []
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(int(r["id_tk_call_sfr"]), []).append(r)
    return out


def _statut_prod_label(s: int) -> str:
    return {1: "Validé", 2: "Annulé", 3: "Num BS ajouté"}.get(int(s or 0), "Pas statué")


def list_ticket_call_sfr(
    du: date, au: date, etat: str = "tous",
) -> list[TicketCallItem]:
    """Onglet Liste : un ligne par ticket TK_CallSFR + resume des paniers."""
    rows = _load_ticket_call_sfr(du, au, etat)
    ids = [int(r["id_tk_call_sfr"]) for r in rows]
    paniers_by_id = _load_paniers_by_tickets(ids)

    out: list[TicketCallItem] = []
    for r in rows:
        id_tc = int(r["id_tk_call_sfr"])
        paniers = paniers_by_id.get(id_tc, [])

        # Compteurs panier
        nb_valide = sum(1 for p in paniers if int(p.get("statut_prod") or 0) in (1, 3))
        nb_avec_num = sum(1 for p in paniers if (p.get("num") or "").strip())

        # Texte de resume panier (multiligne)
        contenu_lines = []
        for p in paniers:
            num = p.get("num") or ""
            etat_p = _statut_prod_label(p.get("statut_prod"))
            line = num
            d = p.get("num_date_saisie")
            if d:
                line += f" ({_date_str(d)})"
            line += f" - {etat_p}"
            contenu_lines.append(line)

        # Delai (date_deb_prise_en_charge - date_h_appel) en minutes
        delai = 0.0
        deb = r.get("date_deb_prise_en_charge")
        app = r.get("date_h_appel")
        if isinstance(deb, datetime) and isinstance(app, datetime):
            delai = (deb - app).total_seconds() / 60.0
            if delai < 0: delai = 0.0

        out.append(TicketCallItem(
            id_tk_call_sfr=str(id_tc),
            id_tk_liste=str(r.get("id_tk_liste") or ""),
            nb_ctt=len(paniers),
            nb_ctt_avec_num=nb_avec_num,
            contenu_panier="\n".join(contenu_lines),
            date_crea=_date_str(r.get("date_crea")),
            nom_vendeur=" ".join(filter(None, [
                (r.get("sa_nom") or "").strip(),
                _capitalize((r.get("sa_prenom") or "").strip()),
            ])),
            nom_client=(r.get("nom_client") or "").strip(),
            prenom_client=_capitalize((r.get("prenom_client") or "").strip()),
            cp=r.get("cp") or "",
            ville=r.get("ville") or "",
            nom_operateur="",      # OPCrea deja resolu via sa_nom/sa_prenom mais c'est l'OP du ticket
            date_deb_prise_en_charge=_date_str(deb),
            date_fin_prise_en_charge=_date_str(r.get("date_fin_prise_en_charge")),
            delai_av_prise_charge_min=round(delai, 2),
            lib_statut=r.get("lib_statut") or "",
            cloturee=bool(r.get("cloturee")),
            nb_valide=nb_valide,
        ))
    return out


def analyse_tk_call_sfr(
    du: date, au: date, etat: str = "tous",
) -> list[AnalyseTrancheItem]:
    """Onglet Analyse : regroupement par 'tranche horaire' (cree le).
    Format tranche : 'Jjj JJ AAAA HH:mm' (cf WinDev DateHeureVersChaine)."""
    rows = _load_ticket_call_sfr(du, au, etat)
    jours_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    buckets: dict[str, AnalyseTrancheItem] = {}
    for r in rows:
        deb = r.get("date_deb_prise_en_charge")
        app = r.get("date_h_appel")
        crea = r.get("date_crea")
        delai = 0.0
        if isinstance(deb, datetime) and isinstance(app, datetime):
            delai = (deb - app).total_seconds() / 60.0
            if delai < 0: delai = 0.0
        if not isinstance(crea, datetime):
            continue

        # Tranche horaire : on tronque a la minute (sans secondes)
        crea_minute = crea.replace(second=0, microsecond=0)
        label = (f"{jours_fr[crea_minute.weekday()]} "
                 f"{crea_minute.strftime('%d %Y %H:%M')}")
        b = buckets.setdefault(label, AnalyseTrancheItem(tranche_horaire=label))
        b.nb_ticket += 1
        if delai < 3: b.moins_3min += 1
        elif delai < 5: b.entre_3_5min += 1
        elif delai < 7: b.entre_5_7min += 1
        else: b.plus_de_7min += 1

    return sorted(buckets.values(), key=lambda x: x.tranche_horaire)


def analyse_ventes_tk_call_sfr(
    du: date, au: date, etat: str = "tous",
) -> AnalyseVentesTotaux:
    """Onglet 'Analyse des ventes' : compteurs validees/annulees/pas_statuees
    + repartition par delai (<3m, 3-5m, 5-7m, >7m)."""
    rows = _load_ticket_call_sfr(du, au, etat)
    ids = [int(r["id_tk_call_sfr"]) for r in rows]
    paniers_by_id = _load_paniers_by_tickets(ids)

    totaux = AnalyseVentesTotaux()
    par_delai: dict[str, AnalyseVentesItem] = {}
    delai_order = ["< 3 min", "Entre 3 et 5 min", "Entre 5 et 7 min", "> 7 min"]
    for d in delai_order:
        par_delai[d] = AnalyseVentesItem(delai=d)

    for r in rows:
        id_tc = int(r["id_tk_call_sfr"])
        deb = r.get("date_deb_prise_en_charge")
        app = r.get("date_h_appel")
        delai = 0.0
        if isinstance(deb, datetime) and isinstance(app, datetime):
            delai = (deb - app).total_seconds() / 60.0
            if delai < 0: delai = 0.0
        delai_lbl = _delai_label(delai)

        for p in paniers_by_id.get(id_tc, []):
            s = int(p.get("statut_prod") or 0)
            if s in (1, 3):
                totaux.ventes_validees += 1
                par_delai[delai_lbl].ventes_valides += 1
            elif s == 2:
                totaux.ventes_annulees += 1
                par_delai[delai_lbl].ventes_annulees += 1
            else:
                totaux.pas_encore_statuees += 1

    totaux.par_delai = [par_delai[d] for d in delai_order]
    return totaux


def send_mails_to_bos(
    ids_contrats: list[int], op_id: int, test_mode: bool = False,
) -> list[SendMailsResult]:
    """Pour chaque contrat selectionne, recupere l'email BO du cluster
    et envoie un mail 'demande RDV technicien'. Met a jour
    sfr_contrat.mail_bo_envoye + mail_bo_date_envoi + info_interne.

    En mode test : envoie tout a a.loudieux@exosphere.fr (sujet prefixe).
    """
    from app.shared.notifications.mail import envoi_mail
    db = get_pg_connection("adv")
    out: list[SendMailsResult] = []

    for id_ctt in ids_contrats:
        r = db.query_one(
            """
            SELECT c.id_contrat, c.num_bs, c.info_interne, c.id_sfr_cluster,
                   clu.mail_bo, clu.nom_cluster
              FROM adv.pgt_sfr_contrat c
              LEFT JOIN adv.pgt_sfr_cluster clu
                ON clu.id_sfr_cluster = c.id_sfr_cluster
             WHERE c.id_contrat = ?
            """,
            (int(id_ctt),),
        )
        if not r:
            out.append(SendMailsResult(
                id_contrat=str(id_ctt), ok=False,
                message="Contrat introuvable",
            ))
            continue

        num_bs = r.get("num_bs") or ""
        mail_bo = (r.get("mail_bo") or "").strip()
        if not mail_bo or "@" not in mail_bo:
            out.append(SendMailsResult(
                id_contrat=str(id_ctt), num_bs=num_bs, ok=False,
                message=f"Mail BO cluster absent/invalide : {mail_bo!r}",
            ))
            continue

        sujet = f"N° {num_bs} – demande rdv technicien"
        html = (
            "Bonjour,<br/><br/>"
            "<p>Ce contrat n'a pas encore de rendez-vous technicien planifié.<br/>"
            "Pouvez-vous le positionner dès que possible et nous en tenir informé.</p>"
            "<p>Je vous remercie par avance.<br/>Cdt,</p>"
            "<p><b>BO Exosphere</b><br/>"
            "<i>Standard : 03.62.27.60.04<br/>"
            "Mail : bo@exosphere.fr</i></p>"
        )

        # Mode test : tout va sur le compte de la dev
        if test_mode:
            to = ["a.loudieux@exosphere.fr"]
            cci = None
            sujet = "TEST - " + sujet
        else:
            to = [mail_bo]
            cci = [
                "bo@exosphere.fr",
                "m.doineau@exosphere.fr",
                "cuneyt.caliskan@sfr.com",
                "intranet@omaya.fr",
            ]

        try:
            sent_ok = envoi_mail(
                sujet=sujet, html=html, destinataires=to,
                cci=cci, expediteur="bo@exosphere.fr",
            )
        except Exception as e:
            out.append(SendMailsResult(
                id_contrat=str(id_ctt), num_bs=num_bs, ok=False,
                message=f"Erreur envoi : {e}",
            ))
            continue

        if not sent_ok:
            out.append(SendMailsResult(
                id_contrat=str(id_ctt), num_bs=num_bs, ok=False,
                message="Echec SMTP",
            ))
            continue

        # Update contrat : marque le mail envoye + log dans info_interne
        old_info = r.get("info_interne") or ""
        new_info = (
            old_info + ("\n" if old_info else "")
            + f"Mail envoyé au BO SFR ({mail_bo}) le "
            + date.today().strftime("%d/%m/%Y")
        )
        try:
            db.query(
                """UPDATE adv.pgt_sfr_contrat
                      SET mail_bo_envoye = TRUE,
                          mail_bo_date_envoi = ?,
                          info_interne = ?,
                          modif_date = NOW(), modif_op = ?,
                          modif_elem = 'modif'
                    WHERE id_contrat = ?""",
                (date.today(), new_info, int(op_id), int(id_ctt)),
            )
        except Exception as e:
            out.append(SendMailsResult(
                id_contrat=str(id_ctt), num_bs=num_bs, ok=True,
                message=f"Mail OK mais erreur UPDATE : {e}",
            ))
            continue

        out.append(SendMailsResult(
            id_contrat=str(id_ctt), num_bs=num_bs, ok=True,
            message=f"Envoyé à {mail_bo}" + (" (TEST)" if test_mode else ""),
        ))

    return out
