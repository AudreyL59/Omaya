"""Accès PostgreSQL (cible de migration HFSQL→PG).

Interface **alignée sur `HFSQLConnection`** (`query` / `query_one` /
`attach_memo`) pour que la bascule des services se limite à remplacer
`get_connection` par `get_pg_connection` une fois le SQL adapté au dialecte PG.

⚠️ NON câblé dans `get_connection` par défaut : l'app tourne encore sur HFSQL.
La bascule se fera service par service, une fois le SQL réécrit (snake_case,
tables `pgt_`, schéma via search_path, `LIMIT` au lieu de `TOP`). Voir
`migration/` + mémoire `project_db_strategy`.

Clé logique = schéma PG (mêmes noms que `DB_CONFIG` HFSQL). Toutes les bases
HFSQL deviennent des schémas d'UNE base PG (`erp_db`).

Prérequis runtime : `pip install psycopg2-binary` (import paresseux ici pour ne
pas casser l'environnement tant que la bascule n'est pas faite).
"""

import os
import threading

from dotenv import load_dotenv

load_dotenv()

# PG_Host_Test (si defini) prime sur PG_HOST : permet au dev local d'avoir
# un PG_HOST de prod dans .env tout en pointant ses tests sur une autre IP.
PG_HOST = (
    os.getenv("PG_HOST_TEST")
    or os.getenv("PG_Host_Test")
    or os.getenv("PG_HOST", "localhost")
)
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DBNAME = os.getenv("PG_DBNAME", "erp_db")
PG_USER = os.getenv("PG_USER", "erp_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))

# Clés logiques = schémas (identiques aux clés HFSQL de connections.DB_CONFIG)
PG_SCHEMAS = {
    "adv", "divers", "recrutement", "rh", "scool",
    "ticket", "ticket_bo", "ticket_dpae", "ticket_rh", "ulease",
}

_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """Pool de connexions paresseux (une seule base `erp_db`)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                from psycopg2.pool import ThreadedConnectionPool
                _pool = ThreadedConnectionPool(
                    1, PG_POOL_MAX,
                    host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME,
                    user=PG_USER, password=PG_PASSWORD,
                )
    return _pool


def _prepare_sql(sql: str, params: tuple) -> str:
    """`?` (style HFSQL) → `%s` (psycopg). Échappe les `%` littéraux (ex.
    `LIKE '%suppr%'`) en `%%` UNIQUEMENT s'il y a des paramètres, sinon
    psycopg les interpréterait."""
    if not params:
        return sql
    return sql.replace("%", "%%").replace("?", "%s")


class PGConnection:
    """Connexion PostgreSQL par schéma logique. Interface compatible
    `HFSQLConnection`."""

    def __init__(self, db_key: str):
        if db_key not in PG_SCHEMAS:
            raise ValueError(
                f"Schéma inconnu : '{db_key}'. Disponibles : {sorted(PG_SCHEMAS)}")
        self.schema = db_key

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Exécute une requête (SELECT *et* INSERT/UPDATE/DELETE, comme le
        faisait HFSQLConnection.query). Retourne les lignes (liste de dicts)
        pour un SELECT, `[]` sinon."""
        from psycopg2.extras import RealDictCursor

        pool = _get_pool()
        conn = pool.getconn()
        try:
            conn.autocommit = True  # pas de transaction aborte sur erreur
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f'SET search_path TO "{self.schema}", public;')
                cur.execute(_prepare_sql(sql, params), params or None)
                if cur.description:
                    return [dict(r) for r in cur.fetchall()]
                return []
        finally:
            pool.putconn(conn)

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def attach_memo(self, table: str, key_field: str, key_value,
                    memo_field: str, file_path: str) -> bool:
        """Écrit un mémo binaire (`bytea`) — remplace `@ATTACHMEMO@` HFSQL.
        Signature identique à HFSQLConnection.attach_memo (le service écrit
        d'abord un fichier, on en lit les octets)."""
        import psycopg2

        with open(file_path, "rb") as f:
            data = f.read()
        self.query(
            f"UPDATE {table} SET {memo_field} = ? WHERE {key_field} = ?",
            (psycopg2.Binary(data), key_value),
        )
        return True


def get_pg_connection(db_key: str) -> PGConnection:
    """Connexion directe (scripts, init)."""
    return PGConnection(db_key)


def get_pg_db(db_key: str):
    """Dépendance FastAPI (miroir de `get_db`) : injecte une PGConnection."""
    def _dependency():
        return PGConnection(db_key)
    return _dependency
