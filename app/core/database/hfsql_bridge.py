"""
Bridge Python -> HFSQL via exécutable WinDev.

Appelle hfsql_bridge.exe en subprocess pour exécuter des requêtes SQL
sur les bases HFSQL protégées par mot de passe fichier.
Le résultat est échangé via un fichier JSON temporaire.
"""

import json
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.config import HFSQL_BRIDGE_PATH

CREATE_NO_WINDOW = 0x08000000


class HFSQLError(Exception):
    """Erreur retournée par le bridge HFSQL."""
    pass


def _flatten_row(row: dict) -> dict:
    """
    Aplatit un enregistrement retourné par HEnregistrementVersJSON.

    WinDev retourne : {"_SOURCE_MaRequête_1": {"col1": val1, "col2": val2}}
    On veut :         {"col1": val1, "col2": val2}
    """
    if len(row) == 1:
        key = next(iter(row))
        if isinstance(row[key], dict):
            return row[key]
    return row


def execute_query(
    server: str,
    user: str,
    password: str,
    file_password: str,
    database: str,
    sql: str,
    connection_name: str = "",
) -> list[dict]:
    """
    Exécute une requête SQL sur HFSQL via le bridge WinDev.

    Retourne une liste de dictionnaires (un par ligne).
    Lève HFSQLError en cas d'erreur.
    """
    bridge = Path(HFSQL_BRIDGE_PATH)
    if not bridge.exists():
        raise HFSQLError(f"Bridge introuvable : {bridge}")

    # Fichier temporaire pour le résultat JSON
    temp_dir = Path(tempfile.gettempdir())
    result_file = temp_dir / f"hfsql_{uuid.uuid4().hex}.json"

    try:
        args = [
            str(bridge),
            server,
            user,
            password,
            file_password,
            database,
            sql,
            str(result_file),
            connection_name,
        ]

        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise HFSQLError("Bridge timeout (30s)")

        if not result_file.exists():
            raise HFSQLError(f"Bridge n'a pas créé le fichier résultat. Exit code: {proc.returncode}")

        # HFSQL écrit en latin-1 par défaut
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                content = result_file.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            content = result_file.read_text(encoding="latin-1", errors="replace")

        if not content.strip():
            raise HFSQLError("Fichier résultat vide")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HFSQLError(f"JSON invalide du bridge: {e}\nContenu: {content[:200]}")

        if not data.get("ok"):
            raise HFSQLError(data.get("error", "Erreur inconnue"))

        # Aplatir les lignes (HEnregistrementVersJSON ajoute un wrapper)
        rows = data.get("rows", [])
        return [_flatten_row(row) for row in rows]

    finally:
        if result_file.exists():
            result_file.unlink()
