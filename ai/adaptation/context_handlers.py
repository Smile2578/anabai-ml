"""Module de gestion des différents types de changements de contexte."""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Protocol
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from ai.templates import ItineraryPlace
from config.config_manager import ConfigManager

class ContextChange(BaseModel):
    """Modèle pour un changement de contexte."""
    model_config = ConfigDict(from_attributes=True)

    change_type: str  # 'weather', 'crowd', 'event'
    severity: float = Field(ge=0.0, le=1.0)
    location: tuple[float, float]  # (latitude, longitude)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: Dict[str, float] = {}

class ContextHandler(Protocol):
    """Protocol pour les gestionnaires de contexte."""
    
    async def evaluate_impact(
        self,
        place: ItineraryPlace,
        change: ContextChange
    ) -> float:
        """Évalue l'impact d'un changement sur un lieu."""
        ...

    async def suggest_adaptation(
        self,
        place: ItineraryPlace,
        change: ContextChange,
        impact: float
    ) -> Optional[ItineraryPlace]:
        """Suggère une adaptation pour un lieu impacté."""
        ...

class WeatherHandler:
    """Gestionnaire des changements météorologiques."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du gestionnaire météo."""
        self.rain_threshold = self.config.get(
            "weather.rain_threshold", 0.5
        )
        self.wind_threshold = self.config.get(
            "weather.wind_threshold", 0.6
        )
        self.temp_range = self.config.get(
            "weather.temp_range", (-5, 35)
        )

    async def evaluate_impact(
        self,
        place: ItineraryPlace,
        change: ContextChange
    ) -> float:
        """Évalue l'impact de la météo sur un lieu."""
        if change.change_type != "weather":
            return 0.0

        # Calcule l'impact en fonction des différents facteurs météo
        rain_impact = change.details.get("rain", 0.0) * 1.0
        wind_impact = change.details.get("wind", 0.0) * 0.8
        temp_impact = change.details.get("temperature", 0.0) * 0.6
        
        # Combine les impacts avec des poids différents
        total_impact = max(
            rain_impact,
            wind_impact,
            temp_impact
        )

        return min(total_impact, 1.0)

    async def suggest_adaptation(
        self,
        place: ItineraryPlace,
        change: ContextChange,
        impact: float
    ) -> Optional[ItineraryPlace]:
        """Suggère une adaptation météo pour un lieu."""
        if impact < self.rain_threshold:
            return None

        # Crée une copie modifiée du lieu avec des ajustements
        adapted_place = place.model_copy()
        adapted_place.adjustments["weather_impact"] = impact
        
        # Ajoute des notes sur les conditions météo
        adapted_place.creator_notes += (
            f"\nConditions météo défavorables : "
            f"impact {impact:.2f}"
        )

        return adapted_place

class CrowdHandler:
    """Gestionnaire des niveaux d'affluence."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du gestionnaire d'affluence."""
        self.crowd_threshold = self.config.get(
            "crowd.threshold", 0.7
        )
        self.wait_time_limit = self.config.get(
            "crowd.wait_time_limit", 60
        )

    async def evaluate_impact(
        self,
        place: ItineraryPlace,
        change: ContextChange
    ) -> float:
        """Évalue l'impact de l'affluence sur un lieu."""
        if change.change_type != "crowd":
            return 0.0

        # Calcule l'impact en fonction du niveau de foule
        crowd_level = change.details.get("level", 0.0)
        wait_time = change.details.get("wait_time", 0.0)
        
        # Normalise le temps d'attente par rapport à la limite
        wait_impact = min(
            wait_time / self.wait_time_limit,
            1.0
        )

        # Combine les impacts
        return max(crowd_level, wait_impact)

    async def suggest_adaptation(
        self,
        place: ItineraryPlace,
        change: ContextChange,
        impact: float
    ) -> Optional[ItineraryPlace]:
        """Suggère une adaptation pour gérer l'affluence."""
        if impact < self.crowd_threshold:
            return None

        # Crée une copie modifiée du lieu
        adapted_place = place.model_copy()
        adapted_place.adjustments["crowd_impact"] = impact
        
        # Ajoute des notes sur l'affluence
        adapted_place.creator_notes += (
            f"\nForte affluence : "
            f"impact {impact:.2f}"
        )

        return adapted_place

class EventHandler:
    """Gestionnaire des événements locaux."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du gestionnaire d'événements."""
        self.event_threshold = self.config.get(
            "event.threshold", 0.3
        )
        self.distance_limit = self.config.get(
            "event.distance_limit", 1000
        )  # mètres

    async def evaluate_impact(
        self,
        place: ItineraryPlace,
        change: ContextChange
    ) -> float:
        """Évalue l'impact d'un événement sur un lieu."""
        if change.change_type != "event":
            return 0.0

        # Calcule l'impact en fonction de l'événement
        event_severity = change.severity
        event_size = change.details.get("size", 0.0)
        event_distance = change.details.get("distance", 0.0)
        
        # L'impact diminue avec la distance
        distance_factor = max(
            0.0,
            1.0 - (event_distance / self.distance_limit)
        )

        # Combine la sévérité, la taille et la distance
        return max(event_severity, event_size) * distance_factor

    async def suggest_adaptation(
        self,
        place: ItineraryPlace,
        change: ContextChange,
        impact: float
    ) -> Optional[ItineraryPlace]:
        """Suggère une adaptation pour tenir compte d'un événement."""
        if impact < self.event_threshold:
            return None

        # Crée une copie modifiée du lieu
        adapted_place = place.model_copy()
        adapted_place.adjustments["event_impact"] = impact
        
        # Ajoute des notes sur l'événement
        adapted_place.creator_notes += (
            f"\nÉvénement à proximité : "
            f"impact {impact:.2f}"
        )

        return adapted_place 