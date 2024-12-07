from datetime import datetime, UTC, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import numpy as np
import os
from dotenv import load_dotenv

from models.base_score import BaseScore
from models.contextual_score import ContextualScore
from models.recommendation import Recommendation, TemplateType
from ai.learning.data_collector import DataCollector
from ai.learning.pattern_analyzer import PatternAnalyzer
from ai.learning.formula_evolver import FormulaEvolver
from ai.monitoring.metrics_tracker import MetricsTracker
from ai.monitoring.feedback_integration import FeedbackIntegration
from ai.monitoring.performance_optimizers import PerformanceOptimizer

# Charger les variables d'environnement
load_dotenv()

@pytest.fixture
def mock_mongodb():
    """Mock pour MongoDB avec des collections asynchrones."""
    db = MagicMock()
    db.feedback_collection = AsyncMock()
    db.metrics_collection = AsyncMock()
    db.patterns_collection = AsyncMock()
    db.formulas_collection = AsyncMock()
    return db

@pytest.fixture
def mock_redis():
    """Mock pour Redis avec des op��rations asynchrones."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis

@pytest.fixture
async def setup_pipeline(mock_mongodb, mock_redis):
    """Configure le pipeline complet avec les composants mockés."""
    # Créer les composants
    data_collector = DataCollector(mongodb_uri=os.getenv("MONGODB_URI"))
    data_collector.client = mock_mongodb

    pattern_analyzer = PatternAnalyzer(
        data_collector=data_collector
    )

    formula_evolver = FormulaEvolver(
        data_collector=data_collector,
        pattern_analyzer=pattern_analyzer,
        min_improvement=0.1
    )

    metrics_tracker = MetricsTracker(
        data_collector=data_collector,
        window_size_hours=24
    )

    feedback_integration = FeedbackIntegration(
        data_collector=data_collector,
        metrics_tracker=metrics_tracker
    )

    performance_optimizer = PerformanceOptimizer(
        metrics_tracker=metrics_tracker
    )

    return {
        "data_collector": data_collector,
        "pattern_analyzer": pattern_analyzer,
        "formula_evolver": formula_evolver,
        "metrics_tracker": metrics_tracker,
        "feedback_integration": feedback_integration,
        "performance_optimizer": performance_optimizer
    }

@pytest.mark.asyncio
async def test_full_recommendation_cycle(setup_pipeline):
    """
    Teste un cycle complet de recommandation avec feedback et optimisation.
    """
    components = setup_pipeline

    # 1. Créer une recommandation
    recommendation = Recommendation(
        final_score=0.8,
        template_type=TemplateType.AI_PLUS,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.95,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        },
        creator_ids=[uuid4(), uuid4()]
    )

    # 2. Simuler des métriques
    for _ in range(5):
        await components["metrics_tracker"].track_metric(
            metric_type="response_time",
            value=0.5
        )

    # 3. Vérifier les métriques
    metrics = await components["metrics_tracker"].get_metric_history(
        metric_type="response_time",
        hours=1
    )
    assert len(metrics) > 0

@pytest.mark.asyncio
async def test_error_handling(setup_pipeline):
    """
    Teste la gestion des erreurs dans le pipeline.
    """
    components = setup_pipeline

    # 1. Tester la gestion des erreurs de base de données
    components["data_collector"].client.feedback_collection.insert_one.side_effect = Exception("DB Error")

    with pytest.raises(Exception):
        await components["data_collector"].collect_feedback(
            user_id=uuid4(),
            feedback_type="rating",
            content=4.5
        )

@pytest.mark.asyncio
async def test_concurrent_operations(setup_pipeline):
    """
    Teste les opérations concurrentes sur le pipeline.
    """
    components = setup_pipeline
    user_id = uuid4()

    # Simuler des opérations concurrentes
    async def collect_data():
        for _ in range(5):
            await components["data_collector"].collect_usage_data(
                user_id=user_id,
                action_type="view",
                data={"duration": 60}
            )

    async def track_metrics():
        for _ in range(5):
            await components["metrics_tracker"].track_metric(
                metric_type="response_time",
                value=0.5
            )

    async def process_feedback():
        for i in range(5):
            await components["feedback_integration"].process_feedback(
                feedback_type="rating",
                content=4.0 + (i * 0.2),
                user_id=user_id
            )

    # Exécuter les opérations en parallèle
    import asyncio
    await asyncio.gather(
        collect_data(),
        track_metrics(),
        process_feedback()
    )

    # Vérifier les résultats
    metrics = await components["metrics_tracker"].get_metric_history(
        metric_type="response_time",
        hours=1
    )
    assert len(metrics) > 0

@pytest.mark.asyncio
async def test_performance_monitoring(setup_pipeline):
    """
    Teste le monitoring des performances du pipeline.
    """
    components = setup_pipeline

    # 1. Simuler une charge de travail avec des métriques problématiques
    for _ in range(10):
        await components["metrics_tracker"].track_metric(
            metric_type="response_time",
            value=2.0  # Temps de réponse élevé
        )
        await components["metrics_tracker"].track_metric(
            metric_type="accuracy",
            value=0.7  # Précision faible
        )
        await components["metrics_tracker"].track_metric(
            metric_type="user_satisfaction",
            value=3.5  # Satisfaction utilisateur faible
        )

    # 2. Identifier les problèmes de performance
    bottlenecks = await components["performance_optimizer"].identify_bottlenecks(
        hours=1
    )

    # 3. Vérifier que les problèmes sont détectés
    assert len(bottlenecks) >= 2  # Au moins les problèmes critiques
    assert any(b["type"] == "response_time" and b["current_value"] > 1.0 for b in bottlenecks)
    assert any(b["type"] == "accuracy" and b["current_value"] < 0.8 for b in bottlenecks)
  