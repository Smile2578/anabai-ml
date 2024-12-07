"""Tests pour le moniteur en temps réel."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from ai.adaptation.real_time_monitoring import (
    RealTimeMonitor,
    MonitoringConfig,
    MonitoringResult
)
from ai.templates import ItineraryPlace

@pytest.fixture
def sample_place() -> ItineraryPlace:
    """Fixture pour créer un lieu de test."""
    return ItineraryPlace(
        place_id=uuid4(),
        name="Test Place",
        description="A test place",
        visit_duration=60,
        recommended_time=datetime.now(UTC),
        creator_notes="Test notes",
        score=0.8,
        adjustments={},
        latitude=35.6895,
        longitude=139.6917
    )

@pytest.fixture
def monitor() -> RealTimeMonitor:
    """Fixture pour créer un moniteur."""
    return RealTimeMonitor()

@pytest.mark.asyncio
async def test_monitor_initialization(monitor: RealTimeMonitor):
    """Teste l'initialisation du moniteur."""
    assert monitor.monitoring_config is not None
    assert 30 <= monitor.monitoring_config.check_interval <= 3600
    assert 0.0 <= monitor.monitoring_config.weather_threshold <= 1.0
    assert 0.0 <= monitor.monitoring_config.crowd_threshold <= 1.0
    assert 0.0 <= monitor.monitoring_config.event_threshold <= 1.0
    assert monitor.monitoring_config.max_distance > 0

@pytest.mark.asyncio
async def test_start_stop_monitoring(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste le démarrage et l'arrêt de la surveillance."""
    # Démarre la surveillance
    await monitor.start_monitoring(sample_place)
    monitored = await monitor.get_monitored_places()
    assert sample_place.place_id in monitored

    # Arrête la surveillance
    await monitor.stop_monitoring(sample_place.place_id)
    monitored = await monitor.get_monitored_places()
    assert sample_place.place_id not in monitored

@pytest.mark.asyncio
async def test_check_conditions_weather(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste la vérification des conditions météo."""
    # Mock les données météo
    weather_data = {
        "severity": 0.8,
        "rain": 0.9,
        "wind": 0.5,
        "temperature": 0.3
    }
    monitor.external_data.get_weather_data = AsyncMock(
        return_value=weather_data
    )
    monitor.external_data.get_crowd_data = AsyncMock(return_value=None)
    monitor.external_data.get_events_data = AsyncMock(return_value=[])

    result = await monitor.check_conditions(sample_place)
    assert result.requires_adaptation
    assert len(result.changes) == 1
    assert result.changes[0].change_type == "weather"

@pytest.mark.asyncio
async def test_check_conditions_crowd(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste la vérification des conditions d'affluence."""
    # Mock les données d'affluence
    crowd_data = {
        "severity": 0.8,
        "level": 0.9,
        "wait_time": 45
    }
    monitor.external_data.get_weather_data = AsyncMock(return_value=None)
    monitor.external_data.get_crowd_data = AsyncMock(
        return_value=crowd_data
    )
    monitor.external_data.get_events_data = AsyncMock(return_value=[])

    result = await monitor.check_conditions(sample_place)
    assert result.requires_adaptation
    assert len(result.changes) == 1
    assert result.changes[0].change_type == "crowd"

@pytest.mark.asyncio
async def test_check_conditions_event(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste la vérification des conditions d'événements."""
    # Mock les données d'événements
    event_data = [{
        "severity": 0.6,
        "size": 0.7,
        "distance": 500,
        "latitude": 35.6895,
        "longitude": 139.6917
    }]
    monitor.external_data.get_weather_data = AsyncMock(return_value=None)
    monitor.external_data.get_crowd_data = AsyncMock(return_value=None)
    monitor.external_data.get_events_data = AsyncMock(
        return_value=event_data
    )

    result = await monitor.check_conditions(sample_place)
    assert result.requires_adaptation
    assert len(result.changes) == 1
    assert result.changes[0].change_type == "event"

@pytest.mark.asyncio
async def test_check_conditions_multiple(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste la vérification de plusieurs conditions."""
    # Mock toutes les données
    weather_data = {
        "severity": 0.8,
        "rain": 0.9,
        "wind": 0.5,
        "temperature": 0.3
    }
    crowd_data = {
        "severity": 0.8,
        "level": 0.9,
        "wait_time": 45
    }
    event_data = [{
        "severity": 0.6,
        "size": 0.7,
        "distance": 500,
        "latitude": 35.6895,
        "longitude": 139.6917
    }]

    monitor.external_data.get_weather_data = AsyncMock(
        return_value=weather_data
    )
    monitor.external_data.get_crowd_data = AsyncMock(
        return_value=crowd_data
    )
    monitor.external_data.get_events_data = AsyncMock(
        return_value=event_data
    )

    result = await monitor.check_conditions(sample_place)
    assert result.requires_adaptation
    assert len(result.changes) == 3
    change_types = {change.change_type for change in result.changes}
    assert change_types == {"weather", "crowd", "event"}

@pytest.mark.asyncio
async def test_check_conditions_no_changes(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste la vérification sans changements significatifs."""
    # Mock des données sous les seuils
    weather_data = {
        "severity": 0.2,
        "rain": 0.2,
        "wind": 0.1,
        "temperature": 0.1
    }
    crowd_data = {
        "severity": 0.3,
        "level": 0.3,
        "wait_time": 10
    }
    event_data = [{
        "severity": 0.2,
        "size": 0.2,
        "distance": 900,
        "latitude": 35.6895,
        "longitude": 139.6917
    }]

    monitor.external_data.get_weather_data = AsyncMock(
        return_value=weather_data
    )
    monitor.external_data.get_crowd_data = AsyncMock(
        return_value=crowd_data
    )
    monitor.external_data.get_events_data = AsyncMock(
        return_value=event_data
    )

    result = await monitor.check_conditions(sample_place)
    assert not result.requires_adaptation
    assert len(result.changes) == 0

@pytest.mark.asyncio
async def test_clear_monitoring(
    monitor: RealTimeMonitor,
    sample_place: ItineraryPlace
):
    """Teste l'arrêt de toute la surveillance."""
    # Ajoute plusieurs lieux
    places = [
        sample_place,
        ItineraryPlace(
            place_id=uuid4(),
            name="Test Place 2",
            description="Another test place",
            visit_duration=60,
            recommended_time=datetime.now(UTC),
            creator_notes="Test notes",
            score=0.8,
            adjustments={},
            latitude=35.6895,
            longitude=139.6917
        )
    ]
    
    for place in places:
        await monitor.start_monitoring(place)

    monitored = await monitor.get_monitored_places()
    assert len(monitored) == 2

    # Arrête toute la surveillance
    await monitor.clear_monitoring()
    monitored = await monitor.get_monitored_places()
    assert len(monitored) == 0 