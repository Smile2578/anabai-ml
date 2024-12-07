from datetime import datetime, UTC, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import numpy as np
import os
from dotenv import load_dotenv

from models.base_score import BaseScore
from models.contextual_score import ContextualScore
from models.recommendation import Recommendation, TemplateType
from ai.learning.data_collector import DataCollector
from ai.monitoring.metrics_tracker import MetricsTracker
from ai.adaptation.real_time_monitoring import RealTimeMonitor
from ai.adaptation.adaptation_engine import AdaptationEngine
from ai.adaptation.context_handlers import WeatherHandler, CrowdHandler, EventHandler
from ai.templates import ItineraryPlace

# Charger les variables d'environnement
load_dotenv()

@pytest.fixture
def mock_mongodb():
    """Mock pour MongoDB avec des collections asynchrones."""
    db = MagicMock()
    db.metrics_collection = AsyncMock()
    db.adaptations_collection = AsyncMock()
    return db

@pytest.fixture
def mock_redis():
    """Mock pour Redis avec des opérations asynchrones."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis

@pytest.fixture
async def setup_adaptation_system(mock_mongodb, mock_redis):
    """Configure le système d'adaptation avec les composants mockés."""
    data_collector = DataCollector(mongodb_uri=os.getenv("MONGODB_URI"))
    data_collector.client = mock_mongodb

    metrics_tracker = MetricsTracker(
        data_collector=data_collector,
        window_size_hours=24
    )

    context_handlers = {
        "weather": WeatherHandler(),
        "crowd": CrowdHandler(),
        "events": EventHandler()
    }

    real_time_monitor = RealTimeMonitor()

    adaptation_engine = AdaptationEngine()

    return {
        "metrics_tracker": metrics_tracker,
        "context_handlers": context_handlers,
        "real_time_monitor": real_time_monitor,
        "adaptation_engine": adaptation_engine
    }

@pytest.mark.asyncio
async def test_weather_adaptation(setup_adaptation_system):
    """
    Teste l'adaptation en temps réel basée sur les changements météo.
    """
    components = setup_adaptation_system

    # 1. Créer un lieu dans l'itinéraire
    place_id = uuid4()
    place = ItineraryPlace(
        place_id=place_id,
        name="Tour Eiffel",
        description="Monument emblématique de Paris",
        latitude=48.8584,
        longitude=2.2945,
        recommended_time=datetime.now(UTC),
        duration=120,
        visit_duration=90,
        score=0.8,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.95,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        },
        creator_id=uuid4()
    )

    # 2. Simuler un changement météo
    conditions = {
        str(place_id): {
            "weather": 0.8  # Sévérité de la condition météo
        }
    }

    # 3. Adapter l'itinéraire
    adaptation_result = await components["adaptation_engine"].adapt_itinerary(
        places=[place],
        conditions=conditions
    )

    assert adaptation_result.total_impact > 0.0
    assert len(adaptation_result.decisions) > 0

@pytest.mark.asyncio
async def test_crowd_adaptation(setup_adaptation_system):
    """
    Teste l'adaptation en temps réel basée sur l'affluence.
    """
    components = setup_adaptation_system

    # 1. Créer un lieu dans l'itinéraire
    place_id = uuid4()
    place = ItineraryPlace(
        place_id=place_id,
        name="Musée du Louvre",
        description="Plus grand musée d'art au monde",
        latitude=48.8606,
        longitude=2.3376,
        recommended_time=datetime.now(UTC),
        duration=180,
        visit_duration=150,
        score=0.8,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.95,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        },
        creator_id=uuid4()
    )

    # 2. Simuler un changement d'affluence
    conditions = {
        str(place_id): {
            "crowd": 0.9  # Sévérité de l'affluence
        }
    }

    # 3. Adapter l'itinéraire
    adaptation_result = await components["adaptation_engine"].adapt_itinerary(
        places=[place],
        conditions=conditions
    )

    assert adaptation_result.total_impact > 0.0
    assert len(adaptation_result.decisions) > 0

@pytest.mark.asyncio
async def test_event_adaptation(setup_adaptation_system):
    """
    Teste l'adaptation en temps réel basée sur les événements.
    """
    components = setup_adaptation_system

    # 1. Créer un lieu dans l'itinéraire
    place_id = uuid4()
    place = ItineraryPlace(
        place_id=place_id,
        name="Arc de Triomphe",
        description="Monument historique au centre de l'Étoile",
        latitude=48.8738,
        longitude=2.2950,
        recommended_time=datetime.now(UTC),
        duration=60,
        visit_duration=45,
        score=0.8,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.95,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        },
        creator_id=uuid4()
    )

    # 2. Simuler un nouvel événement
    conditions = {
        str(place_id): {
            "event": 0.7  # Sévérité de l'événement
        }
    }

    # 3. Adapter l'itinéraire
    adaptation_result = await components["adaptation_engine"].adapt_itinerary(
        places=[place],
        conditions=conditions
    )

    assert adaptation_result.total_impact > 0.0
    assert len(adaptation_result.decisions) > 0

@pytest.mark.asyncio
async def test_multiple_adaptations(setup_adaptation_system):
    """
    Teste l'adaptation en temps réel avec plusieurs changements simultanés.
    """
    components = setup_adaptation_system

    # 1. Créer un lieu dans l'itinéraire
    place_id = uuid4()
    place = ItineraryPlace(
        place_id=place_id,
        name="Notre-Dame",
        description="Cathédrale emblématique de Paris",
        latitude=48.8530,
        longitude=2.3499,
        recommended_time=datetime.now(UTC),
        duration=90,
        visit_duration=75,
        score=0.8,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.95,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        },
        creator_id=uuid4()
    )

    # 2. Simuler plusieurs changements
    conditions = {
        str(place_id): {
            "weather": 0.8,  # Sévérité de la condition météo
            "crowd": 0.9,   # Sévérité de l'affluence
            "event": 0.7    # Sévérité de l'événement
        }
    }

    # 3. Adapter l'itinéraire
    adaptation_result = await components["adaptation_engine"].adapt_itinerary(
        places=[place],
        conditions=conditions
    )

    # 4. Vérifier les adaptations
    assert adaptation_result.total_impact > 0.0
    assert len(adaptation_result.decisions) > 0
    assert any(d.impact_score > 0.0 for d in adaptation_result.decisions)
    assert any(d.action != "monitor" for d in adaptation_result.decisions)
    
    # 5. Vérifier que les places ont été modifiées
    assert len(adaptation_result.adapted_places) > 0
    assert adaptation_result.adapted_places != adaptation_result.original_places
    