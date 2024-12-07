from datetime import datetime, UTC, timedelta
from typing import Dict, List, Literal, Tuple
from uuid import UUID
import numpy as np
from ai.monitoring.metrics_tracker import MetricsTracker

OptimizationType = Literal[
    "response_time",
    "memory_usage",
    "cpu_usage",
    "database_queries",
    "cache_hits"
]

OptimizationStatus = Literal[
    "proposed",
    "testing",
    "validated",
    "rejected"
]

class PerformanceOptimizer:
    """
    Identifie les goulots d'étranglement, propose des améliorations,
    teste des optimisations et valide leur impact.
    """

    OPTIMIZATION_TYPES: List[OptimizationType] = [
        "response_time",
        "memory_usage",
        "cpu_usage",
        "database_queries",
        "cache_hits"
    ]

    def __init__(
        self,
        metrics_tracker: MetricsTracker,
        min_improvement_threshold: float = 0.1,
        test_duration_hours: int = 24
    ) -> None:
        if not 0.0 <= min_improvement_threshold <= 1.0:
            raise ValueError("Le seuil d'amélioration doit être entre 0 et 1")
        if test_duration_hours < 1:
            raise ValueError("La durée de test doit être d'au moins 1 heure")

        self.metrics_tracker = metrics_tracker
        self.min_improvement_threshold = min_improvement_threshold
        self.test_duration_hours = test_duration_hours
        self.active_optimizations: Dict[UUID, Dict[str, float | str | datetime]] = {}

    async def identify_bottlenecks(
        self,
        hours: int = 24
    ) -> List[Dict[str, float | str]]:
        """
        Analyse les métriques pour identifier les goulots d'étranglement.
        """
        if hours < 1:
            raise ValueError("La période d'analyse doit être d'au moins 1 heure")

        bottlenecks = []
        
        # Analyser les temps de réponse
        response_times = await self.metrics_tracker.get_metric_history(
            metric_type="response_time",
            hours=hours
        )
        if response_times:
            avg_response_time = float(np.mean([m["value"] for m in response_times]))
            if avg_response_time > 1.0:  # Plus d'1 seconde en moyenne
                bottlenecks.append({
                    "type": "response_time",
                    "severity": min(1.0, avg_response_time / 5.0),
                    "current_value": avg_response_time,
                    "target_value": 0.5
                })

        # Analyser la précision
        accuracy = await self.metrics_tracker.get_metric_history(
            metric_type="accuracy",
            hours=hours
        )
        if accuracy:
            avg_accuracy = float(np.mean([m["value"] for m in accuracy]))
            if avg_accuracy < 0.8:  # Moins de 80% de précision
                bottlenecks.append({
                    "type": "accuracy",
                    "severity": min(1.0, (0.8 - avg_accuracy) / 0.8),
                    "current_value": avg_accuracy,
                    "target_value": 0.9
                })

        # Analyser la satisfaction utilisateur
        satisfaction = await self.metrics_tracker.get_metric_history(
            metric_type="user_satisfaction",
            hours=hours
        )
        if satisfaction:
            avg_satisfaction = float(np.mean([m["value"] for m in satisfaction]))
            if avg_satisfaction < 4.0:  # Moins de 4/5 de satisfaction
                bottlenecks.append({
                    "type": "user_satisfaction",
                    "severity": min(1.0, (4.0 - avg_satisfaction) / 4.0),
                    "current_value": avg_satisfaction,
                    "target_value": 4.5
                })

        return sorted(
            bottlenecks,
            key=lambda x: float(x["severity"]),
            reverse=True
        )

    async def propose_optimizations(
        self,
        bottlenecks: List[Dict[str, float | str]]
    ) -> List[Dict[str, str | float]]:
        """
        Propose des optimisations basées sur les goulots d'étranglement identifiés.
        """
        optimizations = []
        
        for bottleneck in bottlenecks:
            bottleneck_type = str(bottleneck["type"])
            severity = float(bottleneck["severity"])
            
            if bottleneck_type == "response_time":
                if severity > 0.7:
                    optimizations.append({
                        "type": "response_time",
                        "action": "add_caching",
                        "description": "Ajouter une couche de cache pour les requêtes fréquentes",
                        "expected_improvement": 0.4,
                        "priority": "high"
                    })
                else:
                    optimizations.append({
                        "type": "response_time",
                        "action": "optimize_queries",
                        "description": "Optimiser les requêtes les plus lentes",
                        "expected_improvement": 0.2,
                        "priority": "medium"
                    })
            
            elif bottleneck_type == "cpu_usage":
                if severity > 0.7:
                    optimizations.append({
                        "type": "cpu_usage",
                        "action": "add_worker",
                        "description": "Ajouter un worker pour distribuer la charge",
                        "expected_improvement": 0.5,
                        "priority": "high"
                    })
                else:
                    optimizations.append({
                        "type": "cpu_usage",
                        "action": "optimize_algorithms",
                        "description": "Optimiser les algorithmes gourmands en CPU",
                        "expected_improvement": 0.3,
                        "priority": "medium"
                    })
            
            elif bottleneck_type == "database_queries":
                if severity > 0.7:
                    optimizations.append({
                        "type": "database_queries",
                        "action": "add_indexes",
                        "description": "Ajouter des index sur les champs fréquemment utilisés",
                        "expected_improvement": 0.6,
                        "priority": "high"
                    })
                else:
                    optimizations.append({
                        "type": "database_queries",
                        "action": "batch_queries",
                        "description": "Regrouper les requêtes similaires",
                        "expected_improvement": 0.3,
                        "priority": "medium"
                    })
            
            elif bottleneck_type == "cache_hits":
                if severity > 0.7:
                    optimizations.append({
                        "type": "cache_hits",
                        "action": "increase_cache",
                        "description": "Augmenter la taille du cache et sa durée de vie",
                        "expected_improvement": 0.4,
                        "priority": "high"
                    })
                else:
                    optimizations.append({
                        "type": "cache_hits",
                        "action": "preload_cache",
                        "description": "Précharger les données fréquemment utilisées",
                        "expected_improvement": 0.2,
                        "priority": "medium"
                    })

        return sorted(
            optimizations,
            key=lambda x: float(x["expected_improvement"]),
            reverse=True
        )

    async def start_optimization_test(
        self,
        optimization: Dict[str, str | float],
        test_id: UUID | None = None
    ) -> Dict[str, float | str | datetime]:
        """
        Démarre un test d'optimisation et suit ses résultats.
        """
        if not test_id:
            from uuid import uuid4
            test_id = uuid4()

        test_data = {
            "id": test_id,
            "type": optimization["type"],
            "action": optimization["action"],
            "description": optimization["description"],
            "expected_improvement": float(optimization["expected_improvement"]),
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC) + timedelta(hours=self.test_duration_hours),
            "status": "testing",
            "actual_improvement": 0.0
        }
        
        self.active_optimizations[test_id] = test_data
        return test_data

    async def evaluate_optimization(
        self,
        test_id: UUID
    ) -> Dict[str, float | str | datetime]:
        """
        Évalue les résultats d'une optimisation après la période de test.
        """
        if test_id not in self.active_optimizations:
            raise ValueError("Test d'optimisation non trouvé")

        test_data = self.active_optimizations[test_id]
        if datetime.now(UTC) < test_data["end_time"]:
            raise ValueError("Le test n'est pas encore terminé")

        # Récupérer les métriques avant et après l'optimisation
        before_metrics = await self.metrics_tracker.get_metric_history(
            metric_type=str(test_data["type"]),
            hours=self.test_duration_hours,
            end_time=test_data["start_time"]
        )
        
        after_metrics = await self.metrics_tracker.get_metric_history(
            metric_type=str(test_data["type"]),
            hours=self.test_duration_hours,
            start_time=test_data["start_time"]
        )

        if not before_metrics or not after_metrics:
            test_data["status"] = "rejected"
            test_data["actual_improvement"] = 0.0
            return test_data

        # Calculer l'amélioration
        before_avg = float(np.mean([m["value"] for m in before_metrics]))
        after_avg = float(np.mean([m["value"] for m in after_metrics]))
        
        if str(test_data["type"]) in ["response_time", "cpu_usage", "database_queries"]:
            improvement = (before_avg - after_avg) / before_avg
        else:  # cache_hits
            improvement = (after_avg - before_avg) / (1.0 - before_avg)

        test_data["actual_improvement"] = max(0.0, improvement)
        test_data["status"] = (
            "validated" if improvement >= self.min_improvement_threshold
            else "rejected"
        )

        return test_data

    async def get_active_optimizations(
        self
    ) -> List[Dict[str, float | str | datetime]]:
        """
        Retourne la liste des optimisations en cours de test.
        """
        return [
            test_data for test_data in self.active_optimizations.values()
            if test_data["status"] == "testing"
        ]

    async def get_optimization_history(
        self,
        status: OptimizationStatus | None = None
    ) -> List[Dict[str, float | str | datetime]]:
        """
        Retourne l'historique des optimisations avec leur statut.
        """
        if status:
            return [
                test_data for test_data in self.active_optimizations.values()
                if test_data["status"] == status
            ]
        return list(self.active_optimizations.values()) 