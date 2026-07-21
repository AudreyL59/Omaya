"""Portage WinDev Dialogue_ListeCR_JSON : liste des dialogues du user.

Filtre :
  typeMsg = 0 : dialogues actifs (statut != 4)
  typeMsg = 1 : dialogues clos    (statut  = 4)

Perimetre de visibilite :
  Base : dialogues dont le user est expediteur OU destinataire (dest_ope).
  Si le user est Resp d'equipe (salarie_embauche.RespEquipe=1) :
    + dialogues destines a une orga qu'il gere (dest_orga IN orgas_descendants)
    + dialogues de salaries de ces orgas (avec droit 142 = IntraConv) :
        - lui-meme : sans condition sur Prive
        - autres   : uniquement si Prive = 0

Pour chaque dialogue on renvoie l'agregat dénormalisé (Dests + Echanges
+ PJs regroupees par msg + Histo) via un seul appel API.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import (
    Dialogue, DialogueDest, DialogueHisto, DialogueMsg, DialoguePJ,
)
from app.shared.dialogues.services._helpers import pj_url

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _str_id(v: Any) -> str:
    """IDs 8 octets exposes en string (JS Number depasse 2^53)."""
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _capitalise(v: str) -> str:
    if not v:
        return ""
    return v[:1].upper() + v[1:].lower()


def _fmt_datetime_fr(dt: Any) -> str:
    """Formate un datetime au style WinDev 'Jjj JJ Mmm AAAA, HH:mm'."""
    if not dt:
        return ""
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        mois = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin",
                "Juil", "Aou", "Sep", "Oct", "Nov", "Dec"]
        return (f"{jours[dt.weekday()]} {dt.day:02d} {mois[dt.month - 1]} "
                f"{dt.year}, {dt.hour:02d}:{dt.minute:02d}")
    except Exception:
        return str(dt)


def _iso_datetime(dt: Any) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


# ---------------------------------------------------------------------------
#  Info salarie + expansion Resp d'equipe
# ---------------------------------------------------------------------------

def _info_salarie_dial(id_salarie: int) -> dict:
    """Portage DonneInfoSalarie reduit : retourne id, nom, prenom,
    resp_equipe, affectation (1re orga active du salarie)."""
    rh = get_pg_connection("rh")
    try:
        row = rh.query_one(
            """SELECT s.id_salarie, s.nom, s.prenom, se.resp_equipe
                 FROM rh.pgt_salarie s
                 LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
                WHERE s.id_salarie = ? LIMIT 1""",
            (int(id_salarie),),
        )
    except Exception:
        logger.exception("_info_salarie_dial id=%s", id_salarie)
        return {}
    if not row:
        return {}
    # 1re affectation active du salarie (aff_actif=TRUE)
    affectation_id = 0
    try:
        aff = rh.query_one(
            """SELECT idorganigramme
                 FROM rh.pgt_salarie_organigramme
                WHERE id_salarie = ?
                  AND COALESCE(aff_actif, FALSE) = TRUE
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (int(id_salarie),),
        )
        if aff:
            affectation_id = int(aff.get("idorganigramme") or 0)
    except Exception:
        logger.exception("_info_salarie_dial affectation id=%s", id_salarie)
    return {
        "id_salarie": int(row.get("id_salarie") or 0),
        "nom": row.get("nom") or "",
        "prenom": row.get("prenom") or "",
        "resp_equipe": bool(row.get("resp_equipe")),
        "affectation_id": affectation_id,
    }


