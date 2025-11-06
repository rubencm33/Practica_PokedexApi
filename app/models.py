from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)


class PokedexEntryBase(SQLModel):
    pokemon_id: int = Field(index=True)
    pokemon_name: str
    pokemon_sprite: str  # URL de la imagen
    is_captured: bool = Field(default=False)
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: bool = Field(default=False)


class TeamBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None


class Team(TeamBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trainer_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relaciones
    trainer: "User" = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relaciones
    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="owner")
    teams: List["Team"] = Relationship(back_populates="trainer")


class PokedexEntry(PokedexEntryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relaciones
    owner: User = Relationship(back_populates="pokedex_entries")


class TeamMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    pokedex_entry_id: int = Field(foreign_key="pokedexentry.id")
    position: int = Field(ge=1, le=6)

    # Relaciones
    team: Team = Relationship(back_populates="members")


# -------------------- Schemas --------------------

class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime


class PokedexEntryCreate(PokedexEntryBase):
    is_captured: bool = False
    favorite: bool = False
    nickname: Optional[str] = None
    notes: Optional[str] = None
    capture_date: Optional[datetime] = None


class PokedexEntryUpdate(SQLModel):
    is_captured: Optional[bool] = None
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: Optional[bool] = None


class PokedexEntryRead(PokedexEntryBase):
    """Schema de lectura de una entrada de Pokédex"""
    id: int
    owner_id: int
    created_at: datetime


class TeamMemberRead(SQLModel):
    """Schema de lectura para un miembro del equipo"""
    pokedex_entry_id: int
    position: int


class TeamCreate(TeamBase):
    """Schema para crear un equipo (incluye IDs de Pokémon de la Pokédex)"""
    pokedex_entry_ids: List[int] = Field(max_items=6, min_items=1)


class TeamUpdate(TeamBase):
    """Schema para actualizar un equipo"""
    pokedex_entry_ids: Optional[List[int]] = Field(default=None, max_items=6, min_items=1)


class TeamRead(TeamBase):
    """Schema de lectura de un equipo"""
    id: int
    trainer_id: int
    created_at: datetime
    members: List[TeamMemberRead] = []
