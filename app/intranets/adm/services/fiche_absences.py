"""
Onglet 'Absences' de la fiche salarie ADM.

Transposition de la fenetre WinDev FI_SalarieAbsences :
  - Tableau hierarchique groupe par Periode (AnneeConge, du 1er juin N
    au 31 mai N+1) puis par Type d'absence (IDTypeAbsence).
  - Colonnes : Motif | Du | Au | Nb Jours calendaires (NBJ) | Nb Jours
    ouvres Hors Samedi (NBJ_OUVRES) | nb Samedi.
  - Boutons : Nouveau / Modifier (popup Fen_SalarieAbsence) / Dupliquer
    (copie avec nouvel id) / Supprimer (soft delete via modif_elem).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.core.database.pg import get_pg_connection
from app.core.utils.sentinel_dates import is_sentinel


# --- Jours feries francais -----------------------------------------------

def _easter(year: int) -> date:
    """Calcul de la date de Paques (algorithme de Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d_ = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_ - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, mois, jour)


def _is_jour_ferie_fr(d: date) -> bool:
    """Jours feries metropole (fixes + Paques + derives)."""
    # Fixes
    if (d.month, d.day) in {
        (1, 1),   # Jour de l'an
        (5, 1),   # Fete du travail
        (5, 8),   # Victoire 1945
        (7, 14),  # Fete nationale
        (8, 15),  # Assomption
        (11, 1),  # Toussaint
        (11, 11), # Armistice 1918
        (12, 25), # Noel
    }:
        return True
    # Variables (Paques + derives)
    paques = _easter(d.year)
    if d == paques + timedelta(days=1):  # Lundi de Paques
        return True
    if d == paques + timedelta(days=39): # Jeudi de l'Ascension
        return True
    if d == paques + timedelta(days=50): # Lundi de Pentecote
        return True
    return False


def compute_absence_metadata(date_debut_iso: str, date_fin_iso: str) -> dict:
    """Calcule periode + NBJ + NBJ_OUVRES + nbSamedi a partir des dates ISO.

    Transposition du code WinDev de Fen_SalarieAbsence btn Enregistrer :
      - periode : si date_debut.mois <= 6 -> '(annee-1)-annee' sinon
        'annee-(annee+1)' (annee de conges du 1er juin N au 31 mai N+1).
      - NBJ : nombre de jours calendaires inclusifs.
      - NBJ_OUVRES : nombre de jours lundi-vendredi non feries.
      - nbSamedi : nombre de vendredis travailles (convention Omaya :
        30 jours de conges, 1 vendredi pose = 1 samedi decompte).
        Note : pas de cap a 5/an applique ici, c'est cote operateur.
    """
    if not date_debut_iso:
        return {"periode": "", "nbj": 0, "nbj_ouvres": 0, "nb_samedi": 0}
    try:
        d_deb = datetime.fromisoformat(date_debut_iso).date()
    except ValueError:
        return {"periode": "", "nbj": 0, "nbj_ouvres": 0, "nb_samedi": 0}

    # Periode (annee de conges, du 1er juin N au 31 mai N+1)
    # Mois 1-5 (jan-mai) -> periode precedente (annee-1)-annee
    # Mois 6-12 (juin-dec) -> periode courante annee-(annee+1)
    # NB : le code WinDev fait '<=6' (inclut juin dans periode precedente),
    # ce qui etait un bug : l'utilisateur a confirme '<6' (juin dans la
    # nouvelle periode).
    if d_deb.month < 6:
        periode = f"{d_deb.year - 1}-{d_deb.year}"
    else:
        periode = f"{d_deb.year}-{d_deb.year + 1}"

    nbj = 0
    nbj_ouvres = 0
    nb_samedi = 0
    d_fin: date | None = None
    if date_fin_iso:
        try:
            d_fin = datetime.fromisoformat(date_fin_iso).date()
        except ValueError:
            d_fin = None

    if d_fin and d_fin >= d_deb:
        nbj = (d_fin - d_deb).days + 1
        cur = d_deb
        while cur <= d_fin:
            # WLangage : 1=Lundi ... 7=Dimanche
            jour = cur.isoweekday()
            if jour <= 5 and not _is_jour_ferie_fr(cur):
                nbj_ouvres += 1
                if jour == 5:  # Vendredi (convention Omaya)
                    nb_samedi += 1
            cur += timedelta(days=1)

    return {
        "periode": periode,
        "nbj": nbj,
        "nbj_ouvres": nbj_ouvres,
        "nb_samedi": nb_samedi,
    }


def list_types_absence() -> list[dict]:
    """Combo Type d'absence."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_absence, lib_absence
           FROM rh.pgt_type_absence
           WHERE modif_elem NOT LIKE '%suppr%'
           ORDER BY lib_absence ASC NULLS LAST"""
    )
    return [
        {
            "id_type_absence": _int(r.get("id_type_absence")),
            "lib_absence": _str(r.get("lib_absence")),
        }
        for r in rows
    ]


