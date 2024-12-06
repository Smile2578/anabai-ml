"""Tests pour le module de calcul des multiplicateurs contextuels."""

import pytest
from uuid import uuid4
from datetime import datetime
from ai.scoring.contextual_multipliers import (
    WeatherContext,
    TimeContext,
    CrowdContext,
    ContextualMultiplierInput,
    ContextualMultiplierOutput,
    ContextualMultiplierCalculator
)

@pytest.fixture
def multiplier_calculator() -> ContextualMultiplierCalculator:
    """Fixture pour créer une instance du calculateur."""
    return ContextualMultiplierCalculator()

@pytest.fixture
def optimal_weather() -> WeatherContext:
    """Fixture pour créer un contexte météo optimal."""
    return WeatherContext(
        condition="sunny",
        temperature=22.0,
        precipitation_probability=0.0,
        is_extreme=False
    )

@pytest.fixture
def optimal_time() -> TimeContext:
    """Fixture pour créer un contexte temporel optimal."""
    return TimeContext(
        hour=14,
        day_of_week=2,  # Mercredi
        is_holiday=False,
        season="spring"
    )

@pytest.fixture
def optimal_crowd() -> CrowdContext:
    """Fixture pour créer un contexte de fréquentation optimal."""
    return CrowdContext(
        current_occupancy=0.3,
        expected_occupancy=0.4,
        has_special_event=False,
        queue_time=10
    )

@pytest.fixture
def sample_input(
    optimal_weather: WeatherContext,
    optimal_time: TimeContext,
    optimal_crowd: CrowdContext
) -> ContextualMultiplierInput:
    """Fixture pour créer un exemple de données d'entrée."""
    return ContextualMultiplierInput(
        place_id=uuid4(),
        base_score=0.8,
        weather=optimal_weather,
        time=optimal_time,
        crowd=optimal_crowd,
        place_preferences={
            "cultural": 0.9,
            "outdoor": 0.8
        }
    )

def test_multiplier_initialization(multiplier_calculator: ContextualMultiplierCalculator):
    """Teste l'initialisation du calculateur."""
    assert isinstance(multiplier_calculator, ContextualMultiplierCalculator)
    assert hasattr(multiplier_calculator, "weights")
    assert len(multiplier_calculator.weights) == 3
    assert abs(sum(multiplier_calculator.weights.values()) - 1.0) < 0.001

def test_optimal_conditions(
    multiplier_calculator: ContextualMultiplierCalculator,
    sample_input: ContextualMultiplierInput
):
    """Teste le calcul avec des conditions optimales."""
    result = multiplier_calculator.calculate(sample_input)
    
    assert isinstance(result, ContextualMultiplierOutput)
    assert result.final_score >= sample_input.base_score  # Le score devrait augmenter
    assert all(0.8 <= m <= 1.2 for m in result.multipliers.values())
    assert not result.adjustments  # Pas d'ajustements négatifs

def test_extreme_weather(multiplier_calculator: ContextualMultiplierCalculator, sample_input: ContextualMultiplierInput):
    """Teste le calcul avec des conditions météo extrêmes."""
    sample_input.weather.is_extreme = True
    sample_input.weather.temperature = 38.0
    
    result = multiplier_calculator.calculate(sample_input)
    assert result.multipliers["weather"] == 0.8  # Normalisé à 0.8 minimum
    assert "weather" in result.adjustments

def test_peak_hours(multiplier_calculator: ContextualMultiplierCalculator, sample_input: ContextualMultiplierInput):
    """Teste le calcul pendant les heures de pointe."""
    sample_input.time.hour = 8  # Heure de pointe
    sample_input.time.is_holiday = True
    sample_input.crowd.current_occupancy = 0.9
    
    result = multiplier_calculator.calculate(sample_input)
    assert result.multipliers["time"] <= 0.85  # Valeur minimale garantie
    assert result.multipliers["crowd"] <= 0.85  # Valeur minimale garantie
    assert "time" in result.adjustments
    assert "crowd" in result.adjustments

def test_preference_bonus(multiplier_calculator: ContextualMultiplierCalculator, sample_input: ContextualMultiplierInput):
    """Teste l'application du bonus de préférences."""
    base_result = multiplier_calculator.calculate(sample_input)
    
    # Ajout de plus de préférences
    sample_input.place_preferences["historical"] = 1.0
    sample_input.place_preferences["photography"] = 1.0
    
    bonus_result = multiplier_calculator.calculate(sample_input)
    assert bonus_result.final_score > base_result.final_score

def test_weight_update(multiplier_calculator: ContextualMultiplierCalculator):
    """Teste la mise à jour des poids."""
    new_weights = {
        "weather": 0.4,
        "time": 0.3,
        "crowd": 0.3
    }
    
    multiplier_calculator.update_weights(new_weights)
    assert multiplier_calculator.weights == new_weights

def test_invalid_weights(multiplier_calculator: ContextualMultiplierCalculator):
    """Teste la validation des poids invalides."""
    # Test avec des poids > 1
    invalid_weights = {
        "weather": 1.5,
        "time": 0.3,
        "crowd": 0.2
    }
    with pytest.raises(ValueError):
        multiplier_calculator.update_weights(invalid_weights)
    
    # Test avec une somme != 1
    invalid_weights = {
        "weather": 0.2,
        "time": 0.2,
        "crowd": 0.2
    }
    with pytest.raises(ValueError):
        multiplier_calculator.update_weights(invalid_weights)

def test_queue_time_impact(multiplier_calculator: ContextualMultiplierCalculator, sample_input: ContextualMultiplierInput):
    """Teste l'impact du temps d'attente."""
    # Test avec un temps d'attente court
    sample_input.crowd.queue_time = 15
    short_queue_result = multiplier_calculator.calculate(sample_input)
    
    # Test avec un temps d'attente long
    sample_input.crowd.queue_time = 90
    long_queue_result = multiplier_calculator.calculate(sample_input)
    
    # Le temps d'attente court devrait maintenir un score normal
    assert short_queue_result.multipliers["crowd"] >= 0.85
    # Le temps d'attente long devrait avoir un impact négatif
    assert long_queue_result.multipliers["crowd"] == 0.8
    # Le temps d'attente long devrait générer un ajustement
    assert "crowd" in long_queue_result.adjustments

def test_seasonal_variations(multiplier_calculator: ContextualMultiplierCalculator, sample_input: ContextualMultiplierInput):
    """Teste les variations saisonnières."""
    # Test printemps (optimal)
    sample_input.time.season = "spring"
    spring_result = multiplier_calculator.calculate(sample_input)
    
    # Test été (moins optimal)
    sample_input.time.season = "summer"
    summer_result = multiplier_calculator.calculate(sample_input)
    
    # Test automne
    sample_input.time.season = "autumn"
    autumn_result = multiplier_calculator.calculate(sample_input)
    
    # Test hiver (le moins optimal)
    sample_input.time.season = "winter"
    winter_result = multiplier_calculator.calculate(sample_input)
    
    # Vérification de l'ordre des scores
    assert spring_result.multipliers["time"] >= summer_result.multipliers["time"]
    assert autumn_result.multipliers["time"] >= winter_result.multipliers["time"] 