import sys
import traceback

import anyio
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.core.auth.router import router as auth_router
from app.intranets.vendeur.router import router as vendeur_router
from app.intranets.adm.router import router as adm_router
from app.intranets.call.energie.router import router as call_energie_router
from app.intranets.call.fibre.router import router as call_fibre_router
from app.intranets.call.rh.router import router as call_rh_router
from app.intranets.call.prise_rdv.router import router as call_prise_rdv_router
from app.shared.email.router import router as shared_email_router
from app.shared.recrutement.router_public import router as public_recrutement_router
from app.shared.consent.router_public import router as public_consent_router
from app.shared.sdtc.router import router as shared_sdtc_router
from app.mobile.router import router as mobile_router

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.on_event("startup")
async def _grow_threadpool() -> None:
    """Augmente le pool de threads (def routes -> run_in_threadpool).

    Par defaut anyio limite a 40. Avec 1 worker uvicorn et beaucoup de
    requetes HFSQL (chacune spawn un subprocess + reste bloquee dans le
    thread), 40 peut etre tres vite sature. On passe a 200 pour eviter
    qu'un endpoint long comme /tickets/traites monopolise les threads
    et bloque les ouvertures de fiche.
    """
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 200


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_: Request, exc: Exception):
    """Capture toutes les exceptions non-traitees pour exposer un detail JSON
    cote client (au lieu d'un 500 vide). HTTPException reste gere par FastAPI."""
    # Si c'est deja une HTTPException, la laisser passer au handler natif
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        raise exc
    traceback.print_exc(file=sys.stderr)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )

app.include_router(auth_router)
app.include_router(vendeur_router)
app.include_router(adm_router)
app.include_router(call_energie_router)
app.include_router(call_fibre_router)
app.include_router(call_rh_router)
app.include_router(call_prise_rdv_router)
app.include_router(shared_email_router)
app.include_router(shared_sdtc_router)
# Router public (sans auth) pour la confirmation de RDV par le candidat
app.include_router(public_recrutement_router)
app.include_router(public_consent_router)
# Router mobile (WebRest_Omayapp) - migration progressive de l'app
# Flutter Omayapp. URL iso-WinDev, monte a la racine (pas sous /api)
# pour matcher directement push.omaya.fr/WebRest_Omayapp/*.
app.include_router(mobile_router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "ERP Omaya API is running"}
