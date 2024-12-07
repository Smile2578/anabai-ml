from datetime import datetime, UTC
from typing import Dict, List
import asyncio
import pytest
from uuid import uuid4

from config.observability import ObservabilityManager

class PerformanceScenario:
    """
    Classe de base pour les scénarios de test de performance.
    """
    def __init__(self, observability_manager: ObservabilityManager) -> None:
        self.observability = observability_manager
        self.results: List[Dict[str, float]] = []

    async def run(self, iterations: int) -> None:
        """
        Exécute le scénario pour un nombre donné d'itérations.
        """
        raise NotImplementedError()

    def get_metrics(self) -> Dict[str, float]:
        """
        Retourne les métriques du scénario.
        """
        if not self.results:
            return {}

        total_duration = sum(r["duration"] for r in self.results)
        avg_duration = total_duration / len(self.results)
        max_duration = max(r["duration"] for r in self.results)
        min_duration = min(r["duration"] for r in self.results)

        return {
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "max_duration": max_duration,
            "min_duration": min_duration,
            "iterations": len(self.results)
        }

class GenerateItineraryScenario(PerformanceScenario):
    """
    Scénario de test pour la génération d'itinéraires.
    """
    async def run(self, iterations: int) -> None:
        for _ in range(iterations):
            start_time = datetime.now(UTC)
            
            # Simuler une requête de génération
            await self.observability.track_request(
                endpoint="/generate",
                method="POST",
                status=200,
                duration=0.5  # Durée simulée
            )

            # Simuler le temps de prédiction du modèle
            await self.observability.track_model_prediction(
                model_type="signature",
                duration=0.3
            )

            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            self.results.append({
                "duration": duration,
                "timestamp": start_time.isoformat()
            })

            # Pause courte entre les itérations
            await asyncio.sleep(0.1)

class AdaptItineraryScenario(PerformanceScenario):
    """
    Scénario de test pour l'adaptation d'itinéraires.
    """
    async def run(self, iterations: int) -> None:
        for _ in range(iterations):
            start_time = datetime.now(UTC)
            
            # Simuler une requête d'adaptation
            await self.observability.track_request(
                endpoint="/adapt",
                method="POST",
                status=200,
                duration=0.2  # Durée simulée
            )

            # Simuler le temps de prédiction du modèle
            await self.observability.track_model_prediction(
                model_type="adaptation",
                duration=0.1
            )

            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            self.results.append({
                "duration": duration,
                "timestamp": start_time.isoformat()
            })

            # Pause courte entre les itérations
            await asyncio.sleep(0.05)

class ConcurrentUsersScenario(PerformanceScenario):
    """
    Scénario de test pour les utilisateurs concurrents.
    """
    async def simulate_user(self, user_id: str) -> None:
        """Simule l'activité d'un utilisateur."""
        start_time = datetime.now(UTC)

        # Simuler une séquence d'actions utilisateur
        await self.observability.track_request(
            endpoint="/generate",
            method="POST",
            status=200,
            duration=0.4
        )

        await asyncio.sleep(0.2)  # Pause utilisateur

        await self.observability.track_request(
            endpoint="/adapt",
            method="POST",
            status=200,
            duration=0.3
        )

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        self.results.append({
            "duration": duration,
            "user_id": user_id,
            "timestamp": start_time.isoformat()
        })

    async def run(self, iterations: int) -> None:
        """
        Lance plusieurs utilisateurs simultanés.
        """
        tasks = []
        for _ in range(iterations):
            user_id = str(uuid4())
            task = asyncio.create_task(self.simulate_user(user_id))
            tasks.append(task)

        await self.observability.update_active_users(len(tasks))
        await asyncio.gather(*tasks)
        await self.observability.update_active_users(0)

@pytest.fixture
def observability_manager():
    return ObservabilityManager()

@pytest.mark.asyncio
async def test_generate_itinerary_performance(observability_manager):
    """
    Teste les performances de la génération d'itinéraires.
    """
    scenario = GenerateItineraryScenario(observability_manager)
    await scenario.run(iterations=100)
    
    metrics = scenario.get_metrics()
    assert metrics["average_duration"] < 1.0  # Max 1 seconde en moyenne
    assert metrics["max_duration"] < 2.0      # Max 2 secondes au pire cas

@pytest.mark.asyncio
async def test_adapt_itinerary_performance(observability_manager):
    """
    Teste les performances de l'adaptation d'itinéraires.
    """
    scenario = AdaptItineraryScenario(observability_manager)
    await scenario.run(iterations=100)
    
    metrics = scenario.get_metrics()
    assert metrics["average_duration"] < 0.5  # Max 500ms en moyenne
    assert metrics["max_duration"] < 1.0      # Max 1 seconde au pire cas

@pytest.mark.asyncio
async def test_concurrent_users_performance(observability_manager):
    """
    Teste les performances avec des utilisateurs concurrents.
    """
    scenario = ConcurrentUsersScenario(observability_manager)
    await scenario.run(iterations=50)  # 50 utilisateurs simultanés
    
    metrics = scenario.get_metrics()
    assert metrics["average_duration"] < 2.0  # Max 2 secondes en moyenne
    assert metrics["max_duration"] < 5.0      # Max 5 secondes au pire cas 