def _liste_orga_descendants(id_racine: int) -> set[int]:
    """Portage ListeOrgaComplet : ensemble des idorganigramme
    descendants (inclusif) d'un noeud racine."""
    if not id_racine:
        return set()
    rh = get_pg_connection("rh")
    result: set[int] = {int(id_racine)}
    to_process = [int(id_racine)]
    while to_process:
        parents = tuple(to_process)
        to_process = []
        try:
            rows = rh.query(
                f"""SELECT idorganigramme
                      FROM rh.pgt_organigramme
                     WHERE id_parent IN ({','.join(['?'] * len(parents))})
                       AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
                parents,
            ) or []
        except Exception:
            logger.exception("_liste_orga_descendants parents=%s", parents)
            break
        for r in rows:
            oid = int(r.get("idorganigramme") or 0)
            if oid and oid not in result:
                result.add(oid)
                to_process.append(oid)
    return result


def _salaries_orga_avec_droit(orga_ids: set[int], droit_id: int) -> set[int]:
    """Retourne les id_salarie qui sont affectes a l'une des orgas
    passees ET qui ont le droit `droit_id` actif."""
    if not orga_ids:
        return set()
    rh = get_pg_connection("rh")
    ids_sql = ",".join(str(int(i)) for i in orga_ids)
    try:
        rows = rh.query(
            f"""SELECT DISTINCT so.id_salarie
                  FROM rh.pgt_salarie_organigramme so
                  JOIN rh.pgt_salarie_droit_acces sd ON sd.id_salarie = so.id_salarie
                 WHERE so.idorganigramme IN ({ids_sql})
                   AND sd.id_type_droit_acces = ?
                   AND COALESCE(sd.droit_actif, FALSE) = TRUE""",
            (int(droit_id),),
        ) or []
    except Exception:
        logger.exception("_salaries_orga_avec_droit")
        return set()
    return {int(r.get("id_salarie") or 0) for r in rows if r.get("id_salarie")}


# ---------------------------------------------------------------------------
#  Chargement des dependances d'un dialogue
# ---------------------------------------------------------------------------

def _load_dests(id_dialogue: int, cache_orga: dict, cache_sal: dict) -> list[DialogueDest]:
    db_div = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db_div.query(
            """SELECT id_dialogue_dest, dest_ope, dest_orga
                 FROM divers.pgt_dialoguedest
                WHERE id_dialogues = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (int(id_dialogue),),
        ) or []
    except Exception:
        logger.exception("_load_dests")
        return []
    out: list[DialogueDest] = []
    for r in rows:
        dest_ope = int(r.get("dest_ope") or 0)
        dest_orga = int(r.get("dest_orga") or 0)
        lib = ""
        if dest_ope:
            if dest_ope not in cache_sal:
                try:
                    row = rh.query_one(
                        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                        (dest_ope,),
                    )
                    cache_sal[dest_ope] = row or {}
                except Exception:
                    cache_sal[dest_ope] = {}
            row = cache_sal[dest_ope]
            lib = f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
        elif dest_orga:
            if dest_orga not in cache_orga:
                try:
                    row = rh.query_one(
                        "SELECT lib_orga FROM rh.pgt_organigramme WHERE idorganigramme = ? LIMIT 1",
                        (dest_orga,),
                    )
                    cache_orga[dest_orga] = row or {}
                except Exception:
                    cache_orga[dest_orga] = {}
            lib = (cache_orga[dest_orga].get("lib_orga") or "").strip()
        out.append(DialogueDest(
            IDDialogueDEST=_str_id(r.get("id_dialogue_dest")),
            Dest_Ope=_str_id(dest_ope) if dest_ope else "",
            Dest_Orga=_str_id(dest_orga) if dest_orga else "",
            LibDest=lib,
        ))
    return out


def _load_messages(id_dialogue: int, format_: str,
                   cache_sal: dict) -> list[DialogueMsg]:
    db_div = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db_div.query(
            """SELECT id_dialogue_msg, id_dialogues, contenu,
                      date_heure_creation, expediteur, modif_elem, modif_date
                 FROM divers.pgt_dialoguemsg
                WHERE id_dialogues = ?
                ORDER BY date_heure_creation ASC""",
            (int(id_dialogue),),
        ) or []
    except Exception:
        logger.exception("_load_messages")
        return []
    out: list[DialogueMsg] = []
    for r in rows:
        expediteur = int(r.get("expediteur") or 0)
        modif_elem = (r.get("modif_elem") or "").strip()
        contenu_raw = r.get("contenu") or ""
        msg = DialogueMsg(
            IDMessage=_str_id(r.get("id_dialogue_msg")),
            IDDialogue=_str_id(r.get("id_dialogues")),
            DateHeureCreation=_iso_datetime(r.get("date_heure_creation")),
            Expediteur=_str_id(expediteur),
        )
        if modif_elem == "suppr":
            msg.MsgSuppr = True
            supr_txt = f"Message supprimé le {_fmt_datetime_fr(r.get('modif_date'))}"
            msg.Contenu = supr_txt
            msg.ContenuUni = supr_txt
        else:
            if format_ == "JSON":
                # WinDev: Encode(contenu, encodeURLDepuisUnicode)
                msg.Contenu = quote(contenu_raw, safe="")
            else:
                msg.ContenuUni = contenu_raw
        # Nom expediteur
        if expediteur:
            if expediteur not in cache_sal:
                try:
                    row = rh.query_one(
                        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                        (expediteur,),
                    )
                    cache_sal[expediteur] = row or {}
                except Exception:
                    cache_sal[expediteur] = {}
            row = cache_sal[expediteur]
            msg.NomExp = f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
        out.append(msg)
    return out


