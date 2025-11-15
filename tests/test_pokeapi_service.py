import pytest
import requests.exceptions
from unittest.mock import MagicMock
from fastapi import HTTPException

# Importamos la clase que queremos probar
from app.services.pokeapi_service import PokeAPIService


# NOTA: Estos tests son SÍNCRONOS (usan 'def') porque
# tu PokeAPIService usa 'requests' (síncrono).

def test_pokeapi_service_get_pokemon(mocker):
    """
    Prueba que el servicio obtiene un Pokémon correctamente (Modo Síncrono).
    Usa 'mocker' de pytest-mock para simular la respuesta de 'requests.get'.
    """

    # 1. Preparar el Mock de la respuesta exitosa
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Simulamos los datos JSON que esperamos de la PokeAPI
    mock_response.json.return_value = {"name": "pikachu", "id": 25, "height": 4}

    # Configuramos el 'side_effect' de raise_for_status para que no haga nada
    mock_response.raise_for_status.return_value = None

    # 2. Aplicar el "Parche" (Mock)
    # Interceptamos CUALQUIER llamada a 'requests.get'
    # dentro del módulo 'app.services.pokeapi_service'
    mocker.patch(
        'app.services.pokeapi_service.requests.get',
        return_value=mock_response
    )

    # 3. Ejecutar el código a probar
    service = PokeAPIService()
    pokemon = service.get_pokemon(identifier="pikachu")

    # 4. Verificar el resultado
    assert pokemon is not None
    assert pokemon["name"] == "pikachu"
    assert pokemon["id"] == 25


def test_pokeapi_service_handles_404(mocker):
    """
    Prueba que el servicio maneja un 404 (Pokémon no encontrado)
    y lanza la HTTPException correcta de FastAPI.
    """

    # 1. Preparar el Mock de la respuesta de error 404
    mock_response = MagicMock()
    mock_response.status_code = 404

    # Creamos el error HTTPError real que 'requests' lanzaría
    http_error = requests.exceptions.HTTPError("404 Client Error: Not Found")
    http_error.response = mock_response

    # Configuramos el mock de raise_for_status() para que LANCE el error
    mock_response.raise_for_status.side_effect = http_error

    # 2. Aplicar el "Parche" (Mock)
    mocker.patch(
        'app.services.pokeapi_service.requests.get',
        return_value=mock_response
    )

    # 3. Ejecutar y Verificar la Excepción
    service = PokeAPIService()

    # Usamos pytest.raises para verificar que se lanza la excepción esperada
    with pytest.raises(HTTPException) as exc_info:
        service.get_pokemon(identifier="pokemonquenoexiste")

    # 4. Verificar que es la excepción 404 de FastAPI, no la de requests
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Pokémon no encontrado"


def test_pokeapi_service_handles_timeout(mocker):
    """
    Prueba que el servicio maneja un error de Timeout.
    """
    # 1. Configurar el mock para que lance un Timeout
    mocker.patch(
        'app.services.pokeapi_service.requests.get',
        side_effect=requests.exceptions.Timeout("La conexión expiró")
    )

    # 2. Ejecutar y Verificar la Excepción
    service = PokeAPIService()

    with pytest.raises(HTTPException) as exc_info:
        service.get_pokemon(identifier="pikachu")

    # 3. Verificar que es la excepción 504 de FastAPI
    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "Tiempo de espera agotado"
