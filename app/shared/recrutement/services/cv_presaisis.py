"""Service Fen_CVPresaisis (shared) : liste des mails CV recus et a traiter.

Source : recrutement.pgt_cvtheque_temporaire (mails parses depuis les
boites RH) joint a recrutement.pgt_mails_rh_cv (config boites mail :
ne garde que les import_externe=false).

Filtres : periode (mail_date), id_ste (societe), id_elem_source
(annonceur), id_cvposte (poste), adr_mail_rh (boite mail).

Modes d'affichage :
 - a_traiter : modif_elem NULL ou vide (le mail n'a pas encore ete
   converti en CV ni supprime)
 - convertis : modif_elem='suppr' ET id_cvtheque <> 0 (CV cree puis
   le mail est marque 'suppr' pour ne plus reapparaitre)
 - supprimes : modif_elem='suppr' ET (id_cvtheque IS NULL OR id_cvtheque=0)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.services.recherche_cv import _int, _str


class MailCvRow(BaseModel):
    id_mail: str                  # id_cvtheque_auto (id du mail)
    id_cv: str = ""               # id_cvtheque (si converti)
    nom_prenom: str = ""
    mail_cand: str = ""
    gsm: str = ""
    ville_cand: str = ""
    cp_cand: str = ""
    mail_source: str = ""         # adr_mail_rh
    date_mail: str = ""           # ISO
    id_ste: str = ""
    id_annonceur: str = ""
    id_cvposte: str = ""
    op_saisie: str = ""           # nom de l'op qui a converti (si convertis)
    is_converti: bool = False     # True si id_cv > 0


class ListResult(BaseModel):
    rows: list[MailCvRow]
    nb_a_traiter: int = 0
    nb_convertis: int = 0


def _date_str(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        return d[:19]
    return d.isoformat(sep=" ")[:19]


def list_mail_sources() -> list[dict]:
    """Combo des boites mail RH (importes en interne, pas externes)."""
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT adr_mail_rh, id_ste, id_cv_poste
             FROM recrutement.pgt_mails_rh_cv
            WHERE import_externe = false
              AND is_actif = true
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY adr_mail_rh ASC"""
    ) or []
    return [{"adr": _str(r["adr_mail_rh"]),
             "id_ste": str(_int(r.get("id_ste"))),
             "id_cv_poste": str(_int(r.get("id_cv_poste")))} for r in rows]


def list_presaisis(
    saisis_deb: Optional[date],
    saisis_fin: Optional[date],
    id_ste: str = "",
    id_elem_source: str = "",
    id_cvposte: str = "",
    adr_mail_rh: str = "",
    mode: str = "a_traiter",        # a_traiter | convertis | supprimes
) -> ListResult:
    """Liste les mails CV selon les filtres + mode."""
    db = get_pg_connection("recrutement")

    where: list[str] = ["t.adr_mail_rh = m.adr_mail_rh", "m.import_externe = false"]
    params: list = []

    # Periode
    if saisis_deb:
        dt = datetime.combine(saisis_deb, datetime.min.time())
        where.append("t.mail_date >= ?")
        params.append(dt)
    if saisis_fin:
        dt = datetime.combine(saisis_fin, datetime.max.time().replace(microsecond=0))
        where.append("t.mail_date <= ?")
        params.append(dt)

    # Filtres libres
    if id_ste:
        where.append("CAST(t.id_ste AS TEXT) = ?")
        params.append(str(id_ste))
    if id_elem_source:
        where.append("CAST(t.id_elem_source AS TEXT) = ?")
        params.append(str(id_elem_source))
    if id_cvposte:
        where.append("CAST(t.id_cvposte AS TEXT) = ?")
        params.append(str(id_cvposte))
    if adr_mail_rh:
        where.append("t.adr_mail_rh = ?")
        params.append(adr_mail_rh)

    # Mode
    if mode == "a_traiter":
        where.append("(t.modif_elem IS NULL OR t.modif_elem NOT LIKE '%suppr%')")
    elif mode == "convertis":
        where.append("t.modif_elem = 'suppr'")
        where.append("t.id_cvtheque IS NOT NULL AND t.id_cvtheque <> 0")
    elif mode == "supprimes":
        where.append("t.modif_elem = 'suppr'")
        where.append("(t.id_cvtheque IS NULL OR t.id_cvtheque = 0)")

    sql = f"""
        SELECT t.id_cvtheque_auto, t.id_cvtheque, t.nom, t.prenom,
               t.mail, t.gsm, t.ville, t.cp,
               t.adr_mail_rh, t.mail_date,
               t.id_ste, t.id_elem_source, t.id_cvposte,
               t.modif_elem, t.modif_op
          FROM recrutement.pgt_cvtheque_temporaire t
          JOIN recrutement.pgt_mails_rh_cv m
            ON {" AND ".join(where)}
      ORDER BY t.mail_date DESC NULLS LAST
         LIMIT 2000
    """
    rows = db.query(sql, tuple(params)) or []

    out: list[MailCvRow] = []
    for r in rows:
        nom = _str(r.get("nom")).upper()
        prenom = _str(r.get("prenom"))
        pc = prenom[:1].upper() + prenom[1:].lower() if prenom else ""
        out.append(MailCvRow(
            id_mail=str(_int(r["id_cvtheque_auto"])),
            id_cv=str(_int(r.get("id_cvtheque"))),
            nom_prenom=f"{nom} {pc}".strip(),
            mail_cand=_str(r.get("mail")),
            gsm=_str(r.get("gsm")),
            ville_cand=_str(r.get("ville")),
            cp_cand=_str(r.get("cp")),
            mail_source=_str(r.get("adr_mail_rh")),
            date_mail=_date_str(r.get("mail_date")),
            id_ste=str(_int(r.get("id_ste"))),
            id_annonceur=str(_int(r.get("id_elem_source"))),
            id_cvposte=str(_int(r.get("id_cvposte"))),
            is_converti=bool(_int(r.get("id_cvtheque"))),
        ))

    # Comptages globaux (sans LIMIT)
    cnt = db.query_one(
        """SELECT
              COUNT(*) FILTER (WHERE t.modif_elem IS NULL OR t.modif_elem NOT LIKE '%suppr%') AS nb_a_traiter,
              COUNT(*) FILTER (WHERE t.modif_elem = 'suppr' AND t.id_cvtheque IS NOT NULL AND t.id_cvtheque <> 0) AS nb_convertis
             FROM recrutement.pgt_cvtheque_temporaire t
             JOIN recrutement.pgt_mails_rh_cv m
               ON t.adr_mail_rh = m.adr_mail_rh
              AND m.import_externe = false
        """
    )
    return ListResult(
        rows=out,
        nb_a_traiter=_int(cnt.get("nb_a_traiter")) if cnt else 0,
        nb_convertis=_int(cnt.get("nb_convertis")) if cnt else 0,
    )


