"""
Bridge Python -> HFSQL via exécutable WinDev.

Appelle hfsql_bridge.exe en subprocess pour exécuter des requêtes SQL
sur les bases HFSQL protégées par mot de passe fichier.
Le résultat est échangé via un fichier JSON temporaire.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from app.core.config import HFSQL_BRIDGE_PATH

# Logging des durees HFSQL si BRIDGE_LOG_TIMING=1 (env var).
_LOG_TIMING = os.environ.get("BRIDGE_LOG_TIMING") == "1"

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
    timeout: int = 60,
) -> list[dict]:
    """
    Exécute une requête SQL sur HFSQL via le bridge WinDev.

    Retourne une liste de dictionnaires (un par ligne).
    Lève HFSQLError en cas d'erreur.
    """
    bridge = Path(HFSQL_BRIDGE_PATH)
    if not bridge.exists():
        raise HFSQLError(f"Bridge introuvable : {bridge}")

    # Normalisation : le bridge détecte SELECT via "SELECT " (espace après).
    # On remplace les whitespace initiaux par des espaces simples.
    sql = sql.lstrip()
    if sql[:6].upper() == "SELECT" and len(sql) > 6 and sql[6] in "\n\r\t":
        sql = "SELECT " + sql[6:].lstrip()

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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        _t0 = time.monotonic()
        try:
            stdout_b, stderr_b = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Nettoyage robuste : sur timeout, kill simple ne suffit pas toujours
            # (Dll_ODBC.exe peut survivre avec un lock HFSQL ouvert). On force
            # avec taskkill /T qui tue toute la process tree.
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass
            if proc.poll() is None:
                # Toujours vivant -> taskkill brutal sur le PID + ses enfants
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        timeout=5,
                        capture_output=True,
                        creationflags=CREATE_NO_WINDOW,
                    )
                except Exception:
                    pass
            # Nettoyer le fichier de resultat temporaire
            try:
                if result_file.exists():
                    result_file.unlink()
            except Exception:
                pass
            raise HFSQLError(f"Bridge timeout ({timeout}s)")

        if not result_file.exists():
            # Décode stdout/stderr pour donner un maximum d'infos
            def _dec(b: bytes) -> str:
                if not b:
                    return ""
                for enc in ("utf-8", "cp1252", "latin-1"):
                    try:
                        return b.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return b.decode("latin-1", errors="replace")
            so = _dec(stdout_b).strip()
            se = _dec(stderr_b).strip()
            detail = []
            if so:
                detail.append(f"stdout: {so}")
            if se:
                detail.append(f"stderr: {se}")
            extra = " | ".join(detail) if detail else "(aucune sortie)"
            # On ajoute le début du SQL pour diagnostic (les INSERT/UPDATE sont souvent
            # ignorés silencieusement par les bridges qui ne gèrent que SELECT)
            sql_preview = (sql[:500] + ("…" if len(sql) > 500 else "")).replace("\n", " ")
            raise HFSQLError(
                f"Bridge n'a pas créé le fichier résultat. Exit code: {proc.returncode} | {extra} | SQL: {sql_preview}"
            )

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
        result = [_flatten_row(row) for row in rows]
        if _LOG_TIMING:
            dur = time.monotonic() - _t0
            # Tronque le SQL a 80 chars + remplace les sauts de ligne pour log
            sql_short = " ".join(sql.split())[:120]
            print(f"[HFSQL] {dur:.2f}s ({len(result)} rows) {database}: {sql_short}", file=sys.stderr, flush=True)
        return result

    finally:
        if result_file.exists():
            result_file.unlink()


def attach_memo(
    server: str,
    user: str,
    password: str,
    file_password: str,
    database: str,
    table: str,
    key_field: str,
    key_value,
    memo_field: str,
    file_path: str,
    connection_name: str = "",
) -> bool:
    """Attache un fichier (image/binaire) à un mémo via le bridge WinDev.

    Reproduit HAttacheMémo() : le bridge fait HLitRecherche(table,
    key_field, key_value) puis HAttacheMémo(table, memo_field, file_path,
    hMémoImg) puis HModifie.

    PRÉREQUIS : bridge Dll_ODBC.exe recompilé avec le bloc @ATTACHMEMO@
    (cf. docs/hfsql_bridge_windev.wl). Sans ça → HFSQLError explicite.

    Le binaire ne transitant pas en SQL, l'appelant écrit d'abord la
    donnée dans `file_path` (fichier local lisible par le bridge).
    """
    bridge = Path(HFSQL_BRIDGE_PATH)
    if not bridge.exists():
        raise HFSQLError(f"Bridge introuvable : {bridge}")

    temp_dir = Path(tempfile.gettempdir())
    result_file = temp_dir / f"hfsql_{uuid.uuid4().hex}.json"

    try:
        # Positions = LigneCommande WinDev :
        #  6=@ATTACHMEMO@  7=result_file  8=connexion
        #  9=table 10=key_field 11=key_value 12=memo_field 13=file_path
        args = [
            str(bridge),
            server,
            user,
            password,
            file_password,
            database,
            "@ATTACHMEMO@",
            str(result_file),
            connection_name,
            str(table),
            str(key_field),
            str(key_value),
            str(memo_field),
            str(file_path),
        ]

        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        try:
            proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise HFSQLError("Bridge timeout (30s) sur @ATTACHMEMO@")

        if not result_file.exists():
            raise HFSQLError(
                "Bridge @ATTACHMEMO@ : aucun fichier résultat "
                f"(exit {proc.returncode}). Le bridge Dll_ODBC.exe est-il "
                "recompilé avec le bloc @ATTACHMEMO@ ?"
            )

        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                content = result_file.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            content = result_file.read_text(encoding="latin-1", errors="replace")

        if not content.strip():
            raise HFSQLError("Fichier résultat vide (@ATTACHMEMO@)")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HFSQLError(f"JSON invalide (@ATTACHMEMO@): {e}")
        if not data.get("ok"):
            raise HFSQLError(data.get("error", "Erreur @ATTACHMEMO@ inconnue"))
        return True
    finally:
        if result_file.exists():
            result_file.unlink()
