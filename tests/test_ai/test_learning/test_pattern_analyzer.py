import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from ai.learning.pattern_analyzer import PatternAnalyzer
from ai.learning.data_collector import DataCollector

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
def pattern_analyzer(mock_data_collector):
    return PatternAnalyzer(mock_data_collector)

@pytest.mark.asyncio
async def test_analyze_user_preferences(pattern_analyzer, mock_data_collector):
    """Teste l'analyse des préférences utilisateur."""
    user_id = uuid4()
    now = datetime.now(UTC)
    
    # Simuler des feedbacks
    mock_feedbacks = [
        {
            "rating": 4.5,
            "timestamp": now,
            "context": {"weather": 0.8, "crowd": 0.3}
        },
        {
            "rating": 3.0,
            "timestamp": now - timedelta(days=1),
            "context": {"weather": 0.4, "crowd": 0.7}
        }
    ]
    
    mock_data_collector.get_user_feedback_history.return_value = mock_feedbacks
    
    correlations = await pattern_analyzer.analyze_user_preferences(user_id)
    
    assert isinstance(correlations, dict)
    assert "weather" in correlations
    assert "crowd" in correlations
    assert all(-1.0 <= v <= 1.0 for v in correlations.values())

@pytest.mark.asyncio
async def test_analyze_user_preferences_empty(pattern_analyzer, mock_data_collector):
    """Teste l'analyse avec aucun feedback."""
    mock_data_collector.get_user_feedback_history.return_value = []
    
    correlations = await pattern_analyzer.analyze_user_preferences(uuid4())
    
    assert correlations == {}

@pytest.mark.asyncio
async def test_detect_usage_patterns(pattern_analyzer, mock_data_collector):
    """Teste la détection des patterns d'utilisation."""
    now = datetime.now(UTC)
    
    # Simuler des données d'utilisation
    mock_usage_data = [
        {
            "data": {"duration": 120.5, "clicks": 5},
            "timestamp": now
        },
        {
            "data": {"duration": 90.0, "clicks": 3},
            "timestamp": now - timedelta(hours=1)
        }
    ]
    
    # Configurer le mock pour retourner un curseur simulé
    mock_cursor = AsyncCursorMock(mock_usage_data)
    mock_data_collector.usage_collection.find = MagicMock(return_value=mock_cursor)
    
    patterns = await pattern_analyzer.detect_usage_patterns()
    
    assert isinstance(patterns, list)
    if patterns:  # Si des patterns sont trouvés
        assert all(isinstance(p, dict) for p in patterns)
        assert all("cluster_id" in p for p in patterns)
        assert all("size" in p for p in patterns)
        assert all("mean_values" in p for p in patterns)

@pytest.mark.asyncio
async def test_detect_usage_patterns_empty(pattern_analyzer, mock_data_collector):
    """Teste la détection des patterns avec aucune donnée."""
    # Configurer le mock pour retourner un curseur vide
    mock_cursor = AsyncCursorMock([])
    mock_data_collector.usage_collection.find = MagicMock(return_value=mock_cursor)
    
    patterns = await pattern_analyzer.detect_usage_patterns()
    
    assert patterns == []

@pytest.mark.asyncio
async def test_find_successful_combinations(pattern_analyzer, mock_data_collector):
    """Teste l'identification des combinaisons réussies."""
    # Simuler des feedbacks positifs
    mock_feedbacks = [
        {
            "rating": 4.5,
            "context": {"weather": 0.8, "crowd": 0.3}
        },
        {
            "rating": 4.8,
            "context": {"weather": 0.9, "crowd": 0.2}
        },
        {
            "rating": 4.2,
            "context": {"weather": 0.7, "crowd": 0.4}
        }
    ] * 2  # Dupliquer pour avoir assez d'échantillons

    # Configurer le mock pour retourner un curseur simulé
    mock_cursor = AsyncCursorMock(mock_feedbacks)
    mock_data_collector.feedback_collection.find = MagicMock(return_value=mock_cursor)
    
    combinations = await pattern_analyzer.find_successful_combinations()
    
    assert isinstance(combinations, list)
    if combinations:  # Si des combinaisons sont trouvées
        assert all(isinstance(c, dict) for c in combinations)
        assert all("weather" in c for c in combinations)
        assert all("crowd" in c for c in combinations)
        assert all("frequency" in c for c in combinations)

@pytest.mark.asyncio
async def test_find_successful_combinations_insufficient_data(pattern_analyzer, mock_data_collector):
    """Teste avec un nombre insuffisant d'échantillons."""
    # Configurer le mock pour retourner un curseur avec un seul feedback
    mock_cursor = AsyncCursorMock([{
        "rating": 4.5,
        "context": {"weather": 0.8, "crowd": 0.3}
    }])
    mock_data_collector.feedback_collection.find = MagicMock(return_value=mock_cursor)
    
    combinations = await pattern_analyzer.find_successful_combinations(min_samples=5)
    
    assert combinations == [] 