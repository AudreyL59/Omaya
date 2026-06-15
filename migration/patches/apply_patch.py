"""Applique un patch SQL sur la PG en utilisant psycopg2 + .env du projet.

Usage :
    python migration/patches/apply_patch.py add_cv_suivi_prev_recrut.sql

Le .env doit contenir : PG_HOST, PG_PORT, PG_DBNAME, PG_USER, PG_PASSWORD.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage : python migration/patches/apply_patch.py <fichier.sql>")
        sys.exit(2)

    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(project_root / ".env")

    patch_arg = sys.argv[1]
    patch_path = Path(patch_arg)
    if not patch_path.is_absolute():
        # Cherche d'abord à côté du script, sinon depuis le cwd
        here = Path(__file__).parent / patch_path.name
        patch_path = here if here.exists() else (Path.cwd() / patch_arg)
    if not patch_path.exists():
        print(f"Fichier introuvable : {patch_path}")
        sys.exit(1)

    # Cf. app/core/database/pg.py : PG_HOST_TEST prime sur PG_HOST (permet
    # au dev local d'avoir un PG_HOST de prod dans .env tout en pointant ses
    # tests sur une autre IP).
    host = (
        os.getenv("PG_HOST_TEST")
        or os.getenv("PG_Host_Test")
        or os.getenv("PG_HOST", "localhost")
    )
    port = os.getenv("PG_PORT", "5432")
    dbname = os.getenv("PG_DBNAME", "erp_db")
    user = os.getenv("PG_USER", "erp_user")
    password = os.getenv("PG_PASSWORD", "")

    print(f"Cible : {user}@{host}:{port}/{dbname}")
    print(f"Patch : {patch_path}")

    import psycopg2

    sql = patch_path.read_text(encoding="utf-8")
    conn = psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("OK - patch applique.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
