"""FI_CartePro (type 2 — Carte PRO).

Liste TK_DemandeCartePRO du ticket (base ticket_bo) jointe salarié.
Édition : NumSuivi + photo (remplacement via @ATTACHMEMO@). Si la photo
du salarié est vide, on l'y recopie (cf. WinDev). Impression PDF
(EtatCartePro : photo + nom + raison sociale).
"""

import base64
import io
import os
import tempfile

from app.core.database import get_connection
from app.core.database.pg import get_pg_connection

from ..service import (
    _clean_id,
    _icone_to_data_url,
    _now_windev,
    _to_int,
    load_salaries_minimal,
    maj_op_traitement_ticket,
    salarie_infos_batch,
)


def _photo_data_url(id_ligne: int) -> str:
    """Mémo PHOTO d'une ligne → data URL (PG bytea)."""
    try:
        db = get_pg_connection("ticket_bo")
        r = db.query_one(
            "SELECT id_tk_demande_carte_pro, photo FROM pgt_tk_demande_carte_pro "
            "WHERE id_tk_demande_carte_pro = ?",
            (int(id_ligne),),
        )
        return _icone_to_data_url(r.get("photo") if r else None)
    except Exception:
        return ""


def load(id_ticket: int) -> dict:
    db = get_pg_connection("ticket_bo")
    try:
        rows = db.query(
            """SELECT id_tk_demande_carte_pro, id_salarie, num_suivi
            FROM pgt_tk_demande_carte_pro
            WHERE id_tk_liste = ?
              AND modif_elem NOT LIKE '%suppr%'
            ORDER BY date_crea""",
            (int(id_ticket),),
        )
    except Exception:
        rows = []

    sal_ids: set[int] = set()
    base: list[dict] = []
    for r in rows:
        idl = _clean_id(_to_int(r.get("id_tk_demande_carte_pro")))
        if not idl:
            continue
        sid = _clean_id(_to_int(r.get("id_salarie")))
        if sid:
            sal_ids.add(sid)
        base.append({
            "id": str(idl),
            "id_salarie": str(sid) if sid else "",
            "num_suivi": (r.get("num_suivi") or "").strip(),
        })

    infos = salarie_infos_batch(sal_ids)
    for ligne in base:
        sid = int(ligne["id_salarie"]) if ligne["id_salarie"] else 0
        inf = infos.get(sid, {})
        nom = inf.get("nom", "")
        prenom = inf.get("prenom", "")
        prenom_cap = (
            prenom[:1].upper() + prenom[1:].lower() if prenom else ""
        )
        ligne["nom_prenom"] = f"{nom} {prenom_cap}".strip()
        ligne["date_embauche"] = inf.get("date_embauche", "")
        ligne["entite"] = inf.get("lib_societe", "")
        ligne["photo_data_url"] = _photo_data_url(int(ligne["id"]))

    return {"lignes": base}