def get_absence(id_absence: int) -> dict | None:
    """Recupere une absence pour pre-remplir la popup d'edition."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_absence, id_salarie, id_type_absence,
                  date_debut, date_fin, nbj, nbj_ouvres, nb_samedi, periode
           FROM rh.pgt_absence WHERE id_absence = ?""",
        (int(id_absence),),
    )
    if not row:
        return None
    return {
        "id_absence": str(row.get("id_absence") or ""),
        "id_salarie": str(row.get("id_salarie") or ""),
        "id_type_absence": _int(row.get("id_type_absence")),
        "date_debut": _iso(row.get("date_debut")),
        "date_fin": _iso(row.get("date_fin")),
        "nbj": _int(row.get("nbj")),
        "nbj_ouvres": _int(row.get("nbj_ouvres")),
        "nb_samedi": _int(row.get("nb_samedi")),
        "periode": _str(row.get("periode")),
    }


def save_absence(
    *,
    id_absence: int,  # 0 = creation
    id_salarie: int,
    id_type_absence: int,
    date_debut: str,
    date_fin: str,
    op_id: int,
) -> dict:
    """Cree ou modifie une absence avec calcul automatique des metadonnees."""
    meta = compute_absence_metadata(date_debut, date_fin)
    db = get_pg_connection("rh")

    if id_absence:
        db.query(
            """UPDATE rh.pgt_absence SET
                  id_type_absence = ?,
                  date_debut = ?, date_fin = ?,
                  nbj = ?, nbj_ouvres = ?, nb_samedi = ?,
                  periode = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_absence = ?""",
            (
                int(id_type_absence),
                date_debut or None, date_fin or None,
                meta["nbj"], meta["nbj_ouvres"], meta["nb_samedi"],
                meta["periode"],
                int(op_id), int(id_absence),
            ),
        )
        return {"ok": True, "id_absence": str(id_absence), **meta}

    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_absence
              (id_absence, id_salarie, id_type_absence,
               date_debut, date_fin, nbj, nbj_ouvres, nb_samedi, periode,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id, int(id_salarie), int(id_type_absence),
            date_debut or None, date_fin or None,
            meta["nbj"], meta["nbj_ouvres"], meta["nb_samedi"],
            meta["periode"],
            int(op_id),
        ),
    )
    return {"ok": True, "id_absence": str(new_id), **meta}


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso(v: Any) -> str:
    if v is None or is_sentinel(v):
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _new_id() -> int:
    """ID 8 octets timestamp (cf. WinDev idEntierDateHeureSys)."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def load_absences(id_salarie: int) -> list[dict]:
    """Liste les absences du salarie, triees par periode desc puis par
    type d'absence puis par date debut desc.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              a.id_absence, a.id_type_absence,
              a.date_debut, a.date_fin,
              a.nbj, a.nbj_ouvres, a.nb_samedi,
              a.periode,
              ta.lib_absence
           FROM rh.pgt_absence a
           LEFT JOIN rh.pgt_type_absence ta
             ON ta.id_type_absence = a.id_type_absence
           WHERE a.id_salarie = ?
             AND a.modif_elem NOT LIKE '%suppr%'
           ORDER BY a.periode DESC NULLS LAST,
                    a.id_type_absence ASC,
                    a.date_debut DESC NULLS LAST""",
        (int(id_salarie),),
    )
    return [
        {
            "id_absence": str(r.get("id_absence") or ""),
            "id_type_absence": _int(r.get("id_type_absence")),
            "lib_absence": _str(r.get("lib_absence")),
            "date_debut": _iso(r.get("date_debut")),
            "date_fin": _iso(r.get("date_fin")),
            "nbj": _int(r.get("nbj")),
            "nbj_ouvres": _int(r.get("nbj_ouvres")),
            "nb_samedi": _int(r.get("nb_samedi")),
            "periode": _str(r.get("periode")),
        }
        for r in rows
    ]


def duplicate_absence(id_absence: int, op_id: int) -> dict:
    """Btn 'Dupliquer' : copie l'absence avec un nouvel id (modif_elem='new')."""
    db = get_pg_connection("rh")
    row = db.query_one(
        """SELECT id_salarie, id_type_absence, date_debut, date_fin,
                  nbj, nbj_ouvres, nb_samedi, periode
           FROM rh.pgt_absence WHERE id_absence = ?""",
        (int(id_absence),),
    )
    if not row:
        return {"ok": False, "error": "Absence introuvable"}

    new_id = _new_id()
    db.query(
        """INSERT INTO rh.pgt_absence
              (id_absence, id_salarie, id_type_absence,
               date_debut, date_fin, nbj, nbj_ouvres, nb_samedi, periode,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, 'new')""",
        (
            new_id,
            _int(row.get("id_salarie")),
            _int(row.get("id_type_absence")),
            row.get("date_debut"),
            row.get("date_fin"),
            _int(row.get("nbj")),
            _int(row.get("nbj_ouvres")),
            _int(row.get("nb_samedi")),
            _str(row.get("periode")),
            _int(op_id),
        ),
    )
    return {"ok": True, "id_absence": str(new_id)}


def soft_delete_absence(id_absence: int, op_id: int) -> dict:
    """Btn 'Supprimer' : passe modif_elem='suppr'."""
    db = get_pg_connection("rh")
    db.query(
        """UPDATE rh.pgt_absence SET
              modif_date = NOW(),
              modif_op = ?,
              modif_elem = 'suppr'
            WHERE id_absence = ?""",
        (_int(op_id), int(id_absence)),
    )
    return {"ok": True}
