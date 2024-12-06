"""Tests pour le module de génération d'itinéraires signature."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from ai.templates.signature_template import (
    SignatureTemplate,
    SignatureItinerary,
    ItineraryPlace
)

@pytest.fixture
def signature_template() -> SignatureTemplate:
    """Fixture pour créer une instance du template signature."""
    return SignatureTemplate()

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

@pytest.mark.asyncio
async def test_template_initialization(signature_template: SignatureTemplate):
    """Teste l'initialisation du template."""
    assert isinstance(signature_template, SignatureTemplate)
    assert hasattr(signature_template, "max_places")
    assert hasattr(signature_template, "min_places")
    assert hasattr(signature_template, "max_duration")
    assert hasattr(signature_template, "min_duration")

@pytest.mark.asyncio
async def test_generate_itinerary(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste la génération d'un itinéraire."""
    creator_id = uuid4()
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    assert isinstance(itinerary, SignatureItinerary)
    assert itinerary.creator_id == creator_id
    assert isinstance(itinerary.places, list)
    assert 0.0 <= itinerary.score <= 1.0

@pytest.mark.asyncio
async def test_duration_validation(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste la validation de la durée."""
    creator_id = uuid4()
    
    # Test avec une durée trop courte
    with pytest.raises(ValueError):
        await signature_template.generate(
            creator_id=creator_id,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=60  # Trop court
        )
    
    # Test avec une durée trop longue
    with pytest.raises(ValueError):
        await signature_template.generate(
            creator_id=creator_id,
            preferences=sample_preferences,
            start_time=sample_start_time,
            duration=1000  # Trop long
        )

@pytest.mark.asyncio
async def test_excluded_places(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste l'exclusion de lieux."""
    creator_id = uuid4()
    excluded_places = [uuid4(), uuid4()]
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences=sample_preferences,
        start_time=sample_start_time,
        excluded_places=excluded_places
    )
    
    # Vérifie qu'aucun lieu exclu n'est présent
    place_ids = [place.place_id for place in itinerary.places]
    assert not any(place_id in excluded_places for place_id in place_ids)

@pytest.mark.asyncio
async def test_itinerary_timing(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste la gestion du timing dans l'itinéraire."""
    creator_id = uuid4()
    duration = 240  # 4 heures
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
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
async def test_creator_expertise_influence(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste l'influence de l'expertise du créateur."""
    creator_id = uuid4()
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    # Vérifie que l'expertise du créateur est présente
    assert itinerary.creator_expertise
    assert isinstance(itinerary.creator_expertise, list)
    assert all(isinstance(exp, str) for exp in itinerary.creator_expertise)

@pytest.mark.asyncio
async def test_score_calculation(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste le calcul des scores."""
    creator_id = uuid4()
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    # Vérifie les scores
    assert 0.0 <= itinerary.score <= 1.0
    for place in itinerary.places:
        assert 0.0 <= place.score <= 1.0

@pytest.mark.asyncio
async def test_empty_preferences(signature_template: SignatureTemplate, sample_start_time: datetime):
    """Teste la génération avec des préférences vides."""
    creator_id = uuid4()
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences={},
        start_time=sample_start_time
    )
    
    assert isinstance(itinerary, SignatureItinerary)
    assert itinerary.places  # Devrait quand même générer un itinéraire

@pytest.mark.asyncio
async def test_distance_calculation(
    signature_template: SignatureTemplate,
    sample_preferences: dict,
    sample_start_time: datetime
):
    """Teste le calcul des distances."""
    creator_id = uuid4()
    
    itinerary = await signature_template.generate(
        creator_id=creator_id,
        preferences=sample_preferences,
        start_time=sample_start_time
    )
    
    assert itinerary.total_distance >= 0.0
    assert isinstance(itinerary.total_distance, float) 