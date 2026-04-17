"""
Abstraction multi-bases HFSQL via bridge WinDev.

Usage dans un router :
    from app.core.database import get_db

    @router.get("/clients")
    def list_clients(db=Depends(get_db("adv"))):
        rows = db.query("SELECT * FROM client WHERE IDClient = ?", (42,))
        return rows

Pour changer de SGBD (ex: PostgreSQL), il suffit de remplacer
la classe HFSQLConnection par une implémentation SQLAlchemy.
"""

import os
from dotenv import load_dotenv

from app.core.database.hfsql_bridge import execute_query, HFSQLError

load_dotenv()

# Config serveur HFSQL
HFSQL_HOST = os.getenv("HFSQL_HOST", "localhost")
HFSQL_PORT = os.getenv("HFSQL_PORT", "4901")
HFSQL_USER = os.getenv("HFSQL_USER", "admin")
HFSQL_PASSWORD = os.getenv("HFSQL_PASSWORD", "")
HFSQL_DB_PASSWORD = os.getenv("HFSQL_DB_PASSWORD", "")

# Mapping nom logique -> (nom BDD, nom connexion WinDev)
DB_CONFIG = {
    "adv":         (os.getenv("HFSQL_DB_ADV", "Bdd_Omaya_ADV"),         "MaCoInt_Omaya_ADV"),
    "divers":      (os.getenv("HFSQL_DB_DIVERS", "Bdd_Omaya_Divers"),   "MaCoInt_Omaya_Divers"),
    "recrutement": (os.getenv("HFSQL_DB_RECRUTEMENT", "Bdd_Omaya_Recrutement"), "MaCoInt_Omaya_Recrutement"),
    "rh":          (os.getenv("HFSQL_DB_RH", "Bdd_Omaya_RH"),           "MaCoInt_Omaya_RH"),
    "scool":       (os.getenv("HFSQL_DB_SCOOL", "Bdd_Omaya_Scool"),     "MaCoInt_Omaya_Scool"),
    "ticket":      (os.getenv("HFSQL_DB_TICKET", "Bdd_Omaya_Ticket"),   "MaCoInt_Omaya_Ticket"),
    "ticket_bo":   (os.getenv("HFSQL_DB_TICKET_BO", "Bdd_Omaya_Ticket_BO"), "MaCoInt_Omaya_Ticket_BO"),
    "ticket_dpae": (os.getenv("HFSQL_DB_TICKET_DPAE", "Bdd_Omaya_Ticket_DPAE"), "MaCoInt_Omaya_Ticket_DPAE"),
    "ticket_rh":   (os.getenv("HFSQL_DB_TICKET_RH", "Bdd_Omaya_Ticket_RH"), "MaCoInt_Omaya_Ticket_RH"),
    "ulease":      (os.getenv("HFSQL_DB_ULEASE", "ulease"),             "MaCoInt_Omaya_Ulease"),
}

# Rétro-compat
DB_NAMES = {k: v[0] for k, v in DB_CONFIG.items()}


class HFSQLConnection:
    """
    Wrapper de connexion HFSQL via le bridge WinDev.

    Fournit une interface simple : query(sql) -> list[dict]
    """

    def __init__(self, db_key: str):
        if db_key not in DB_CONFIG:
            raise ValueError(f"Base inconnue : '{db_key}'. Disponibles : {list(DB_CONFIG.keys())}")
        self.db_key = db_key
        self.db_name, self.connection_name = DB_CONFIG[db_key]
        self.server = f"{HFSQL_HOST}:{HFSQL_PORT}"

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Exécute une requête SQL et retourne les résultats.

        Les paramètres sont injectés dans le SQL avant envoi au bridge.
        Utiliser ? comme placeholder : query("SELECT * FROM t WHERE id = ?", (42,))
        """
        # Substitution simple des paramètres (le bridge ne supporte pas les params natifs)
        final_sql = sql
        for param in params:
            if isinstance(param, str):
                # Échapper les quotes simples
                safe = param.replace("'", "''")
                final_sql = final_sql.replace("?", f"'{safe}'", 1)
            elif param is None:
                final_sql = final_sql.replace("?", "NULL", 1)
            else:
                final_sql = final_sql.replace("?", str(param), 1)

        return execute_query(
            server=self.server,
            user=HFSQL_USER,
            password=HFSQL_PASSWORD,
            file_password=HFSQL_DB_PASSWORD,
            database=self.db_name,
            sql=final_sql,
            connection_name=self.connection_name,
        )

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Exécute une requête et retourne la première ligne, ou None."""
        rows = self.query(sql, params)
        return rows[0] if rows else None


def get_db(db_key: str):
    """
    Dépendance FastAPI — injecte une connexion HFSQL par nom logique.

    Usage :
        @router.get("/example")
        def example(db=Depends(get_db("rh"))):
            rows = db.query("SELECT * FROM salarie WHERE IDSalarie = ?", (123,))
            ...
    """
    def _dependency():
        return HFSQLConnection(db_key)
    return _dependency


def get_connection(db_key: str) -> HFSQLConnection:
    """Connexion directe (hors dépendance FastAPI), pour scripts ou init."""
    return HFSQLConnection(db_key)
