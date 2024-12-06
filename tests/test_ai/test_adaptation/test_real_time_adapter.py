"""Tests pour le module d'adaptation en temps réel."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from ai.adaptation.real_time_adapter import (
    RealTimeAdapter,
    WeatherCondition,
    CrowdLevel,
    LocalEvent,
    AdaptationResult,
    ItineraryPlace
)

@pytest.fixture
def adapter() -> RealTimeAdapter:
    """Fixture pour créer une instance de l'adaptateur."""
    return RealTimeAdapter()

@pytest.fixture
def sample_place() -> ItineraryPlace:
    """Fixture pour créer un lieu de test."""
    return ItineraryPlace(
        place_id=uuid4(),
        name="Temple en plein air",
        description="Un temple extérieur avec jardin zen",
        visit_duration=60,
        recommended_time=datetime.now(UTC),
        creator_notes="Magnifique au lever du soleil",
        score=0.85,
        adjustments={},
        latitude=35.6762,
        longitude=139.6503
    )

@pytest.fixture
def sample_places(sample_place: ItineraryPlace) -> list:
    """Fixture pour créer une liste de lieux de test."""
    places = [sample_place]
    for i in range(2):
        places.append(ItineraryPlace(
            place_id=uuid4(),
            name=f"Lieu test {i+1}",
            description="Un lieu intérieur",
            visit_duration=45,
            recommended_time=datetime.now(UTC) + timedelta(hours=i+1),
            creator_notes="Notes de test",
            score=0.75 - (i * 0.1),
            adjustments={},
            latitude=35.6762 + (i * 0.01),
            longitude=139.6503 + (i * 0.01)
        ))
    return places

@pytest.fixture
def sample_preferences() -> dict:
    """Fixture pour créer des préférences de test."""
    return {
        "temples": 0.9,
        "culture": 0.8,
        "gastronomie": 0.7,
        "nature": 0.6
    }

@pytest.mark.asyncio
async def test_adapter_initialization(adapter: RealTimeAdapter):
    """Teste l'initialisation de l'adaptateur."""
    assert isinstance(adapter, RealTimeAdapter)
    assert hasattr(adapter, "weather_threshold")
    assert hasattr(adapter, "crowd_threshold")
    assert hasattr(adapter, "event_impact_threshold")
    assert hasattr(adapter, "max_alternatives")
    assert hasattr(adapter, "min_confidence")

@pytest.mark.asyncio
async def test_check_conditions(adapter: RealTimeAdapter, sample_place: ItineraryPlace):
    """Teste la vérification des conditions."""
    timestamp = datetime.now(UTC)
    weather, crowd, events = await adapter.check_conditions(sample_place, timestamp)
    
    assert isinstance(weather, WeatherCondition)
    assert isinstance(crowd, CrowdLevel)
    assert isinstance(events, list)
    assert all(isinstance(event, LocalEvent) for event in events)

@pytest.mark.asyncio
async def test_adapt_itinerary(
    adapter: RealTimeAdapter,
    sample_places: list,
    sample_preferences: dict
):
    """Teste l'adaptation d'un itinéraire."""
    start_time = datetime.now(UTC)
    results = await adapter.adapt_itinerary(
        places=sample_places,
        start_time=start_time,
        preferences=sample_preferences
    )
    
    assert isinstance(results, list)
    assert len(results) == len(sample_places)
    assert all(isinstance(result, AdaptationResult) for result in results)

@pytest.mark.asyncio
async def test_weather_impact(adapter: RealTimeAdapter, sample_place: ItineraryPlace):
    """Teste l'évaluation de l'impact météorologique."""
    weather = WeatherCondition(
        temperature=25.0,
        humidity=60.0,
        conditions="Rain",
        description="Light rain",
        timestamp=datetime.now(UTC)
    )
    
    impact = adapter._evaluate_weather_impact(weather, sample_place)
    assert isinstance(impact, float)
    assert 0.0 <= impact <= 1.0

@pytest.mark.asyncio
async def test_crowd_impact(adapter: RealTimeAdapter, sample_place: ItineraryPlace):
    """Teste l'évaluation de l'impact de l'affluence."""
    crowd = CrowdLevel(
        level=0.8,
        source="test",
        timestamp=datetime.now(UTC)
    )
    
    impact = adapter._evaluate_crowd_impact(crowd, sample_place)
    assert isinstance(impact, float)
    assert 0.0 <= impact <= 1.0

