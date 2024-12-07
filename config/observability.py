from datetime import datetime, UTC
from typing import Dict, List
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

class ObservabilityManager:
    """
    Gère l'observabilité de l'application avec Prometheus.
    """
    
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """
        Initialise le gestionnaire d'observabilité.
        
        Args:
            registry: Registry Prometheus personnalisé. Si None, utilise le registry par défaut.
        """
        self.registry = registry or CollectorRegistry()
        
        # Compteur de requêtes
        self.request_counter = Counter(
            'anabai_requests',
            'Nombre total de requêtes',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        # Histogramme des temps de réponse
        self.response_time = Histogram(
            'anabai_response_time',
            'Temps de réponse des requêtes',
            ['endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        # Gauge pour les utilisateurs actifs
        self.active_users = Gauge(
            'anabai_active_users',
            'Nombre d\'utilisateurs actifs',
            registry=self.registry
        )
        
        # Histogramme pour les prédictions du modèle
        self.model_prediction_time = Histogram(
            'anabai_model_prediction_time',
            'Temps de prédiction du modèle',
            ['model_type'],
            buckets=[0.1, 0.3, 0.5, 1.0, 2.0],
            registry=self.registry
        )
        
        # Compteur d'erreurs
        self.error_counter = Counter(
            'anabai_errors',
            'Nombre total d\'erreurs',
            ['type'],
            registry=self.registry
        )

    async def track_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration: float
    ) -> None:
        """
        Enregistre une requête et son temps de réponse.
        """
        self.request_counter.labels(
            endpoint=endpoint,
            method=method,
            status=status
        ).inc()
        
        self.response_time.labels(
            endpoint=endpoint
        ).observe(duration)

    async def track_model_prediction(
        self,
        model_type: str,
        duration: float
    ) -> None:
        """
        Enregistre le temps de prédiction d'un modèle.
        """
        self.model_prediction_time.labels(
            model_type=model_type
        ).observe(duration)

    async def track_error(self, error_type: str) -> None:
        """
        Enregistre une erreur.
        """
        self.error_counter.labels(
            type=error_type
        ).inc()

    async def update_active_users(self, count: int) -> None:
        """
        Met à jour le nombre d'utilisateurs actifs.
        """
        self.active_users.set(count)

    def get_metrics(self) -> Dict[str, float]:
        """
        Retourne toutes les métriques actuelles.
        """
        total_requests = 0
        total_errors = 0
        response_time_sum = 0
        active_users_value = 0

        for metric in self.registry.collect():
            if metric.name == "anabai_requests":
                for sample in metric.samples:
                    if sample.name.endswith("_total"):
                        total_requests += sample.value
            elif metric.name == "anabai_response_time":
                for sample in metric.samples:
                    if sample.name.endswith("_sum"):
                        response_time_sum += sample.value
            elif metric.name == "anabai_active_users":
                for sample in metric.samples:
                    active_users_value = sample.value
            elif metric.name == "anabai_errors":
                for sample in metric.samples:
                    if sample.name.endswith("_total"):
                        total_errors += sample.value

        return {
            'total_requests': total_requests,
            'average_response_time': response_time_sum,
            'active_users': active_users_value,
            'total_errors': total_errors
        } 