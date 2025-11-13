from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import conlist, BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlmodel import Session, select, delete
from typing import Optional, List
from starlette.responses import StreamingResponse
from app.database import get_session
from app.models import Team, TeamCreate, TeamPokemon, PokedexEntry, User
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/v1/teams", tags=["Teams"])

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    if len(team_data.pokemon_ids) > 6:
        raise HTTPException(
            status_code=400,
            detail="Un equipo no puede tener más de 6 Pokémon."
        )
    pokedex_query = select(PokedexEntry.pokemon_id).where(
        PokedexEntry.owner_id == current_user.id
    )
    user_pokemon_ids = db.exec(pokedex_query).all()

    missing = [pid for pid in team_data.pokemon_ids if pid not in user_pokemon_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes Pokémon no están en tu Pokédex: {missing}"
        )
    team = Team(
        name=team_data.name,
        description=team_data.description,
        owner_id=current_user.id
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    for pid in team_data.pokemon_ids:
        db.add(TeamPokemon(team_id=team.id, pokemon_id=pid))
    db.commit()

    return {
        "message": "Equipo creado correctamente",
        "team_id": team.id,
        "team_name": team.name
    }

@router.get("/", response_model=list[dict])
def list_teams(
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    teams = db.exec(select(Team).where(Team.owner_id == current_user.id)).all()
    if not teams:
        return []

    result = []
    for team in teams:
        team_pokemons = db.exec(
            select(TeamPokemon.pokemon_id).where(TeamPokemon.team_id == team.id)
        ).all()

        result.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "created_at": team.created_at,
            "pokemon_ids": team_pokemons
        })

    return result

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pokemon_ids: Optional[List[int]] = None  # Máximo 6 validado en la lógica


@router.put("/{team_id}", response_model=TeamUpdate)
def update_team(
        team_id: int,
        team_update: TeamUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    team = db.get(Team, team_id)
    if not team or team.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Team not found or not owned by user")

    if team_update.name:
        team.name = team_update.name
    if team_update.description:
        team.description = team_update.description

    if team_update.pokemon_ids is not None:
        if len(team_update.pokemon_ids) > 6:
            raise HTTPException(status_code=400, detail="Team cannot have more than 6 Pokémon")

        user_pokemon_ids = db.exec(
            select(PokedexEntry.pokemon_id).where(PokedexEntry.owner_id == current_user.id)
        ).all()

        for pid in team_update.pokemon_ids:
            if pid not in user_pokemon_ids:
                raise HTTPException(status_code=400, detail=f"User does not own Pokémon {pid}")

        stmt = delete(TeamPokemon).where(TeamPokemon.team_id == team.id)
        db.exec(stmt)

        for pid in team_update.pokemon_ids:
            db.add(TeamPokemon(team_id=team.id, pokemon_id=pid))

    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}/export")
def export_team_pdf(team_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    team = db.get(Team, team_id)
    if not team or team.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Team not found")
    team_pokemons = db.exec(
        select(PokedexEntry).where(PokedexEntry.pokemon_id.in_([tp.pokemon_id for tp in team.team_pokemon]))
    ).all()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 50, f"Equipo: {team.name}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 80, f"Descripción: {team.description or ''}")
    y = height - 120
    for p in team_pokemons:
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, f"{p.pokemon_name} (ID: {p.pokemon_id})")
        y -= 15
        pdf.setFont("Helvetica", 12)
        pdf.drawString(60, y, f"Apodo: {p.nickname or 'N/A'}")
        y -= 15
        pdf.drawString(60, y, f"Capturado: {'Sí' if p.is_captured else 'No'}")
        y -= 25
    total_captured = sum(1 for p in team_pokemons if p.is_captured)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"Estadísticas del equipo:")
    y -= 15
    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, y, f"Pokémon capturados: {total_captured}/{len(team_pokemons)}")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=team_{team.id}.pdf"}
    )
