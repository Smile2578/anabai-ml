from datetime import datetime, UTC
from typing import Dict, List
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY

@dataclass
class MetricsConfig:
    """Configuration des métriques de monitoring."""
    enabled: bool = True
    export_interval_seconds: int = 15
    retention_days: int = 30

@dataclass
class AlertConfig:
    """Configuration des alertes."""
    threshold_response_time_ms: float = 1000.0
    threshold_error_rate: float = 0.01
    threshold_memory_usage: float = 0.85
    alert_cooldown_minutes: int = 15

@dataclass
class TracingConfig:
    """Configuration du traçage distribué."""
    enabled: bool = True
    sample_rate: float = 0.1
    max_spans_per_trace: int = 100

class ObservabilityManager:
    """
    Gère la configuration et l'initialisation des outils d'observabilité.
    """

    def __init__(
        self,
        metrics_config: MetricsConfig | None = None,
        alert_config: AlertConfig | None = None,
        tracing_config: TracingConfig | None = None,
        registry: CollectorRegistry | None = None
    ) -> None:
        self.metrics_config = metrics_config or MetricsConfig()
        self.alert_config = alert_config or AlertConfig()
        self.tracing_config = tracing_config or TracingConfig()
        self.registry = registry or REGISTRY

        # Métriques Prometheus
        self.request_counter = Counter(
            'anabai_requests_total',
            'Nombre total de requêtes',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )

        self.response_time = Histogram(
            'anabai_response_time_seconds',
            'Temps de réponse des requêtes',
            ['endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )

        self.memory_usage = Gauge(
            'anabai_memory_usage_bytes',
            'Utilisation mémoire du processus',
            registry=self.registry
        )

        self.active_users = Gauge(
            'anabai_active_users',
            'Nombre d\'utilisateurs actifs',
            registry=self.registry
        )

        self.model_prediction_time = Histogram(
            'anabai_model_prediction_seconds',
            'Temps de prédiction du modèle',
            ['model_type'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0],
            registry=self.registry
        )

        # Compteurs internes pour le suivi des erreurs
        self._error_counters: Dict[str, Dict[str, int]] = {}
        self.last_alert_time: Dict[str, datetime] = {}

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
            status=str(status)
        ).inc()

        self.response_time.labels(
            endpoint=endpoint
        ).observe(duration)

        # Mise à jour des compteurs internes
        if endpoint not in self._error_counters:
            self._error_counters[endpoint] = {"total": 0, "errors": 0}
        
        self._error_counters[endpoint]["total"] += 1
        if status >= 500:
            self._error_counters[endpoint]["errors"] += 1

        # Vérification des alertes
        await self.check_alerts(endpoint, duration, status)

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

    async def update_memory_usage(self, bytes_used: int) -> None:
        """
        Met à jour l'utilisation mémoire.
        """
        self.memory_usage.set(bytes_used)

        # Vérification de l'alerte mémoire
        if bytes_used > self.alert_config.threshold_memory_usage:
            await self.trigger_alert(
                "memory_usage",
                f"Utilisation mémoire élevée : {bytes_used:.2f}%"
            )

    async def update_active_users(self, count: int) -> None:
        """
        Met à jour le nombre d'utilisateurs actifs.
        """
        self.active_users.set(count)

    async def check_alerts(
        self,
        endpoint: str,
        duration: float,
        status: int
    ) -> None:
        """
        Vérifie si des alertes doivent être déclenchées.
        """
        # Alerte temps de réponse
        if duration * 1000 > self.alert_config.threshold_response_time_ms:
            await self.trigger_alert(
                "response_time",
                f"Temps de réponse élevé sur {endpoint}: {duration*1000:.2f}ms"
            )

        # Alerte taux d'erreur
        if status >= 500:
            counters = self._error_counters.get(endpoint, {"total": 0, "errors": 0})
            if counters["total"] > 0:
                error_rate = counters["errors"] / counters["total"]
                if error_rate > self.alert_config.threshold_error_rate:
                    await self.trigger_alert(
                        "error_rate",
                        f"Taux d'erreur élevé sur {endpoint}: {error_rate*100:.2f}%"
                    )

    async def trigger_alert(self, alert_type: str, message: str) -> None:
        """
        Déclenche une alerte si le cooldown est passé.
        """
        now = datetime.now(UTC)
        last_alert = self.last_alert_time.get(alert_type)

        if not last_alert or (
            now - last_alert
        ).total_seconds() > self.alert_config.alert_cooldown_minutes * 60:
            # TODO: Intégrer avec un système d'alerting externe
            print(f"ALERTE - {now}: {message}")
            self.last_alert_time[alert_type] = now

    def get_metrics_snapshot(self) -> Dict[str, float]:
        """
        Retourne un snapshot des métriques actuelles.
        """
        total_requests = 0
        response_time_sum = 0.0
        memory_usage_value = 0.0
        active_users_value = 0.0
        model_prediction_time_sum = 0.0

        # Collecter les métriques du registre
        for metric in self.registry.collect():
            if metric.name == "anabai_requests_total":
                for sample in metric.samples:
                    total_requests += sample.value
            elif metric.name == "anabai_response_time_seconds":
                for sample in metric.samples:
                    if sample.name.endswith("_sum"):
                        response_time_sum += sample.value
            elif metric.name == "anabai_memory_usage_bytes":
                for sample in metric.samples:
                    memory_usage_value = sample.value
            elif metric.name == "anabai_active_users":
                for sample in metric.samples:
                    active_users_value = sample.value
            elif metric.name == "anabai_model_prediction_seconds":
                for sample in metric.samples:
                    if sample.name.endswith("_sum"):
                        model_prediction_time_sum += sample.value

        # Ajouter les compteurs internes
        total_requests_internal = sum(
            counters["total"] for counters in self._error_counters.values()
        )

        return {
            "requests_total": float(total_requests_internal or total_requests),
            "average_response_time": float(response_time_sum),
            "memory_usage": float(memory_usage_value),
            "active_users": float(active_users_value),
            "model_prediction_time": float(model_prediction_time_sum)
        } 