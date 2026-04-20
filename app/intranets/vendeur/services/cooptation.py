"""
Services cooptation : listing, recherche vendeurs, création.

Transposition de PAGE_Cooptations / POPUP_SansNom1 / Popup1 WinDev.
Table cvtheque + cvsuivi dans Bdd_Omaya_Recrutement.
"""

import base64
import re
import struct
from datetime import datetime

from app.core.database import get_connection


def _to_int_safe(v) -> int:
    """Convertit une valeur HFSQL en int, en décodant base64 si nécessaire (8-byte integers)."""
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _now_windev() -> str:
    """Format date/heure WinDev : YYYYMMDDHHMMSSmmm (17 chars)."""
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"


def _today_windev() -> str:
    """Date du jour WinDev : YYYYMMDD."""
    return datetime.now().strftime("%Y%m%d")


def _new_id() -> int:
    """ID unique à partir de la date/heure (équivalent idEntierDateHeureSys)."""
    return int(_now_windev())


def _format_tel(tel: str) -> str:
    """Garde uniquement les chiffres du numéro de téléphone."""
    return re.sub(r"\D", "", tel or "")


def lister_cooptations_du_jour(id_salarie: int) -> list[dict]:
    """Liste des cooptations saisies par l'utilisateur aujourd'hui."""
    db = get_connection("recrutement")
    today = _today_windev()

    rows = db.query(
        """SELECT NOM, PRENOM, DateSAISIE
        FROM cvtheque
        WHERE Opé_SAISIE = ?
          AND LEFT(DateSAISIE, 8) >= ?
        ORDER BY DateSAISIE DESC""",
        (id_salarie, today),
    )

    return [
        {
            "nom": r.get("NOM") or "",
            "prenom": r.get("PRENOM") or "",
            "date_saisie": r.get("DateSAISIE") or "",
        }
        for r in rows
    ]


def _orga_descendants(db, root_ids: set[int]) -> set[int]:
    """
    Retourne les idorganigramme de l'orga racine + tous ses descendants.
    BFS itératif pour ne pas dépendre des CTE récursifs HFSQL.
    """
    all_ids = set(root_ids)
    frontier = set(root_ids)
    while frontier:
        ids_sql = ",".join(str(i) for i in frontier)
        rows = db.query(
            f"""SELECT idorganigramme FROM organigramme
            WHERE IdPARENT IN ({ids_sql})
              AND ModifELEM NOT LIKE '%suppr%'"""
        )
        next_frontier = set()
        for r in rows:
            cid = int(r.get("idorganigramme") or 0)
            if cid and cid not in all_ids:
                all_ids.add(cid)
                next_frontier.add(cid)
        frontier = next_frontier
    return all_ids


def rechercher_vendeurs(
    id_salarie_user: int,
    search: str,
    acces_global: bool = False,
    is_resp: bool = False,
) -> list[dict]:
    """
    Recherche les vendeurs (salariés actifs) accessibles à l'utilisateur connecté.

    - `acces_global=True` : recherche sur tous les salariés actifs (droit ProdRezo).
    - `is_resp=True` : manager → orga du user + descendants.
    - Sinon : uniquement l'orga directe du user.
    """
    search = (search or "").strip().upper()
    if not search:
        return []

    db = get_connection("rh")
    today = _today_windev()
    like_pattern = f"{search}%"

    # Acces global : recherche sur tous les salariés actifs
    if acces_global:
        rows = db.query(
            """SELECT DISTINCT s.IDSalarie, s.NOM, s.PRENOM
            FROM salarie s
            INNER JOIN salarie_embauche se ON s.IDSalarie = se.IDSalarie
            WHERE se.EnActivité = 1
              AND s.NOM LIKE ?
            ORDER BY s.NOM, s.PRENOM""",
            (like_pattern,),
        )
        return [
            {
                "id_salarie": str(_to_int_safe(r.get("IDSalarie"))),
                "nom": r.get("NOM") or "",
                "prenom": r.get("PRENOM") or "",
                "poste": "",
            }
            for r in rows
        ]

    # 1. Récupérer les organigrammes actifs du user
    orga_rows = db.query(
        """SELECT DISTINCT idorganigramme FROM salarie_organigramme
        WHERE IDSalarie = ?
          AND ModifELEM NOT LIKE '%suppr%'
          AND LEFT(DateDébut, 8) <= ?""",
        (id_salarie_user, today),
    )
    orga_ids = {int(r.get("idorganigramme") or 0) for r in orga_rows}
    orga_ids.discard(0)

    # Si le user est manager, on ajoute tous les sous-orgas
    if is_resp and orga_ids:
        orga_ids = _orga_descendants(db, orga_ids)

    if not orga_ids:
        # Fallback : tous les salariés actifs (si pas d'orga active pour le user)
        rows = db.query(
            "SELECT DISTINCT s.IDSalarie, s.NOM, s.PRENOM FROM salarie s "
            "INNER JOIN salarie_embauche se ON s.IDSalarie = se.IDSalarie "
            "WHERE se.EnActivité = 1 AND s.NOM LIKE ? "
            "ORDER BY s.NOM, s.PRENOM",
            (like_pattern,),
        )
        return [
            {
                "id_salarie": str(_to_int_safe(r.get("IDSalarie"))),
                "nom": r.get("NOM") or "",
                "prenom": r.get("PRENOM") or "",
                "poste": "",
            }
            for r in rows
        ]
    orga_ids_sql = ",".join(str(i) for i in orga_ids)

    # 2. Lister les salariés actifs des mêmes orgas, dont le nom commence par `search`
    rows = db.query(
        f"""SELECT DISTINCT s.IDSalarie, s.NOM, s.PRENOM
        FROM salarie s
        INNER JOIN salarie_embauche se ON s.IDSalarie = se.IDSalarie
        INNER JOIN salarie_organigramme so ON s.IDSalarie = so.IDSalarie
        WHERE so.ModifELEM NOT LIKE '%suppr%'
          AND LEFT(so.DateDébut, 8) <= ?
          AND so.idorganigramme IN ({orga_ids_sql})
          AND se.EnActivité = 1
          AND s.NOM LIKE ?
        ORDER BY s.NOM, s.PRENOM""",
        (today, like_pattern),
    )

    return [
        {
            "id_salarie": str(_to_int_safe(r.get("IDSalarie"))),
            "nom": r.get("NOM") or "",
            "prenom": r.get("PRENOM") or "",
            "poste": "",
        }
        for r in rows
    ]


