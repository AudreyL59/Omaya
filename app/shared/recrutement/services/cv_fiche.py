"""Service Fen_CVFiche (shared : ADM + Vendeur + Call RH).

Endpoints metier :
- get_fiche(id_cv) : detail complet (cvtheque + dernier statut + coopteur)
- list_cvsuivi(id_cv) : historique CvSuivi avec resolveur op_nom + statut_lib
- save_fiche(id_cv, payload, op_id) : enregistrer (HModifie + ajoute CvSuivi
  si statut change). Concatene la nouvelle observation a observ.
- restatuer(id_cv, op_id) : juste ajoute CvSuivi avec le statut courant
  (pas de modif cvtheque autre).
- statut_quick(id_cv, payload, op_id) : applique un statut rapide
  (Refus Cand / RH / Msg Rep / Hors Cible / Etudiant / A recontacter).
- reactualiser(id_cv, op_id) : update date_reac + ajoute CvSuivi statut=1.
- add_observation(id_cv, obs, op_id) : ajoute juste une ligne datee a observ.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.shared.recrutement.schemas.cv_fiche import (
    CheckDoublonPayload, CheckDoublonResponse, CreateCVPayload,
    CreateCVResponse, CVFicheDetail, CVFichePayload, CVObservationPayload,
    CVStatutQuickPayload, CVSuiviRow, DoublonCandidat,
)
from app.shared.recrutement.services.recherche_cv import (
    _calc_age, _int, _norm_date, _str,
)


def _new_id() -> int:
    """idEntierDateHeureSys : timestamp YYYYMMDDHHMMSSmmm sur 8 octets."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def get_fiche(id_cv: int) -> Optional[CVFicheDetail]:
    """Recupere la fiche cvtheque + dernier statut + ville + coopteur."""
    db = get_pg_connection("recrutement")
    row = db.query_one(
        """SELECT cv.*, c.code_postal, c.nom_ville
             FROM recrutement.pgt_cvtheque cv
             LEFT JOIN divers.pgt_communes_france c
                    ON c.id_communes_france = cv.id_communes_france
            WHERE cv.id_cvtheque = ?""",
        (int(id_cv),),
    )
    if not row:
        return None

    # Dernier statut (le plus recent dans cvsuivi)
    last = db.query_one(
        """SELECT id_cv_statut FROM recrutement.pgt_cvsuivi
            WHERE id_cvtheque = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY datecrea DESC NULLS LAST LIMIT 1""",
        (int(id_cv),),
    )
    id_statut = _int(last["id_cv_statut"]) if last else 0

    # Coopteur (si source=1)
    coopteur_nom = ""
    id_src = _int(row.get("id_cvsource"))
    id_elem = _int(row.get("id_elem_source"))
    if id_src == 1 and id_elem:
        db_rh = get_pg_connection("rh")
        s = db_rh.query_one(
            "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ?",
            (id_elem,),
        )
        if s:
            coopteur_nom = (
                f"{_str(s['nom']).upper()} {_str(s['prenom']).strip().title()}"
            )

    return CVFicheDetail(
        id_cvtheque=str(_int(row.get("id_cvtheque"))),
        nom=_str(row.get("nom")),
        prenom=_str(row.get("prenom")),
        adresse=_str(row.get("adresse")),
        id_communes_france=str(_int(row.get("id_communes_france"))),
        code_postal=_str(row.get("code_postal")),
        nom_ville=_str(row.get("nom_ville")),
        pays=_str(row.get("pays")) or "FRANCE",
        date_naissance=str(row.get("date_naissance") or "")[:10],
        age=_calc_age(row.get("date_naissance")),
        permis_b=bool(row.get("permis_b")),
        vehicule=bool(row.get("vehicule")),
        mail=_str(row.get("mail")),
        gsm=_str(row.get("gsm")),
        id_cvposte=str(_int(row.get("id_cvposte"))),
        id_cvsource=str(id_src) if id_src else "",
        id_elem_source=str(id_elem) if id_elem else "",
        id_ste=str(_int(row.get("id_ste"))) if _int(row.get("id_ste")) else "",
        id_cv_statut=str(id_statut) if id_statut else "",
        date_rappel=str(row.get("date_rappel") or "")[:10],
        observ=_str(row.get("observ")),
        fic_cv=_str(row.get("fic_cv")),
        date_saisie=str(row.get("date_saisie") or "")[:19],
        date_reac=str(row.get("date_reac") or "")[:19],
        coopteur_nom=coopteur_nom,
    )


