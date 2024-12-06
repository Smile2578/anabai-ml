import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from aioresponses import aioresponses
from data_feeds.external_data_manager import ExternalDataManager
import aiohttp
from urllib.parse import urlencode

@pytest.fixture
def mock_session():
    """Fixture pour créer un mock de la session HTTP."""
    mock = MagicMock(spec=aiohttp.ClientSession)
    mock.close = AsyncMock()
    mock.get = MagicMock()
    mock.get.return_value.__aenter__ = AsyncMock()
    mock.get.return_value.__aexit__ = AsyncMock()
    return mock

@pytest.fixture
def mock_response():
    """Fixture pour créer un mock de la réponse HTTP."""
    mock = AsyncMock()
    mock.raise_for_status = AsyncMock()
    mock.json = AsyncMock()
    return mock

@pytest.fixture
def manager(mock_session):
    """Fixture pour créer une instance de ExternalDataManager avec un mock de session."""
    data_manager = ExternalDataManager()
    data_manager.session = mock_session
    return data_manager

@pytest.mark.asyncio
async def test_get_weather_data(manager, mock_session, mock_response):
    """Teste la récupération des données météo."""
    test_lat = 35.6895
    test_lon = 139.6917
    test_response = {
        "main": {
            "temp": 20.5,
            "humidity": 65
        },
        "weather": [
            {
                "main": "Clear",
                "description": "clear sky"
            }
        ]
    }

    mock_response.json.return_value = test_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await manager.get_weather_data(test_lat, test_lon)
    
    assert isinstance(result, dict)
    assert "temperature" in result
    assert "humidity" in result
    assert "conditions" in result
    assert "description" in result
    assert "timestamp" in result
    assert isinstance(datetime.fromisoformat(result["timestamp"]), datetime)

@pytest.mark.asyncio
async def test_get_events_data(manager, mock_session, mock_response):
    """Teste la récupération des données d'événements."""
    test_lat = 35.6895
    test_lon = 139.6917
    test_response = {
        "results": [
            {
                "name": "Festival local",
                "geometry": {
                    "location": {
                        "lat": test_lat,
                        "lng": test_lon
                    }
                },
                "place_id": "test_place_id",
                "types": ["event", "point_of_interest"]
            }
        ]
    }

    mock_response.json.return_value = test_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await manager.get_events_data(test_lat, test_lon)
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Festival local"
    assert "location" in result[0]
    assert "place_id" in result[0]
    assert "types" in result[0]
    assert "timestamp" in result[0]

@pytest.mark.asyncio
async def test_get_place_details(manager, mock_session, mock_response):
    """Teste la récupération des détails d'un lieu."""
    test_place_id = "test_place_id"
    test_response = {
        "result": {
            "name": "Lieu test",
            "formatted_address": "1-1 Test Street, Tokyo, Japan",
            "geometry": {
                "location": {
                    "lat": 35.6762,
                    "lng": 139.6503
                }
            },
            "rating": 4.5,
            "opening_hours": {
                "open_now": True
            },
            "price_level": 2
        }
    }

    mock_response.json.return_value = test_response
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await manager.get_place_details(test_place_id)
    
    assert isinstance(result, dict)
    assert "details" in result
    assert result["details"]["name"] == "Lieu test"
    assert "timestamp" in result