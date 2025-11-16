from pydantic import ConfigDict
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, UTC

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    email: str = Field(unique=True, index=True)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="owner")
    teams: List["Team"] = Relationship(back_populates="owner")


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    created_at: datetime


class PokedexEntryBase(SQLModel):
    pokemon_id: int = Field(index=True)
    pokemon_name: str
    pokemon_sprite: str  # URL de la imagen
    is_captured: bool = Field(default=False)
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = Field(default=None, max_length=50)
    favorite: bool = Field(default=False)


class PokedexEntry(PokedexEntryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relaciones
    owner: User = Relationship(back_populates="pokedex_entries")


class PokedexEntryCreate(SQLModel):
    pokemon_id: int
    nickname: Optional[str] = None
    is_captured: bool = False


class PokedexEntryUpdate(SQLModel):
    is_captured: Optional[bool] = None
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = None
    favorite: Optional[bool] = None


class PokedexEntryRead(PokedexEntryBase):
    id: int
    pokemon_id: int
    nickname: Optional[str] = None
    is_captured: bool = False

    model_config = ConfigDict(from_attributes=True)

class TeamBase(SQLModel):
    name: str = Field(index=True, min_length=3, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)


class Team(TeamBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    owner: Optional["User"] = Relationship(back_populates="teams")
    team_pokemon: List["TeamPokemon"] = Relationship(back_populates="team")

    @property
    def pokemon_ids(self) -> List[int]:
        return [tp.pokemon_id for tp in self.team_pokemon]


class TeamCreate(TeamBase):
    pokemon_ids: List[int]


class TeamRead(TeamBase):
    id: int
    pokemon_ids: List[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TeamPokemon(SQLModel, table=True):
    team_id: int = Field(foreign_key="team.id", primary_key=True)
    pokemon_id: int = Field(primary_key=True)

    team: Optional["Team"] = Relationship(back_populates="team_pokemon")
