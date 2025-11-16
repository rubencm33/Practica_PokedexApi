from collections import Counter
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Optional, List
from starlette import status
from app.database import get_session
from app.models import PokedexEntry, PokedexEntryCreate, PokedexEntryUpdate, PokedexEntryRead
from app.dependencies import get_db, get_current_user
from fastapi.responses import StreamingResponse
import csv
import io
from app.services.pokeapi_service import PokeAPIService
from app.auth import rate_limited

router = APIRouter(prefix="/api/v1/pokedex", tags=["Pokedex"])
pokeapi_service = PokeAPIService()

POKEDEX_LIMIT = {}

@router.post("/", response_model=PokedexEntryRead, status_code=status.HTTP_201_CREATED)
def add_pokemon_to_pokedex(
    entry_data: PokedexEntryCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):  # 100 requests/min
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    try:
        pokemon_data = pokeapi_service.get_pokemon(entry_data.pokemon_id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    pokemon_name = pokemon_data["name"]
    pokemon_sprite = pokemon_data["sprites"]["front_default"]

    entry = PokedexEntry(
        pokemon_id=entry_data.pokemon_id,
        pokemon_name=pokemon_name,
        pokemon_sprite=pokemon_sprite,
        nickname=entry_data.nickname,
        is_captured=entry_data.is_captured,
        owner_id=current_user.id
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@router.get("/", response_model=List[dict])
def list_pokedex(
    captured: Optional[bool] = None,
    favorite: Optional[bool] = None,
    sort: str = Query("pokemon_id", enum=["pokemon_id", "pokemon_name", "capture_date"]),
    order: str = Query("asc", enum=["asc", "desc"]),
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)

    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    sort_column = getattr(PokedexEntry, sort)
    if order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column).offset(offset).limit(limit)

    entries = db.exec(query).all()
    return [
        {
            "entry_id": e.id,
            "pokemon_id": e.pokemon_id,
            "nickname": e.nickname,
            "is_captured": e.is_captured
        }
        for e in entries
    ]

@router.patch("/{entry_id}", response_model=dict)
def update_pokedex_entry(
    entry_id: int,
    update_data: PokedexEntryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    entry = db.get(PokedexEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes modificar esta entrada")

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "is_captured": entry.is_captured,
        "capture_date": entry.capture_date,
        "nickname": entry.nickname,
        "favorite": entry.favorite
    }

@router.delete("/{entry_id}", status_code=204)
def delete_pokedex_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    entry = db.get(PokedexEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar esta entrada")

    db.delete(entry)
    db.commit()
    return {"message": "Se ha eliminado correctamente el Pokémon de la Pokédex"}

@router.get("/export")
def export_pokedex(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    captured: Optional[bool] = None,
    favorite: Optional[bool] = None
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)
    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    entries = db.exec(query).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["pokemon_id", "pokemon_name", "nickname", "is_captured", "favorite"])

    for e in entries:
        writer.writerow([e.pokemon_id, e.pokemon_name, e.nickname, e.is_captured, e.favorite])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pokedex.csv"}
    )


@router.get("/stats")
def get_pokedex_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    ip = current_user.username
    if rate_limited(ip, POKEDEX_LIMIT, 100, 60):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones, inténtalo más tarde")

    entries = db.exec(select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)).all()

    if not entries:
        return {
            "total_pokemon": 0,
            "captured": 0,
            "favorites": 0,
            "completion_percentage": 0.0,
            "most_common_type": None,
            "capture_streak_days": 0
        }

    total_pokemon = len(entries)
    captured_entries = [e for e in entries if e.is_captured]
    captured = len(captured_entries)
    favorites = sum(1 for e in entries if e.favorite)
    completion_percentage = round((captured / total_pokemon) * 100, 1)

    types = []
    for e in entries:
        try:
            pokemon_data = pokeapi_service.get_pokemon(e.pokemon_id)
            if pokemon_data["types"]:
                types.append(pokemon_data["types"][0]["type"]["name"])
        except Exception:
            continue
    most_common_type = Counter(types).most_common(1)
    most_common_type = most_common_type[0][0] if most_common_type else None

    captured_dates = sorted([e.capture_date.date() for e in captured_entries if e.capture_date])
    capture_streak_days = 0
    if captured_dates:
        streak = 1
        for i in range(len(captured_dates) - 1, 0, -1):
            if (captured_dates[i] - captured_dates[i - 1]).days == 1:
                streak += 1
            else:
                break
        capture_streak_days = streak

    return {
        "total_pokemon": total_pokemon,
        "captured": captured,
        "favorites": favorites,
        "completion_percentage": completion_percentage,
        "most_common_type": most_common_type,
        "capture_streak_days": capture_streak_days
    }
