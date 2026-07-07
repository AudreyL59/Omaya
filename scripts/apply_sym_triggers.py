"""Applique migration/symmetricds/sym_triggers.sql sur la base interne
via psycopg2 (utilise la config .env du projet - meme host que l'app).

Utile quand psql n'est pas dans le PATH du poste dev. Sans equivalent
pour 'symadmin sync-triggers' qui doit tourner sur le serveur interne.

Usage :
    python scripts/apply_sym_triggers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Charge le .env avant d'importer la config
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import psycopg2  # noqa: E402


HERE = Path(__file__).resolve().parents[1]
SQL_FILE = HERE / "migration" / "symmetricds" / "sym_triggers.sql"


def main() -> int:
    import os
    host = (
        os.getenv("PG_HOST_TEST")
        or os.getenv("PG_Host_Test")
        or os.getenv("PG_HOST", "localhost")
    )
    port = int(os.getenv("PG_PORT", "5432"))
    dbname = os.getenv("PG_DBNAME", "erp_db")
    user = os.getenv("PG_USER", "erp_user")
    password = os.getenv("PG_PASSWORD", "")
    if not password:
        print("[KO] PG_PASSWORD absent du .env")
        return 1
    if not SQL_FILE.exists():
        print(f"[KO] Fichier introuvable : {SQL_FILE}")
        return 1

    print(f"[i] Connexion {user}@{host}:{port}/{dbname}")
    print(f"[i] Fichier : {SQL_FILE} ({SQL_FILE.stat().st_size} bytes)")

    with psycopg2.connect(
        host=host, port=port, dbname=dbname,
        user=user, password=password,
    ) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            sql = SQL_FILE.read_text(encoding="utf-8")
            cur.execute(sql)
        conn.commit()
    print("[OK] sym_triggers.sql applique avec succes.")
    print("")
    print("Etape suivante SUR LE SERVEUR INTERNE (192.168.1.203) :")
    print("    cd C:\\symmetricds\\bin")
    print("    .\\symadmin --engine erp-interne sync-triggers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
