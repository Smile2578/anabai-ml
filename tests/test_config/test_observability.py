import pytest
from datetime import datetime, UTC, timedelta
from prometheus_client import CollectorRegistry
from config.observability import (
    ObservabilityManager,
    MetricsConfig,
    AlertConfig,
    TracingConfig
)

@pytest.fixture
def registry():
    """Fixture pour créer un registre Prometheus unique par test."""
    return CollectorRegistry()

@pytest.fixture
def observability_manager(registry):
    """Fixture pour créer un gestionnaire d'observabilité avec config par défaut."""
    return ObservabilityManager(registry=registry)

@pytest.fixture
def custom_config_manager(registry):
    """Fixture pour créer un gestionnaire avec config personnalisée."""
    metrics_config = MetricsConfig(
        enabled=True,
        export_interval_seconds=30,
        retention_days=15
    )
    alert_config = AlertConfig(
        threshold_response_time_ms=500.0,
        threshold_error_rate=0.05,
        threshold_memory_usage=0.75,
        alert_cooldown_minutes=5
    )
    tracing_config = TracingConfig(
        enabled=True,
        sample_rate=0.2,
        max_spans_per_trace=50
    )
    return ObservabilityManager(
        metrics_config=metrics_config,
        alert_config=alert_config,
        tracing_config=tracing_config,
        registry=registry
    )

@pytest.mark.asyncio
async def test_track_request(observability_manager):
    """Teste l'enregistrement d'une requête."""
    await observability_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.5
    )

    metrics = observability_manager.get_metrics_snapshot()
    assert metrics["requests_total"] > 0
    assert metrics["average_response_time"] > 0

@pytest.mark.asyncio
async def test_track_model_prediction(observability_manager):
    """Teste l'enregistrement d'une prédiction de modèle."""
    await observability_manager.track_model_prediction(
        model_type="signature",
        duration=0.1
    )

    metrics = observability_manager.get_metrics_snapshot()
    assert metrics["model_prediction_time"] > 0

@pytest.mark.asyncio
async def test_memory_usage_alert(custom_config_manager):
    """Teste le déclenchement d'une alerte mémoire."""
    # Simuler une utilisation mémoire élevée (80%)
    await custom_config_manager.update_memory_usage(0.8)

    metrics = custom_config_manager.get_metrics_snapshot()
    assert metrics["memory_usage"] == 0.8
    # L'alerte devrait être déclenchée car > 75%
    assert "memory_usage" in custom_config_manager.last_alert_time

@pytest.mark.asyncio
async def test_error_rate_alert(custom_config_manager):
    """Teste le déclenchement d'une alerte de taux d'erreur."""
    # Simuler des erreurs
    for _ in range(10):
        await custom_config_manager.track_request(
            endpoint="/generate",
            method="POST",
            status=500,
            duration=0.1
        )

    assert "error_rate" in custom_config_manager.last_alert_time

@pytest.mark.asyncio
async def test_response_time_alert(custom_config_manager):
    """Teste le déclenchement d'une alerte de temps de réponse."""
    # Simuler une requête lente (600ms > 500ms seuil)
    await custom_config_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.6
    )

    assert "response_time" in custom_config_manager.last_alert_time

@pytest.mark.asyncio
async def test_alert_cooldown(custom_config_manager):
    """Teste le cooldown des alertes."""
    # Première alerte
    await custom_config_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.6
    )

    first_alert_time = custom_config_manager.last_alert_time["response_time"]

    # Deuxième alerte immédiate (ne devrait pas déclencher)
    await custom_config_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.6
    )

    assert custom_config_manager.last_alert_time["response_time"] == first_alert_time

@pytest.mark.asyncio
async def test_active_users_tracking(observability_manager):
    """Teste le suivi des utilisateurs actifs."""
    await observability_manager.update_active_users(100)
    
    metrics = observability_manager.get_metrics_snapshot()
    assert metrics["active_users"] == 100

@pytest.mark.asyncio
async def test_metrics_snapshot(observability_manager):
    """Teste la génération d'un snapshot de métriques."""
    # Générer quelques données
    await observability_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.3
    )
    await observability_manager.update_memory_usage(0.5)
    await observability_manager.update_active_users(50)

    metrics = observability_manager.get_metrics_snapshot()
    
    assert "requests_total" in metrics
    assert "average_response_time" in metrics
    assert "memory_usage" in metrics
    assert "active_users" in metrics
    assert metrics["active_users"] == 50
    assert metrics["memory_usage"] == 0.5 