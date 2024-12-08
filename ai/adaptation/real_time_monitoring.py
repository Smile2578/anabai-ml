"""Module de surveillance en temps réel des conditions."""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Set
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
import time
import psutil

from config.config_manager import ConfigManager
from data_feeds.external_data_manager import ExternalDataManager
from data_feeds.cache_manager import CacheManager
from ai.templates import ItineraryPlace
from ai.monitoring.metrics_tracker import MetricsTracker
from .context_handlers import (
    ContextChange,
    WeatherHandler,
    CrowdHandler,
    EventHandler
)

class MonitoringConfig(BaseModel):
    """Configuration du moniteur en temps réel."""
    model_config = ConfigDict(from_attributes=True)

    check_interval: int = Field(ge=30, le=3600)  # secondes
    weather_threshold: float = Field(ge=0.0, le=1.0)
    crowd_threshold: float = Field(ge=0.0, le=1.0)
    event_threshold: float = Field(ge=0.0, le=1.0)
    max_distance: float = Field(ge=0.0)  # mètres
    performance_check_interval: int = Field(ge=10, le=300)  # secondes

class MonitoringResult(BaseModel):
    """Résultat d'une vérification des conditions."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    changes: List[ContextChange]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requires_adaptation: bool = False
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

class RealTimeMonitor:
    """Moniteur en temps réel des conditions."""

    def __init__(self, metrics_tracker: MetricsTracker):
        """Initialise le moniteur."""
        self.config = ConfigManager()
        self.external_data = ExternalDataManager()
        self.cache = CacheManager()
        self.metrics_tracker = metrics_tracker
        self._load_config()
        self._init_handlers()
        self._monitored_places: Set[UUID] = set()
        self._last_performance_check = datetime.now(UTC)

    def _load_config(self) -> None:
        """Charge la configuration du moniteur."""
        self.monitoring_config = MonitoringConfig(
            check_interval=self.config.get(
                "monitoring.check_interval", 300
            ),
            weather_threshold=self.config.get(
                "monitoring.weather_threshold", 0.5
            ),
            crowd_threshold=self.config.get(
                "monitoring.crowd_threshold", 0.5
            ),
            event_threshold=self.config.get(
                "monitoring.event_threshold", 0.3
            ),
            max_distance=self.config.get(
                "monitoring.max_distance", 1000
            ),
            performance_check_interval=self.config.get(
                "monitoring.performance_check_interval", 30
            )
        )

    def _init_handlers(self) -> None:
        """Initialise les gestionnaires de contexte."""
        self.weather_handler = WeatherHandler()
        self.crowd_handler = CrowdHandler()
        self.event_handler = EventHandler()

    async def check_system_performance(self) -> Dict[str, float]:
        """
        Vérifie les métriques de performance système.
        """
        now = datetime.now(UTC)
        if (now - self._last_performance_check).total_seconds() < self.monitoring_config.performance_check_interval:
            return {}

        # Mesures système
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        performance_metrics = {
            "cpu_usage": cpu_percent / 100.0,
            "memory_usage": memory.percent / 100.0,
            "disk_usage": disk.percent / 100.0,
            "system_load": sum(psutil.getloadavg()) / 3.0 / psutil.cpu_count()
        }

        # Mise à jour des métriques Prometheus
        await self.metrics_tracker.update_system_load(performance_metrics["system_load"])

        self._last_performance_check = now
        return performance_metrics

    async def start_monitoring(self, place: ItineraryPlace) -> None:
        """Démarre la surveillance d'un lieu."""
        self._monitored_places.add(place.place_id)
        await self.metrics_tracker.track_metric(
            metric_type="adaptation_speed",
            value=1.0,
            context={"action": "start_monitoring", "place_id": str(place.place_id)}
        )

    async def stop_monitoring(self, place_id: UUID) -> None:
        """Arrête la surveillance d'un lieu."""
        self._monitored_places.discard(place_id)
        await self.metrics_tracker.track_metric(
            metric_type="adaptation_speed",
            value=1.0,
            context={"action": "stop_monitoring", "place_id": str(place_id)}
        )

    async def check_conditions(
        self,
        place: ItineraryPlace
    ) -> MonitoringResult:
        """Vérifie les conditions actuelles pour un lieu."""
        start_time = time.time()
        changes: List[ContextChange] = []
        requires_adaptation = False

        try:
            # Vérification des performances système
            performance_metrics = await self.check_system_performance()

            # Vérifie la météo
            weather_data = await self.external_data.get_weather_data(
                place.latitude,
                place.longitude
            )
            if weather_data:
                weather_change = ContextChange(
                    change_type="weather",
                    severity=weather_data.get("severity", 0.0),
                    location=(place.latitude, place.longitude),
                    details={
                        "rain": weather_data.get("rain", 0.0),
                        "wind": weather_data.get("wind", 0.0),
                        "temperature": weather_data.get("temperature", 0.0)
                    }
                )
                impact = await self.weather_handler.evaluate_impact(
                    place,
                    weather_change
                )
                if impact >= self.monitoring_config.weather_threshold:
                    changes.append(weather_change)
                    requires_adaptation = True

            # Vérifie l'affluence
            crowd_data = await self.external_data.get_crowd_data(
                place.place_id
            )
            if crowd_data:
                crowd_change = ContextChange(
                    change_type="crowd",
                    severity=crowd_data.get("severity", 0.0),
                    location=(place.latitude, place.longitude),
                    details={
                        "level": crowd_data.get("level", 0.0),
                        "wait_time": crowd_data.get("wait_time", 0.0)
                    }
                )
                impact = await self.crowd_handler.evaluate_impact(
                    place,
                    crowd_change
                )
                if impact >= self.monitoring_config.crowd_threshold:
                    changes.append(crowd_change)
                    requires_adaptation = True

            # Vérifie les événements
            events_data = await self.external_data.get_events_data(
                place.latitude,
                place.longitude,
                self.monitoring_config.max_distance
            )
            
            # Trouve l'événement le plus impactant
            max_event_impact = 0.0
            max_event_change = None
            
            for event in events_data:
                event_change = ContextChange(
                    change_type="event",
                    severity=event.get("severity", 0.0),
                    location=(
                        event.get("latitude", place.latitude),
                        event.get("longitude", place.longitude)
                    ),
                    details={
                        "size": event.get("size", 0.0),
                        "distance": event.get("distance", 0.0)
                    }
                )
                impact = await self.event_handler.evaluate_impact(
                    place,
                    event_change
                )
                if impact > max_event_impact:
                    max_event_impact = impact
                    max_event_change = event_change

            if max_event_impact >= self.monitoring_config.event_threshold:
                changes.append(max_event_change)
                requires_adaptation = True

            # Enregistrement des métriques de performance
            duration = time.time() - start_time
            await self.metrics_tracker.track_metric(
                metric_type="response_time",
                value=duration,
                context={"operation": "check_conditions", "place_id": str(place.place_id)}
            )

            return MonitoringResult(
                place_id=place.place_id,
                changes=changes,
                requires_adaptation=requires_adaptation,
                performance_metrics=performance_metrics
            )

        except Exception as e:
            await self.metrics_tracker.track_error(str(type(e).__name__))
            raise

    async def get_monitored_places(self) -> Set[UUID]:
        """Retourne l'ensemble des lieux surveillés."""
        return self._monitored_places.copy()

    async def clear_monitoring(self) -> None:
        """Arrête la surveillance de tous les lieux."""
        self._monitored_places.clear()
        await self.metrics_tracker.track_metric(
            metric_type="adaptation_speed",
            value=1.0,
            context={"action": "clear_monitoring"}
        ) 