def _load_pjs(id_dialogue: int, cache_sal: dict) -> list[DialoguePJ]:
    db_div = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db_div.query(
            """SELECT id_dialogue_pj, id_dialogues, id_dialogue_msg,
                      nom_fic, date_heure_creation, expediteur
                 FROM divers.pgt_dialoguepj
                WHERE id_dialogues = ?
                  AND (modif_elem IS NULL OR modif_elem <> 'suppr')""",
            (int(id_dialogue),),
        ) or []
    except Exception:
        logger.exception("_load_pjs")
        return []
    out: list[DialoguePJ] = []
    for r in rows:
        expediteur = int(r.get("expediteur") or 0)
        nom_exp = ""
        if expediteur:
            if expediteur not in cache_sal:
                try:
                    row = rh.query_one(
                        "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                        (expediteur,),
                    )
                    cache_sal[expediteur] = row or {}
                except Exception:
                    cache_sal[expediteur] = {}
            row = cache_sal[expediteur]
            nom_exp = f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
        pj = DialoguePJ(
            IDPJ=_str_id(r.get("id_dialogue_pj")),
            IDDialogue=_str_id(r.get("id_dialogues")),
            NomFic=r.get("nom_fic") or "",
            Url=pj_url(r.get("id_dialogues"), r.get("nom_fic") or ""),
            DateHeureCreation=_iso_datetime(r.get("date_heure_creation")),
            Expediteur=_str_id(expediteur) if expediteur else "",
            NomExp=nom_exp,
        )
        # attache l'IDDialogueMSG en attribut prive (non exporte Pydantic)
        # -> merge dans _regroupe_pjs
        pj_dict = pj.model_dump()
        pj_dict["_id_msg"] = int(r.get("id_dialogue_msg") or 0)
        out.append(pj_dict)  # type: ignore[arg-type]
    return out  # type: ignore[return-value]


def _load_histo(id_dialogue: int) -> list[DialogueHisto]:
    db_div = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db_div.query(
            """SELECT h.id_dialogue_histo, h.modif_date, h.modif_op,
                      h.id_dialogue_statut, st.lib_statut
                 FROM divers.pgt_dialoguehisto h
                 LEFT JOIN divers.pgt_dialoguestatut st
                        ON st.id_dialogue_statut = h.id_dialogue_statut
                WHERE h.id_dialogues = ?
                ORDER BY h.modif_date DESC""",
            (int(id_dialogue),),
        ) or []
    except Exception:
        logger.exception("_load_histo")
        return []
    out: list[DialogueHisto] = []
    for r in rows:
        modif_op = int(r.get("modif_op") or 0)
        nom_ope = ""
        if modif_op:
            try:
                row = rh.query_one(
                    "SELECT nom, prenom FROM rh.pgt_salarie WHERE id_salarie = ? LIMIT 1",
                    (modif_op,),
                )
                if row:
                    nom_ope = f"{row.get('nom') or ''} {_capitalise(row.get('prenom') or '')}".strip()
            except Exception:
                pass
        out.append(DialogueHisto(
            FaitLe=_fmt_datetime_fr(r.get("modif_date")),
            NomOpe=nom_ope,
            LibStatut=r.get("lib_statut") or "",
        ))
    return out


# ---------------------------------------------------------------------------
#  Proc principale
# ---------------------------------------------------------------------------

