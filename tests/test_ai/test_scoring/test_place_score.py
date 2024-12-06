"""Tests pour le module de calcul du score des lieux."""

import pytest
from uuid import uuid4
from datetime import datetime
from ai.scoring.place_score import (
    PlaceMetrics,
    PlaceScoreInput,
    PlaceScoreOutput,
    PlaceScoreCalculator
)

@pytest.fixture
def place_score_calculator() -> PlaceScoreCalculator:
    """Fixture pour créer une instance du calculateur de score."""
    return PlaceScoreCalculator()

@pytest.fixture
def sample_metrics() -> PlaceMetrics:
    """Fixture pour créer des métriques de test."""
    return PlaceMetrics(
        average_rating=4.5,
        review_count=100,
        popularity_score=0.8,
        accessibility_score=0.9,
        categories=["temple", "cultural", "historical"],
        amenities={
            "parking": True,
            "restroom": True,
            "restaurant": True,
            "gift_shop": True,
            "guide": True
        },
        peak_hours={
            "morning": 0.7,
            "afternoon": 1.0,
            "evening": 0.5
        },
        seasonal_factors={
            "spring": 1.0,
            "summer": 0.8,
            "autumn": 0.9,
            "winter": 0.6
        }
    )

@pytest.fixture
def sample_input(sample_metrics: PlaceMetrics) -> PlaceScoreInput:
    """Fixture pour créer un exemple de données d'entrée."""
    return PlaceScoreInput(
        place_id=uuid4(),
        metrics=sample_metrics,
        current_season="spring",
        current_hour="afternoon",
        target_categories=["temple", "cultural"]
    )

def test_place_score_initialization(place_score_calculator: PlaceScoreCalculator):
    """Teste l'initialisation du calculateur de score."""
    assert isinstance(place_score_calculator, PlaceScoreCalculator)
    assert hasattr(place_score_calculator, "weights")
    assert len(place_score_calculator.weights) == 6
    assert abs(sum(place_score_calculator.weights.values()) - 1.0) < 0.001

def test_place_score_calculation(
    place_score_calculator: PlaceScoreCalculator,
    sample_input: PlaceScoreInput
):
    """Teste le calcul du score lieu."""
    result = place_score_calculator.calculate(sample_input)
    
    assert isinstance(result, PlaceScoreOutput)
    assert 0.0 <= result.place_score <= 1.0
    assert result.place_id == sample_input.place_id
    assert isinstance(result.calculation_timestamp, datetime)
    assert len(result.component_scores) == 6
    assert result.category_match is not None
    assert result.time_relevance is not None
    assert result.seasonal_relevance is not None

def test_place_score_with_empty_metrics():
    """Teste le calcul avec des métriques minimales."""
    calculator = PlaceScoreCalculator()
    metrics = PlaceMetrics(
        average_rating=0.0,
        review_count=0,
        popularity_score=0.0,
        accessibility_score=0.0
    )
    input_data = PlaceScoreInput(
        place_id=uuid4(),
        metrics=metrics
    )
    
    result = calculator.calculate(input_data)
    assert result.place_score <= 0.5  # Score moyen ou inférieur dû aux valeurs par défaut
    assert result.category_match is None

def test_place_score_weight_update(place_score_calculator: PlaceScoreCalculator):
    """Teste la mise à jour des poids."""
    new_weights = {
        "rating": 0.3,
        "popularity": 0.2,
        "accessibility": 0.15,
        "amenities": 0.15,
        "time_relevance": 0.1,
        "seasonal_relevance": 0.1
    }
    
    place_score_calculator.update_weights(new_weights)
    assert place_score_calculator.weights == new_weights

def test_place_score_invalid_weights(place_score_calculator: PlaceScoreCalculator):
    """Teste la validation des poids invalides."""
    # Test avec des poids > 1
    invalid_weights = {
        "rating": 1.5,
        "popularity": 0.2
    }
    with pytest.raises(ValueError):
        place_score_calculator.update_weights(invalid_weights)
    
    # Test avec une somme != 1
    invalid_weights = {
        "rating": 0.1,
        "popularity": 0.1,
        "accessibility": 0.1,
        "amenities": 0.1,
        "time_relevance": 0.1,
        "seasonal_relevance": 0.1
    }
    with pytest.raises(ValueError):
        place_score_calculator.update_weights(invalid_weights)

def test_category_matching(place_score_calculator: PlaceScoreCalculator, sample_metrics: PlaceMetrics):
    """Teste le calcul de correspondance des catégories."""
    input_data = PlaceScoreInput(
        place_id=uuid4(),
        metrics=sample_metrics,
        target_categories=["temple", "cultural"]
    )
    
    result = place_score_calculator.calculate(input_data)
    assert result.category_match == 1.0  # Correspondance parfaite
    
    input_data.target_categories = ["temple", "shopping"]
    result = place_score_calculator.calculate(input_data)
    assert result.category_match == 0.5  # Correspondance partielle

def test_temporal_relevance(place_score_calculator: PlaceScoreCalculator, sample_metrics: PlaceMetrics):
    """Teste le calcul de la pertinence temporelle."""
    input_data = PlaceScoreInput(
        place_id=uuid4(),
        metrics=sample_metrics,
        current_hour="afternoon"  # Heure de pointe dans sample_metrics
    )
    
    result = place_score_calculator.calculate(input_data)
    assert result.time_relevance == 1.0
    
    input_data.current_hour = "night"  # Heure non définie
    result = place_score_calculator.calculate(input_data)
    assert result.time_relevance == 0.5  # Valeur par défaut

def test_seasonal_relevance(place_score_calculator: PlaceScoreCalculator, sample_metrics: PlaceMetrics):
    """Teste le calcul de la pertinence saisonnière."""
    input_data = PlaceScoreInput(
        place_id=uuid4(),
        metrics=sample_metrics,
        current_season="spring"  # Meilleure saison dans sample_metrics
    )
    
    result = place_score_calculator.calculate(input_data)
    assert result.seasonal_relevance == 1.0
    
    input_data.current_season = "winter"
    result = place_score_calculator.calculate(input_data)
    assert result.seasonal_relevance == 0.6