"""Tests pour le module d'adaptation des itinéraires."""

import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict
from uuid import uuid4
from ai.adaptation.adaptation_engine import (
    AdaptationEngine,
    AdaptationDecision,
    AdaptationResult
)
from ai.templates import ItineraryPlace

@pytest.fixture
def adaptation_engine() -> AdaptationEngine:
    """Fixture pour créer une instance de AdaptationEngine."""
    return AdaptationEngine()

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
def sample_conditions(sample_place: ItineraryPlace) -> Dict[str, Dict[str, float]]:
    """Fixture pour créer des conditions de test."""
    return {
        str(sample_place.place_id): {
            "weather": 0.8,  # Mauvais temps
            "crowd": 0.6,    # Affluence modérée
            "event": 0.3,    # Petit événement
            "accessibility": 0.2  # Bonne accessibilité
        }
    }

@pytest.mark.asyncio
async def test_evaluate_conditions(
    adaptation_engine: AdaptationEngine,
    sample_place: ItineraryPlace
):
    """Teste l'évaluation des conditions."""
    conditions = {
        "weather": 0.8,
        "crowd": 0.6
    }
    
    impact, reason = await adaptation_engine.evaluate_conditions(
        sample_place,
        conditions
    )
    
    assert 0.0 <= impact <= 1.0
    assert reason in ["weather", "crowd"]
    assert reason == "weather"  # Car impact weather le plus élevé

@pytest.mark.asyncio
async def test_decide_adaptation_skip(
    adaptation_engine: AdaptationEngine,
    sample_place: ItineraryPlace
):
    """Teste la décision de sauter un lieu."""
    decision = await adaptation_engine.decide_adaptation(
        sample_place,
        0.8,  # Impact élevé
        "weather"
    )
    
    assert isinstance(decision, AdaptationDecision)
    assert decision.action == "skip"
    assert "weather" in decision.reason
    assert decision.confidence > 0.8

@pytest.mark.asyncio
async def test_decide_adaptation_reschedule(
    adaptation_engine: AdaptationEngine,
    sample_place: ItineraryPlace
):
    """Teste la décision de reprogrammer un lieu."""
    decision = await adaptation_engine.decide_adaptation(
        sample_place,
        0.4,  # Impact modéré
        "crowd"
    )
    
    assert isinstance(decision, AdaptationDecision)
    assert decision.action == "reschedule"
    assert "crowd" in decision.reason
    assert decision.new_time is not None
    assert decision.new_time > sample_place.recommended_time

@pytest.mark.asyncio
async def test_decide_adaptation_monitor(
    adaptation_engine: AdaptationEngine,
    sample_place: ItineraryPlace
):
    """Teste la décision de surveiller un lieu."""
    decision = await adaptation_engine.decide_adaptation(
        sample_place,
        0.2,  # Impact faible
        "event"
    )
    
    assert isinstance(decision, AdaptationDecision)
    assert decision.action == "monitor"
    assert "event" in decision.reason
    assert decision.confidence > 0.7

@pytest.mark.asyncio
async def test_adapt_itinerary(
    adaptation_engine: AdaptationEngine,
    sample_place: ItineraryPlace,
    sample_conditions: Dict[str, Dict[str, float]]
):
    """Teste l'adaptation complète d'un itinéraire."""
    places = [sample_place]
    
    result = await adaptation_engine.adapt_itinerary(places, sample_conditions)
    
    assert isinstance(result, AdaptationResult)
    assert len(result.decisions) == len(places)
    assert 0.0 <= result.total_impact <= 1.0
    assert result.original_places == places
    
    # Vérifie que l'adaptation a été appliquée
    if result.decisions[0].action == "skip":
        assert len(result.adapted_places) == 0
    elif result.decisions[0].action == "reschedule":
        assert len(result.adapted_places) == 1
        assert result.adapted_places[0].recommended_time != places[0].recommended_time
    else:
        assert len(result.adapted_places) == 1
        assert result.adapted_places[0] == places[0]

@pytest.mark.asyncio
async def test_adaptation_with_multiple_places(
    adaptation_engine: AdaptationEngine
):
    """Teste l'adaptation avec plusieurs lieux."""
    places = [
        ItineraryPlace(
            place_id=uuid4(),
            name=f"Place {i}",
            description=f"Description {i}",
            visit_duration=60,
            recommended_time=datetime.now(UTC) + timedelta(hours=i),
            creator_notes=f"Notes {i}",
            score=0.8,
            adjustments={},
            latitude=35.6895,
            longitude=139.6917
        )
        for i in range(3)
    ]
    
    conditions = {
        str(places[0].place_id): {"weather": 0.9},  # Skip (> 0.7)
        str(places[1].place_id): {"crowd": 0.4},    # Reschedule (> 0.3)
        str(places[2].place_id): {"event": 0.2}     # Monitor (< 0.3)
    }
    
    result = await adaptation_engine.adapt_itinerary(places, conditions)
    
    assert len(result.decisions) == 3
    assert result.decisions[0].action == "skip"
    assert result.decisions[1].action == "reschedule"
    assert result.decisions[2].action == "monitor"
    assert len(result.adapted_places) == 2  # Un lieu skippé