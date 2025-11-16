from urllib import request
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
    name: str | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    ip = current_user.username
    if rate_limited(ip, SEARCH_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    try:
        data = pokeapi_service.search_pokemon(limit=limit, offset=offset)

        results = data.get("results", data)

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
    if rate_limited(ip, DETAIL_LIMIT, 100, 60):
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
    if rate_limited(ip, CARD_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    data = pokeapi_service.get_pokemon(id_or_name)
    species = pokeapi_service.get_pokemon_species(id_or_name)

    export_dir = "app/exports"
    os.makedirs(export_dir, exist_ok=True)
    file_path = os.path.join(export_dir, f"{data['name']}_card.pdf")

    image_url = data["sprites"]["other"]["official-artwork"]["front_default"]
    img_path = os.path.join(export_dir, f"{data['name']}.png")
    request.urlretrieve(image_url, img_path)

    types = [t["type"]["name"] for t in data["types"]]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    description = next(
        (e["flavor_text"] for e in species["flavor_text_entries"] if e["language"]["name"] == "es"),
        "Descripción no disponible."
    ).replace("\n", " ")

    c = canvas.Canvas(file_path, pagesize=letter)

    c.setFillColor("#ECECEC")
    c.rect(0, 0, 612, 792, fill=1)

    c.setFillColor("white")
    c.roundRect(40, 40, 532, 712, 20, fill=1)

    c.setFillColor("black")
    c.setFont("Helvetica-Bold", 28)
    c.drawString(60, 730, data["name"].capitalize())

    c.setFont("Helvetica", 14)
    c.drawString(60, 705, f"ID: {data['id']}")
    c.drawString(60, 685, f"Tipos: {', '.join(types)}")

    if os.path.exists(img_path):
        c.drawImage(img_path, 330, 500, width=230, height=230, preserveAspectRatio=True)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, 640, "Estadísticas:")

    c.setFont("Helvetica", 12)
    y = 620
    for key in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
        c.drawString(60, y, f"{key.upper()}: {stats.get(key, 0)}")
        y -= 18

    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, 470, "Descripción:")

    text = c.beginText(60, 450)
    text.setFont("Helvetica", 12)
    for line in description.split(". "):
        text.textLine(line)
    c.drawText(text)

    c.save()

    return FileResponse(file_path, filename=f"{data['name']}_card.pdf", media_type="application/pdf")

