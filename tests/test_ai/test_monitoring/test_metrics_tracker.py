import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from ai.monitoring.metrics_tracker import MetricsTracker, MetricType
from ai.learning.data_collector import DataCollector

class AsyncCursorMock:
    def __init__(self, data):
        self.data = data
        self._sort_order = None

    def sort(self, field, direction):
        self._sort_order = (field, direction)
        return self

    async def to_list(self, length=None):
        if self._sort_order:
            field, direction = self._sort_order
            sorted_data = sorted(
                self.data,
                key=lambda x: x[field],
                reverse=(direction == -1)
            )
            return sorted_data
        return self.data

@pytest.fixture
def mock_data_collector():
    collector = AsyncMock(spec=DataCollector)
    collector.metrics_collection = AsyncMock()
    collector.metrics_collection.find = MagicMock()
    collector.metrics_collection.insert_one = AsyncMock()
    return collector

@pytest.fixture
def metrics_tracker(mock_data_collector):
    return MetricsTracker(
        data_collector=mock_data_collector,
        window_size_hours=24
    )

@pytest.mark.asyncio
async def test_metrics_tracker_initialization():
    """Teste l'initialisation du MetricsTracker."""
    collector = AsyncMock(spec=DataCollector)
    
    tracker = MetricsTracker(
        data_collector=collector,
        window_size_hours=12
    )
    
    assert tracker.window_size.total_seconds() == 12 * 3600
    assert isinstance(tracker.current_metrics, dict)
    assert isinstance(tracker.thresholds, dict)
    assert all(t in tracker.METRIC_TYPES for t in tracker.thresholds.keys())

@pytest.mark.asyncio
async def test_metrics_tracker_invalid_window():
    """Teste la validation de la taille de fenêtre."""
    collector = AsyncMock(spec=DataCollector)
    
    with pytest.raises(ValueError):
        MetricsTracker(
            data_collector=collector,
            window_size_hours=0
        )

@pytest.mark.asyncio
async def test_track_metric(metrics_tracker, mock_data_collector):
    """Teste l'enregistrement d'une métrique."""
    await metrics_tracker.track_metric(
        metric_type="accuracy",
        value=0.85,
        context={"model": "recommendation"}
    )
    
    mock_data_collector.metrics_collection.insert_one.assert_called_once()
    call_args = mock_data_collector.metrics_collection.insert_one.call_args[0][0]
    
    assert call_args["type"] == "accuracy"
    assert call_args["value"] == 0.85
    assert "timestamp" in call_args
    assert call_args["context"] == {"model": "recommendation"}

@pytest.mark.asyncio
async def test_track_metric_invalid_type(metrics_tracker):
    """Teste la validation du type de métrique."""
    with pytest.raises(ValueError):
        await metrics_tracker.track_metric(
            metric_type="invalid_type",  # type: ignore
            value=0.85
        )

@pytest.mark.asyncio
async def test_track_metric_invalid_value(metrics_tracker):
    """Teste la validation de la valeur de métrique."""
    with pytest.raises(ValueError):
        await metrics_tracker.track_metric(
            metric_type="accuracy",
            value="invalid"  # type: ignore
        )

@pytest.mark.asyncio
async def test_get_metric_history(metrics_tracker, mock_data_collector):
    """Teste la récupération de l'historique des métriques."""
    now = datetime.now(UTC)
    mock_metrics = [
        {
            "type": "accuracy",
            "value": 0.85,
            "timestamp": now
        },
        {
            "type": "accuracy",
            "value": 0.82,
            "timestamp": now - timedelta(hours=1)
        }
    ]
    
    mock_cursor = AsyncCursorMock(mock_metrics)
    mock_data_collector.metrics_collection.find.return_value = mock_cursor
    
    history = await metrics_tracker.get_metric_history("accuracy", hours=24)
    
    assert len(history) == 2
    assert all("value" in m for m in history)
    assert all("timestamp" in m for m in history)

@pytest.mark.asyncio
async def test_get_metric_history_invalid_type(metrics_tracker):
    """Teste la validation du type pour l'historique."""
    with pytest.raises(ValueError):
        await metrics_tracker.get_metric_history(
            metric_type="invalid_type",  # type: ignore
            hours=24
        )

@pytest.mark.asyncio
async def test_get_metric_history_invalid_hours(metrics_tracker):
    """Teste la validation des heures pour l'historique."""
    with pytest.raises(ValueError):
        await metrics_tracker.get_metric_history(
            metric_type="accuracy",
            hours=0
        )

@pytest.mark.asyncio
async def test_get_current_performance(metrics_tracker, mock_data_collector):
    """Teste la récupération des performances actuelles."""
    now = datetime.now(UTC)
    mock_metrics = [
        {
            "type": "accuracy",
            "value": 0.85,
            "timestamp": now
        },
        {
            "type": "response_time",
            "value": 1.5,
            "timestamp": now
        }
    ]
    
    mock_cursor = AsyncCursorMock(mock_metrics)
    mock_data_collector.metrics_collection.find.return_value = mock_cursor
    
    performance = await metrics_tracker.get_current_performance()
    
    assert isinstance(performance, dict)
    assert "accuracy" in performance
    assert "response_time" in performance
    assert all(isinstance(v, float) for v in performance.values())

@pytest.mark.asyncio
async def test_get_current_performance_empty(metrics_tracker, mock_data_collector):
    """Teste la récupération des performances sans données."""
    mock_cursor = AsyncCursorMock([])
    mock_data_collector.metrics_collection.find.return_value = mock_cursor
    
    performance = await metrics_tracker.get_current_performance()
    
    assert performance == metrics_tracker.current_metrics

@pytest.mark.asyncio
async def test_check_thresholds(metrics_tracker):
    """Teste la vérification des seuils."""
    # Configurer des métriques courantes
    metrics_tracker.current_metrics = {
        "accuracy": 0.9,  # Au-dessus du seuil
        "response_time": 1.5,  # En dessous du seuil (bon)
        "user_satisfaction": 3.5  # En dessous du seuil (mauvais)
    }
    
    status = metrics_tracker.check_thresholds()
    
    assert isinstance(status, dict)
    assert status["accuracy"] is True
    assert status["response_time"] is True
    assert status["user_satisfaction"] is False

@pytest.mark.asyncio
async def test_get_performance_summary(metrics_tracker, mock_data_collector):
    """Teste la génération du résumé des performances."""
    now = datetime.now(UTC)
    mock_metrics = [
        {
            "type": "accuracy",
            "value": 0.85,
            "timestamp": now
        },
        {
            "type": "accuracy",
            "value": 0.82,
            "timestamp": now - timedelta(hours=1)
        }
    ]
    
    mock_cursor = AsyncCursorMock(mock_metrics)
    mock_data_collector.metrics_collection.find.return_value = mock_cursor
    
    summary = await metrics_tracker.get_performance_summary()
    
    assert isinstance(summary, dict)
    if "accuracy" in summary:
        assert "mean" in summary["accuracy"]
        assert "std" in summary["accuracy"]
        assert "min" in summary["accuracy"]
        assert "max" in summary["accuracy"]
        assert "count" in summary["accuracy"]

@pytest.mark.asyncio
async def test_get_performance_summary_empty(metrics_tracker, mock_data_collector):
    """Teste la génération du résumé sans données."""
    mock_cursor = AsyncCursorMock([])
    mock_data_collector.metrics_collection.find.return_value = mock_cursor
    
    summary = await metrics_tracker.get_performance_summary()
    
    assert summary == {} 