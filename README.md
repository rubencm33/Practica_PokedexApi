# Pokédex API

## Descripción
Este proyecto es una API REST desarrollada como práctica individual para la asignatura, donde implemento un sistema completo de gestión de una Pokédex utilizando FastAPI.  
La API permite consultar información de Pokémon desde la PokeAPI, gestionar una Pokédex personal, exportar datos, crear equipos y generar cartas en PDF.

Incluye funcionalidades avanzadas como autenticación JWT, rate limiting personalizado, logging estructurado, versionado de API, validaciones de usuarios y generación de recursos descargables.

Repositorio del proyecto:  
https://github.com/rubencm33/Practica_PokedexApi.git

## Instalación
git clone https://github.com/rubencm33/Practica_PokedexApi.git

cd Practica_PokedexApi

python -m venv .venv

source .venv/bin/activate   # Linux/Mac

.venv\Scripts\activate      # Windows

pip install -r requirements.txt

## Inicialización de la Base de Datos
from app.database import init_db
init_db()

## Configuración (.env)
SECRET_KEY=tu_clave_secreta

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=sqlite:///./pokedex.db

POKEAPI_URL=https://pokeapi.co/api/v2

LOG_LEVEL=INFO

## Ejecución
uvicorn app.main:app --reload  
Documentación: http://127.0.0.1:8000/docs

## Testing
pytest

# Endpoints Principales

## Autenticación — /api/v1/auth
POST /register — Registro de usuarios  
POST /login — Login con JWT  

## Pokémon — /api/v1/pokemon
GET /search — Búsqueda con filtros  
GET /{id_or_name} — Información completa  
GET /{id_or_name}/card — Genera carta PDF  

## Pokédex — /api/v1/pokedex
GET / — Listar Pokédex  
POST /add — Añadir Pokémon  
PATCH /{id}/capture — Marcar como capturado  
PATCH /{id}/favorite — Marcar como favorito  
GET /export — Exportar Pokédex en CSV  

## Equipos — /api/v1/teams
Crear equipo  
Añadir / retirar Pokémon  
Eliminar equipo  
Listar equipos  

# Decisiones de Seguridad

## Autenticación JWT
Todos los endpoints protegidos requieren token válido.

## Rate Limiting
Aplicado a:
- /pokemon/search  
- /pokemon/{id}  
- /pokemon/{id}/card  
- /pokedex/export  

## Logging estructurado
Registra:
- Requests  
- Errores  
- Rate limit excedido  
- Llamadas a la PokeAPI  

Guardado en `pokedex_api.log`.

## Mejoras Futuras
- Añadir paginación básica en las búsquedas de Pokémon.  
- Mejorar los mensajes de error para que sean más descriptivos.  
- Añadir más filtros simples (por tipo, por generación, etc.).  
- Implementar un contador de cuántas veces se consulta un Pokémon.  
- Guardar logs también en consola para depuración más rápida.  
- Crear un endpoint que devuelva estadísticas simples del usuario (número de capturados, favoritos, equipos creados…).

## Video Mostrando las funcionalidades de la api
Enlace al video(Loom):
https://www.loom.com/share/347376d2bd014d5bacd01f92d16cae2c