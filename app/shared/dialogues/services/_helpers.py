"""Helpers communs au module Dialogues."""

from __future__ import annotations

import os


def docs_url() -> str:
    """URL publique servant les fichiers PJ (IIS statique cote interne,
    equivalent OVH cote FTP web).

    Ex : 'https://interne.omaya.fr' (sans slash final).
    """
    return (os.environ.get("DOCS_URL", "") or "").rstrip("/")


def pj_url(id_dialogue: int | str, nom_fic: str) -> str:
    """URL publique complete d'une PJ.

    Construction : {DOCS_URL}/DocConv/{id_dialogue}/{nom_fic}.
    Retourne '' si DOCS_URL n'est pas configure — dans ce cas le
    frontend retombera sur son endpoint fallback authentifie.
    """
    base = docs_url()
    if not base or not id_dialogue or not nom_fic:
        return ""
    return f"{base}/DocConv/{int(id_dialogue)}/{nom_fic}"