@pytest.mark.asyncio
async def test_event_impact(adapter: RealTimeAdapter, sample_place: ItineraryPlace):
    """Teste l'évaluation de l'impact des événements."""
    current_time = datetime.now(UTC)
    events = [
        LocalEvent(
            event_id=uuid4(),
            name="Festival local",
            location={"lat": sample_place.latitude + 0.001, "lng": sample_place.longitude + 0.001},
            type="festival",
            start_time=current_time - timedelta(hours=1),
            impact_radius=1000.0
        )
    ]
    
    impact = adapter._evaluate_event_impact(events, sample_place, current_time)
    assert isinstance(impact, float)
    assert 0.0 <= impact <= 1.0

@pytest.mark.asyncio
async def test_find_alternatives(
    adapter: RealTimeAdapter,
    sample_place: ItineraryPlace,
    sample_preferences: dict
):
    """Teste la recherche d'alternatives."""
    current_time = datetime.now(UTC)
    weather = WeatherCondition(
        temperature=25.0,
        humidity=60.0,
        conditions="Clear",
        description="Clear sky",
        timestamp=current_time
    )
    crowd = CrowdLevel(
        level=0.5,
        source="test",
        timestamp=current_time
    )
    events = []
    
    alternatives = await adapter._find_alternatives(
        place=sample_place,
        current_time=current_time,
        preferences=sample_preferences,
        weather=weather,
        crowd=crowd,
        events=events
    )
    
    assert isinstance(alternatives, list)
    assert all(isinstance(alt, ItineraryPlace) for alt in alternatives)
    assert len(alternatives) <= adapter.max_alternatives

@pytest.mark.asyncio
async def test_adaptation_confidence(
    adapter: RealTimeAdapter,
    sample_place: ItineraryPlace
):
    """Teste le calcul du score de confiance pour l'adaptation."""
    current_time = datetime.now(UTC)
    alternative = ItineraryPlace(
        place_id=uuid4(),
        name="Alternative test",
        description="Un lieu alternatif",
        visit_duration=60,
        recommended_time=current_time,
        creator_notes="Alternative pour mauvais temps",
        score=0.8,
        adjustments={},
        latitude=35.6762 + 0.001,
        longitude=139.6503 + 0.001
    )
    weather = WeatherCondition(
        temperature=25.0,
        humidity=60.0,
        conditions="Clear",
        description="Clear sky",
        timestamp=current_time
    )
    crowd = CrowdLevel(
        level=0.5,
        source="test",
        timestamp=current_time
    )
    events = []
    
    confidence = adapter._calculate_adaptation_confidence(
        original=sample_place,
        alternative=alternative,
        weather=weather,
        crowd=crowd,
        events=events
    )
    
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0

@pytest.mark.asyncio
async def test_adaptation_reason(adapter: RealTimeAdapter):
    """Teste la génération des raisons d'adaptation."""
    reason = adapter._get_adaptation_reason(
        weather_impact=0.8,
        crowd_impact=0.9,
        event_impact=0.6
    )
    
    assert isinstance(reason, str)
    assert reason.startswith("Adaptation nécessaire")
    assert "météorologique" in reason.lower()
    assert "affluence" in reason.lower()
    assert "événement" in reason.lower()

@pytest.mark.asyncio
async def test_empty_itinerary(adapter: RealTimeAdapter, sample_preferences: dict):
    """Teste l'adaptation d'un itinéraire vide."""
    start_time = datetime.now(UTC)
    results = await adapter.adapt_itinerary(
        places=[],
        start_time=start_time,
        preferences=sample_preferences
    )
    
    assert isinstance(results, list)
    assert len(results) == 0

@pytest.mark.asyncio
async def test_adaptation_thresholds(
    adapter: RealTimeAdapter,
    sample_place: ItineraryPlace,
    sample_preferences: dict
):
    """Teste les seuils d'adaptation."""
    start_time = datetime.now(UTC)
    
    # Test avec des impacts sous les seuils
    adapter.weather_threshold = 1.0
    adapter.crowd_threshold = 1.0
    adapter.event_impact_threshold = 1.0
    
    results = await adapter.adapt_itinerary(
        places=[sample_place],
        start_time=start_time,
        preferences=sample_preferences
    )
    
    assert len(results) == 1
    assert results[0].adaptation_reason == "Aucune adaptation nécessaire"
    assert results[0].confidence_score == 1.0 