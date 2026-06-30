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
