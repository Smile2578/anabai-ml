from datetime import datetime, UTC, timedelta
from typing import Dict, List, Literal
from uuid import UUID
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from ai.learning.data_collector import DataCollector
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

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
        window_size_hours: int = 24,
        registry: CollectorRegistry | None = None
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

        # Initialisation des métriques Prometheus
        self.registry = registry or CollectorRegistry()
        
        # Compteurs
        self.request_counter = Counter(
            'anabai_requests_total',
            'Nombre total de requêtes',
            registry=self.registry
        )
        self.error_counter = Counter(
            'anabai_errors_total',
            'Nombre total d\'erreurs',
            ['error_type'],
            registry=self.registry
        )

        # Histogrammes
        self.response_time_histogram = Histogram(
            'anabai_response_time_seconds',
            'Distribution des temps de réponse',
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        self.score_histogram = Histogram(
            'anabai_score_distribution',
            'Distribution des scores',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )

        # Jauges
        self.active_users = Gauge(
            'anabai_active_users',
            'Nombre d\'utilisateurs actifs',
            registry=self.registry
        )
        self.system_load = Gauge(
            'anabai_system_load',
            'Charge système',
            registry=self.registry
        )

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

        # Stockage MongoDB
        metric_data = {
            "type": metric_type,
            "value": float(value),
            "context": context or {},
            "timestamp": datetime.now(UTC)
        }
        await self.data_collector.metrics_collection.insert_one(metric_data)
        self.current_metrics[metric_type] = value

        # Mise à jour des métriques Prometheus
        if metric_type == "response_time":
            self.response_time_histogram.observe(value)
        elif metric_type == "accuracy":
            self.score_histogram.observe(value)

    async def track_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration: float
    ) -> None:
        """
        Suit une requête HTTP.
        """
        self.request_counter.inc()
        self.response_time_histogram.observe(duration)
        
        if status >= 400:
            self.error_counter.labels(error_type=f"http_{status}").inc()

    async def track_error(self, error_type: str) -> None:
        """
        Enregistre une erreur.
        """
        self.error_counter.labels(error_type=error_type).inc()

    async def update_active_users(self, count: int) -> None:
        """
        Met à jour le nombre d'utilisateurs actifs.
        """
        self.active_users.set(count)

    async def update_system_load(self, load: float) -> None:
        """
        Met à jour la charge système.
        """
        self.system_load.set(load)

    def get_prometheus_metrics(self) -> Dict[str, float]:
        """
        Récupère les métriques Prometheus actuelles.
        """
        return {
            "total_requests": self.request_counter._value.get(),
            "total_errors": sum(
                counter._value.get()
                for counter in self.error_counter._metrics.values()
            ),
            "active_users": self.active_users._value.get(),
            "system_load": self.system_load._value.get()
        }

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