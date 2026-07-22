"""Router mobile (WebRest_Omayapp) — API REST iso-URL avec les WS
WinDev originaux, pour migration progressive de l'app Flutter Omayapp.

URL cible (IIS reverse proxy vers ce backend) :
  https://push.omaya.fr/WebRest_Omayapp/*      (OVH)
  https://sos.push.omaya.fr/WebRest_Omayapp/*  (interne)

Convention endpoints : ecriture EXACTE du xlsx
D:\\Claude\\WinDev\\WebServices\\Liste webservices_rest Appli.xlsx.
CamelCase preserve (AgCial, Dialogues, CallSFR, etc.), pas de
transformation kebab-case.

Chaque groupe (Dialogues, Call, RH, AgCial, etc.) est monte via un
sous-router pour clarte. La logique metier est REUTILISEE depuis les
services shared/intranets deja portes cote web (evite la duplication).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.mobile import auth as auth_router
from app.mobile import call as call_router
from app.mobile import call_sfr as call_sfr_router
from app.mobile import dialogues as dialogues_router
from app.mobile import misc as misc_router

router = APIRouter(prefix="/WebRest_Omayapp", tags=["mobile"])


@router.get("/Ping", tags=["mobile-healthcheck"])
def ping():
    """Healthcheck simple pour valider la config IIS + backend."""
    return {"status": "ok", "service": "WebRest_Omayapp"}


# Sous-routers par groupe fonctionnel — a completer au fur et a mesure
# du portage des 192 endpoints du xlsx (34 groupes).
router.include_router(auth_router.router)
router.include_router(dialogues_router.router)
router.include_router(call_router.router)
router.include_router(call_sfr_router.router)
router.include_router(misc_router.router)