def list_cvsuivi(id_cv: int) -> list[CVSuiviRow]:
    """Historique CvSuivi avec op_nom + statut_lib resolus.

    Si une ligne a une datecrea vide/NULL (cas typique du suivi initial
    'Non Traite' cree a la saisie sans timestamp), on remplace par la
    date_saisie de la cvtheque.
    """
    db = get_pg_connection("recrutement")
    rows = db.query(
        """SELECT id_cv_suivi, datecrea, op_crea, id_cv_statut,
                  type_elem, id_elem, observation
             FROM recrutement.pgt_cvsuivi
            WHERE id_cvtheque = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY datecrea DESC NULLS LAST""",
        (int(id_cv),),
    ) or []
    if not rows:
        return []

    # Fallback date : si une ligne a datecrea vide, on charge la
    # date_saisie de la cvtheque + on PATCH l'enregistrement pour ne plus
    # refaire le fallback aux prochaines lectures.
    has_empty = any(not r.get("datecrea") for r in rows)
    if has_empty:
        fr = db.query_one(
            "SELECT date_saisie FROM recrutement.pgt_cvtheque "
            "WHERE id_cvtheque = ?",
            (int(id_cv),),
        )
        if fr and fr.get("date_saisie"):
            empty_ids = [_int(r["id_cv_suivi"]) for r in rows
                         if not r.get("datecrea") and _int(r.get("id_cv_suivi"))]
            if empty_ids:
                ph = ",".join(["?"] * len(empty_ids))
                db.query(
                    f"""UPDATE recrutement.pgt_cvsuivi
                           SET datecrea = ?, modif_date = NOW()
                         WHERE id_cv_suivi IN ({ph})""",
                    (fr["date_saisie"], *empty_ids),
                )
                # Mets a jour les rows en memoire pour le rendu actuel
                for r in rows:
                    if not r.get("datecrea"):
                        r["datecrea"] = fr["date_saisie"]

    # Resolveur op_crea -> nom_prenom
    op_ids = {_int(r["op_crea"]) for r in rows if _int(r.get("op_crea"))}
    ops: dict[int, str] = {}
    if op_ids:
        db_rh = get_pg_connection("rh")
        ph = ",".join(["?"] * len(op_ids))
        opr = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie "
            f"WHERE id_salarie IN ({ph})",
            tuple(op_ids),
        ) or []
        ops = {_int(r["id_salarie"]):
               f"{_str(r['nom']).upper()} {_str(r['prenom']).strip().title()}"
               for r in opr}

    # Statuts (un seul SELECT pour les libs)
    statut_ids = {_int(r["id_cv_statut"]) for r in rows
                  if _int(r.get("id_cv_statut"))}
    statut_libs: dict[int, str] = {}
    if statut_ids:
        ph = ",".join(["?"] * len(statut_ids))
        sr = db.query(
            f"SELECT id_cv_statut, lib_statut FROM recrutement.pgt_cvstatut "
            f"WHERE id_cv_statut IN ({ph})",
            tuple(statut_ids),
        ) or []
        statut_libs = {_int(r["id_cv_statut"]): _str(r["lib_statut"])
                       for r in sr}

    return [CVSuiviRow(
        id_cv_suivi=str(_int(r["id_cv_suivi"])),
        datecrea=str(r["datecrea"] or "")[:19],
        op_crea=str(_int(r.get("op_crea"))),
        op_nom=ops.get(_int(r.get("op_crea")), ""),
        id_cv_statut=str(_int(r.get("id_cv_statut"))),
        statut_lib=statut_libs.get(_int(r.get("id_cv_statut")), ""),
        type_elem=_str(r.get("type_elem")),
        id_elem=str(_int(r.get("id_elem"))) if _int(r.get("id_elem")) else "",
        observation=_str(r.get("observation")),
    ) for r in rows]


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _add_cvsuivi(
    db, id_cv: int, id_statut: int, op_id: int, observation: str = "",
) -> int:
    """Ajoute une ligne CvSuivi. Retourne le nouvel id."""
    new_id = _new_id()
    db.query(
        """INSERT INTO recrutement.pgt_cvsuivi
             (id_cv_suivi, id_cvtheque, datecrea, op_crea, id_cv_statut,
              type_elem, id_elem, observation,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, NOW(), ?, ?, '', 0, ?,
                   NOW(), ?, 'new')""",
        (new_id, int(id_cv), int(op_id), int(id_statut),
         observation, int(op_id)),
    )
    return new_id


