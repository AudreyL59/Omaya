import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.core.auth.router import router as auth_router
from app.intranets.vendeur.router import router as vendeur_router
from app.intranets.adm.router import router as adm_router
from app.intranets.call.energie.router import router as call_energie_router
from app.intranets.call.fibre.router import router as call_fibre_router
from app.intranets.call.rh.router import router as call_rh_router
from app.intranets.call.prise_rdv.router import router as call_prise_rdv_router

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

app.include_router(auth_router)
app.include_router(vendeur_router)
app.include_router(adm_router)
app.include_router(call_energie_router)
app.include_router(call_fibre_router)
app.include_router(call_rh_router)
app.include_router(call_prise_rdv_router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "ERP Omaya API is running"}
