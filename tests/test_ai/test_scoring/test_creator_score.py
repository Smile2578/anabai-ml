"""Tests pour le module de calcul du score des créateurs."""

import pytest
from uuid import uuid4
from datetime import datetime
from ai.scoring.creator_score import (
    CreatorMetrics,
    CreatorScoreInput,
    CreatorScoreOutput,
    CreatorScoreCalculator
)

@pytest.fixture
def creator_score_calculator() -> CreatorScoreCalculator:
    """Fixture pour créer une instance du calculateur de score."""
    return CreatorScoreCalculator()

@pytest.fixture
def sample_metrics() -> CreatorMetrics:
    """Fixture pour créer des métriques de test."""
    return CreatorMetrics(
        total_content=50,
        average_rating=4.5,
        engagement_rate=0.75,
        expertise_areas={
            "temples": 0.9,
            "restaurants": 0.8,
            "shopping": 0.6
        },
        content_freshness=0.85
    )

@pytest.fixture
def sample_input(sample_metrics: CreatorMetrics) -> CreatorScoreInput:
    """Fixture pour créer un exemple de données d'entrée."""
    return CreatorScoreInput(
        creator_id=uuid4(),
        metrics=sample_metrics,
        target_categories=["temples", "restaurants"]
    )

def test_creator_score_initialization(creator_score_calculator: CreatorScoreCalculator):
    """Teste l'initialisation du calculateur de score."""
    assert isinstance(creator_score_calculator, CreatorScoreCalculator)
    assert hasattr(creator_score_calculator, "weights")
    assert len(creator_score_calculator.weights) == 5
    assert abs(sum(creator_score_calculator.weights.values()) - 1.0) < 0.001

def test_creator_score_calculation(
    creator_score_calculator: CreatorScoreCalculator,
    sample_input: CreatorScoreInput
):
    """Teste le calcul du score créateur."""
    result = creator_score_calculator.calculate(sample_input)
    
    assert isinstance(result, CreatorScoreOutput)
    assert 0.0 <= result.creator_score <= 1.0
    assert result.creator_id == sample_input.creator_id
    assert isinstance(result.calculation_timestamp, datetime)
    assert len(result.component_scores) == 5
    assert result.expertise_match is not None

def test_creator_score_with_empty_metrics():
    """Teste le calcul avec des métriques minimales."""
    calculator = CreatorScoreCalculator()
    metrics = CreatorMetrics(
        total_content=0,
        average_rating=0.0,
        engagement_rate=0.0,
        content_freshness=0.0
    )
    input_data = CreatorScoreInput(
        creator_id=uuid4(),
        metrics=metrics
    )
    
    result = calculator.calculate(input_data)
    assert result.creator_score < 0.01  # Score très proche de 0
    assert all(v <= 0.01 for v in result.component_scores.values())

def test_creator_score_weight_update(creator_score_calculator: CreatorScoreCalculator):
    """Teste la mise à jour des poids."""
    new_weights = {
        "content_volume": 0.1,
        "rating": 0.3,
        "engagement": 0.2,
        "expertise": 0.3,
        "freshness": 0.1
    }
    
    creator_score_calculator.update_weights(new_weights)
    assert creator_score_calculator.weights == new_weights

def test_creator_score_invalid_weights(creator_score_calculator: CreatorScoreCalculator):
    """Teste la validation des poids invalides."""
    # Test avec des poids > 1
    invalid_weights = {
        "content_volume": 1.5,
        "rating": 0.3,
        "engagement": 0.2,
        "expertise": 0.3,
        "freshness": 0.1
    }
    with pytest.raises(ValueError):
        creator_score_calculator.update_weights(invalid_weights)
    
    # Test avec une somme != 1
    invalid_weights = {
        "content_volume": 0.1,
        "rating": 0.1,
        "engagement": 0.1,
        "expertise": 0.1,
        "freshness": 0.1
    }
    with pytest.raises(ValueError):
        creator_score_calculator.update_weights(invalid_weights)

def test_expertise_matching(creator_score_calculator: CreatorScoreCalculator):
    """Teste le calcul du score d'expertise pour des catégories spécifiques."""
    metrics = CreatorMetrics(
        total_content=10,
        average_rating=4.0,
        engagement_rate=0.5,
        expertise_areas={
            "temples": 1.0,
            "restaurants": 0.0
        },
        content_freshness=0.5
    )
    
    # Test avec une seule catégorie ciblée
    input_data = CreatorScoreInput(
        creator_id=uuid4(),
        metrics=metrics,
        target_categories=["temples"]
    )
    result = creator_score_calculator.calculate(input_data)
    assert result.expertise_match == 1.0
    
    # Test avec plusieurs catégories
    input_data.target_categories = ["temples", "restaurants"]
    result = creator_score_calculator.calculate(input_data)
    assert result.expertise_match == 0.5

def test_content_volume_normalization(creator_score_calculator: CreatorScoreCalculator):
    """Teste la normalisation du score de volume de contenu."""
    metrics = CreatorMetrics(
        total_content=1000,  # Grand nombre de contenus
        average_rating=3.0,
        engagement_rate=0.5,
        content_freshness=0.5
    )
    input_data = CreatorScoreInput(
        creator_id=uuid4(),
        metrics=metrics
    )
    
    result = creator_score_calculator.calculate(input_data)
    assert result.component_scores["content_volume"] == 1.0  # Devrait être plafonné à 1.0