def _format_observ_line(text: str, op_prenom: str) -> str:
    """Format WinDev : 'JJ/MM/AAAA HH:MM par <prenom> : <text>'."""
    return (datetime.now().strftime("%d/%m/%Y %H:%M")
            + " par " + op_prenom + " : " + text.strip())


def _op_prenom(op_id: int) -> str:
    db = get_pg_connection("rh")
    r = db.query_one(
        "SELECT prenom FROM rh.pgt_salarie WHERE id_salarie = ?", (int(op_id),),
    )
    return _str(r.get("prenom")).strip().title() if r else ""


# ---------------------------------------------------------------------------
# Save / actions
# ---------------------------------------------------------------------------


def save_fiche(id_cv: int, p: CVFichePayload, op_id: int) -> dict:
    """Enregistrement (Btn Enregistrer) :
    - UPDATE cvtheque
    - si statut change vs courant : INSERT CvSuivi avec le nouveau
    - si nouvelle_observation : concatene a observ
    """
    db = get_pg_connection("recrutement")

    # Recupere le statut courant pour comparaison
    cur = db.query_one(
        """SELECT id_cv_statut FROM recrutement.pgt_cvsuivi
            WHERE id_cvtheque = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY datecrea DESC NULLS LAST LIMIT 1""",
        (int(id_cv),),
    )
    old_statut = _int(cur["id_cv_statut"]) if cur else 0
    new_statut = _int(p.id_cv_statut)

    # Recupere observ actuelle pour concat
    cur_cv = db.query_one(
        "SELECT observ FROM recrutement.pgt_cvtheque WHERE id_cvtheque = ?",
        (int(id_cv),),
    )
    observ = _str(cur_cv.get("observ")) if cur_cv else ""
    if p.nouvelle_observation.strip():
        prenom = _op_prenom(op_id)
        if observ:
            observ = observ + "\n" + _format_observ_line(p.nouvelle_observation, prenom)
        else:
            observ = _format_observ_line(p.nouvelle_observation, prenom)

    # Date rappel : forcee a NULL si statut <> 2 (A recontacter)
    date_rappel = p.date_rappel if new_statut == 2 else None
    if date_rappel == "":
        date_rappel = None

    # Format tel + email
    gsm = "".join(c for c in p.gsm if c.isdigit() or c == "+")
    mail = p.mail.strip().lower().replace(" ", "")

    db.query(
        """UPDATE recrutement.pgt_cvtheque SET
              nom = ?, prenom = ?, adresse = ?, id_communes_france = ?,
              pays = ?, date_naissance = ?,
              permis_b = ?, vehicule = ?, mail = ?, gsm = ?,
              id_cvposte = ?, id_cvsource = ?, id_elem_source = ?,
              id_ste = ?, observ = ?, date_rappel = ?,
              modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (
            p.nom.upper().strip(), p.prenom.strip(), p.adresse.strip(),
            _int(p.id_communes_france), p.pays.strip().upper() or "FRANCE",
            p.date_naissance or None,
            bool(p.permis_b), bool(p.vehicule), mail, gsm,
            _int(p.id_cvposte), _int(p.id_cvsource), _int(p.id_elem_source),
            _int(p.id_ste), observ, date_rappel,
            int(op_id), int(id_cv),
        ),
    )

    statut_changed = (new_statut != old_statut and new_statut > 0)
    if statut_changed:
        obs = ""
        if new_statut == 6:
            obs = "Statué en direct sans prise de RDV"
        _add_cvsuivi(db, id_cv, new_statut, op_id, obs)

    return {"ok": True, "statut_change": statut_changed}


def restatuer(id_cv: int, op_id: int) -> dict:
    """Btn 'Restatuer le CV' : ajoute juste CvSuivi avec le statut courant."""
    db = get_pg_connection("recrutement")
    cur = db.query_one(
        """SELECT id_cv_statut FROM recrutement.pgt_cvsuivi
            WHERE id_cvtheque = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY datecrea DESC NULLS LAST LIMIT 1""",
        (int(id_cv),),
    )
    if not cur:
        return {"ok": False, "error": "no_statut"}
    statut = _int(cur["id_cv_statut"])
    _add_cvsuivi(db, id_cv, statut, op_id, "")
    return {"ok": True, "id_cv_statut": str(statut)}


def statut_quick(id_cv: int, p: CVStatutQuickPayload, op_id: int) -> dict:
    """Btn statut rapide : applique un nouveau statut + ajoute CvSuivi.

    Si meme statut que courant : restatuer (ajoute juste CvSuivi).
    """
    db = get_pg_connection("recrutement")
    cur = db.query_one(
        """SELECT id_cv_statut FROM recrutement.pgt_cvsuivi
            WHERE id_cvtheque = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY datecrea DESC NULLS LAST LIMIT 1""",
        (int(id_cv),),
    )
    old_statut = _int(cur["id_cv_statut"]) if cur else 0
    new_statut = _int(p.id_cv_statut)

    if new_statut == old_statut:
        # Restatuer simple
        _add_cvsuivi(db, id_cv, new_statut, op_id, p.observation)
        return {"ok": True, "mode": "restatue"}

    # Sinon : update cvtheque (date_rappel si statut=2) + CvSuivi
    date_rappel = p.date_rappel if new_statut == 2 else None
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET date_rappel = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (date_rappel, int(op_id), int(id_cv)),
    )
    _add_cvsuivi(db, id_cv, new_statut, op_id, p.observation)
    return {"ok": True, "mode": "change"}


def reactualiser(id_cv: int, op_id: int) -> dict:
    """Btn 'Reactualiser la fiche' : update date_reac + CvSuivi statut=1."""
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET date_reac = NOW(), ope_reac = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (int(op_id), int(op_id), int(id_cv)),
    )
    _add_cvsuivi(db, id_cv, 1, op_id, "Réactualisation")
    return {"ok": True}


def get_mots_cles(id_cv: int) -> str:
    """Btn loupe Fen_CVEditMotsCles : recupere les mots cles du CV."""
    db = get_pg_connection("recrutement")
    r = db.query_one(
        "SELECT mots_cles FROM recrutement.pgt_cvtheque WHERE id_cvtheque = ?",
        (int(id_cv),),
    )
    return _str(r.get("mots_cles")) if r else ""


def save_mots_cles(id_cv: int, mots_cles: str, op_id: int) -> dict:
    """Btn 'Enregistrer' Fen_CVEditMotsCles : UPDATE des mots cles."""
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET mots_cles = ?, modif_date = NOW(),
                  modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (mots_cles, int(op_id), int(id_cv)),
    )
    return {"ok": True, "mots_cles": mots_cles}


def check_doublon(p: CheckDoublonPayload) -> CheckDoublonResponse:
    """Verifie si un CV avec ce mobile (ou mail) existe deja.

    Le nom+prenom n'est PAS utilise comme critere de doublon car
    homonymes frequents (faux positifs trop nombreux).

    Match :
      - gsm normalise (que des chiffres) — discriminant principal
      - mail (egalite stricte, lowercase trim) — discriminant secondaire
    Retourne tous les candidats trouves (max 10).
    """
    db = get_pg_connection("recrutement")
    where: list[str] = []
    params: list = []

    gsm_clean = "".join(c for c in (p.gsm or "") if c.isdigit())
    if gsm_clean and len(gsm_clean) >= 8:
        # Normalise le GSM stocke aussi pour comparer (regexp_replace)
        where.append("REGEXP_REPLACE(gsm, '[^0-9]', '', 'g') = ?")
        params.append(gsm_clean)
    mail = (p.mail or "").strip().lower().replace(" ", "")
    if mail:
        where.append("LOWER(mail) = ?")
        params.append(mail)

    if not where:
        return CheckDoublonResponse(found=False, candidats=[])

    sql = f"""
        SELECT id_cvtheque, nom, prenom, mail, gsm, date_saisie
          FROM recrutement.pgt_cvtheque
         WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           AND ({" OR ".join(where)})
      ORDER BY date_saisie DESC LIMIT 10
    """
    rows = db.query(sql, tuple(params)) or []
    candidats = [DoublonCandidat(
        id_cvtheque=str(_int(r["id_cvtheque"])),
        identite=(
            f"{_str(r['nom']).upper()} "
            f"{_str(r['prenom']).strip().title()}"
        ).strip(),
        mail=_str(r.get("mail")),
        gsm=_str(r.get("gsm")),
        date_saisie=str(r.get("date_saisie") or "")[:10],
    ) for r in rows]
    return CheckDoublonResponse(found=bool(candidats), candidats=candidats)


def create_cv(p: CreateCVPayload, op_id: int) -> CreateCVResponse:
    """Btn 'Enregistrer' de Fen_CVSaisie : INSERT cvtheque + cvsuivi initial.

    Si force_doublon=True, le statut initial est force a 8 (CV Doublon),
    sinon on prend p.id_cv_statut (defaut '1' = Non Traite).
    """
    db = get_pg_connection("recrutement")

    id_new = _new_id()
    statut = 8 if p.force_doublon else (_int(p.id_cv_statut) or 1)

    # Normalisation
    gsm = "".join(c for c in (p.gsm or "") if c.isdigit() or c == "+")
    mail = (p.mail or "").strip().lower().replace(" ", "")
    nom = (p.nom or "").strip().upper()
    prenom = (p.prenom or "").strip()
    pays = (p.pays or "FRANCE").strip().upper()

    # id_elem_source selon source (=salarie coopteur OU annonceur)
    id_src = _int(p.id_cvsource)
    id_elem = _int(p.id_elem_source) if id_src in (1, 2) else 0

    # INSERT cvtheque (Origine=1 cf. WinDev hardcode)
    db.query(
        """INSERT INTO recrutement.pgt_cvtheque (
              id_cvtheque, origine, nom, prenom, adresse,
              id_communes_france, id_elem_source, date_naissance, pays,
              permis_b, vehicule, mail, gsm, id_cvposte, id_cvsource,
              id_ste, fic_cv, date_saisie, ope_saisie,
              modif_op, modif_date, modif_elem,
              date_reac, ope_reac, observ, date_rappel)
           VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?,
                   '', NOW(), ?, ?, NOW(), 'new',
                   NULL, 0, '', NULL)""",
        (id_new, nom, prenom, (p.adresse or "").strip(),
         _int(p.id_communes_france), id_elem,
         p.date_naissance or None, pays,
         bool(p.permis_b), bool(p.vehicule), mail, gsm,
         _int(p.id_cvposte), id_src, _int(p.id_ste),
         int(op_id), int(op_id)),
    )

    # INSERT cvsuivi initial avec le statut applique
    id_suivi = _new_id() + 1
    db.query(
        """INSERT INTO recrutement.pgt_cvsuivi
             (id_cv_suivi, id_cvtheque, datecrea, op_crea, id_cv_statut,
              type_elem, id_elem, observation,
              modif_date, modif_op, modif_elem)
           VALUES (?, ?, NOW(), ?, ?, '', 0, '',
                   NOW(), ?, 'new')""",
        (id_suivi, id_new, int(op_id), statut, int(op_id)),
    )

    return CreateCVResponse(
        ok=True,
        id_cvtheque=str(id_new),
        id_cv_suivi=str(id_suivi),
        statut_applique=str(statut),
    )


def delete_fiche(id_cv: int, op_id: int) -> dict:
    """Btn 'Supprimer' : soft-delete via modif_elem = 'suppr'."""
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET modif_op = ?, modif_date = NOW(), modif_elem = 'suppr'
            WHERE id_cvtheque = ?""",
        (int(op_id), int(id_cv)),
    )
    return {"ok": True}


