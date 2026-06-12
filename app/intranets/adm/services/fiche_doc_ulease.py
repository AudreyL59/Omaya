"""
Service Fen_SalarieDocUlease : generation des documents Ulease.

Transposition du pattern Fen_SalarieDocRH adapte aux tables Ulease :
  - Modeles : ulease.pgt_doc_ulease (contenu DOCX en bytea)
  - Types   : ulease.pgt_doc_ulease_type
  - Suivi   : rh.pgt_salarie_doc_ulease
  - Demande : ticket_rh.pgt_tk_demande_sign_ulease (type 34 = signature Ulease)
  - Ticket  : ticket.pgt_tk_liste (service JU, type 34)

Reutilise les helpers prives de fiche_doc_rh_generate (publipostage,
DOCX -> PDF, FTP TempCttw, chargement salarie/societe).
"""

from __future__ import annotations

import io
import os
import sys
import traceback
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection
from app.intranets.adm.services.fiche_doc_rh_generate import (
    _docx_to_pdf,
    _load_salarie,
    _load_societe,
    _new_id,
    _replace_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _iso(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _fmt_fr_date(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _load_id_ste(id_salarie: int) -> int:
    """Recupere idSte du salarie via embauche (1er rattachement)."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_ste FROM rh.pgt_salarie_embauche
            WHERE id_salarie = ? LIMIT 1""",
        (int(id_salarie),),
    )
    return int(row.get("id_ste") or 0) if row else 0


def _load_vehicule_by_pc(id_vehicule_pc: int) -> dict:
    """Charge l'attribution vehicule_conducteur + fiche vehicule par IdPC."""
    if not id_vehicule_pc:
        return {}
    db = get_pg_connection("ulease")
    row = db.query_one(
        """SELECT vc.id_vehicule, vc.perception_date, vc.perception_heure,
                  vc.restitution_date, vc.restitution_heure,
                  vc.k_mdepart, vc.info_vehicule,
                  vf.immat, vf.modele, vf.id_vehicule_marque
             FROM ulease.pgt_vehicule_conducteur vc
             LEFT JOIN ulease.pgt_vehicule_fiche vf
               ON vf.id_vehicule = vc.id_vehicule
            WHERE vc.id_vehicule_pc = ?
            LIMIT 1""",
        (int(id_vehicule_pc),),
    ) or {}
    if row.get("id_vehicule_marque"):
        marque = db.query_one(
            """SELECT nom FROM ulease.pgt_vehicule_marque
                WHERE id_vehicule_marque = ? LIMIT 1""",
            (int(row["id_vehicule_marque"]),),
        )
        if marque:
            row["lib_marque"] = marque.get("nom") or ""
    return row


# ---------------------------------------------------------------------------
# Listing modeles
# ---------------------------------------------------------------------------


def list_models(id_salarie: int) -> list[dict]:
    """Liste des modeles Ulease disponibles pour ce salarie.

    Filtres (cf. WinDev) :
      - doc_actif = TRUE
      - non suppr
      - id_ste = salarie.idSte OU id_ste = 0
      - id_type_doc <> 12
    """
    id_ste = _load_id_ste(id_salarie)
    db = get_pg_connection("ulease")
    rows = db.query(
        """SELECT du.id_doc_ulease, du.id_type_doc, du.titre, du.info_cpl,
                  du.id_ste, du.prioritaire,
                  dut.lib_type
             FROM ulease.pgt_doc_ulease du
             LEFT JOIN ulease.pgt_doc_ulease_type dut
               ON dut.id_type_doc = du.id_type_doc
            WHERE (du.modif_elem IS NULL OR du.modif_elem NOT LIKE '%suppr%')
              AND du.doc_actif = TRUE
              AND (du.id_ste = ? OR du.id_ste = 0)
              AND du.id_type_doc <> 12
            ORDER BY du.id_ste DESC, du.prioritaire DESC NULLS LAST,
                     du.titre""",
        (id_ste,),
    )
    out = []
    db_rh = get_pg_connection("rh")
    societes_cache: dict[int, str] = {}
    for r in rows or []:
        ste = int(r.get("id_ste") or 0)
        rs = ""
        if ste:
            if ste in societes_cache:
                rs = societes_cache[ste]
            else:
                soc = db_rh.query_one(
                    """SELECT rs_interne FROM rh.pgt_societe
                        WHERE id_ste = ? LIMIT 1""",
                    (ste,),
                )
                rs = (soc or {}).get("rs_interne") or ""
                societes_cache[ste] = rs
        out.append({
            "id_doc_ulease": _str(r.get("id_doc_ulease")),
            "id_type_doc": int(r.get("id_type_doc") or 0),
            "lib_type": _str(r.get("lib_type")),
            "titre": _str(r.get("titre")),
            "info_cpl": _str(r.get("info_cpl")),
            "id_ste": _str(r.get("id_ste")),
            "rs_interne": rs,
            "prioritaire": bool(r.get("prioritaire")),
        })
    return out


# ---------------------------------------------------------------------------
# Publipostage + generation
# ---------------------------------------------------------------------------


def _load_model_content(id_doc_ulease: int) -> dict:
    """Charge le DOCX modele + titre + type."""
    db = get_pg_connection("ulease")
    row = db.query_one(
        """SELECT contenu, titre, id_type_doc, id_ste
             FROM ulease.pgt_doc_ulease
            WHERE id_doc_ulease = ? LIMIT 1""",
        (int(id_doc_ulease),),
    )
    if not row:
        raise ValueError(f"Modele Ulease {id_doc_ulease} introuvable")
    contenu = row.get("contenu")
    if contenu is None:
        raise ValueError(f"Modele Ulease {id_doc_ulease} sans contenu DOCX")
    if isinstance(contenu, memoryview):
        contenu = bytes(contenu)
    return {
        "docx_bytes": contenu,
        "titre": _str(row.get("titre")),
        "id_type_doc": int(row.get("id_type_doc") or 0),
        "id_ste": int(row.get("id_ste") or 0),
    }


def _civilite_lib(civ: int) -> str:
    return {1: "Monsieur", 2: "Madame"}.get(int(civ or 0), "")


def _build_publiposted_docx_ulease(
    *,
    id_salarie: int,
    id_doc_ulease: int,
    id_vehicule_pc: int = 0,
) -> dict:
    """Charge le DOCX modele + publipostage simple.

    Variables remplacees :
      - Salarie : S_NOM, S_PRENOM, S_CIVILITE, S_ADRESSE, S_CP, S_VILLE,
        S_DATENAISS, S_LIEUNAISS, S_NUMSS, S_TEL
      - Societe : RS_INTERNE, ADRESSE_STE, CP_STE, VILLE_STE
      - Vehicule (si idPC) : V_IMMAT, V_MARQUE, V_MODELE, V_KMDEPART,
        V_DATEPERCEPTION, V_HEUREPERCEPTION, V_DATERESTITUTION,
        V_HEURERESTITUTION
      - Date du jour : S_DATEEDITION

    NB : remplacements minimalistes. Variables manquantes (S_SIGN, S_MENTION,
    etc.) seront ajoutees au fur et a mesure des besoins reels.
    """
    from docx import Document

    model = _load_model_content(id_doc_ulease)
    docx_bytes = model["docx_bytes"]
    titre_doc = model["titre"]
    id_type_doc = model["id_type_doc"]

    # Chargement des donnees
    s_data = _load_salarie(id_salarie)
    sal = s_data["salarie"]
    coord = s_data["coord"]
    emb = s_data["embauche"]
    id_ste = int(emb.get("id_ste") or 0)
    soc = _load_societe(id_ste) if id_ste else {}
    veh = _load_vehicule_by_pc(id_vehicule_pc) if id_vehicule_pc else {}

    mapping = {
        "S_NOM": _str(sal.get("nom")),
        "S_PRENOM": _str(sal.get("prenom")),
        "S_CIVILITE": _civilite_lib(sal.get("civilite")),
        "S_ADRESSE": _str(coord.get("adresse1")),
        "S_CP": _str(coord.get("cp")),
        "S_VILLE": _str(coord.get("ville")),
        "S_DATENAISS": _fmt_fr_date(sal.get("date_naiss")),
        "S_LIEUNAISS": _str(sal.get("lieu_naiss")),
        "S_NUMSS": _str(sal.get("num_ss")),
        "S_TEL": _str(coord.get("tel_mob")),
        "S_DATEEDITION": _fmt_fr_date(datetime.now()),
        "RS_INTERNE": _str(soc.get("rs_interne")),
        "ADRESSE_STE": _str(soc.get("adresse1")),
        "CP_STE": _str(soc.get("cp")),
        "VILLE_STE": _str(soc.get("ville")),
        "V_IMMAT": _str(veh.get("immat")),
        "V_MARQUE": _str(veh.get("lib_marque")),
        "V_MODELE": _str(veh.get("modele")),
        "V_KMDEPART": _str(veh.get("k_mdepart") or ""),
        "V_DATEPERCEPTION": _fmt_fr_date(veh.get("perception_date")),
        "V_HEUREPERCEPTION": _str(veh.get("perception_heure"))[:5],
        "V_DATERESTITUTION": _fmt_fr_date(veh.get("restitution_date")),
        "V_HEURERESTITUTION": _str(veh.get("restitution_heure"))[:5],
    }

    doc = Document(io.BytesIO(docx_bytes))
    _replace_text(doc, mapping)

    out = io.BytesIO()
    doc.save(out)
    return {
        "docx_bytes": out.getvalue(),
        "titre_doc": titre_doc,
        "id_type_doc": id_type_doc,
        "nom_salarie": (_str(sal.get("nom")) + "_" + _str(sal.get("prenom"))).strip("_"),
    }


def preview_pdf(
    *, id_salarie: int, id_doc_ulease: int, id_vehicule_pc: int = 0
) -> dict:
    """Bouton 'Export PDF' : genere le PDF SANS ecrire en base."""
    built = _build_publiposted_docx_ulease(
        id_salarie=id_salarie,
        id_doc_ulease=id_doc_ulease,
        id_vehicule_pc=id_vehicule_pc,
    )
    pdf_bytes = _docx_to_pdf(built["docx_bytes"])
    safe_nom = built["nom_salarie"].replace(" ", "_") or str(id_salarie)
    safe_titre = built["titre_doc"].replace("/", "-").replace("\\", "-")[:80]
    filename = f"{safe_nom}_{safe_titre}.pdf" if safe_titre else f"{safe_nom}.pdf"
    return {"pdf_bytes": pdf_bytes, "filename": filename}


def generate_doc_ulease(
    *,
    id_salarie: int,
    id_doc_ulease: int,
    id_vehicule_pc: int,
    op_id: int,
    create_suivi: bool = True,
) -> dict:
    """Bouton 'Ticket Omaya' : genere DOCX + PDF + 3 INSERTs PG +
    upload FTP.

    Retourne {ok, id_ticket, id_demande_sign_ulease, id_salarie_doc_ulease,
              pdf_url, titre_doc}.
    """
    built = _build_publiposted_docx_ulease(
        id_salarie=id_salarie,
        id_doc_ulease=id_doc_ulease,
        id_vehicule_pc=id_vehicule_pc,
    )
    docx_bytes = built["docx_bytes"]
    titre_doc = built["titre_doc"]
    id_type_doc = built["id_type_doc"]

    # idDA : pour l'instant, on prend le 1er DA/DR de l'organigramme
    # actif du salarie (a affiner si besoin)
    s_data = _load_salarie(id_salarie)
    idorganigramme = int((s_data["orga"] or {}).get("idorganigramme") or 0)
    id_da = 0  # TODO: RecupListeDaDr (a transposer si necessaire)

    id_ticket = _new_id()

    # 1. Suivi d'edition (optionnel - WinDev fait un OuiNon)
    id_salarie_doc_ulease = 0
    if create_suivi:
        db_rh = get_pg_connection("rh")
        id_salarie_doc_ulease = _new_id()
        db_rh.query(
            """INSERT INTO rh.pgt_salarie_doc_ulease
                  (id_salarie_doc_ulease, id_doc_ulease_type, id_salarie,
                   id_da, date_edition, recu,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, ?, NOW(), FALSE,
                       NOW(), ?, 'new')""",
            (
                id_salarie_doc_ulease,
                id_type_doc,
                int(id_salarie),
                id_da,
                int(op_id),
            ),
        )

    # 2. Demande signature Ulease
    id_demande = _new_id()
    db_trh = get_pg_connection("ticket_rh")
    db_trh.query(
        """INSERT INTO ticket_rh.pgt_tk_demande_sign_ulease
              (id_demande_sign_ulease, id_tk_liste, idorganigramme,
               id_salarie_ulease, id_salarie, id_da, id_pc,
               type_ctt_w, titre_contrat, contenu,
               contrat_genere, contrat_valide, contrat_signe, contrat_annul,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?,
                   TRUE, FALSE, FALSE, FALSE,
                   NOW(), ?, 'new')""",
        (
            id_demande, id_ticket, idorganigramme,
            id_salarie_doc_ulease, int(id_salarie), id_da,
            int(id_vehicule_pc or 0),
            str(id_type_doc), titre_doc, docx_bytes,
            int(op_id),
        ),
    )

    # 3. Ticket (type 34 = signature Ulease, service JU)
    db_t = get_pg_connection("ticket")
    db_t.query(
        """INSERT INTO ticket.pgt_tk_liste
              (id_tk_liste, date_crea, op_crea, op_dest, service,
               id_tk_type_demande, id_tk_statut, cloturee,
               modif_date, modif_op, modif_elem,
               op_traitement_staff, ordre_traitement_staff)
           VALUES (?, NOW(), ?, ?, 'JU', 34, 1, FALSE, NOW(), ?, 'new',
                   0, 0)""",
        (id_ticket, int(op_id), int(id_salarie), int(op_id)),
    )

    # 4. DOCX -> PDF
    pdf_bytes = _docx_to_pdf(docx_bytes)

    # 5. Upload FTP TempCttw (sert d'aperçu apres signature)
    pdf_name = f"{id_ticket}-DocUlease.pdf"
    try:
        from app.shared.tickets.forms.cttw_pdf import ftp_upload
        ftp_path = os.getenv("FTP_TEMPCTTW_PATH", "/OMAYA/TempCttw")
        ftp_upload(ftp_path, pdf_name, pdf_bytes)
    except Exception:
        # PDF deja en base via pgt_tk_demande_sign_ulease.contenu (DOCX)
        traceback.print_exc(file=sys.stderr)

    return {
        "ok": True,
        "id_ticket": str(id_ticket),
        "id_demande_sign_ulease": str(id_demande),
        "id_salarie_doc_ulease": str(id_salarie_doc_ulease),
        "titre_doc": titre_doc,
        "pdf_url": f"https://interne.omaya.fr/TempCttw/{pdf_name}",
    }
