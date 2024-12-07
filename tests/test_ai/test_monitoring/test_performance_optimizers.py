from datetime import datetime, UTC, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
import numpy as np
from ai.monitoring.performance_optimizers import PerformanceOptimizer

@pytest.fixture
def mock_metrics_tracker():
    tracker = AsyncMock()
    return tracker

@pytest.fixture
def performance_optimizer(mock_metrics_tracker):
    return PerformanceOptimizer(
        metrics_tracker=mock_metrics_tracker,
        min_improvement_threshold=0.1,
        test_duration_hours=24
    )

@pytest.mark.asyncio
async def test_identify_bottlenecks(performance_optimizer):
    # Simuler des métriques de temps de réponse élevées
    performance_optimizer.metrics_tracker.get_metric_history.return_value = [
        {"value": 2.5, "type": "response_time"},  # 2.5 secondes de temps de réponse
        {"value": 1.8, "type": "response_time"},
        {"value": 2.2, "type": "response_time"}
    ]
    
    bottlenecks = await performance_optimizer.identify_bottlenecks(hours=24)
    
    assert len(bottlenecks) > 0
    assert any(b["type"] == "response_time" for b in bottlenecks)
    assert all(b["current_value"] > 1.0 for b in bottlenecks if b["type"] == "response_time")

@pytest.mark.asyncio
async def test_propose_optimizations(performance_optimizer):
    bottlenecks = [
        {
            "type": "response_time",
            "severity": 0.8,
            "current_value": 2.5,
            "target_value": 0.5
        },
        {
            "type": "cpu_usage",
            "severity": 0.6,
            "current_value": 85.0,
            "target_value": 50.0
        }
    ]
    
    optimizations = await performance_optimizer.propose_optimizations(bottlenecks)
    
    assert len(optimizations) == 2
    assert optimizations[0]["type"] == "response_time"
    assert "action" in optimizations[0]
    assert "description" in optimizations[0]
    assert "expected_improvement" in optimizations[0]
    assert "priority" in optimizations[0]

@pytest.mark.asyncio
async def test_start_optimization_test(performance_optimizer):
    optimization = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Ajouter une couche de cache",
        "expected_improvement": 0.4
    }
    
    test_id = uuid4()
    test_data = await performance_optimizer.start_optimization_test(
        optimization=optimization,
        test_id=test_id
    )
    
    assert test_data["id"] == test_id
    assert test_data["type"] == optimization["type"]
    assert test_data["action"] == optimization["action"]
    assert test_data["status"] == "testing"
    assert test_data["actual_improvement"] == 0.0
    assert isinstance(test_data["start_time"], datetime)
    assert isinstance(test_data["end_time"], datetime)

@pytest.mark.asyncio
async def test_evaluate_optimization_success(performance_optimizer):
    # Préparer un test d'optimisation
    test_id = uuid4()
    optimization = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Ajouter une couche de cache",
        "expected_improvement": 0.4
    }
    await performance_optimizer.start_optimization_test(
        optimization=optimization,
        test_id=test_id
    )
    
    # Simuler des métriques avant/après
    performance_optimizer.metrics_tracker.get_metric_history.side_effect = [
        [{"value": 2.0}, {"value": 2.2}, {"value": 1.8}],  # Avant
        [{"value": 1.0}, {"value": 1.2}, {"value": 0.8}]   # Après
    ]
    
    # Avancer le temps pour que le test soit terminé
    test_data = performance_optimizer.active_optimizations[test_id]
    test_data["end_time"] = datetime.now(UTC) - timedelta(hours=1)
    
    result = await performance_optimizer.evaluate_optimization(test_id)
    
    assert result["status"] == "validated"
    assert result["actual_improvement"] > 0.1

