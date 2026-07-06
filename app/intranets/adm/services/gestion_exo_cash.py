"""
Service Gestion Exo Cash (transposition Fen_GestionExoCash).

3 onglets :
  1. Lots (pgt_exo_cash_lot)
  2. Famille Prod (pgt_exo_cash_famille_lot)
  3. Suivi des livrets (pgt_salarie_livret AGG)

Cf. WinDev Code Init :
  - ReqLot         : JOIN exo_cash_lot + exo_cash_famille_lot + salarie (modif_op)
  - reqListeFamille: SELECT famille_lot WHERE modif_elem != 'suppr'
  - reqSuiviLivret : SUM(debit/credit) par salarie actif hors id_ste=4 et id=6
"""

import base64
import logging
from datetime import date, datetime
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _new_id() -> int:
    """Id 8 octets (equiv WinDev idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _to_iso(v) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)[:19]
    return s if not is_sentinel(s) else ""


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return "-".join(x[:1].upper() + x[1:].lower() for x in p.split("-"))


def _photo_url(id_lot: int, num: int) -> Optional[str]:
    """Retourne une URL relative pour recuperer la photo si presente."""
    return f"/api/adm/gestion-exo-cash/lots/{id_lot}/photo/{num}"


# --------------------------------------------------------------------
# Onglet 1 : Lots
# --------------------------------------------------------------------

def list_lots() -> list[dict]:
    """Cf. WinDev ReqLot : liste des lots avec famille + operateur modif."""
    db = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    rows = db.query(
        """SELECT l.id_exo_cash_lot, l.id_exo_cash_famille_lot,
                  l.lib_lot, l.marque, l.categorie, l.montant, l.stock,
                  l.sur_commande, l.en_solde, l.montant_solde,
                  l.solde_deb, l.solde_fin, l.is_actif,
                  l.description, l.modif_date, l.modif_op,
                  (l.photo1 IS NOT NULL) AS has_photo1,
                  (l.photo2 IS NOT NULL) AS has_photo2,
                  (l.photo3 IS NOT NULL) AS has_photo3,
                  f.lib_famille_lot
             FROM divers.pgt_exo_cash_lot l
             JOIN divers.pgt_exo_cash_famille_lot f
                  ON f.id_exo_cash_famille_lot = l.id_exo_cash_famille_lot
            WHERE (l.modif_elem IS NULL OR l.modif_elem NOT LIKE '%suppr%')
            ORDER BY f.lib_famille_lot ASC NULLS LAST,
                     l.marque ASC NULLS LAST,
                     l.lib_lot ASC NULLS LAST""",
    ) or []

    # Enrichissement modif_op (rh.pgt_salarie)
    op_ids = {int(r.get("modif_op") or 0) for r in rows}
    op_ids.discard(0)
    ops = {}
    if op_ids:
        try:
            ids_sql = ",".join(str(i) for i in op_ids)
            for s in rh.query(
                f"SELECT id_salarie, nom, prenom FROM pgt_salarie "
                f"WHERE id_salarie IN ({ids_sql})",
            ) or []:
                sid = int(s["id_salarie"])
                nom = (s.get("nom") or "").strip()
                prenom = _cap_prenom((s.get("prenom") or "").strip())
                ops[sid] = f"{nom} {prenom}".strip()
        except Exception:
            pass

    return [
        {
            "id_exo_cash_lot": _clean_id(r.get("id_exo_cash_lot")),
            "id_exo_cash_famille_lot": _clean_id(r.get("id_exo_cash_famille_lot")),
            "lib_famille_lot": (r.get("lib_famille_lot") or "").strip(),
            "marque": (r.get("marque") or "").strip(),
            "lib_lot": (r.get("lib_lot") or "").strip(),
            "categorie": int(r.get("categorie") or 0),
            "montant": float(r.get("montant") or 0),
            "stock": int(r.get("stock") or 0),
            "sur_commande": bool(r.get("sur_commande")),
            "en_solde": bool(r.get("en_solde")),
            "montant_solde": float(r.get("montant_solde") or 0),
            "solde_deb": _to_iso(r.get("solde_deb")),
            "solde_fin": _to_iso(r.get("solde_fin")),
            "is_actif": bool(r.get("is_actif")),
            "description": r.get("description") or "",
            "modif_date": _to_iso(r.get("modif_date")),
            "modif_op": _clean_id(r.get("modif_op")),
            "modif_op_nom": ops.get(int(r.get("modif_op") or 0), ""),
            "has_photo1": bool(r.get("has_photo1")),
            "has_photo2": bool(r.get("has_photo2")),
            "has_photo3": bool(r.get("has_photo3")),
        }
        for r in rows
    ]


def get_lot(id_lot: int) -> Optional[dict]:
    """Detail d'un lot (sans les photos - a recuperer via endpoint dedie)."""
    db = get_pg_connection("divers")
    r = db.query_one(
        """SELECT id_exo_cash_lot, id_exo_cash_famille_lot,
                  lib_lot, marque, categorie, montant, stock,
                  sur_commande, en_solde, montant_solde,
                  solde_deb, solde_fin, is_actif, description,
                  (photo1 IS NOT NULL) AS has_photo1,
                  (photo2 IS NOT NULL) AS has_photo2,
                  (photo3 IS NOT NULL) AS has_photo3
             FROM divers.pgt_exo_cash_lot
            WHERE id_exo_cash_lot = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (int(id_lot),),
    )
    if not r:
        return None
    return {
        "id_exo_cash_lot": _clean_id(r.get("id_exo_cash_lot")),
        "id_exo_cash_famille_lot": _clean_id(r.get("id_exo_cash_famille_lot")),
        "marque": (r.get("marque") or "").strip(),
        "lib_lot": (r.get("lib_lot") or "").strip(),
        "categorie": int(r.get("categorie") or 0),
        "montant": float(r.get("montant") or 0),
        "stock": int(r.get("stock") or 0),
        "sur_commande": bool(r.get("sur_commande")),
        "en_solde": bool(r.get("en_solde")),
        "montant_solde": float(r.get("montant_solde") or 0),
        "solde_deb": _to_iso(r.get("solde_deb")),
        "solde_fin": _to_iso(r.get("solde_fin")),
        "is_actif": bool(r.get("is_actif")),
        "description": r.get("description") or "",
        "has_photo1": bool(r.get("has_photo1")),
        "has_photo2": bool(r.get("has_photo2")),
        "has_photo3": bool(r.get("has_photo3")),
    }


def save_lot(payload: dict, op_id: int) -> dict:
    """Cf. WinDev Btn Enregistrer :
    - Si id_exo_cash_lot == 0 : INSERT (avec nouvel id)
    - Sinon : UPDATE
    Retour : {ok, id_exo_cash_lot}
    """
    db = get_pg_connection("divers")
    id_lot = int(payload.get("id_exo_cash_lot") or 0)
    now = _now_iso()

    fields = {
        "id_exo_cash_famille_lot": int(payload.get("id_exo_cash_famille_lot") or 0),
        "marque": (payload.get("marque") or "")[:25],
        "lib_lot": (payload.get("lib_lot") or "")[:50],
        "description": payload.get("description") or "",
        "montant": float(payload.get("montant") or 0),
        "categorie": int(payload.get("categorie") or 0),
        "stock": int(payload.get("stock") or 0),
        "sur_commande": bool(payload.get("sur_commande")),
        "en_solde": bool(payload.get("en_solde")),
        "montant_solde": float(payload.get("montant_solde") or 0),
        "solde_deb": payload.get("solde_deb") or None,
        "solde_fin": payload.get("solde_fin") or None,
        "is_actif": bool(payload.get("is_actif", True)),
    }

    if id_lot == 0:
        id_lot = _new_id()
        try:
            db.query(
                """INSERT INTO divers.pgt_exo_cash_lot
                     (id_exo_cash_lot, id_exo_cash_famille_lot, marque, lib_lot,
                      description, montant, categorie, stock, sur_commande,
                      en_solde, montant_solde, solde_deb, solde_fin, is_actif,
                      modif_op, modif_date, modif_elem)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, 'new')""",
                (
                    id_lot,
                    fields["id_exo_cash_famille_lot"],
                    fields["marque"], fields["lib_lot"],
                    fields["description"], fields["montant"],
                    fields["categorie"], fields["stock"],
                    fields["sur_commande"], fields["en_solde"],
                    fields["montant_solde"],
                    fields["solde_deb"], fields["solde_fin"],
                    fields["is_actif"],
                    int(op_id), now,
                ),
            )
        except Exception as e:
            logger.exception("INSERT pgt_exo_cash_lot")
            return {"ok": False, "error": f"INSERT : {e}"}
    else:
        try:
            db.query(
                """UPDATE divers.pgt_exo_cash_lot
                      SET id_exo_cash_famille_lot = ?, marque = ?,
                          lib_lot = ?, description = ?, montant = ?,
                          categorie = ?, stock = ?, sur_commande = ?,
                          en_solde = ?, montant_solde = ?,
                          solde_deb = ?, solde_fin = ?, is_actif = ?,
                          modif_op = ?, modif_date = ?, modif_elem = 'modif'
                    WHERE id_exo_cash_lot = ?""",
                (
                    fields["id_exo_cash_famille_lot"],
                    fields["marque"], fields["lib_lot"],
                    fields["description"], fields["montant"],
                    fields["categorie"], fields["stock"],
                    fields["sur_commande"], fields["en_solde"],
                    fields["montant_solde"],
                    fields["solde_deb"], fields["solde_fin"],
                    fields["is_actif"],
                    int(op_id), now,
                    id_lot,
                ),
            )
        except Exception as e:
            logger.exception("UPDATE pgt_exo_cash_lot")
            return {"ok": False, "error": f"UPDATE : {e}"}

    return {"ok": True, "id_exo_cash_lot": str(id_lot)}


def duplicate_lot(id_lot: int, op_id: int) -> dict:
    """Cf. WinDev Btn Duplique : nouvel id + copie de toutes les colonnes.
    Les photos sont copiees aussi (bytea to bytea, INSERT ... SELECT).
    """
    db = get_pg_connection("divers")
    new_id = _new_id()
    now = _now_iso()
    try:
        db.query(
            """INSERT INTO divers.pgt_exo_cash_lot
                 (id_exo_cash_lot, id_exo_cash_famille_lot, marque, lib_lot,
                  description, montant, categorie, stock, sur_commande,
                  en_solde, montant_solde, solde_deb, solde_fin, is_actif,
                  photo1, photo2, photo3,
                  modif_op, modif_date, modif_elem)
               SELECT ?, id_exo_cash_famille_lot, marque, lib_lot,
                      description, montant, categorie, stock, sur_commande,
                      en_solde, montant_solde, solde_deb, solde_fin, is_actif,
                      photo1, photo2, photo3,
                      ?, ?, 'new'
                 FROM divers.pgt_exo_cash_lot
                WHERE id_exo_cash_lot = ?""",
            (new_id, int(op_id), now, int(id_lot)),
        )
    except Exception as e:
        logger.exception("duplicate pgt_exo_cash_lot")
        return {"ok": False, "error": f"DUPLICATE : {e}"}
    return {"ok": True, "id_exo_cash_lot": str(new_id)}


def delete_lot(id_lot: int, op_id: int) -> dict:
    """Cf. WinDev Btn Suppr : soft-delete (modif_elem = 'suppr')."""
    db = get_pg_connection("divers")
    now = _now_iso()
    try:
        db.query(
            """UPDATE divers.pgt_exo_cash_lot
                  SET modif_op = ?, modif_date = ?, modif_elem = 'suppr'
                WHERE id_exo_cash_lot = ?""",
            (int(op_id), now, int(id_lot)),
        )
    except Exception as e:
        return {"ok": False, "error": f"DELETE : {e}"}
    return {"ok": True}


def upload_photo(
    id_lot: int, num: int, content: bytes, op_id: int,
) -> dict:
    """Cf. WinDev Charger Photo N + Btn Enregistrer :
    HAttacheMemo(ExoCashLot, PhotoN, LibFicPhotoN).
    Ecrit le bytea dans la colonne photoN + met a jour modif_op/date.
    """
    if num not in (1, 2, 3):
        return {"ok": False, "error": "Numero photo invalide"}
    col = f"photo{num}"
    db = get_pg_connection("divers")
    now = _now_iso()
    try:
        db.query(
            f"""UPDATE divers.pgt_exo_cash_lot
                   SET {col} = ?,
                       modif_op = ?, modif_date = ?, modif_elem = 'modif'
                 WHERE id_exo_cash_lot = ?""",
            (content, int(op_id), now, int(id_lot)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE photo : {e}"}
    return {"ok": True}


def delete_photo(id_lot: int, num: int, op_id: int) -> dict:
    """Cf. WinDev Btn Suppr photo N : Photo = '' + UPDATE."""
    if num not in (1, 2, 3):
        return {"ok": False, "error": "Numero photo invalide"}
    col = f"photo{num}"
    db = get_pg_connection("divers")
    now = _now_iso()
    try:
        db.query(
            f"""UPDATE divers.pgt_exo_cash_lot
                   SET {col} = NULL,
                       modif_op = ?, modif_date = ?, modif_elem = 'modif'
                 WHERE id_exo_cash_lot = ?""",
            (int(op_id), now, int(id_lot)),
        )
    except Exception as e:
        return {"ok": False, "error": f"DELETE photo : {e}"}
    return {"ok": True}


def get_photo(id_lot: int, num: int) -> Optional[bytes]:
    """Retourne le contenu de la photo (bytea) ou None."""
    if num not in (1, 2, 3):
        return None
    col = f"photo{num}"
    db = get_pg_connection("divers")
    r = db.query_one(
        f"SELECT {col} AS photo FROM divers.pgt_exo_cash_lot "
        f"WHERE id_exo_cash_lot = ?",
        (int(id_lot),),
    )
    if not r:
        return None
    v = r.get("photo")
    if v is None:
        return None
    if isinstance(v, memoryview):
        return v.tobytes()
    if isinstance(v, bytes):
        return v
    # psycopg2 peut renvoyer str si bytea sort en hex - tenter decode
    if isinstance(v, str):
        try:
            return base64.b64decode(v)
        except Exception:
            return None
    return None


# --------------------------------------------------------------------
# Onglet 2 : Familles (lookup pour combo)
# --------------------------------------------------------------------

def list_familles() -> list[dict]:
    """Cf. WinDev reqListeFamille : liste des familles actives."""
    db = get_pg_connection("divers")
    rows = db.query(
        """SELECT id_exo_cash_famille_lot, lib_famille_lot,
                  (icone IS NOT NULL) AS has_icone
             FROM divers.pgt_exo_cash_famille_lot
            WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
            ORDER BY lib_famille_lot ASC NULLS LAST""",
    ) or []
    return [
        {
            "id_exo_cash_famille_lot": _clean_id(r.get("id_exo_cash_famille_lot")),
            "lib_famille_lot": (r.get("lib_famille_lot") or "").strip(),
            "has_icone": bool(r.get("has_icone")),
        }
        for r in rows
    ]


def save_famille(id_famille: int, lib_famille: str, op_id: int) -> dict:
    """Cf. WinDev Btn Enregistrer Famille : INSERT si id=0, UPDATE sinon."""
    lib_famille = (lib_famille or "").strip()[:50]
    if not lib_famille:
        return {"ok": False, "error": "Libelle vide"}
    db = get_pg_connection("divers")
    now = _now_iso()
    if id_famille == 0:
        id_famille = _new_id()
        try:
            db.query(
                """INSERT INTO divers.pgt_exo_cash_famille_lot
                     (id_exo_cash_famille_lot, lib_famille_lot,
                      modif_op, modif_date, modif_elem)
                   VALUES (?, ?, ?, ?, 'new')""",
                (id_famille, lib_famille, int(op_id), now),
            )
        except Exception as e:
            return {"ok": False, "error": f"INSERT : {e}"}
    else:
        try:
            db.query(
                """UPDATE divers.pgt_exo_cash_famille_lot
                      SET lib_famille_lot = ?,
                          modif_op = ?, modif_date = ?, modif_elem = 'modif'
                    WHERE id_exo_cash_famille_lot = ?""",
                (lib_famille, int(op_id), now, id_famille),
            )
        except Exception as e:
            return {"ok": False, "error": f"UPDATE : {e}"}
    return {"ok": True, "id_exo_cash_famille_lot": str(id_famille)}


def delete_famille(id_famille: int, op_id: int) -> dict:
    """Cf. WinDev Btn Suppr Famille : soft-delete."""
    db = get_pg_connection("divers")
    now = _now_iso()
    try:
        db.query(
            """UPDATE divers.pgt_exo_cash_famille_lot
                  SET modif_op = ?, modif_date = ?, modif_elem = 'suppr'
                WHERE id_exo_cash_famille_lot = ?""",
            (int(op_id), now, int(id_famille)),
        )
    except Exception as e:
        return {"ok": False, "error": f"DELETE : {e}"}
    return {"ok": True}


def upload_icone(id_famille: int, content: bytes, op_id: int) -> dict:
    """Cf. WinDev Btn Telecharger + Enregistrer : HAttacheMemo(icone, ...)."""
    db = get_pg_connection("divers")
    now = _now_iso()
    try:
        db.query(
            """UPDATE divers.pgt_exo_cash_famille_lot
                  SET icone = ?,
                      modif_op = ?, modif_date = ?, modif_elem = 'modif'
                WHERE id_exo_cash_famille_lot = ?""",
            (content, int(op_id), now, int(id_famille)),
        )
    except Exception as e:
        return {"ok": False, "error": f"UPDATE icone : {e}"}
    return {"ok": True}


def get_icone(id_famille: int) -> Optional[bytes]:
    """Retourne le bytea de l'icone ou None."""
    db = get_pg_connection("divers")
    r = db.query_one(
        "SELECT icone FROM divers.pgt_exo_cash_famille_lot "
        "WHERE id_exo_cash_famille_lot = ?",
        (int(id_famille),),
    )
    if not r:
        return None
    v = r.get("icone")
    if v is None:
        return None
    if isinstance(v, memoryview):
        return v.tobytes()
    if isinstance(v, bytes):
        return v
    if isinstance(v, str):
        try:
            return base64.b64decode(v)
        except Exception:
            return None
    return None


