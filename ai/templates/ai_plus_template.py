"""Module de génération d'itinéraires combinant recommandations humaines et IA."""

from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager
from ai.scoring.base_score import BaseScoreCalculator
from ai.scoring.creator_score import CreatorScoreCalculator
from ai.scoring.place_score import PlaceScoreCalculator
from ai.scoring.contextual_multipliers import ContextualMultiplierCalculator
from .signature_template import ItineraryPlace
from .fusion_template import FusionTemplate

class AIRecommendation(BaseModel):
    """Modèle pour une recommandation de l'IA."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    similarity_score: Optional[float] = None
    diversity_score: Optional[float] = None

class AIPlusItinerary(BaseModel):
    """Modèle pour un itinéraire enrichi par l'IA."""
    model_config = ConfigDict(from_attributes=True)

    itinerary_id: UUID
    creator_ids: List[UUID]
    creator_names: List[str]
    creator_expertises: List[List[str]]
    places: List[ItineraryPlace]
    ai_recommendations: List[AIRecommendation]
    total_duration: int  # en minutes
    total_distance: float  # en kilomètres
    creation_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score: float = Field(ge=0.0, le=1.0)
    fusion_weights: Dict[UUID, float]  # Poids de chaque créateur
    ai_weight: float = Field(ge=0.0, le=1.0)  # Poids des recommandations IA

