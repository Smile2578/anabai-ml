"""Module de gestion des adaptations d'itinéraires en temps réel."""

from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager
from ai.templates import ItineraryPlace

class AdaptationDecision(BaseModel):
    """Modèle pour une décision d'adaptation."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    action: str  # 'skip', 'reschedule', 'replace'
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternative_place_id: Optional[UUID] = None
    new_time: Optional[datetime] = None
    impact_score: float = Field(ge=0.0, le=1.0)

class AdaptationResult(BaseModel):
    """Modèle pour le résultat d'une adaptation."""
    model_config = ConfigDict(from_attributes=True)

    original_places: List[ItineraryPlace]
    adapted_places: List[ItineraryPlace]
    decisions: List[AdaptationDecision]
    total_impact: float = Field(ge=0.0, le=1.0)
    adaptation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class AdaptationEngine:
    """Moteur d'adaptation des itinéraires en temps réel."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du moteur d'adaptation."""
        self.min_confidence = self.config.get(
            "adaptation.min_confidence", 0.7
        )
        self.max_impact = self.config.get(
            "adaptation.max_impact", 0.5
        )
        self.reschedule_threshold = self.config.get(
            "adaptation.reschedule_threshold", 0.3
        )
        self.skip_threshold = self.config.get(
            "adaptation.skip_threshold", 0.7
        )

    def _get_condition_weight(self, condition: str) -> float:
        """Retourne le poids d'une condition pour le calcul d'impact."""
        weights = {
            "weather": 1.0,
            "crowd": 0.8,
            "event": 0.6,
            "accessibility": 0.4
        }
        return weights.get(condition, 0.1)

    async def evaluate_conditions(
        self,
        place: ItineraryPlace,
        current_conditions: Dict[str, float]
    ) -> Tuple[float, str]:
        """Évalue l'impact des conditions sur un lieu."""
        if not current_conditions:
            return 0.0, "no_conditions"

        total_impact = 0.0
        primary_reason = ""
        max_impact = 0.0

        for condition, severity in current_conditions.items():
            weight = self._get_condition_weight(condition)
            weighted_impact = severity * weight
            if weighted_impact > max_impact:
                max_impact = weighted_impact
                primary_reason = condition
            total_impact += weighted_impact

        # Normalise l'impact total
        total_conditions = len(current_conditions)
        max_weight = max(self._get_condition_weight(c) for c in current_conditions)
        normalized_impact = total_impact / (total_conditions * max_weight)

        return normalized_impact, primary_reason

    async def decide_adaptation(
        self,
        place: ItineraryPlace,
        impact: float,
        reason: str
    ) -> AdaptationDecision:
        """Décide de l'action d'adaptation appropriée."""
        if impact >= self.skip_threshold:
            return AdaptationDecision(
                place_id=place.place_id,
                action="skip",
                reason=f"Impact {reason} trop élevé",
                confidence=min(impact + 0.1, 1.0),
                impact_score=impact
            )
        elif impact >= self.reschedule_threshold:
            return AdaptationDecision(
                place_id=place.place_id,
                action="reschedule",
                reason=f"Impact {reason} modéré",
                confidence=impact,
                impact_score=impact,
                new_time=self._calculate_new_time(place)
            )
        else:
            return AdaptationDecision(
                place_id=place.place_id,
                action="monitor",
                reason=f"Impact {reason} faible",
                confidence=1.0 - impact,
                impact_score=impact
            )

    def _calculate_new_time(self, place: ItineraryPlace) -> datetime:
        """Calcule un nouveau créneau horaire pour un lieu."""
        # Pour les tests, on décale de 2 heures
        new_time = place.recommended_time + timedelta(hours=2)
        return new_time

    async def adapt_itinerary(
        self,
        places: List[ItineraryPlace],
        conditions: Dict[str, Dict[str, float]]
    ) -> AdaptationResult:
        """Adapte un itinéraire en fonction des conditions actuelles."""
        decisions = []
        adapted_places = []
        total_impact = 0.0

        for place in places:
            # Évalue les conditions pour ce lieu
            place_conditions = conditions.get(str(place.place_id), {})
            impact, reason = await self.evaluate_conditions(place, place_conditions)
            
            # Prend une décision d'adaptation
            decision = await self.decide_adaptation(place, impact, reason)
            decisions.append(decision)
            total_impact = max(total_impact, impact)

            # Applique la décision
            if decision.action == "skip":
                continue
            elif decision.action == "reschedule":
                adapted_place = place.model_copy()
                adapted_place.recommended_time = decision.new_time
                adapted_places.append(adapted_place)
            else:
                adapted_places.append(place)

        return AdaptationResult(
            original_places=places,
            adapted_places=adapted_places,
            decisions=decisions,
            total_impact=total_impact
        ) 