# --------------------------------------------------------------------
# Onglet 3 : Suivi des livrets (AGG salarie_Livret)
# --------------------------------------------------------------------

def list_suivi_livrets() -> list[dict]:
    """Cf. WinDev reqSuiviLivret : SUM debit/credit par salarie actif.

    Filtres :
      - modif_elem != 'suppr'
      - en_activite = TRUE
      - id_ste <> 4 (a preciser : quelle societe est exclue ?)
      - id_salarie <> 6 (utilisateur systeme exclu)
      - id_salarie <> 0

    Tri par -Solde_Livret (credit - debit) DESC.
    """
    db_rh = get_pg_connection("rh")
    rows = db_rh.query(
        """SELECT l.id_salarie,
                  s.nom, s.prenom,
                  COALESCE(SUM(l.montant_debit), 0) AS somme_debit,
                  COALESCE(SUM(l.montant_credit), 0) AS somme_credit
             FROM pgt_salarie s
             JOIN pgt_salarie_livret l
                  ON s.id_salarie = l.id_salarie
             JOIN pgt_salarie_embauche e
                  ON e.id_salarie = s.id_salarie
            WHERE (l.modif_elem IS NULL
                   OR l.modif_elem NOT LIKE '%suppr%')
              AND e.en_activite = TRUE
              AND e.id_ste <> 4
              AND e.id_salarie <> 6
              AND e.id_salarie <> 0
            GROUP BY l.id_salarie, s.nom, s.prenom
            ORDER BY (COALESCE(SUM(l.montant_credit), 0)
                    - COALESCE(SUM(l.montant_debit), 0)) DESC""",
    ) or []
    return [
        {
            "id_salarie": _clean_id(r.get("id_salarie")),
            "nom_prenom": (
                f"{(r.get('nom') or '').strip()} "
                f"{_cap_prenom((r.get('prenom') or '').strip())}"
            ).strip(),
            "somme_debit": float(r.get("somme_debit") or 0),
            "somme_credit": float(r.get("somme_credit") or 0),
            "solde_livret": (
                float(r.get("somme_credit") or 0)
                - float(r.get("somme_debit") or 0)
            ),
        }
        for r in rows
    ]
