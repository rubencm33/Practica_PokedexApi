import logging
from typing import Optional, List, Dict
import httpx
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def get_pokemon(self, identifier: str | int) -> Dict:
        url = f"{self.BASE_URL}/pokemon/{identifier}"
        logger.info(f"Llamando a {url}")

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()


        except requests.exceptions.HTTPError as e:

            status = e.response.status_code if e.response else 500

            if status == 404:
                raise HTTPException(status_code=404, detail="Pokémon no encontrado")

            raise HTTPException(status_code=status, detail="Error en la API de PokeAPI")
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    def search_pokemon(self, limit: int = 20, offset: int = 0) -> Dict:
        url = f"{self.BASE_URL}/pokemon"
        query_params = {"limit": limit, "offset": offset}

        try:
            response = requests.get(url, params=query_params, timeout=5)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError:
            raise HTTPException(status_code=response.status_code, detail="Error al obtener la lista de Pokémon")
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    def get_pokemon_by_type(self, type_name: str) -> List[Dict]:
        url = f"{self.BASE_URL}/type/{type_name}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tipo de Pokémon '{type_name}' no encontrado."
                )

            response.raise_for_status()  # Lanza error si hay otro tipo de fallo HTTP

            data = response.json()

            pokemon_list = [
                {"name": p["pokemon"]["name"], "url": p["pokemon"]["url"]}
                for p in data.get("pokemon", [])
            ]

            return pokemon_list

        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Tiempo de espera agotado con la PokeAPI.")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def get_pokemon_species(self, identifier: str | int) -> Dict:
        url = f"{self.BASE_URL}/pokemon-species/{identifier}"
        logger.info(f"Llamando a {url}")

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 500
            if status == 404:
                raise HTTPException(status_code=404, detail="Información de especie no encontrada")
            raise HTTPException(status_code=status, detail="Error al obtener datos de especie de PokeAPI")
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

pokeapi_service = PokeAPIService()