@pytest.mark.asyncio
async def test_evaluate_optimization_failure(performance_optimizer):
    # Préparer un test d'optimisation
    test_id = uuid4()
    optimization = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Ajouter une couche de cache",
        "expected_improvement": 0.4
    }
    await performance_optimizer.start_optimization_test(
        optimization=optimization,
        test_id=test_id
    )
    
    # Simuler des métriques avant/après sans amélioration
    performance_optimizer.metrics_tracker.get_metric_history.side_effect = [
        [{"value": 2.0}, {"value": 2.2}, {"value": 1.8}],  # Avant
        [{"value": 2.1}, {"value": 2.3}, {"value": 1.9}]   # Après
    ]
    
    # Avancer le temps pour que le test soit terminé
    test_data = performance_optimizer.active_optimizations[test_id]
    test_data["end_time"] = datetime.now(UTC) - timedelta(hours=1)
    
    result = await performance_optimizer.evaluate_optimization(test_id)
    
    assert result["status"] == "rejected"
    assert result["actual_improvement"] < 0.1

@pytest.mark.asyncio
async def test_get_active_optimizations(performance_optimizer):
    # Ajouter quelques tests
    optimization1 = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Test 1",
        "expected_improvement": 0.4
    }
    optimization2 = {
        "type": "cpu_usage",
        "action": "add_worker",
        "description": "Test 2",
        "expected_improvement": 0.5
    }
    
    test1 = await performance_optimizer.start_optimization_test(optimization1)
    test2 = await performance_optimizer.start_optimization_test(optimization2)
    
    active_tests = await performance_optimizer.get_active_optimizations()
    
    assert len(active_tests) == 2
    assert any(t["id"] == test1["id"] for t in active_tests)
    assert any(t["id"] == test2["id"] for t in active_tests)

@pytest.mark.asyncio
async def test_get_optimization_history(performance_optimizer):
    # Ajouter des tests avec différents statuts
    optimization1 = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Test 1",
        "expected_improvement": 0.4
    }
    optimization2 = {
        "type": "cpu_usage",
        "action": "add_worker",
        "description": "Test 2",
        "expected_improvement": 0.5
    }
    
    test1 = await performance_optimizer.start_optimization_test(optimization1)
    test2 = await performance_optimizer.start_optimization_test(optimization2)
    
    # Marquer un test comme validé
    performance_optimizer.active_optimizations[test1["id"]]["status"] = "validated"
    
    # Récupérer l'historique filtré
    validated_tests = await performance_optimizer.get_optimization_history(
        status="validated"
    )
    testing_tests = await performance_optimizer.get_optimization_history(
        status="testing"
    )
    all_tests = await performance_optimizer.get_optimization_history()
    
    assert len(validated_tests) == 1
    assert len(testing_tests) == 1
    assert len(all_tests) == 2

def test_invalid_improvement_threshold():
    with pytest.raises(ValueError, match="Le seuil d'amélioration doit être entre 0 et 1"):
        PerformanceOptimizer(
            metrics_tracker=AsyncMock(),
            min_improvement_threshold=1.5
        )

def test_invalid_test_duration():
    with pytest.raises(ValueError, match="La durée de test doit être d'au moins 1 heure"):
        PerformanceOptimizer(
            metrics_tracker=AsyncMock(),
            test_duration_hours=0
        )

@pytest.mark.asyncio
async def test_evaluate_optimization_not_found(performance_optimizer):
    with pytest.raises(ValueError, match="Test d'optimisation non trouvé"):
        await performance_optimizer.evaluate_optimization(uuid4())

@pytest.mark.asyncio
async def test_evaluate_optimization_not_finished(performance_optimizer):
    # Préparer un test d'optimisation
    test_id = uuid4()
    optimization = {
        "type": "response_time",
        "action": "add_caching",
        "description": "Test en cours",
        "expected_improvement": 0.4
    }
    await performance_optimizer.start_optimization_test(
        optimization=optimization,
        test_id=test_id
    )
    
    with pytest.raises(ValueError, match="Le test n'est pas encore terminé"):
        await performance_optimizer.evaluate_optimization(test_id) 