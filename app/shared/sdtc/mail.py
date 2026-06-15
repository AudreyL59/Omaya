"""
SDTC - btn 'Mail SDTC' + sauvegarde du contenu mail dans pgt_salarie_sortie.

Transposition de :
1. Bloc final du btn 'Generation des PDFs, XLS et du mail recap' :
   sauvegarde MailObjet + MailContenu dans pgt_salarie_sortie.
2. Btn 'Mail SDTC' : prepare le payload pour pre-remplir Fen_EnvoieEmail.
   - Expediteur : fpe@exosphere.fr
   - A          : service_paie@cneidf.cerfrance.fr
   - CC         : a.dubois@exosphere.fr, m.doineau@exosphere.fr, fpe@exosphere.fr
   - Objet      : MailObjet stocke ("DEMANDE SDTC NomSal // NomSte")
   - HTML       : MailContenu stocke (InfoSalarie substitue)
"""

from __future__ import annotations

from app.core.database.pg import get_pg_connection

from .helpers import _str


# Adresses cf. WinDev btn 'Mail SDTC'
EXPEDITEUR_SDTC = "fpe@exosphere.fr"
DESTINATAIRES_A = ["service_paie@cneidf.cerfrance.fr"]
DESTINATAIRES_CC = [
    "a.dubois@exosphere.fr",
    "m.doineau@exosphere.fr",
    "fpe@exosphere.fr",
]


def save_mail_content(
    *, id_salarie: int, objet: str, contenu_html: str, op_id: int
) -> dict:
    """Sauvegarde MailContenu + MailObjet dans pgt_salarie_sortie.

    Cf. WinDev btn 'Generation PDFs/XLS/Mail' :
      HLitRecherche(salarie_sortie, IDSalarie, idSalarié, hIdentique)
      si HTrouve alors
        salarie_sortie.MailContenu = monText
        salarie_sortie.MailObjet   = 'DEMANDE SDTC NomSal // NomSte'
        salarie_sortie.ModifDate   = DateHeureSys()
        salarie_sortie.ModifOp     = usersCial
        salarie_sortie.ModifElem   = 'modif'
        HModifie(salarie_sortie)
    """
    db = get_pg_connection("rh")
    row = db.query_one(
        "SELECT id_salarie FROM rh.pgt_salarie_sortie WHERE id_salarie = ?",
        (int(id_salarie),),
    )
    if not row:
        # Cf. WinDev : pas de cas particulier si la sortie n'existe pas,
        # mais on cree une ligne pour eviter de perdre le mail
        db.execute(
            """INSERT INTO rh.pgt_salarie_sortie
                  (id_salarie, id_type_sortie, mail_objet, mail_contenu,
                   modif_date, modif_op, modif_elem)
               VALUES (?, 0, ?, ?, NOW(), ?, 'new')""",
            (int(id_salarie), objet, contenu_html, int(op_id)),
        )
        return {"ok": True, "created": True}

    db.execute(
        """UPDATE rh.pgt_salarie_sortie
              SET mail_objet = ?,
                  mail_contenu = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_salarie = ?""",
        (objet, contenu_html, int(op_id), int(id_salarie)),
    )
    return {"ok": True, "created": False}


def build_mail_objet(nom_salarie: str, nom_societe: str) -> str:
    """Cf. WinDev :
      salarie_sortie.MailObjet = 'DEMANDE SDTC ' + NomSalarie + ' // ' + NomSte
    """
    return f"DEMANDE SDTC {nom_salarie} // {nom_societe}".strip()


def get_mail_payload(id_salarie: int) -> dict:
    """Btn 'Mail SDTC' : recupere les infos sauvegardees pour pre-remplir
    Fen_EnvoieEmail.

    Retourne :
      {expediteur, a, cc, objet, html} avec :
      - expediteur : 'fpe@exosphere.fr'
      - a          : ['service_paie@cneidf.cerfrance.fr']
      - cc         : ['a.dubois@exosphere.fr', 'm.doineau@exosphere.fr',
                      'fpe@exosphere.fr']
      - objet      : MailObjet stocke
      - html       : MailContenu stocke
    """
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT mail_objet, mail_contenu
             FROM rh.pgt_salarie_sortie
            WHERE id_salarie = ?""",
        (int(id_salarie),),
    )
    objet = _str((row or {}).get("mail_objet"))
    contenu = _str((row or {}).get("mail_contenu"))
    return {
        "expediteur": EXPEDITEUR_SDTC,
        "a": list(DESTINATAIRES_A),
        "cc": list(DESTINATAIRES_CC),
        "objet": objet,
        "html": contenu,
    }