class AIPlusTemplate:
    """Générateur d'itinéraires enrichis par l'IA."""

    def __init__(self):
        self.config = ConfigManager()
        self.base_scorer = BaseScoreCalculator()
        self.creator_scorer = CreatorScoreCalculator()
        self.place_scorer = PlaceScoreCalculator()
        self.context_scorer = ContextualMultiplierCalculator()
        self.fusion_template = FusionTemplate()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du template."""
        self.max_places = self.config.get("templates.ai_plus.max_places", 12)
        self.min_places = self.config.get("templates.ai_plus.min_places", 5)
        self.max_duration = self.config.get("templates.ai_plus.max_duration", 720)  # 12 heures
        self.min_duration = self.config.get("templates.ai_plus.min_duration", 300)  # 5 heures
        self.min_creators = self.config.get("templates.ai_plus.min_creators", 2)
        self.max_creators = self.config.get("templates.ai_plus.max_creators", 5)
        self.ai_weight = self.config.get("templates.ai_plus.ai_weight", 0.3)
        self.min_confidence = self.config.get("templates.ai_plus.min_confidence", 0.6)

    async def generate(
        self,
        creator_ids: List[UUID],
        preferences: Dict[str, float],
        start_time: datetime,
        duration: Optional[int] = None,
        excluded_places: Optional[List[UUID]] = None,
        user_history: Optional[List[Dict]] = None
    ) -> AIPlusItinerary:
        """Génère un itinéraire enrichi par l'IA."""
        # Validation des paramètres
        if len(creator_ids) < self.min_creators:
            raise ValueError(f"Au moins {self.min_creators} créateurs sont requis")
        if len(creator_ids) > self.max_creators:
            raise ValueError(f"Maximum {self.max_creators} créateurs autorisés")

        if duration:
            if duration < self.min_duration or duration > self.max_duration:
                raise ValueError(f"La durée doit être entre {self.min_duration} et {self.max_duration} minutes")
        else:
            duration = self.max_duration

        excluded_places = excluded_places or []
        user_history = user_history or []

        # Génération de l'itinéraire de base avec le template de fusion
        base_itinerary = await self.fusion_template.generate(
            creator_ids=creator_ids,
            preferences=preferences,
            start_time=start_time,
            duration=duration * 0.8,  # Réserve 20% pour les recommandations IA
            excluded_places=excluded_places
        )

        # Génération des recommandations IA
        ai_recommendations = await self._generate_ai_recommendations(
            base_itinerary=base_itinerary,
            preferences=preferences,
            user_history=user_history,
            excluded_places=excluded_places + [p.place_id for p in base_itinerary.places]
        )

        # Fusion des recommandations
        final_places = await self._merge_recommendations(
            base_places=base_itinerary.places,
            ai_recommendations=ai_recommendations,
            duration=duration,
            start_time=start_time
        )

        # Réorganisation des horaires
        current_time = start_time
        for place in final_places:
            place.recommended_time = current_time
            current_time += timedelta(minutes=place.visit_duration)

        # Calcul du score final
        final_score = self._calculate_final_score(
            base_score=base_itinerary.score,
            ai_recommendations=ai_recommendations,
            final_places=final_places
        )

        # Construction de l'objet itinéraire
        return AIPlusItinerary(
            itinerary_id=uuid4(),
            creator_ids=base_itinerary.creator_ids,
            creator_names=base_itinerary.creator_names,
            creator_expertises=base_itinerary.creator_expertises,
            places=final_places,
            ai_recommendations=ai_recommendations,
            total_duration=sum(place.visit_duration for place in final_places),
            total_distance=self._calculate_total_distance(final_places),
            score=final_score,
            fusion_weights=base_itinerary.fusion_weights,
            ai_weight=self.ai_weight
        )

    async def _generate_ai_recommendations(
        self,
        base_itinerary: AIPlusItinerary,
        preferences: Dict[str, float],
        user_history: List[Dict],
        excluded_places: List[UUID]
    ) -> List[AIRecommendation]:
        """Génère des recommandations basées sur l'IA."""
        # Pour les tests, nous générons des recommandations factices
        recommendations = []
        mock_places = [
            {
                "place_id": uuid4(),
                "name": "Temple Zen",
                "description": "Un temple paisible pour la méditation",
                "visit_duration": 60,
                "categories": ["temples", "spiritualité"],
                "confidence": 0.85,
                "reasoning": "Correspond aux préférences spirituelles de l'utilisateur"
            },
            {
                "place_id": uuid4(),
                "name": "Café Traditionnel",
                "description": "Un café servant des pâtisseries locales",
                "visit_duration": 45,
                "categories": ["gastronomie", "culture"],
                "confidence": 0.75,
                "reasoning": "Complète bien la visite du temple voisin"
            }
        ]

        for place in mock_places:
            if place["place_id"] not in excluded_places:
                recommendations.append(AIRecommendation(
                    place_id=place["place_id"],
                    confidence_score=place["confidence"],
                    reasoning=place["reasoning"],
                    similarity_score=0.8,
                    diversity_score=0.7
                ))

        return recommendations

    async def _merge_recommendations(
        self,
        base_places: List[ItineraryPlace],
        ai_recommendations: List[AIRecommendation],
        duration: int,
        start_time: datetime
    ) -> List[ItineraryPlace]:
        """Fusionne les recommandations de base avec celles de l'IA."""
        # Conversion des recommandations IA en lieux
        ai_places = []
        
        for rec in ai_recommendations:
            if rec.confidence_score >= self.min_confidence:
                ai_places.append(ItineraryPlace(
                    place_id=rec.place_id,
                    name="Lieu recommandé par IA",
                    description="Description générée par IA",
                    visit_duration=60,
                    recommended_time=start_time,  # Sera mis à jour plus tard
                    creator_notes=rec.reasoning,
                    score=rec.confidence_score,
                    adjustments={"ai_confidence": str(rec.confidence_score)},
                    latitude=35.6895,  # Coordonnées fictives pour les tests
                    longitude=139.6917
                ))

        # Fusion et tri par score
        all_places = base_places + ai_places
        all_places.sort(key=lambda x: x.score, reverse=True)

        # Sélection des lieux dans la limite de durée
        selected_places = []
        total_duration = 0
        current_time = start_time

        for place in all_places:
            if total_duration + place.visit_duration <= duration:
                place_copy = place.model_copy()
                place_copy.recommended_time = current_time
                selected_places.append(place_copy)
                total_duration += place.visit_duration
                current_time += timedelta(minutes=place.visit_duration)

            if total_duration >= duration or len(selected_places) >= self.max_places:
                break

        if len(selected_places) < self.min_places:
            raise ValueError(f"Impossible de générer un itinéraire avec au moins {self.min_places} lieux")

        if total_duration > duration:
            raise ValueError(f"La durée totale ({total_duration} min) dépasse la durée maximale autorisée ({duration} min)")

        return selected_places

    def _calculate_final_score(
        self,
        base_score: float,
        ai_recommendations: List[AIRecommendation],
        final_places: List[ItineraryPlace]
    ) -> float:
        """Calcule le score final de l'itinéraire."""
        if not final_places:
            return 0.0

        # Score moyen des recommandations IA
        ai_scores = [rec.confidence_score for rec in ai_recommendations]
        ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 0.0

        # Score final pondéré
        return min(1.0, base_score * (1 - self.ai_weight) + ai_score * self.ai_weight)

    def _calculate_total_distance(self, places: List[ItineraryPlace]) -> float:
        """Calcule la distance totale de l'itinéraire."""
        # Pour les tests, nous utilisons une distance fictive
        if not places:
            return 0.0
        return len(places) * 1.5  # 1.5 km entre chaque lieu en moyenne 