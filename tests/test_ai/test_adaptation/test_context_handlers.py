"""Tests pour les gestionnaires de contexte."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from ai.adaptation.context_handlers import (
    ContextChange,
    WeatherHandler,
    CrowdHandler,
    EventHandler
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
def weather_handler() -> WeatherHandler:
    """Fixture pour créer un gestionnaire météo."""
    return WeatherHandler()

@pytest.fixture
def crowd_handler() -> CrowdHandler:
    """Fixture pour créer un gestionnaire d'affluence."""
    return CrowdHandler()

@pytest.fixture
def event_handler() -> EventHandler:
    """Fixture pour créer un gestionnaire d'événements."""
    return EventHandler()

@pytest.mark.asyncio
async def test_weather_impact_calculation(
    weather_handler: WeatherHandler,
    sample_place: ItineraryPlace
):
    """Teste le calcul d'impact météo."""
    change = ContextChange(
        change_type="weather",
        severity=0.8,
        location=(35.6895, 139.6917),
        details={
            "rain": 0.9,
            "wind": 0.5,
            "temperature": 0.3
        }
    )

    impact = await weather_handler.evaluate_impact(sample_place, change)
    assert 0.0 <= impact <= 1.0
    assert impact == 0.9  # Impact max de la pluie

@pytest.mark.asyncio
async def test_weather_adaptation_suggestion(
    weather_handler: WeatherHandler,
    sample_place: ItineraryPlace
):
    """Teste la suggestion d'adaptation météo."""
    change = ContextChange(
        change_type="weather",
        severity=0.8,
        location=(35.6895, 139.6917),
        details={"rain": 0.9}
    )

    adapted_place = await weather_handler.suggest_adaptation(
        sample_place,
        change,
        0.9
    )

    assert adapted_place is not None
    assert "weather_impact" in adapted_place.adjustments
    assert "météo" in adapted_place.creator_notes.lower()

@pytest.mark.asyncio
async def test_crowd_impact_calculation(
    crowd_handler: CrowdHandler,
    sample_place: ItineraryPlace
):
    """Teste le calcul d'impact d'affluence."""
    change = ContextChange(
        change_type="crowd",
        severity=0.7,
        location=(35.6895, 139.6917),
        details={
            "level": 0.8,
            "wait_time": 45
        }
    )

    impact = await crowd_handler.evaluate_impact(sample_place, change)
    assert 0.0 <= impact <= 1.0
    assert impact == 0.8  # Impact max du niveau de foule

@pytest.mark.asyncio
async def test_crowd_adaptation_suggestion(
    crowd_handler: CrowdHandler,
    sample_place: ItineraryPlace
):
    """Teste la suggestion d'adaptation d'affluence."""
    change = ContextChange(
        change_type="crowd",
        severity=0.8,
        location=(35.6895, 139.6917),
        details={"level": 0.8}
    )

    adapted_place = await crowd_handler.suggest_adaptation(
        sample_place,
        change,
        0.8
    )

    assert adapted_place is not None
    assert "crowd_impact" in adapted_place.adjustments
    assert "affluence" in adapted_place.creator_notes.lower()

@pytest.mark.asyncio
async def test_event_impact_calculation(
    event_handler: EventHandler,
    sample_place: ItineraryPlace
):
    """Teste le calcul d'impact d'événement."""
    change = ContextChange(
        change_type="event",
        severity=0.6,
        location=(35.6895, 139.6917),
        details={
            "size": 0.7,
            "distance": 500  # mètres
        }
    )

    impact = await event_handler.evaluate_impact(sample_place, change)
    assert 0.0 <= impact <= 1.0
    assert impact == pytest.approx(0.35, rel=0.1)  # Impact réduit par la distance

@pytest.mark.asyncio
async def test_event_adaptation_suggestion(
    event_handler: EventHandler,
    sample_place: ItineraryPlace
):
    """Teste la suggestion d'adaptation d'événement."""
    change = ContextChange(
        change_type="event",
        severity=0.6,
        location=(35.6895, 139.6917),
        details={
            "size": 0.7,
            "distance": 500
        }
    )

    adapted_place = await event_handler.suggest_adaptation(
        sample_place,
        change,
        0.5
    )

    assert adapted_place is not None
    assert "event_impact" in adapted_place.adjustments
    assert "événement" in adapted_place.creator_notes.lower()

@pytest.mark.asyncio
async def test_wrong_change_type(
    weather_handler: WeatherHandler,
    crowd_handler: CrowdHandler,
    event_handler: EventHandler,
    sample_place: ItineraryPlace
):
    """Teste la gestion des mauvais types de changement."""
    change = ContextChange(
        change_type="invalid",
        severity=0.5,
        location=(35.6895, 139.6917)
    )

    # Tous les handlers devraient retourner 0.0 pour un type invalide
    assert await weather_handler.evaluate_impact(sample_place, change) == 0.0
    assert await crowd_handler.evaluate_impact(sample_place, change) == 0.0
    assert await event_handler.evaluate_impact(sample_place, change) == 0.0

@pytest.mark.asyncio
async def test_below_threshold_adaptation(
    weather_handler: WeatherHandler,
    crowd_handler: CrowdHandler,
    event_handler: EventHandler,
    sample_place: ItineraryPlace
):
    """Teste qu'aucune adaptation n'est suggérée sous le seuil."""
    change = ContextChange(
        change_type="weather",
        severity=0.2,
        location=(35.6895, 139.6917)
    )

    # Impact trop faible, pas d'adaptation
    assert await weather_handler.suggest_adaptation(sample_place, change, 0.2) is None
    assert await crowd_handler.suggest_adaptation(sample_place, change, 0.2) is None
    assert await event_handler.suggest_adaptation(sample_place, change, 0.2) is None 