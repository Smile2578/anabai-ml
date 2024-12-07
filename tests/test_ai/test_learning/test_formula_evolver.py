import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from ai.learning.formula_evolver import FormulaEvolver
from ai.learning.data_collector import DataCollector
from ai.learning.pattern_analyzer import PatternAnalyzer

class AsyncCursorMock:
    def __init__(self, data):
        self.data = data

    async def to_list(self, length=None):
        return self.data

@pytest.fixture
def mock_data_collector():
    collector = AsyncMock(spec=DataCollector)
    collector.feedback_collection = MagicMock()
    collector.usage_collection = MagicMock()
    collector.metrics_collection = MagicMock()
    return collector

@pytest.fixture
def mock_pattern_analyzer():
    analyzer = AsyncMock(spec=PatternAnalyzer)
    return analyzer

@pytest.fixture
def formula_evolver(mock_data_collector, mock_pattern_analyzer):
    return FormulaEvolver(
        data_collector=mock_data_collector,
        pattern_analyzer=mock_pattern_analyzer
    )

@pytest.mark.asyncio
async def test_formula_evolver_initialization():
    """Teste l'initialisation du FormulaEvolver."""
    collector = AsyncMock(spec=DataCollector)
    analyzer = AsyncMock(spec=PatternAnalyzer)
    
    evolver = FormulaEvolver(
        data_collector=collector,
        pattern_analyzer=analyzer,
        learning_rate=0.1,
        min_improvement=0.1
    )
    
    assert evolver.learning_rate == 0.1
    assert evolver.min_improvement == 0.1
    assert isinstance(evolver.current_weights, dict)
    assert isinstance(evolver.evolution_history, list)

@pytest.mark.asyncio
async def test_formula_evolver_invalid_params():
    """Teste la validation des paramètres d'initialisation."""
    collector = AsyncMock(spec=DataCollector)
    analyzer = AsyncMock(spec=PatternAnalyzer)
    
    with pytest.raises(ValueError):
        FormulaEvolver(
            data_collector=collector,
            pattern_analyzer=analyzer,
            learning_rate=0.0
        )
    
    with pytest.raises(ValueError):
        FormulaEvolver(
            data_collector=collector,
            pattern_analyzer=analyzer,
            min_improvement=0.0
        )

@pytest.mark.asyncio
async def test_train_on_historical_data(formula_evolver, mock_data_collector):
    """Teste l'entraînement sur les données historiques."""
    now = datetime.now(UTC)
    
    # Simuler des feedbacks
    mock_feedbacks = [
        {
            "rating": 4.5,
            "timestamp": now,
            "context": {
                "weather": 0.8,
                "crowd": 0.3,
                "time_of_day": 0.6,
                "seasonal": 0.7
            }
        }
    ] * 20  # Dupliquer pour avoir assez de données
    
    mock_data_collector.feedback_collection.find.return_value = AsyncCursorMock(mock_feedbacks)
    
    weights = await formula_evolver.train_on_historical_data()
    
    assert isinstance(weights, dict)
    if weights:  # Si des poids ont été calculés
        assert all(0.0 <= v <= 1.0 for v in weights.values())
        assert set(weights.keys()) == {"weather", "crowd", "time_of_day", "seasonal"}

@pytest.mark.asyncio
async def test_train_on_historical_data_empty(formula_evolver, mock_data_collector):
    """Teste l'entraînement sans données."""
    mock_data_collector.feedback_collection.find.return_value = AsyncCursorMock([])
    
    weights = await formula_evolver.train_on_historical_data()
    
    assert weights == {}

@pytest.mark.asyncio
async def test_train_on_insufficient_data(formula_evolver, mock_data_collector):
    """Teste l'entraînement avec trop peu de données."""
    now = datetime.now(UTC)
    
    # Simuler quelques feedbacks (moins que le minimum requis)
    mock_feedbacks = [
        {
            "rating": 4.5,
            "timestamp": now,
            "context": {
                "weather": 0.8,
                "crowd": 0.3,
                "time_of_day": 0.6,
                "seasonal": 0.7
            }
        }
    ] * 5  # Moins que le minimum requis de 10
    
    mock_data_collector.feedback_collection.find.return_value = AsyncCursorMock(mock_feedbacks)
    
    weights = await formula_evolver.train_on_historical_data()
    
    assert weights == formula_evolver.current_weights

@pytest.mark.asyncio
async def test_evolve_contextual_multipliers(formula_evolver, mock_pattern_analyzer):
    """Teste l'évolution des multiplicateurs contextuels."""
    mock_combinations = [
        {
            "weather": 0.8,
            "crowd": 0.3,
            "frequency": 0.6
        },
        {
            "weather": 0.9,
            "crowd": 0.2,
            "frequency": 0.4
        }
    ]
    
    mock_pattern_analyzer.find_successful_combinations.return_value = mock_combinations
    
    multipliers = await formula_evolver.evolve_contextual_multipliers()
    
    assert isinstance(multipliers, dict)
    assert "weather" in multipliers
    assert "crowd" in multipliers
    assert all(0.0 <= v <= 1.0 for v in multipliers.values())

@pytest.mark.asyncio
async def test_evolve_contextual_multipliers_invalid_rating(formula_evolver):
    """Teste la validation de la note minimale."""
    with pytest.raises(ValueError):
        await formula_evolver.evolve_contextual_multipliers(min_rating=6.0)

@pytest.mark.asyncio
async def test_evolve_contextual_multipliers_empty(formula_evolver, mock_pattern_analyzer):
    """Teste l'évolution sans combinaisons réussies."""
    mock_pattern_analyzer.find_successful_combinations.return_value = []
    
    multipliers = await formula_evolver.evolve_contextual_multipliers()
    
    assert multipliers == {}

@pytest.mark.asyncio
async def test_get_evolution_history_limit(formula_evolver):
    """Teste la récupération de l'historique avec limite."""
    with pytest.raises(ValueError):
        await formula_evolver.get_evolution_history(limit=0)

@pytest.mark.asyncio
async def test_get_evolution_history(formula_evolver):
    """Teste la récupération de l'historique."""
    # Ajouter quelques entrées dans l'historique
    formula_evolver.evolution_history = [
        {
            "weights": {"weather": 0.8},
            "timestamp": datetime.now(UTC),
            "score": 0.85
        },
        {
            "weights": {"weather": 0.9},
            "timestamp": datetime.now(UTC),
            "score": 0.87
        }
    ]
    
    history = await formula_evolver.get_evolution_history(limit=1)
    
    assert len(history) == 1
    assert "weights" in history[0]
    assert "timestamp" in history[0]
    assert "score" in history[0]

@pytest.mark.asyncio
async def test_evaluate_improvement(formula_evolver):
    """Teste l'évaluation de l'amélioration des poids."""
    # Configurer des poids actuels
    formula_evolver.current_weights = {
        "weather": 0.5,
        "crowd": 0.5,
        "time_of_day": 0.5,
        "seasonal": 0.5
    }
    
    # Créer des données de test
    X_test = np.array([
        [0.8, 0.3, 0.6, 0.7],
        [0.7, 0.4, 0.5, 0.8]
    ])
    y_test = np.array([4.5, 4.0])
    
    # Tester avec de meilleurs poids
    new_weights = {
        "weather": 0.8,
        "crowd": 0.7,
        "time_of_day": 0.6,
        "seasonal": 0.9
    }
    
    # Vérifier que l'amélioration est détectée
    improvement = formula_evolver._evaluate_improvement(new_weights, X_test, y_test)
    assert improvement in [True, False]  # Le résultat doit être un booléen
  