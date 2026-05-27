"""Applique le schema PostgreSQL sur un serveur cible.

Execute, dans l'ordre : 00_sync_control.sql puis les 10 schemas
(adv.sql, divers.sql, ... ulease.sql) du dossier migration/schema/.

Connexion : arguments CLI ou variables d'env (utiles dans .env) :
    PG_HOST  PG_PORT  PG_DBNAME  PG_USER  PG_PASSWORD

Usage :
    python migration/apply_schema.py                 # depuis .env / defauts
    python migration/apply_schema.py --host 192.168.1.50 --dbname erp_db \
        --user erp_user --password ****
    python migration/apply_schema.py --reset         # DROP SCHEMA avant (re-apply propre)
    python migration/apply_schema.py --dry-run       # liste sans executer

Prerequis : pip install psycopg2-binary
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Charge le .env du projet (parent de migration/), quel que soit le cwd.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main() -> None:
    ap = argparse.ArgumentParser(description="Applique le schema PG (sync_control + 10 schemas).")
    ap.add_argument("--host", default=os.getenv("PG_HOST", "localhost"))
    ap.add_argument("--port", default=os.getenv("PG_PORT", "5432"))
    ap.add_argument("--dbname", default=os.getenv("PG_DBNAME", "erp_db"))
    ap.add_argument("--user", default=os.getenv("PG_USER", "erp_user"))
    ap.add_argument("--password", default=os.getenv("PG_PASSWORD", ""))
    ap.add_argument("--input", default=str(Path(__file__).parent / "schema"))
    ap.add_argument("--reset", action="store_true",
                    help="DROP SCHEMA ... CASCADE + reset sync_control avant d'appliquer")
    ap.add_argument("--dry-run", action="store_true", help="liste les fichiers sans executer")
    args = ap.parse_args()

    in_dir = Path(args.input)
    files = sorted(in_dir.glob("*.sql"))
    if not files:
        print(f"Aucun .sql dans {in_dir}")
        return
    data_files = [f for f in files if not f.name.startswith("00_")]  # schemas data

    print(f"Cible : {args.user}@{args.host}:{args.port}/{args.dbname}")
    print("Fichiers (ordre d'application) :")
    for f in files:
        print(f"  - {f.name}")
    if args.dry_run:
        print("\n[dry-run] rien n'a ete execute.")
        return

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 manquant -> pip install psycopg2-binary")
        sys.exit(1)

    try:
        conn = psycopg2.connect(host=args.host, port=args.port, dbname=args.dbname,
                                user=args.user, password=args.password)
    except UnicodeDecodeError as e:
        # Message d'erreur serveur en Windows-1252 (locale FR) -> psycopg2 echoue
        # a le decoder en UTF-8. On recupere les octets et on les decode en cp1252.
        msg = (e.object.decode("cp1252", "replace")
               if getattr(e, "object", None) else str(e))
        print("\nConnexion echouee (message serveur, decode cp1252) :")
        print("  " + msg.strip())
        print("\nVerifie : PG_USER / PG_PASSWORD dans .env (ils sont vides ?), "
              "les droits, et l'entree pg_hba.conf pour ton IP.")
        sys.exit(1)
    conn.set_client_encoding("UTF8")
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            if args.reset:
                for f in data_files:
                    schema = f.stem
                    print(f"  DROP SCHEMA {schema} CASCADE")
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE;')
                cur.execute("TRUNCATE public.sync_control;"
                            if _table_exists(cur, "public", "sync_control") else "SELECT 1;")
                conn.commit()
            for f in files:
                print(f"  applique {f.name} ...")
                cur.execute(f.read_text(encoding="utf-8"))
                conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_schema, count(*) FROM information_schema.tables "
                "WHERE table_type = 'BASE TABLE' "
                "AND table_schema NOT IN ('pg_catalog', 'information_schema') "
                "GROUP BY table_schema ORDER BY table_schema;")
            print("\n--- Tables par schema ---")
            total = 0
            for s, n in cur.fetchall():
                print(f"  {s:<14} {n}")
                total += n
            print(f"  {'TOTAL':<14} {total}")
        print("\nOK.")
    except Exception as e:
        conn.rollback()
        print(f"\nERREUR : {e}")
        sys.exit(1)
    finally:
        conn.close()


def _table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
        (schema, table))
    return cur.fetchone() is not None


if __name__ == "__main__":
    main()
