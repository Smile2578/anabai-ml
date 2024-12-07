"""Tests pour le module de sélection des templates."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from ai.templates.template_selector import TemplateSelector, TemplateSelectionCriteria
from ai.templates.signature_template import SignatureTemplate
from ai.templates.fusion_template import FusionTemplate
from ai.templates.ai_plus_template import AIPlusTemplate

@pytest.fixture
def template_selector() -> TemplateSelector:
    """Fixture pour créer une instance de TemplateSelector."""
    return TemplateSelector()

@pytest.fixture
def base_criteria() -> TemplateSelectionCriteria:
    """Fixture pour créer des critères de base."""
    return TemplateSelectionCriteria(
        user_id=uuid4(),
        creator_ids=[uuid4()],
        preferences={"nature": 0.8, "culture": 0.6},
        start_time=datetime.now(UTC),
        duration=480,
        excluded_places=[]
    )

@pytest.mark.asyncio
async def test_select_signature_template(
    template_selector: TemplateSelector,
    base_criteria: TemplateSelectionCriteria
):
    """Teste la sélection du SignatureTemplate."""
    # Un seul créateur -> SignatureTemplate
    template = await template_selector.select_template(base_criteria)
    assert isinstance(template, SignatureTemplate)

@pytest.mark.asyncio
async def test_select_fusion_template(
    template_selector: TemplateSelector,
    base_criteria: TemplateSelectionCriteria
):
    """Teste la sélection du FusionTemplate."""
    # 3 créateurs -> FusionTemplate
    criteria = base_criteria.model_copy()
    criteria.creator_ids = [uuid4() for _ in range(3)]
    
    template = await template_selector.select_template(criteria)
    assert isinstance(template, FusionTemplate)

@pytest.mark.asyncio
async def test_select_ai_plus_template(
    template_selector: TemplateSelector,
    base_criteria: TemplateSelectionCriteria
):
    """Teste la sélection du AIPlusTemplate."""
    # 6 créateurs -> AIPlusTemplate
    criteria = base_criteria.model_copy()
    criteria.creator_ids = [uuid4() for _ in range(6)]
    
    template = await template_selector.select_template(criteria)
    assert isinstance(template, AIPlusTemplate)

@pytest.mark.asyncio
async def test_generate_itinerary(
    template_selector: TemplateSelector,
    base_criteria: TemplateSelectionCriteria
):
    """Teste la génération d'un itinéraire."""
    itinerary = await template_selector.generate_itinerary(base_criteria)
    
    assert itinerary is not None
    assert len(itinerary.places) > 0
    assert itinerary.total_duration <= base_criteria.duration

@pytest.mark.asyncio
async def test_template_selection_criteria_validation():
    """Teste la validation des critères de sélection."""
    # Test des valeurs invalides
    with pytest.raises(ValueError):
        TemplateSelectionCriteria(
            user_id=uuid4(),
            creator_ids=[],  # Liste vide non autorisée
            preferences={},
            start_time=datetime.now(UTC),
            duration=480,
            min_creator_score=1.5  # Score > 1 non autorisé
        )

    with pytest.raises(ValueError):
        TemplateSelectionCriteria(
            user_id=uuid4(),
            creator_ids=[uuid4()],
            preferences={},
            start_time=datetime.now(UTC),
            duration=480,
            min_ai_confidence=-0.1  # Score < 0 non autorisé
        ) 