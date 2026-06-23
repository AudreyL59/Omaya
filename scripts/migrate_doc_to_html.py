"""
Migration one-shot : convertit le contenu DOCX en HTML pour les tables
pgt_doc_ulease (schema ulease) et pgt_doc_rh (schema rh).

Pourquoi : l'editeur React WYSIWYG (contentEditable) souffre de bugs
quand on lui injecte un HTML genere par mammoth depuis un DOCX (listes
qui ne basculent pas, structures imbriquees mal reconnues par
execCommand insertUnorderedList, etc.). Si le contenu est deja en HTML
'propre', l'editeur le traite nativement et toutes les commandes
fonctionnent.

Idempotent : ne touche que les contenus DOCX (magic PK\\x03\\x04), laisse
les HTML/autres tranquilles. Peut etre relance autant de fois que
voulu (ex : apres une nouvelle synchro HFSQL qui aurait reinjecte du
DOCX).

Usage :
  venv/Scripts/python.exe scripts/migrate_doc_to_html.py [--dry-run]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Pour permettre l'import 'app.*' quand on lance le script depuis n'importe ou.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mammoth  # noqa: E402
import psycopg2  # noqa: E402

from app.core.database.pg import get_pg_connection  # noqa: E402


def _is_docx(content: bytes) -> bool:
    return bool(content) and content[:4] == b"PK\x03\x04"


def _convert(content: bytes) -> str | None:
    try:
        res = mammoth.convert_to_html(io.BytesIO(content))
        return res.value
    except Exception as e:
        print(f"    ERREUR mammoth : {e}")
        return None


def _migrate_table(schema: str, table: str, id_col: str, dry: bool) -> None:
    db = get_pg_connection(schema)
    rows = db.query(
        f"""SELECT {id_col}, titre, contenu
              FROM {schema}.{table}
             WHERE (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
               AND contenu IS NOT NULL"""
    ) or []

    nb_docx = 0
    nb_html = 0
    nb_other = 0
    nb_convert = 0
    nb_err = 0

    for r in rows:
        c = r.get("contenu")
        if isinstance(c, memoryview):
            c = bytes(c)
        if not isinstance(c, (bytes, bytearray)):
            nb_other += 1
            continue
        if not _is_docx(c):
            # Deja HTML (ou autre format type RTF) -> on ne touche pas
            if c.lstrip().startswith(b"<"):
                nb_html += 1
            else:
                nb_other += 1
            continue
        nb_docx += 1
        rid = r.get(id_col)
        titre = (r.get("titre") or "")[:50]
        print(f"  [{schema}.{table}] id={rid} {titre!r}")
        html = _convert(bytes(c))
        if html is None:
            nb_err += 1
            continue
        html_bytes = html.encode("utf-8")
        print(f"    -> {len(c)} bytes DOCX -> {len(html_bytes)} bytes HTML")
        if not dry:
            db.query(
                f"""UPDATE {schema}.{table}
                       SET contenu = ?,
                           modif_date = NOW(),
                           modif_elem = COALESCE(modif_elem, 'modif')
                     WHERE {id_col} = ?""",
                (psycopg2.Binary(html_bytes), rid),
            )
            nb_convert += 1

    print()
    print(f"  Bilan {schema}.{table} :")
    print(f"    DOCX detectes        : {nb_docx}")
    print(f"    Convertis (UPDATE)   : {nb_convert if not dry else 0} (dry-run)" if dry else f"    Convertis (UPDATE)   : {nb_convert}")
    print(f"    Erreurs conversion   : {nb_err}")
    print(f"    Deja HTML (ignores)  : {nb_html}")
    print(f"    Autres (ignores)     : {nb_other}")
    print()


def main() -> None:
    dry = "--dry-run" in sys.argv
    if dry:
        print("MODE DRY-RUN : aucune ecriture en BDD.")
        print()

    print("=== pgt_doc_ulease (schema ulease) ===")
    _migrate_table("ulease", "pgt_doc_ulease", "id_doc_ulease", dry)

    print("=== pgt_doc_rh (schema rh) ===")
    _migrate_table("rh", "pgt_doc_rh", "id_doc_rh", dry)

    print("Termine.")


if __name__ == "__main__":
    main()
