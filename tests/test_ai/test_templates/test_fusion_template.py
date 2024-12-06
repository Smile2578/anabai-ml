"""Tests pour le module de génération d'itinéraires fusionnés."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from ai.templates.fusion_template import (
    FusionTemplate,
    FusionItinerary,
    ItineraryPlace
)

@pytest.fixture
def fusion_template() -> FusionTemplate:
    """Fixture pour créer une instance du template de fusion."""
    return FusionTemplate()

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

@pytest.mark.asyncio
async def test_template_initialization(fusion_template: FusionTemplate):
    """Teste l'initialisation du template."""
    assert isinstance(fusion_template, FusionTemplate)
    assert hasattr(fusion_template, "max_places")
    assert hasattr(fusion_template, "min_places")
    assert hasattr(fusion_template, "max_duration")
    assert hasattr(fusion_template, "min_duration")
    assert hasattr(fusion_template, "min_creators")
    assert hasattr(fusion_template, "max_creators")

@pytest.mark.asyncio
async def test_generate_itinerary(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la génération d'un itinéraire."""
    itinerary = await fusion_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    assert isinstance(itinerary, FusionItinerary)
    assert itinerary.creator_ids == sample_creator_ids
    assert isinstance(itinerary.places, list)
    assert 0.0 <= itinerary.score <= 1.0
    assert all(isinstance(w, float) for w in itinerary.fusion_weights.values())
    assert sum(itinerary.fusion_weights.values()) == pytest.approx(1.0)

@pytest.mark.asyncio
async def test_duration_validation(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la validation de la durée."""
    # Test avec une durée trop courte
    with pytest.raises(ValueError):
        await fusion_template.generate(
            creator_ids=sample_creator_ids,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=120  # Trop court
        )
    
    # Test avec une durée trop longue
    with pytest.raises(ValueError):
        await fusion_template.generate(
            creator_ids=sample_creator_ids,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=1000  # Trop long
        )

@pytest.mark.asyncio
async def test_creators_count_validation(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste la validation du nombre de créateurs."""
    # Test avec trop peu de créateurs
    with pytest.raises(ValueError):
        await fusion_template.generate(
            creator_ids=[uuid4()],  # Un seul créateur
            preferences=sample_preferences,
            start_time=sample_start_time
        )
    
    # Test avec trop de créateurs
    too_many_creators = [uuid4() for _ in range(6)]
    with pytest.raises(ValueError):
        await fusion_template.generate(
            creator_ids=too_many_creators,
            preferences=sample_preferences,
            start_time=sample_start_time
        )

@pytest.mark.asyncio
async def test_excluded_places(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste l'exclusion de lieux."""
    excluded_places = [uuid4(), uuid4()]
    
    itinerary = await fusion_template.generate(
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
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la gestion du timing dans l'itinéraire."""
    duration = 360  # 6 heures
    
    itinerary = await fusion_template.generate(
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
async def test_fusion_weights(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste le calcul des poids de fusion."""
    itinerary = await fusion_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    # Vérifie que les poids sont valides
    assert len(itinerary.fusion_weights) == len(sample_creator_ids)
    assert all(0.0 <= w <= 1.0 for w in itinerary.fusion_weights.values())
    assert sum(itinerary.fusion_weights.values()) == pytest.approx(1.0)

@pytest.mark.asyncio
async def test_score_calculation(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste le calcul des scores."""
    itinerary = await fusion_template.generate(
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
    fusion_template: FusionTemplate,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste la génération avec des préférences vides."""
    itinerary = await fusion_template.generate(
        creator_ids=sample_creator_ids,
        preferences={},
        start_time=sample_start_time
    )
    
    assert isinstance(itinerary, FusionItinerary)
    assert itinerary.places  # Devrait quand même générer un itinéraire

@pytest.mark.asyncio
async def test_distance_calculation(
    fusion_template: FusionTemplate,
    sample_preferences: dict,
    sample_start_time: datetime,
    sample_creator_ids: list
):
    """Teste le calcul des distances."""
    itinerary = await fusion_template.generate(
        creator_ids=sample_creator_ids,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    assert itinerary.total_distance >= 0.0
    assert isinstance(itinerary.total_distance, float) 