from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Optional, List
from starlette import status
from app.database import get_session
from app.models import PokedexEntry, PokedexEntryCreate, PokedexEntryUpdate
from app.dependencies import get_db, get_current_user
from fastapi.responses import StreamingResponse
import csv
import io
from app.services.pokeapi_service import PokeAPIService

router = APIRouter(prefix="/api/v1/pokedex", tags=["Pokedex"])
pokeapi_service = PokeAPIService()
@router.post("/", response_model=PokedexEntryCreate, status_code=status.HTTP_201_CREATED)
def add_pokemon_to_pokedex(
    entry_data: PokedexEntryCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session)
):
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
    return {
        "pokemon_id": entry.pokemon_id,
        "nickname": entry.nickname,
        "is_captured": entry.is_captured
    }

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
    entry = db.get(PokedexEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    if entry.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes modificar esta entrada")

    for key, value in update_data.dict(exclude_unset=True).items():
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
    format: str = Query("csv", enum=["csv", "pdf"]),
    captured: Optional[bool] = None,
    favorite: Optional[bool] = None
):
    query = select(PokedexEntry).where(PokedexEntry.owner_id == current_user.id)

    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    entries = db.exec(query).all()

    if format == "csv":
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

    raise HTTPException(status_code=501, detail="Formato PDF no implementado")



