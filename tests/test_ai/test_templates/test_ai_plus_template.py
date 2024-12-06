"""Tests pour le module de génération d'itinéraires enrichis par l'IA."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from ai.templates.ai_plus_template import (
    AIPlusTemplate,
    AIPlusItinerary,
    AIRecommendation,
    ItineraryPlace
)

@pytest.fixture
def ai_plus_template() -> AIPlusTemplate:
    """Fixture pour créer une instance du template AI Plus."""
    return AIPlusTemplate()

@pytest.fixture
def sample_preferences() -> dict:
    """Fixture pour créer des préférences de test."""
    return {
        "temples": 0.9,
        "culture": 0.8,
        "gastronomie": 0.7,
        "nature": 0.6
    }

@pytest.fixture
def sample_start_time() -> datetime:
    """Fixture pour créer une date de début de test."""
    return datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)

@pytest.fixture
def sample_creator_ids() -> list:
    """Fixture pour créer une liste d'IDs de créateurs."""
    return [uuid4() for _ in range(3)]

@pytest.fixture
def sample_user_history() -> list:
    """Fixture pour créer un historique utilisateur de test."""
    return [
        {
            "place_id": uuid4(),
            "rating": 4.5,
            "visit_date": datetime.now(UTC) - timedelta(days=30),
            "duration": 120
        },
        {
            "place_id": uuid4(),
            "rating": 3.8,
            "visit_date": datetime.now(UTC) - timedelta(days=15),
            "duration": 90
        }
    ]

@pytest.mark.asyncio
async def test_template_initialization(ai_plus_template: AIPlusTemplate):
    """Teste l'initialisation du template."""
    assert isinstance(ai_plus_template, AIPlusTemplate)
    assert hasattr(ai_plus_template, "max_places")
    assert hasattr(ai_plus_template, "min_places")
    assert hasattr(ai_plus_template, "max_duration")
    assert hasattr(ai_plus_template, "min_duration")
    assert hasattr(ai_plus_template, "min_creators")
    assert hasattr(ai_plus_template, "max_creators")
    assert hasattr(ai_plus_template, "ai_weight")
    assert hasattr(ai_plus_template, "min_confidence")

@pytest.mark.asyncio
async def test_generate_itinerary(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list,
    sample_user_history: list
):
    """Teste la génération d'un itinéraire."""
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time,
        user_history=sample_user_history
    )
    
    assert isinstance(itinerary, AIPlusItinerary)
    assert itinerary.creator_ids == sample_creator_ids
    assert isinstance(itinerary.places, list)
    assert isinstance(itinerary.ai_recommendations, list)
    assert 0.0 <= itinerary.score <= 1.0
    assert 0.0 <= itinerary.ai_weight <= 1.0
    assert all(isinstance(w, float) for w in itinerary.fusion_weights.values())
    assert sum(itinerary.fusion_weights.values()) == pytest.approx(1.0)

@pytest.mark.asyncio
async def test_duration_validation(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la validation de la durée."""
    # Test avec une durée trop courte
    with pytest.raises(ValueError):
        await ai_plus_template.generate(
            creator_ids=sample_creator_ids,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=180  # Trop court
        )
    
    # Test avec une durée trop longue
    with pytest.raises(ValueError):
        await ai_plus_template.generate(
            creator_ids=sample_creator_ids,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=1000  # Trop long
        )

@pytest.mark.asyncio
async def test_creators_count_validation(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste la validation du nombre de créateurs."""
    # Test avec trop peu de créateurs
    with pytest.raises(ValueError):
        await ai_plus_template.generate(
            creator_ids=[uuid4()],  # Un seul créateur
            preferences=sample_preferences,
            start_time=sample_start_time
        )
    
    # Test avec trop de créateurs
    too_many_creators = [uuid4() for _ in range(6)]
    with pytest.raises(ValueError):
        await ai_plus_template.generate(
            creator_ids=too_many_creators,
            preferences=sample_preferences,
            start_time=sample_start_time
        )

@pytest.mark.asyncio
async def test_excluded_places(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste l'exclusion de lieux."""
    excluded_places = [uuid4(), uuid4()]
    
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time,
        excluded_places=excluded_places
    )
    
    # Vérifie qu'aucun lieu exclu n'est présent
    place_ids = [place.place_id for place in itinerary.places]
    assert not any(place_id in excluded_places for place_id in place_ids)

@pytest.mark.asyncio
async def test_itinerary_timing(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la gestion du timing dans l'itinéraire."""
    duration = 480  # 8 heures
    
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time,
        duration=duration
    )
    
    # Vérifie que la durée totale respecte la limite
    assert itinerary.total_duration <= duration
    
    # Vérifie que les horaires sont cohérents
    current_time = sample_start_time
    for place in itinerary.places:
        assert place.recommended_time >= current_time
        current_time = place.recommended_time + timedelta(minutes=place.visit_duration)

@pytest.mark.asyncio
async def test_ai_recommendations(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list,
    sample_user_history: list
):
    """Teste les recommandations de l'IA."""
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time,
        user_history=sample_user_history
    )
    
    # Vérifie les recommandations IA
    assert itinerary.ai_recommendations
    for rec in itinerary.ai_recommendations:
        assert isinstance(rec, AIRecommendation)
        assert 0.0 <= rec.confidence_score <= 1.0
        assert rec.confidence_score >= ai_plus_template.min_confidence
        assert rec.reasoning
        if rec.similarity_score is not None:
            assert 0.0 <= rec.similarity_score <= 1.0
        if rec.diversity_score is not None:
            assert 0.0 <= rec.diversity_score <= 1.0

@pytest.mark.asyncio
async def test_score_calculation(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste le calcul des scores."""
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    # Vérifie les scores
    assert 0.0 <= itinerary.score <= 1.0
    for place in itinerary.places:
        assert 0.0 <= place.score <= 1.0

@pytest.mark.asyncio
async def test_empty_preferences(
    ai_plus_template: AIPlusTemplate,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la génération avec des préférences vides."""
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences={},
        start_time=sample_start_time
    )
    
    assert isinstance(itinerary, AIPlusItinerary)
    assert itinerary.places  # Devrait quand même générer un itinéraire

@pytest.mark.asyncio
async def test_distance_calculation(
    ai_plus_template: AIPlusTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste le calcul des distances."""
    itinerary = await ai_plus_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    assert itinerary.total_distance >= 0.0
    assert isinstance(itinerary.total_distance, float) 