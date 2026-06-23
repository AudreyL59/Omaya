"""
Service Fen_ListeDocUlease (ADM Ulease -> Liste des documents Ulease).

Calque sur ctt_travail.py mais en plus simple :
- Pas de id_type_produit / doc_dpae / doc_dpae_distrib / photo_dpae.
- Tables : ulease.pgt_doc_ulease + ulease.pgt_doc_ulease_type.
- Societe (id_ste) en cross-schema rh.pgt_societe pour le libelle.

Boutons :
  - list_docs (glissiere actif/archive)
  - duplicate_doc (force prioritaire=False)
  - archive_doc / restore_doc (doc_actif=False/True)
  - delete_doc (soft delete)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.shared.notifications.mail import envoi_mail


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _new_id() -> int:
    """idEntierDateHeureSys WinDev."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def list_docs(doc_actif: bool = True) -> list[dict]:
    """ReqListeDocUlease : JOIN type + societe (cross-schema)."""
    db_ul = get_pg_connection("ulease")
    rows = db_ul.query(
        """SELECT d.id_doc_ulease, d.id_type_doc, d.titre, d.info_cpl,
                  d.datecrea, d.doc_actif, d.prioritaire, d.modif_date,
                  d.id_ste, t.lib_type
             FROM ulease.pgt_doc_ulease d
        LEFT JOIN ulease.pgt_doc_ulease_type t
               ON t.id_type_doc = d.id_type_doc
            WHERE (d.modif_elem IS NULL OR d.modif_elem NOT LIKE '%suppr%')
              AND COALESCE(d.doc_actif, FALSE) = ?
         ORDER BY t.lib_type ASC NULLS LAST, d.titre ASC""",
        (bool(doc_actif),),
    ) or []

    # Libelle societe (cross-schema rh)
    ids_ste = sorted({_int(r.get("id_ste")) for r in rows if _int(r.get("id_ste"))})
    ste_by_id: dict[int, str] = {}
    if ids_ste:
        db_rh = get_pg_connection("rh")
        placeholders = ",".join(["?"] * len(ids_ste))
        srows = db_rh.query(
            f"""SELECT id_ste, COALESCE(rs_interne, raison_sociale) AS lib
                  FROM rh.pgt_societe WHERE id_ste IN ({placeholders})""",
            tuple(ids_ste),
        ) or []
        ste_by_id = {_int(s.get("id_ste")): _str(s.get("lib")) for s in srows}

    return [
        {
            "id_doc_ulease": str(_int(r.get("id_doc_ulease")) or r.get("id_doc_ulease") or ""),
            "id_type_doc": str(_int(r.get("id_type_doc")) or ""),
            "lib_type": _str(r.get("lib_type")),
            "titre": _str(r.get("titre")),
            "info_cpl": _str(r.get("info_cpl")),
            "id_ste": str(_int(r.get("id_ste")) or ""),
            "ste_lib": ste_by_id.get(_int(r.get("id_ste")), ""),
            "prioritaire": bool(r.get("prioritaire")),
            "datecrea": _str(r.get("datecrea"))[:19],
            "modif_date": _str(r.get("modif_date"))[:19],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def duplicate_doc(
    id_doc_ulease: int, op_id: int, user_login: str = "",
    user_prenom: str = "",
) -> dict:
    """Btn Dupliquer : copie le doc, force prioritaire=False, modif_elem='new'."""
    db = get_pg_connection("ulease")
    src = db.query_one(
        "SELECT * FROM ulease.pgt_doc_ulease WHERE id_doc_ulease = ? LIMIT 1",
        (int(id_doc_ulease),),
    )
    if not src:
        return {"ok": False, "error": "Document introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO ulease.pgt_doc_ulease
              (id_doc_ulease, id_type_doc, titre, info_cpl, contenu,
               datecrea, doc_actif, prioritaire, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?,
                   NOW(), TRUE, FALSE, ?,
                   NOW(), ?, 'new')""",
        (
            new_id,
            _int(src.get("id_type_doc")),
            _str(src.get("titre")),
            _str(src.get("info_cpl")),
            src.get("contenu"),
            _int(src.get("id_ste")),
            int(op_id),
        ),
    )

    # Mail a marie@exosphere.fr (cf. WinDev usersCial <> 256)
    if int(op_id) != 256 and user_login:
        try:
            envoi_mail(
                sujet=f"Document Ulease duplique {_str(src.get('titre'))} - {_str(src.get('info_cpl'))}",
                html=(
                    f"<p>Bonjour,</p>"
                    f"<p>Le document Ulease <b>{_str(src.get('titre'))} - "
                    f"{_str(src.get('info_cpl'))}</b> vient d'etre duplique par "
                    f"<b>{user_prenom or user_login}</b>.</p>"
                    f"<p>Cordialement.</p>"
                ),
                destinataires=["marie@exosphere.fr"],
                expediteur=user_login,
            )
        except Exception:
            pass
    return {"ok": True, "id_doc_ulease": str(new_id)}


def archive_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Btn Archiver : doc_actif=FALSE."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET doc_actif = FALSE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


def restore_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Re-actif depuis l'archive."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET doc_actif = TRUE,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


def delete_doc(id_doc_ulease: int, op_id: int) -> dict:
    """Btn Supprimer : soft delete (modif_elem='suppr')."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'suppr'
            WHERE id_doc_ulease = ?""",
        (int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Combo types doc
# ---------------------------------------------------------------------------


def list_types_doc() -> list[dict]:
    """Combo Type Doc Ulease."""
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT id_type_doc, lib_type FROM ulease.pgt_doc_ulease_type
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY lib_type""",
    ) or []
    return [
        {"id_type_doc": str(_int(r.get("id_type_doc"))), "lib": _str(r.get("lib_type"))}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Fen_EditionDocUlease - meta + contenu + publipostage
# ---------------------------------------------------------------------------


def get_doc_meta(id_doc_ulease: int) -> dict | None:
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT id_doc_ulease, id_type_doc, titre, info_cpl,
                  doc_actif, prioritaire, id_ste,
                  octet_length(contenu) AS taille_contenu
             FROM ulease.pgt_doc_ulease
            WHERE id_doc_ulease = ? LIMIT 1""",
        (int(id_doc_ulease),),
    )
    if not r:
        return None
    return {
        "id_doc_ulease": str(_int(r.get("id_doc_ulease"))),
        "id_type_doc": str(_int(r.get("id_type_doc")) or ""),
        "titre": _str(r.get("titre")),
        "info_cpl": _str(r.get("info_cpl")),
        "doc_actif": bool(r.get("doc_actif")),
        "prioritaire": bool(r.get("prioritaire")),
        "id_ste": str(_int(r.get("id_ste")) or ""),
        "taille_contenu": _int(r.get("taille_contenu")),
    }


def create_doc_blank(op_id: int) -> dict:
    """Btn Nouveau (cote modal) : cree un doc vide. Cf. WinDev HRAZ+HAjoute."""
    db = get_pg_connection("ulease")
    new_id = _new_id()
    db.query(
        """INSERT INTO ulease.pgt_doc_ulease
              (id_doc_ulease, id_type_doc, titre, info_cpl,
               datecrea, doc_actif, prioritaire, id_ste,
               modif_date, modif_op, modif_elem)
           VALUES (?, 0, 'Nouveau document', '',
                   NOW(), TRUE, FALSE, 0,
                   NOW(), ?, 'new')""",
        (new_id, int(op_id)),
    )
    return {"ok": True, "id_doc_ulease": str(new_id)}


def update_doc_meta(id_doc_ulease: int, payload: dict, op_id: int) -> dict:
    """PUT metadonnees (sans contenu)."""
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET id_type_doc = ?,
                  titre = ?,
                  info_cpl = ?,
                  id_ste = ?,
                  doc_actif = ?,
                  prioritaire = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (
            _int(payload.get("id_type_doc")),
            _str(payload.get("titre")),
            _str(payload.get("info_cpl")),
            _int(payload.get("id_ste")),
            bool(payload.get("doc_actif")),
            bool(payload.get("prioritaire")),
            int(op_id),
            int(id_doc_ulease),
        ),
    )
    return {"ok": True}


def upload_doc_content(id_doc_ulease: int, content: bytes, op_id: int) -> dict:
    """Replace le bytea 'contenu' (upload d'un .docx ou HTML)."""
    if not content:
        return {"ok": False, "error": "Contenu vide"}
    import psycopg2
    db = get_pg_connection("ulease")
    db.query(
        """UPDATE ulease.pgt_doc_ulease
              SET contenu = ?,
                  modif_date = NOW(),
                  modif_op = ?,
                  modif_elem = 'modif'
            WHERE id_doc_ulease = ?""",
        (psycopg2.Binary(content), int(op_id), int(id_doc_ulease)),
    )
    return {"ok": True, "taille": len(content)}


def download_doc_content(id_doc_ulease: int) -> bytes | None:
    db = get_pg_connection("ulease")
    r = db.query_one(
        "SELECT contenu FROM ulease.pgt_doc_ulease WHERE id_doc_ulease = ? LIMIT 1",
        (int(id_doc_ulease),),
    )
    if not r:
        return None
    c = r.get("contenu")
    if c is None:
        return None
    return bytes(c) if isinstance(c, memoryview) else c


# ---------------------------------------------------------------------------
# Combos Test avec : salaries + vehicules attribues
# ---------------------------------------------------------------------------


def list_salaries_test() -> list[dict]:
    """Combo 'Test avec' (cote modal Edition) : salaries pour
    publipostage de test reel (alternative aux donnees fictives).
    Limite 200 pour eviter une combo geante."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY nom ASC, prenom ASC LIMIT 200""",
    ) or []
    return [{
        "id_salarie": str(_int(r.get("id_salarie"))),
        "lib": f"{_str(r.get('nom'))} {_str(r.get('prenom')).strip().capitalize()}".strip(),
    } for r in rows]


def list_attributions_salarie(id_salarie: int) -> list[dict]:
    """Combo 'Avec vehicule' pour le salarie selectionne :
    vehicule_conducteur actifs (RestitutionDate vide ou >= today)."""
    if not id_salarie:
        return []
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT vc.id_vehicule_pc, vf.immat,
                  vc.perception_date, vc.restitution_date
             FROM ulease.pgt_vehicule_conducteur vc
       INNER JOIN ulease.pgt_conducteur c
               ON c.id_conducteur = vc.id_conducteur
       INNER JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
            WHERE (vc.modif_elem IS NULL OR vc.modif_elem NOT LIKE '%suppr%')
              AND c.id_salarie = ?
         ORDER BY vc.perception_date DESC LIMIT 50""",
        (int(id_salarie),),
    ) or []
    out = []
    for r in rows:
        immat = _str(r.get("immat"))
        d_deb = _str(r.get("perception_date"))[:10]
        d_fin = _str(r.get("restitution_date"))[:10]
        lib = f"{immat} (du {d_deb}" + (f" au {d_fin})" if d_fin else " - en cours)")
        out.append({
            "id_vehicule_pc": str(_int(r.get("id_vehicule_pc"))),
            "lib": lib,
        })
    return out


# ---------------------------------------------------------------------------
# Publipostage Vehicule (specifique Ulease)
# ---------------------------------------------------------------------------


_FAKE_VEHICULE = {
    "AUTO_IMMA": "AB-123-CD",
    "AUTO_TYPE": "RENAULT CLIO",
    "AUTO_CV": "5",
    "AUTO_KM": "12500",
    "DATE_DEB": datetime.now().strftime("%d/%m/%Y"),
    "DATE_FIN": "",
}


def _vehicule_variables(id_pc: int) -> dict:
    """Variables AUTO_* + DATE_DEB/DATE_FIN depuis vehicule_conducteur."""
    if not id_pc:
        return {}
    db = get_pg_connection("ulease")
    r = db.query_one(
        """SELECT vc.perception_date, vc.restitution_date,
                  vf.immat, vf.modele, vf.k_mdepart, vf.chevaux_fiscaux,
                  vm.nom AS marque_nom
             FROM ulease.pgt_vehicule_conducteur vc
       INNER JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
        LEFT JOIN ulease.pgt_vehicule_marque vm
               ON vm.id_vehicule_marque = vf.id_vehicule_marque
            WHERE vc.id_vehicule_pc = ? LIMIT 1""",
        (int(id_pc),),
    )
    if not r:
        return {}
    def _fr(v) -> str:
        if not v:
            return ""
        s = str(v)
        if len(s) >= 10 and s[4] == "-":
            return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
        return s
    return {
        "AUTO_IMMA": _str(r.get("immat")),
        "AUTO_TYPE": f"{_str(r.get('marque_nom'))} {_str(r.get('modele'))}".strip(),
        "AUTO_CV": str(_int(r.get("chevaux_fiscaux")) or ""),
        "AUTO_KM": str(_int(r.get("k_mdepart")) or ""),
        "DATE_DEB": _fr(r.get("perception_date")),
        "DATE_FIN": _fr(r.get("restitution_date")),
    }


def _salarie_variables(id_salarie: int) -> dict:
    """Variables S_* depuis pgt_salarie + pgt_salarie_coordonnees +
    pgt_salarie_embauche (cf. WinDev Publipostage_Salarié)."""
    if not id_salarie:
        return {}
    db_rh = get_pg_connection("rh")
    s = db_rh.query_one(
        """SELECT civilite, nom, prenom, lieu_naiss, dep_naiss, num_ss,
                  date_naiss FROM rh.pgt_salarie
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    if not s:
        return {}
    coord = db_rh.query_one(
        """SELECT adresse1, cp, ville FROM rh.pgt_salarie_coordonnees
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    emb = db_rh.query_one(
        """SELECT date_debut, date_fin_per_essai, date_anciennete
             FROM rh.pgt_salarie_embauche
            WHERE id_salarie = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY date_debut DESC LIMIT 1""",
        (int(id_salarie),),
    ) or {}
    def _fr(v) -> str:
        if not v:
            return ""
        s = str(v)
        if len(s) >= 10 and s[4] == "-":
            return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
        return s
    civ = _int(s.get("civilite"))
    titre = "Mr." if civ == 1 else "Mme"
    return {
        "S_TITRE": titre,
        "S_NOM": _str(s.get("nom")),
        "S_PRENOM": _str(s.get("prenom")),
        "S_LNAISS": _str(s.get("lieu_naiss")),
        "S_DEPNAISS": str(_int(s.get("dep_naiss")) or ""),
        "S_NUMSS": _str(s.get("num_ss")),
        "S_DNAISS": _fr(s.get("date_naiss")),
        "S_ADRESSE": _str(coord.get("adresse1")),
        "S_CP": _str(coord.get("cp")),
        "S_VILLE": _str(coord.get("ville")),
        "DATE_CTS": _fr(emb.get("date_debut")),
        "DATE_ANC": _fr(emb.get("date_anciennete")),
        "FIN_PER_ESSAI": _fr(emb.get("date_fin_per_essai")),
        "SECTEURAGENCE": "",  # ReqOrgaCourante a brancher si besoin
        "S_MENTION": "",
        "S_SIGN": "",
    }


# ---------------------------------------------------------------------------
# Test PDF (Btn 'Tester Mise en page')
# ---------------------------------------------------------------------------


def publipostage_test_pdf(
    id_doc_ulease: int,
    id_ste: int,
    id_salarie: int = 0,
    id_vehicule_pc: int = 0,
    titre_doc: str = "",
) -> bytes | None:
    """Btn 'Tester Mise en page' Fen_EditionDocUlease : PDF avec :
      - donnees fictives si id_salarie=0
      - donnees salarie reel sinon
      - + variables vehicule si id_vehicule_pc != 0 (ou fictives).
    Delegue a generer_pdf_publiposte (reutilise ctt_travail)."""
    from app.intranets.adm.services.ctt_travail import (
        _FAKE_SALARIE, _docx_to_html, _replace_in_docx,
        _societe_variables, generer_pdf_publiposte, is_docx,
    )

    content = download_doc_content(id_doc_ulease)
    if not content:
        return None

    # Variables salarie
    if id_salarie:
        variables = _salarie_variables(id_salarie)
    else:
        variables = dict(_FAKE_SALARIE)

    # Variables vehicule
    if id_vehicule_pc:
        variables.update(_vehicule_variables(id_vehicule_pc))
    else:
        variables.update(_FAKE_VEHICULE)

    # Variables societe
    if id_ste:
        ste_vars = _societe_variables(id_ste)
        if titre_doc:
            ste_vars["DOCTITRE"] = titre_doc
        variables.update(ste_vars)

    # Convertit DOCX -> HTML si necessaire + substitue les variables.
    if is_docx(content):
        try:
            filled = _replace_in_docx(content, variables)
            body_html = _docx_to_html(filled)
        except Exception:
            return None
    else:
        try:
            body_html = content.decode("utf-8")
            for key, val in sorted(
                variables.items(), key=lambda kv: -len(kv[0]),
            ):
                if key == "STE_LOGO":
                    continue
                body_html = body_html.replace(key, str(val))
        except Exception:
            return None

    return generer_pdf_publiposte(body_html, id_ste=id_ste)
