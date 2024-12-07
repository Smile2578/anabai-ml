import pytest
from datetime import datetime, UTC
from prometheus_client import CollectorRegistry
from config.observability import ObservabilityManager

@pytest.fixture
def registry():
    """Fixture pour créer un registre Prometheus unique par test."""
    return CollectorRegistry()

@pytest.fixture
def observability_manager(registry):
    """Fixture pour créer un gestionnaire d'observabilité."""
    return ObservabilityManager(registry=registry)

@pytest.mark.asyncio
async def test_track_request(observability_manager):
    """Teste l'enregistrement d'une requête."""
    await observability_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.5
    )

    metrics = observability_manager.get_metrics()
    assert metrics["total_requests"] > 0
    assert metrics["average_response_time"] > 0

@pytest.mark.asyncio
async def test_track_model_prediction(observability_manager):
    """Teste l'enregistrement d'une prédiction de modèle."""
    await observability_manager.track_model_prediction(
        model_type="signature",
        duration=0.1
    )

    # Vérifier que la métrique a été enregistrée via le registry
    for metric in observability_manager.registry.collect():
        if metric.name == "anabai_model_prediction_time":
            assert len(metric.samples) > 0
            break

@pytest.mark.asyncio
async def test_track_error(observability_manager):
    """Teste l'enregistrement d'une erreur."""
    await observability_manager.track_error("validation_error")

    metrics = observability_manager.get_metrics()
    assert metrics["total_errors"] > 0

@pytest.mark.asyncio
async def test_active_users_tracking(observability_manager):
    """Teste le suivi des utilisateurs actifs."""
    await observability_manager.update_active_users(100)
    
    metrics = observability_manager.get_metrics()
    assert metrics["active_users"] == 100

@pytest.mark.asyncio
async def test_metrics_collection(observability_manager):
    """Teste la collecte complète des métriques."""
    # Générer des données de test
    await observability_manager.track_request(
        endpoint="/generate",
        method="POST",
        status=200,
        duration=0.3
    )
    await observability_manager.track_error("validation_error")
    await observability_manager.update_active_users(50)
    await observability_manager.track_model_prediction(
        model_type="signature",
        duration=0.2
    )

    metrics = observability_manager.get_metrics()
    
    # Vérifier toutes les métriques
    assert metrics["total_requests"] > 0
    assert metrics["average_response_time"] > 0
    assert metrics["active_users"] == 50
    assert metrics["total_errors"] > 0

@pytest.mark.asyncio
async def test_multiple_requests(observability_manager):
    """Teste l'enregistrement de plusieurs requêtes."""
    for _ in range(5):
        await observability_manager.track_request(
            endpoint="/generate",
            method="POST",
            status=200,
            duration=0.1
        )

    metrics = observability_manager.get_metrics()
    assert metrics["total_requests"] == 5 