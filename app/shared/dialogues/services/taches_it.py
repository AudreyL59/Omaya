"""Tâches IT liées à un dialogue (onglet 'Suivi IT' cote WinDev).

Table source : divers.pgt_tache_it (id_dialogues fait le lien).
Statut + type resolus via pgt_type_statut / pgt_type_tache.
Nom des operateurs resolu via pgt_salarie (nom + prenom capitalise).
Le champ Contenu est stocke en RTF cote HFSQL -> conversion en plain
text pour l'affichage web (cf. _rtf_to_text).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.database.pg import get_pg_connection
from app.shared.dialogues.schemas.dialogues import TacheIT

logger = logging.getLogger(__name__)


# Groupes RTF a supprimer completement (destinations non-textuelles).
_RTF_SKIP_GROUPS = re.compile(
    r"\{\s*\\(?:fonttbl|colortbl|stylesheet|info|pict|header|footer|"
    r"footnote|comment|xmlnstbl|listtable|listoverridetable|revtbl|"
    r"rsidtbl|generator|\*\\[a-zA-Z]+)[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
    re.DOTALL,
)


def _rtf_to_text(rtf: str) -> str:
    """Convertit un RTF simple (Riched20 / WinDev) en plain text.

    Gere : hex escapes \\'XX (latin-1), \\par/\\line -> newline, \\tab
    -> tab, suppression des groupes non-textuels (fonttbl, colortbl,
    stylesheet, info, generator, \\*\\anything…) et des autres
    commandes \\word[digits]?.

    Retourne la chaine telle quelle si elle ne commence pas par
    '{\\rtf' (deja plain text).
    """
    if not rtf or not rtf.lstrip().startswith("{\\rtf"):
        return rtf or ""
    s = rtf
    # 1. Vire les groupes de destination non-textuels — plusieurs passes
    #    tant que le regex matche (les groupes peuvent s'imbriquer).
    for _ in range(6):
        s2 = _RTF_SKIP_GROUPS.sub("", s)
        if s2 == s:
            break
        s = s2
    # 2. Retire les accolades qui restent (elles ne portent que du groupage)
    #    tout en preservant leur contenu.
    s = s.replace("{", "").replace("}", "")
    # 3. Decode les hex escapes \'XX comme cp1252 (WinDev/Windows FR)
    def _hex(m: re.Match) -> str:
        try:
            return bytes([int(m.group(1), 16)]).decode("cp1252")
        except Exception:
            return ""
    s = re.sub(r"\\'([0-9a-fA-F]{2})", _hex, s)
    # 4. \par / \line / \pard -> newline ; \tab -> tab
    s = re.sub(r"\\par(?![a-zA-Z])\s?", "\n", s)
    s = re.sub(r"\\line(?![a-zA-Z])\s?", "\n", s)
    s = re.sub(r"\\pard(?![a-zA-Z])\s?", "\n", s)
    s = re.sub(r"\\tab(?![a-zA-Z])\s?", "\t", s)
    # 5. Vire toutes les autres commandes \word[digits]? + espace optionnel
    s = re.sub(r"\\[a-zA-Z]+-?\d*\s?", "", s)
    # 6. Vire les backslashes echappees restantes
    s = s.replace("\\\\", "\\").replace("\\{", "{").replace("\\}", "}")
    # 7. Nettoyage : lignes vides multiples -> une seule, trim global
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def _str_id(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _capitalise(v: str) -> str:
    return v[:1].upper() + v[1:].lower() if v else ""


def _iso_datetime(dt: Any) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt)


def liste_taches_it(id_dialogue: int) -> list[TacheIT]:
    """Retourne les taches IT liees a un dialogue, tri par date de creation
    decroissante. Statuts et types resolus par un LEFT JOIN.
    """
    if not id_dialogue:
        return []
    db_div = get_pg_connection("divers")
    rh = get_pg_connection("rh")
    try:
        rows = db_div.query(
            """SELECT t.id_tache_it, t.id_dialogues, t.titre, t.contenu,
                      t.datecrea, t.op_crea, t.ope_traitement,
                      COALESCE(t.terminee, FALSE) AS terminee,
                      t.terminee_date, t.version,
                      s.lib_statut, s.couleur_statut,
                      tp.lib_tache
                 FROM divers.pgt_tache_it t
                 LEFT JOIN divers.pgt_type_statut s
                        ON s.id_type_statut = t.id_type_statut
                 LEFT JOIN divers.pgt_type_tache tp
                        ON tp.id_type_tache = t.id_type_tache
                WHERE t.id_dialogues = ?
                  AND (t.modif_elem IS NULL OR t.modif_elem <> 'suppr')
                ORDER BY t.datecrea DESC""",
            (int(id_dialogue),),
        ) or []
    except Exception:
        logger.exception("liste_taches_it id=%s", id_dialogue)
        return []

    # Cache noms salaries (op_crea + ope_traitement) — evite N+1
    ids = {int(r.get("op_crea") or 0) for r in rows}
    ids |= {int(r.get("ope_traitement") or 0) for r in rows}
    ids.discard(0)
    noms: dict[int, str] = {}
    if ids:
        try:
            ids_sql = ",".join(str(i) for i in ids)
            salaries = rh.query(
                f"""SELECT id_salarie, nom, prenom
                     FROM rh.pgt_salarie
                    WHERE id_salarie IN ({ids_sql})""",
            ) or []
            for s in salaries:
                sid = int(s.get("id_salarie") or 0)
                noms[sid] = f"{s.get('nom') or ''} {_capitalise(s.get('prenom') or '')}".strip()
        except Exception:
            logger.exception("liste_taches_it: noms salaries")

    out: list[TacheIT] = []
    for r in rows:
        op_crea = int(r.get("op_crea") or 0)
        op_trait = int(r.get("ope_traitement") or 0)
        out.append(TacheIT(
            IDTacheIT=_str_id(r.get("id_tache_it")),
            IDDialogue=_str_id(r.get("id_dialogues")),
            Titre=r.get("titre") or "",
            Contenu=_rtf_to_text(r.get("contenu") or ""),
            LibStatut=r.get("lib_statut") or "",
            CouleurStatut=int(r.get("couleur_statut") or 0),
            LibTache=r.get("lib_tache") or "",
            DateCrea=_iso_datetime(r.get("datecrea")),
            OpCrea=_str_id(op_crea) if op_crea else "",
            NomOpCrea=noms.get(op_crea, ""),
            OpTraitement=_str_id(op_trait) if op_trait else "",
            NomOpTraitement=noms.get(op_trait, ""),
            Terminee=bool(r.get("terminee")),
            TermineeDate=_iso_datetime(r.get("terminee_date")),
            Version=r.get("version") or "",
        ))
    return out
