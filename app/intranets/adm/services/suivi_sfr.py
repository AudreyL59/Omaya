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
