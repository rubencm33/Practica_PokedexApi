from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from app.services.pokeapi_service import PokeAPIService
from app.dependencies import get_current_user
from app.auth import rate_limited
from app.models import User
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/api/v1/pokemon", tags=["Pokémon"])
pokeapi_service = PokeAPIService()

SEARCH_LIMIT = {}
DETAIL_LIMIT = {}
CARD_LIMIT = {}

@router.get("/search")
def search_pokemon(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    ip = current_user.username
    if rate_limited(ip, SEARCH_LIMIT, 30, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    try:
        data = pokeapi_service.search_pokemon(limit=limit, offset=offset)

        results = data.get("results", data)  # fallback por si devuelve lista

        simplified = []
        for entry in results:
            pokemon_name = entry.get("name") if isinstance(entry, dict) else entry

            if name and name.lower() not in pokemon_name.lower():
                continue

            pokemon_data = pokeapi_service.get_pokemon(pokemon_name)
            simplified.append({
                "id": pokemon_data["id"],
                "name": pokemon_data["name"],
                "sprite": pokemon_data["sprites"]["front_default"],
                "types": [t["type"]["name"] for t in pokemon_data["types"]]
            })

        if not simplified:
            return {"message": "No se encontraron Pokémon con ese nombre"}

        return simplified

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener Pokémon: {str(e)}")

@router.get("/{id_or_name}")
def get_pokemon_details(
    id_or_name: str,
    current_user: User = Depends(get_current_user),
):
    ip = current_user.username
    if rate_limited(ip, DETAIL_LIMIT, 30, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    try:
        data = pokeapi_service.get_pokemon(id_or_name)
        details = {
            "id": data["id"],
            "name": data["name"],
            "types": [t["type"]["name"] for t in data["types"]],
            "abilities": [a["ability"]["name"] for a in data["abilities"]],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
            "sprites": data["sprites"]
        }
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener detalles: {str(e)}")

@router.get("/{id_or_name}/card")
def generate_pokemon_card(
    id_or_name: str,
        current_user: User = Depends(get_current_user),
):
    ip = current_user.username
    if rate_limited(ip, CARD_LIMIT, 10, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    data = pokeapi_service.get_pokemon(id_or_name)
    species = pokeapi_service.get_pokemon_species(id_or_name)

    export_dir = "app/exports"
    os.makedirs(export_dir, exist_ok=True)
    file_path = os.path.join(export_dir, f"{data['name']}_card.pdf")

    c = canvas.Canvas(file_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(200, 750, f"Pokémon Card: {data['name'].capitalize()}")

    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"ID: {data['id']}")
    c.drawString(100, 700, f"Tipos: {', '.join([t['type']['name'] for t in data['types']])}")
    c.drawString(100, 680, f"Habilidades: {', '.join([a['ability']['name'] for a in data['abilities']])}")

    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    c.drawString(100, 660, f"HP: {stats.get('hp', 0)}")
    c.drawString(100, 640, f"Ataque: {stats.get('attack', 0)}")
    c.drawString(100, 620, f"Defensa: {stats.get('defense', 0)}")
    c.drawString(100, 600, f"Velocidad: {stats.get('speed', 0)}")

    description = next(
        (entry["flavor_text"] for entry in species["flavor_text_entries"] if entry["language"]["name"] == "es"),
        "Descripción no disponible."
    )
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(100, 560, f"Descripción: {description.replace(chr(10), ' ')}")

    c.showPage()
    c.save()

    return FileResponse(file_path, filename=f"{data['name']}_card.pdf", media_type="application/pdf")