def _decode_image(b64: str) -> bytes | None:
    """data URL ou base64 brut → octets."""
    if not b64:
        return None
    s = b64.strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma == -1:
            return None
        s = s[comma + 1:]
    try:
        return base64.b64decode(s)
    except Exception:
        return None


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    id_ligne = str(payload.get("id_ligne") or "")
    if not id_ligne.isdigit():
        return {"ok": False, "error": "Ligne invalide"}
    num_suivi = str(payload.get("num_suivi") or "").strip()
    now = _now_windev()

    db = get_connection("ticket_bo")
    # IDSalarie de la ligne (pour la photo + recopie salarié)
    row = db.query_one(
        "SELECT IDSalarie FROM TK_DemandeCartePRO "
        "WHERE IDTK_DemandeCartePRO = ?",
        (int(id_ligne),),
    )
    if not row:
        return {"ok": False, "error": "Ligne introuvable"}
    id_salarie = _clean_id(_to_int(row.get("IDSalarie")))

    db.query(
        """UPDATE TK_DemandeCartePRO
        SET NumSuivi = ?, ModifDate = ?, ModifELEM = 'modif', ModifOP = ?
        WHERE IDTK_DemandeCartePRO = ?""",
        (num_suivi, now, int(user_id), int(id_ligne)),
    )

    # Photo (optionnelle) : remplacement du mémo via @ATTACHMEMO@
    img = _decode_image(payload.get("photo_b64") or "")
    if img:
        tmp = os.path.join(
            tempfile.gettempdir(), f"cartepro_{id_ligne}.jpg"
        )
        with open(tmp, "wb") as f:
            f.write(img)
        try:
            db.attach_memo(
                "TK_DemandeCartePRO", "IDTK_DemandeCartePRO",
                int(id_ligne), "PHOTO", tmp,
            )
            # Si la photo du salarié est vide → on l'y recopie (cf. WinDev).
            # Le check de la photo se fait sur HFSQL (pre-attach) pour eviter
            # le lag PG, l'attach_memo reste HFSQL.
            if id_salarie:
                db_rh = get_connection("rh")
                sp = db_rh.query_one(
                    "SELECT IDSalarie, Photo FROM salarie WHERE IDSalarie = ?",
                    (int(id_salarie),),
                )
                if not _icone_to_data_url(sp.get("Photo") if sp else None):
                    db_rh.attach_memo(
                        "salarie", "IDSalarie", int(id_salarie),
                        "Photo", tmp,
                    )
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    maj_op_traitement_ticket(int(id_ticket), int(user_id))
    return {"ok": True}


def print_pdf(id_ticket: int, payload: dict) -> bytes:
    """État WinDev EtatCartePro → PDF (photo + nom + raison sociale)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    id_ligne = str(payload.get("id_ligne") or "")
    if not id_ligne.isdigit():
        raise ValueError("Ligne invalide")

    db = get_connection("ticket_bo")
    row = db.query_one(
        "SELECT IDSalarie FROM TK_DemandeCartePRO "
        "WHERE IDTK_DemandeCartePRO = ?",
        (int(id_ligne),),
    )
    id_salarie = _clean_id(_to_int(row.get("IDSalarie"))) if row else 0
    sal = load_salaries_minimal({id_salarie}) if id_salarie else {}
    info_soc = salarie_infos_batch({id_salarie}) if id_salarie else {}
    s = sal.get(id_salarie, {})
    nom = s.get("nom", "")
    prenom = s.get("prenom", "")
    prenom_cap = prenom[:1].upper() + prenom[1:].lower() if prenom else ""
    lib_nom = f"{nom} {prenom_cap}".strip()
    lib_rs = info_soc.get(id_salarie, {}).get("lib_societe", "")

    data_url = _photo_data_url(int(id_ligne))
    img_bytes = _decode_image(data_url) if data_url else None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Cadrage repris de l'état WinDev EtatCartePro (cf. PDF de réf) :
    # vignette centrée dans un cadre ~42x52 mm, placée vers le haut,
    # puis nom + raison sociale en gras centrés dessous.
    box_w, box_h = 42 * mm, 52 * mm
    box_top = h - 38 * mm           # bord haut du cadre photo
    bottom_img = box_top - box_h    # bord bas effectif (par défaut)
    if img_bytes:
        try:
            ir = ImageReader(io.BytesIO(img_bytes))
            iw, ih = ir.getSize()
            ratio = min(box_w / iw, box_h / ih)
            dw, dh = iw * ratio, ih * ratio
            x = (w - dw) / 2
            y = box_top - dh
            c.drawImage(
                ir, x, y, dw, dh,
                preserveAspectRatio=True, mask="auto",
            )
            bottom_img = y
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, bottom_img - 12 * mm, lib_nom)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(w / 2, bottom_img - 20 * mm, lib_rs)
    c.showPage()
    c.save()
    return buf.getvalue()
