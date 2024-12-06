"""Tests pour le module de calcul du score de base."""

import pytest
from uuid import UUID, uuid4
from ai.scoring.base_score import BaseScoreCalculator, BaseScoreInput, BaseScoreOutput

@pytest.fixture
def base_score_calculator() -> BaseScoreCalculator:
    """Fixture pour créer une instance de BaseScoreCalculator."""
    return BaseScoreCalculator()

@pytest.fixture
def sample_input() -> BaseScoreInput:
    """Fixture pour créer un exemple de données d'entrée."""
    return BaseScoreInput(
        place_id=uuid4(),
        creator_id=uuid4(),
        static_factors={
            "popularity": 0.8,
            "uniqueness": 0.7,
            "accessibility": 0.9,
            "seasonal_relevance": 0.6,
            "creator_reputation": 0.75
        }
    )

def test_base_score_initialization(base_score_calculator: BaseScoreCalculator) -> None:
    """Teste l'initialisation du calculateur de score."""
    assert isinstance(base_score_calculator, BaseScoreCalculator)
    assert hasattr(base_score_calculator, "weights")
    assert len(base_score_calculator.weights) == 5
    assert all(0.0 <= w <= 1.0 for w in base_score_calculator.weights.values())

def test_base_score_calculation(
    base_score_calculator: BaseScoreCalculator,
    sample_input: BaseScoreInput
) -> None:
    """Teste le calcul du score de base."""
    result = base_score_calculator.calculate(sample_input)
    
    assert isinstance(result, BaseScoreOutput)
    assert isinstance(result.base_score, float)
    assert 0.0 <= result.base_score <= 1.0
    assert len(result.factor_contributions) == len(base_score_calculator.weights)
    assert all(0.0 <= v <= 1.0 for v in result.factor_contributions.values())

def test_base_score_with_empty_factors(base_score_calculator: BaseScoreCalculator) -> None:
    """Teste le calcul avec des facteurs vides."""
    input_data = BaseScoreInput(
        place_id=uuid4(),
        creator_id=uuid4()
    )
    
    result = base_score_calculator.calculate(input_data)
    assert result.base_score == 0.0
    assert all(v == 0.0 for v in result.factor_contributions.values())

def test_base_score_with_partial_factors(base_score_calculator: BaseScoreCalculator) -> None:
    """Teste le calcul avec des facteurs partiels."""
    input_data = BaseScoreInput(
        place_id=uuid4(),
        creator_id=uuid4(),
        static_factors={
            "popularity": 1.0,
            "uniqueness": 1.0
        }
    )
    
    result = base_score_calculator.calculate(input_data)
    assert 0.0 < result.base_score < 1.0
    assert result.factor_contributions["popularity"] > 0.0
    assert result.factor_contributions["uniqueness"] > 0.0
    assert result.factor_contributions["accessibility"] == 0.0

def test_weight_update(base_score_calculator: BaseScoreCalculator) -> None:
    """Teste la mise à jour des poids."""
    new_weights = {
        "popularity": 0.4,
        "uniqueness": 0.3
    }
    
    base_score_calculator.update_weights(new_weights)
    assert base_score_calculator.weights["popularity"] == 0.4
    assert base_score_calculator.weights["uniqueness"] == 0.3

def test_invalid_weight_update(base_score_calculator: BaseScoreCalculator) -> None:
    """Teste la validation des poids invalides."""
    invalid_weights = {
        "popularity": 1.5,  # Supérieur à 1
        "uniqueness": -0.1  # Inférieur à 0
    }
    
    with pytest.raises(ValueError):
        base_score_calculator.update_weights(invalid_weights) 