def creer_cooptation(
    data: dict,
    id_salarie_user: int,
    id_ste_user: int,
) -> int:
    """
    Crée une cooptation dans cvtheque + entrée cvsuivi initiale.

    data contient : nom, prenom, date_naissance, age, cp, id_ville, gsm,
                    commentaire, id_vendeur, cooptation_directe, nom_parrain, lien_parente

    Retourne l'ID de la cooptation créée.
    """
    db = get_connection("recrutement")

    id_coopt = _new_id()
    now = _now_windev()

    # Date de naissance : si vide et âge fourni, calcul approximatif
    date_naiss = (data.get("date_naissance") or "").strip()
    age = int(data.get("age") or 0)
    commentaire = data.get("commentaire") or ""
    if not date_naiss and age > 0:
        annee = datetime.now().year - age
        date_naiss = f"{annee}{datetime.now().strftime('%m%d')}"
        commentaire += f"\nAge saisi directement : {age} ans, date de naissance approximative recalculée"

    # Observation selon cooptation directe ou via parrain
    if data.get("cooptation_directe"):
        observ = f"{commentaire}\nCooptation directe"
    else:
        parrain = (data.get("nom_parrain") or "").upper()
        lien = data.get("lien_parente") or ""
        observ = f"{commentaire}\nParrain : {parrain}\nLien : {lien}"

    nom = (data.get("nom") or "").upper()
    prenom = (data.get("prenom") or "").upper()
    gsm = _format_tel(data.get("gsm") or "")
    id_ville = int(data.get("id_ville") or 0)
    id_vendeur = int(data.get("id_vendeur") or 0)

    db.query(
        """INSERT INTO cvtheque (
            IDcvtheque, Origine, GSM, IDCommunesFrance, NOM, PRENOM,
            DateNaissance, IDcvsource, IDcvposte, IdElemSource, OBSERV,
            DateSAISIE, IdSte, Opé_SAISIE, MotsClés,
            ModifDate, ModifOP, ModifELEM
        ) VALUES (?, 2, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?, ?, '', ?, ?, 'new')""",
        (
            id_coopt, gsm, id_ville, nom, prenom,
            date_naiss, id_vendeur, observ,
            now, id_ste_user, id_salarie_user,
            now, id_salarie_user,
        ),
    )

    id_suivi = _new_id() + 1
    db.query(
        """INSERT INTO CvSuivi (
            IDCvSuivi, IDcvtheque, OPCREA, IdCvStatut, TypeElem, IdElem,
            Observation, ModifDate, ModifOp, ModifElem
        ) VALUES (?, ?, ?, 1, '', '', '', ?, ?, 'new')""",
        (id_suivi, id_coopt, id_salarie_user, now, id_salarie_user),
    )

    return id_coopt
