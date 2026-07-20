"""
Client HTTP generique pour proxifier les WebService WinDev
(WebRest_Omayapp) utilises par les ecrans Ticket Call Energie + Fibre.

Cf. docs/tickets_call_screens_analysis.md pour la spec.

Utilise urllib.request (stdlib, pas de dependance externe — coherent
avec le reste du projet cote adm/services/suivi_sfr.py).

Cette couche est **temporaire (Phase 2)** : chaque endpoint sera
remplace au fur et a mesure par un service PG (Phase 3).
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import WEBREST_BASE_URL


logger = logging.getLogger(__name__)

# Prefixe commun cote WinDev
WEBREST_PATH_PREFIX = "/WebRest_Omayapp"


class WSError(Exception):
    """Erreur de proxy vers un WebService WinDev."""
    def __init__(self, status: int, message: str, url: str):
        super().__init__(f"WS {status} {url}: {message}")
        self.status = status
        self.message = message
        self.url = url


def _url(path: str) -> str:
    """Construit l'URL absolue : {base}/WebRest_Omayapp/{path}."""
    if not path.startswith("/"):
        path = "/" + path
    return WEBREST_BASE_URL.rstrip("/") + WEBREST_PATH_PREFIX + path


def get(path: str, timeout: float = 15.0) -> Any:
    """GET JSON vers un WebService WinDev.

    Retourne le body decode JSON (list ou dict). Leve WSError sur echec.
    """
    url = _url(path)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise WSError(e.code, body, url) from e
    except Exception as e:
        raise WSError(0, str(e), url) from e
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        # Certains WS renvoient du texte brut / vide
        return raw.decode("utf-8", errors="replace")


def post(
    path: str,
    payload: dict | list | None = None,
    timeout: float = 15.0,
) -> Any:
    """POST JSON vers un WebService WinDev.

    payload = None -> POST vide (Content-Length: 0). Certains WS
    WinDev exigent ca (ex: /Call/ClientsNonFinalises/{id}).

    Retourne le body decode JSON.
    """
    url = _url(path)
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        headers["Content-Length"] = "0"
    try:
        req = urllib.request.Request(
            url, data=data, method="POST", headers=headers,
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise WSError(e.code, body, url) from e
    except Exception as e:
        raise WSError(0, str(e), url) from e
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


def post_multipart_windev(
    path: str,
    file_name: str,
    file_bytes: bytes,
    content_type: str = "application/pdf",
    timeout: float = 90.0,
) -> Any:
    """POST multipart/form-data compatible WinDev (boundary specifique).

    Reproduit exactement le format `----WinDevBoundary<ms>` utilise
    par le pkg http de Flutter pour /RecepFichier.
    """
    import time as _time
    boundary = f"----WinDevBoundary{int(_time.time() * 1000)}"
    lf = b"\r\n"
    body = b""
    body += f"--{boundary}\r\n".encode("ascii")
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
    ).encode("utf-8")
    body += f"Content-Type: {content_type}\r\n\r\n".encode("ascii")
    body += file_bytes
    body += lf
    body += f"--{boundary}--\r\n".encode("ascii")
    url = _url(path)
    try:
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        try:
            b = e.read().decode("utf-8", errors="replace")
        except Exception:
            b = ""
        raise WSError(e.code, b, url) from e
    except Exception as e:
        raise WSError(0, str(e), url) from e
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")


# --- Helpers -------------------------------------------------------------

def encode_path_segment(v: Any) -> str:
    """URL-encode un segment de chemin (usersCial, code, id...)."""
    return urllib.parse.quote(str(v), safe="")
