from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.routers.auth import router as auth_router
from app.services.pokeapi_service import PokeAPIService
from app.routers import pokemon, pokedex, teams
import logging
from datetime import datetime, UTC

app = FastAPI(title="Pokedex API")
pokeapi_service = PokeAPIService()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    ),
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pokedex_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pokedex_api")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now(UTC)
    logger.info(f"Request start: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
    except RateLimitExceeded:
        logger.warning(f"Rate limit exceeded: {request.method} {request.url.path}")
        raise
    except Exception as e:
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {str(e)}")
        raise
    duration = (datetime.now(UTC) - start_time).total_seconds()
    logger.info(f"Request end: {request.method} {request.url.path} | Status: {response.status_code} | Duration: {duration:.3f}s")
    return response

@app.get("/pokemon/type/{type_name}")
@limiter.limit("30/minute")
def get_pokemon_by_type(request: Request, type_name: str):
    logger.info(f"PokeAPI call: get_pokemon_by_type {type_name}")
    return pokeapi_service.get_pokemon_by_type(type_name=type_name)

@app.get("/pokemon/{id_or_name}")
@limiter.limit("30/minute")
def get_pokemon(request: Request, id_or_name: str):
    logger.info(f"PokeAPI call: get_pokemon {id_or_name}")
    return pokeapi_service.get_pokemon(identifier=id_or_name)

@app.get("/pokemon")
@limiter.limit("30/minute")
def search_pokemon(request: Request, limit: int = 20, offset: int = 0):
    logger.info(f"PokeAPI call: search_pokemon limit={limit} offset={offset}")
    return pokeapi_service.search_pokemon(limit=limit, offset=offset)

@app.get("/pokemon/species/{id_or_name}")
@limiter.limit("100/minute")
def get_pokemon_species(request: Request, id_or_name: str):
    logger.info(f"PokeAPI call: get_pokemon_species {id_or_name}")
    return pokeapi_service.get_pokemon_species(identifier=id_or_name)

app.include_router(auth_router)
app.include_router(pokemon.router)
app.include_router(pokedex.router)
app.include_router(teams.router)

if __name__ == "__main__":
    import uvicorn
    from app.database import init_db
    init_db()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