def upload_cv_file(
    id_cv: int, nom: str, file_bytes: bytes, original_filename: str,
    op_id: int,
) -> dict:
    """Btn 'Joindre un CV' : upload FTP vers /OMAYA/cvtheque/ + maj fic_cv.

    Naming WinDev : <IdCV>-CV-<NOM_clean><ext>, fallback <IdCV>_<uuid><ext>.
    Le fichier est servi par IIS via DOCS_URL/cvtheque/<nom>.
    """
    import ftplib
    import io
    import re
    import uuid as uuid_mod
    from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER

    if not file_bytes:
        return {"ok": False, "error": "empty"}

    # Extension
    ext = ""
    if "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1].lower()

    # Nom propre (style WinDev : ccSansPonctuationNiEspace + ccSansAccent)
    nom_clean = re.sub(r"[^a-zA-Z0-9]", "", nom or "")
    new_name = f"{int(id_cv)}-CV-{nom_clean}{ext}"
    new_name = new_name.replace(" ", "_")
    if not nom_clean:
        new_name = f"{int(id_cv)}_{uuid_mod.uuid4().hex}{ext}"

    # Upload FTP vers /OMAYA/cvtheque/
    rep_ftp = "/OMAYA/cvtheque"
    try:
        ftp = ftplib.FTP(timeout=15)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
    except Exception as e:
        return {"ok": False, "error": f"FTP connect: {e}"}

    try:
        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            # Cree le dossier si absent
            for part in rep_ftp.strip("/").split("/"):
                try:
                    ftp.cwd(part)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(part)
                        ftp.cwd(part)
                    except ftplib.error_perm:
                        return {"ok": False,
                                "error": f"Impossible de créer {rep_ftp}"}
        ftp.storbinary(f"STOR {new_name}", io.BytesIO(file_bytes))
    except Exception as e:
        return {"ok": False, "error": f"FTP STOR: {e}"}
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    # Update cvtheque.fic_cv (seulement si upload OK)
    db = get_pg_connection("recrutement")
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET fic_cv = ?, modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (new_name, int(op_id), int(id_cv)),
    )
    return {"ok": True, "fic_cv": new_name}


def add_observation(id_cv: int, p: CVObservationPayload, op_id: int) -> dict:
    """Btn disquette : ajoute juste une ligne datee a observ.

    Pas de CvSuivi cree.
    """
    if not p.observation.strip():
        return {"ok": False, "error": "empty"}
    db = get_pg_connection("recrutement")
    cur = db.query_one(
        "SELECT observ FROM recrutement.pgt_cvtheque WHERE id_cvtheque = ?",
        (int(id_cv),),
    )
    if not cur:
        return {"ok": False, "error": "not_found"}
    prenom = _op_prenom(op_id)
    observ = _str(cur.get("observ"))
    line = _format_observ_line(p.observation, prenom)
    observ = observ + "\n" + line if observ else line
    db.query(
        """UPDATE recrutement.pgt_cvtheque
              SET observ = ?, modif_date = NOW(), modif_op = ?, modif_elem = 'new'
            WHERE id_cvtheque = ?""",
        (observ, int(op_id), int(id_cv)),
    )
    return {"ok": True, "observ": observ}
