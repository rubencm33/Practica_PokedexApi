from fastapi import FastAPI
from app.services.pokeapi_service import PokeAPIService

app = FastAPI(title="Pokedex API")
pokeapi_service = PokeAPIService()
@app.get("/pokemon/type/{type_name}")
def get_pokemon_by_type(type_name: str):
    return pokeapi_service.get_pokemon_by_type(type_name=type_name)
@app.get("/pokemon/{id_or_name}")
def get_pokemon(id: str | int):
    return pokeapi_service.get_pokemon(identifier=id)
@app.get("/pokemon")
def search_pokemon(limit: int = 20, offset: int = 0):
    return pokeapi_service.search_pokemon(limit=limit, offset=offset)
@app.get("/pokemon/species/{id_or_name}")
def get_pokemon_species(id_or_name: str | int):
    return pokeapi_service.get_pokemon_species(identifier=id_or_name)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