def soft_delete_mail(id_mail: int, op_id: int) -> dict:
    if not id_mail:
        return {"ok": False, "error": "id_required"}
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque_temporaire
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
            WHERE id_cvtheque_auto = ?""",
        (int(op_id), int(id_mail)),
    )
    return {"ok": True}


def soft_delete_mails(ids: list[int], op_id: int) -> dict:
    if not ids:
        return {"ok": False, "error": "empty"}
    db = get_pg_connection("recrutement")
    in_clause = ",".join(str(int(i)) for i in ids if int(i))
    if not in_clause:
        return {"ok": False, "error": "empty"}
    db.query(
        f"""UPDATE recrutement.pgt_cvtheque_temporaire
               SET modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
             WHERE id_cvtheque_auto IN ({in_clause})""",
        (int(op_id),),
    )
    return {"ok": True, "count": in_clause.count(",") + 1}


def restore_mail(id_mail: int, op_id: int) -> dict:
    """Bouton 'Restaurer ce mail' : repasse modif_elem='modif' pour que
    le mail reapparaisse dans la liste 'a traiter'."""
    if not id_mail:
        return {"ok": False, "error": "id_required"}
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque_temporaire
              SET modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
            WHERE id_cvtheque_auto = ?""",
        (int(op_id), int(id_mail)),
    )
    return {"ok": True}


def link_mail_to_cv(id_mail: int, id_cv: int, op_id: int) -> dict:
    """Apres conversion : marque le mail temp comme suppr + lie l'id_cv
    cree (cf WinDev reqUpCvTemp)."""
    if not id_mail or not id_cv:
        return {"ok": False, "error": "ids_required"}
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque_temporaire
              SET modif_date = NOW(), modif_op = ?,
                  modif_elem = 'suppr', id_cvtheque = ?
            WHERE id_cvtheque_auto = ?""",
        (int(op_id), int(id_cv), int(id_mail)),
    )
    return {"ok": True}


def get_mail_contenu(id_mail: int) -> dict:
    """Pour Fen_CvPreSaisiContenu (loupe verte) : retourne le contenu
    complet d'un mail (objet + contenu + nom du fichier CV attache)."""
    db = get_pg_connection("recrutement")
    r = db.query_one(
        """SELECT id_cvtheque_auto, nom, prenom, mail, gsm, ville, cp,
                  mail_objet, mail_contenu, mail_date, fic_cv, lien_cv,
                  adr_mail_rh, observ
             FROM recrutement.pgt_cvtheque_temporaire
            WHERE id_cvtheque_auto = ?""",
        (int(id_mail),),
    )
    if not r:
        return {}
    return {
        "id_mail": str(_int(r["id_cvtheque_auto"])),
        "nom": _str(r.get("nom")),
        "prenom": _str(r.get("prenom")),
        "mail": _str(r.get("mail")),
        "gsm": _str(r.get("gsm")),
        "ville": _str(r.get("ville")),
        "cp": _str(r.get("cp")),
        "mail_objet": _str(r.get("mail_objet")),
        "mail_contenu": _str(r.get("mail_contenu")),
        "mail_date": _date_str(r.get("mail_date")),
        "fic_cv": _str(r.get("fic_cv")),
        "lien_cv": _str(r.get("lien_cv")),
        "adr_mail_rh": _str(r.get("adr_mail_rh")),
        "observ": _str(r.get("observ")),
    }
