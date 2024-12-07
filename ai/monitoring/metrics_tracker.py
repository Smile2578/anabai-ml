from datetime import datetime, UTC, timedelta
from typing import Dict, List, Literal
from uuid import UUID
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from ai.learning.data_collector import DataCollector

MetricType = Literal[
    "accuracy",
    "response_time",
    "user_satisfaction",
    "recommendation_diversity",
    "adaptation_speed"
]

class MetricsTracker:
    """
    Suit les indicateurs clés de performance (temps de réponse, taux de satisfaction,
    uptime) pour s'assurer de la qualité du service.
    """

    METRIC_TYPES: List[MetricType] = [
        "accuracy",
        "response_time",
        "user_satisfaction",
        "recommendation_diversity",
        "adaptation_speed"
    ]

    def __init__(
        self,
        data_collector: DataCollector,
        window_size_hours: int = 24
    ) -> None:
        if window_size_hours < 1:
            raise ValueError("La taille de la fenêtre doit être d'au moins 1 heure")

        self.data_collector = data_collector
        self.window_size = timedelta(hours=window_size_hours)
        self.current_metrics: Dict[str, float] = {}
        self.thresholds: Dict[str, float] = {
            "accuracy": 0.8,
            "response_time": 2.0,  # secondes
            "user_satisfaction": 4.0,  # sur 5
            "recommendation_diversity": 0.7,
            "adaptation_speed": 0.9
        }

    async def track_metric(
        self,
        metric_type: MetricType,
        value: float,
        context: Dict[str, float] | None = None
    ) -> None:
        """
        Enregistre une nouvelle mesure de métrique.
        """
        if metric_type not in self.METRIC_TYPES:
            raise ValueError(f"Type de métrique invalide : {metric_type}")

        if not isinstance(value, (int, float)):
            raise ValueError("La valeur doit être numérique")

        metric_data = {
            "type": metric_type,
            "value": float(value),
            "context": context or {},
            "timestamp": datetime.now(UTC)
        }

        await self.data_collector.metrics_collection.insert_one(metric_data)
        self.current_metrics[metric_type] = value

    async def get_metric_history(
        self,
        metric_type: MetricType,
        hours: int = 24
    ) -> List[Dict[str, float]]:
        """
        Récupère l'historique d'une métrique sur une période donnée.
        """
        if metric_type not in self.METRIC_TYPES:
            raise ValueError(f"Type de métrique invalide : {metric_type}")

        if hours < 1:
            raise ValueError("La période doit être d'au moins 1 heure")

        cutoff_date = datetime.now(UTC) - timedelta(hours=hours)
        
        cursor = self.data_collector.metrics_collection.find({
            "type": metric_type,
            "timestamp": {"$gte": cutoff_date}
        }).sort("timestamp", -1)

        return await cursor.to_list(length=1000)

    async def get_current_performance(self) -> Dict[str, float]:
        """
        Calcule les métriques de performance actuelles.
        """
        now = datetime.now(UTC)
        cutoff_date = now - self.window_size
        
        # Récupérer toutes les métriques récentes
        cursor = self.data_collector.metrics_collection.find({
            "timestamp": {"$gte": cutoff_date}
        })
        metrics = await cursor.to_list(length=None)

        if not metrics:
            return self.current_metrics

        # Calculer les moyennes par type
        performance: Dict[str, List[float]] = {}
        for metric in metrics:
            metric_type = metric["type"]
            if metric_type not in performance:
                performance[metric_type] = []
            performance[metric_type].append(metric["value"])

        # Mettre à jour les métriques courantes
        for metric_type, values in performance.items():
            self.current_metrics[metric_type] = float(np.mean(values))

        return self.current_metrics

    def check_thresholds(self) -> Dict[str, bool]:
        """
        Vérifie si les métriques actuelles respectent les seuils définis.
        """
        status = {}
        for metric_type, threshold in self.thresholds.items():
            if metric_type in self.current_metrics:
                value = self.current_metrics[metric_type]
                # Pour le temps de réponse, plus bas est meilleur
                if metric_type == "response_time":
                    status[metric_type] = value <= threshold
                else:
                    status[metric_type] = value >= threshold
            else:
                status[metric_type] = False
        return status

    async def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Génère un résumé des performances avec statistiques.
        """
        now = datetime.now(UTC)
        cutoff_date = now - self.window_size
        
        cursor = self.data_collector.metrics_collection.find({
            "timestamp": {"$gte": cutoff_date}
        })
        metrics = await cursor.to_list(length=None)

        if not metrics:
            return {}

        summary = {}
        for metric_type in self.METRIC_TYPES:
            values = [
                m["value"] for m in metrics
                if m["type"] == metric_type
            ]
            
            if values:
                summary[metric_type] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "count": len(values)
                }

        return summary 