def liste_dialogues(type_msg: int, id_vend: int,
                    format_: str = "JSON") -> list[Dialogue]:
    """Portage Dialogue_ListeCR_JSON.

    type_msg : 0 = actifs (statut != 4), autre = clos (statut = 4)
    id_vend  : id du salarie connecte
    format_  : 'JSON' -> encode URL le contenu des messages ;
               sinon renvoie le texte brut dans ContenuUni.
    """
    if not id_vend:
        return []

    # 1. Info user + expansion Resp
    user_info = _info_salarie_dial(id_vend)
    is_resp = user_info.get("resp_equipe", False)
    aff_id = user_info.get("affectation_id", 0)

    extra_orgas: set[int] = set()
    extra_vends_all: set[int] = set()   # sans condition Prive
    extra_vends_pub: set[int] = set()   # uniquement si Prive=0

    if is_resp and aff_id:
        extra_orgas = _liste_orga_descendants(aff_id)
        salaries = _salaries_orga_avec_droit(extra_orgas, 142)
        for sid in salaries:
            if sid == id_vend:
                extra_vends_all.add(sid)
            else:
                extra_vends_pub.add(sid)

    # 2. Construire les clauses de visibilite dynamiques (litteraux entiers,
    #    pas de placeholders — les IDs sont des int contrôlés localement).
    conds = [f"(d.expediteur = {int(id_vend)} OR dd.dest_ope = {int(id_vend)})"]
    if extra_orgas:
        ids_sql = ",".join(str(int(i)) for i in extra_orgas)
        conds.append(f"dd.dest_orga IN ({ids_sql})")
    if extra_vends_all:
        for sid in extra_vends_all:
            conds.append(f"(d.expediteur = {int(sid)} OR dd.dest_ope = {int(sid)})")
    if extra_vends_pub:
        ids_sql = ",".join(str(int(i)) for i in extra_vends_pub)
        conds.append(
            f"((d.expediteur IN ({ids_sql}) OR dd.dest_ope IN ({ids_sql})) "
            f"AND COALESCE(d.prive, FALSE) = FALSE)"
        )
    visibilite = " OR ".join(conds)
    if int(type_msg) == 0:
        statut_clause = "d.id_dialogue_statut <> 4"
    else:
        statut_clause = "d.id_dialogue_statut = 4"

    sql = f"""SELECT DISTINCT d.id_dialogues, d.expediteur, d.sujet,
                     d.id_dialogue_statut, d.id_dialogue_theme,
                     d.prive, d.date_heure_creation
                FROM divers.pgt_dialogues d
                JOIN divers.pgt_dialoguedest dd ON dd.id_dialogues = d.id_dialogues
               WHERE (d.modif_elem IS NULL OR d.modif_elem <> 'suppr')
                 AND ({visibilite})
                 AND {statut_clause}
               ORDER BY d.date_heure_creation DESC"""

    db_div = get_pg_connection("divers")
    try:
        rows = db_div.query(sql) or []
    except Exception:
        logger.exception("liste_dialogues sql=%s", sql)
        return []

    # 3. Cache lib_theme + salaries + orga pour eviter N+1
    themes_map: dict[int, str] = {}
    try:
        for t in (db_div.query(
                "SELECT id_dialogue_theme, lib_theme FROM divers.pgt_dialoguetheme"
        ) or []):
            themes_map[int(t.get("id_dialogue_theme") or 0)] = t.get("lib_theme") or ""
    except Exception:
        logger.exception("liste_dialogues themes cache")

    cache_orga: dict = {}
    cache_sal: dict = {}

    out: list[Dialogue] = []
    for r in rows:
        id_dial = int(r.get("id_dialogues") or 0)
        if not id_dial:
            continue

        dial = Dialogue(
            IDDialogue=_str_id(id_dial),
            Sujet=r.get("sujet") or "",
            IdStatut=int(r.get("id_dialogue_statut") or 0),
            IdTheme=int(r.get("id_dialogue_theme") or 0),
            LibTheme=themes_map.get(int(r.get("id_dialogue_theme") or 0), ""),
            IsPrive=bool(r.get("prive")),
            DateHeureCreation=_iso_datetime(r.get("date_heure_creation")),
            Expediteur=_str_id(r.get("expediteur")),
        )

        dial.Dests = _load_dests(id_dial, cache_orga, cache_sal)
        dial.Echanges = _load_messages(id_dial, format_, cache_sal)

        # PJs (avec _id_msg attribut prive pour regroupement)
        pjs_raw = _load_pjs(id_dial, cache_sal)
        pjs_clean: list[DialoguePJ] = []
        for pj_dict in pjs_raw:  # type: ignore[assignment]
            id_msg = int(pj_dict.pop("_id_msg", 0))
            pj = DialoguePJ(**pj_dict)
            pjs_clean.append(pj)
            if id_msg:
                # regrouper la PJ dans le message correspondant
                for m in dial.Echanges:
                    if m.IDMessage and int(m.IDMessage) == id_msg:
                        m.mesPJs.append(pj)
                        break
        dial.PJs = pjs_clean

        dial.Histo = _load_histo(id_dial)

        # Calcul MsgNonLu
        try:
            reqLu = db_div.query(
                """SELECT date_lecture
                     FROM divers.pgt_dialoguelu
                    WHERE id_salarie = ? AND id_dialogues = ?
                    ORDER BY date_lecture DESC LIMIT 1""",
                (int(id_vend), id_dial),
            ) or []
        except Exception:
            reqLu = []
        if not reqLu:
            dial.MsgNonLu = True
            dial.DateLecture = dial.DateHeureCreation
        else:
            date_lecture = reqLu[0].get("date_lecture")
            date_lecture_iso = _iso_datetime(date_lecture)
            dial.DateLecture = date_lecture_iso
            for m in dial.Echanges:
                # Comparaison string ISO -> OK si meme format 'YYYY-MM-DD HH:MM:SS'
                if (m.DateHeureCreation and date_lecture_iso
                        and m.DateHeureCreation > date_lecture_iso
                        and m.Expediteur and int(m.Expediteur or 0) != id_vend):
                    dial.MsgNonLu = True
                    break

        out.append(dial)

    return out
