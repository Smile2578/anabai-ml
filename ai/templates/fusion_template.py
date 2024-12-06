"""Module de génération d'itinéraires basés sur la fusion des recommandations de plusieurs créateurs."""

from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager
from ai.scoring.base_score import BaseScoreCalculator
from ai.scoring.creator_score import CreatorScoreCalculator
from ai.scoring.place_score import PlaceScoreCalculator
from ai.scoring.contextual_multipliers import ContextualMultiplierCalculator
from .signature_template import ItineraryPlace, SignatureTemplate

class FusionItinerary(BaseModel):
    """Modèle pour un itinéraire fusionné."""
    model_config = ConfigDict(from_attributes=True)

    itinerary_id: UUID
    creator_ids: List[UUID]
    creator_names: List[str]
    creator_expertises: List[List[str]]
    places: List[ItineraryPlace]
    total_duration: int  # en minutes
    total_distance: float  # en kilomètres
    creation_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score: float = Field(ge=0.0, le=1.0)
    fusion_weights: Dict[UUID, float]  # Poids de chaque créateur dans la fusion

class FusionTemplate:
    """Générateur d'itinéraires basés sur la fusion des recommandations."""

    def __init__(self):
        self.config = ConfigManager()
        self.base_scorer = BaseScoreCalculator()
        self.creator_scorer = CreatorScoreCalculator()
        self.place_scorer = PlaceScoreCalculator()
        self.context_scorer = ContextualMultiplierCalculator()
        self.signature_template = SignatureTemplate()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du template."""
        self.max_places = self.config.get("templates.fusion.max_places", 10)
        self.min_places = self.config.get("templates.fusion.min_places", 4)
        self.max_duration = self.config.get("templates.fusion.max_duration", 600)  # 10 heures
        self.min_duration = self.config.get("templates.fusion.min_duration", 240)  # 4 heures
        self.min_creators = self.config.get("templates.fusion.min_creators", 2)
        self.max_creators = self.config.get("templates.fusion.max_creators", 5)

    async def generate(
        self,
        creator_ids: List[UUID],
        preferences: Dict[str, float],
        start_time: datetime,
        duration: Optional[int] = None,
        excluded_places: Optional[List[UUID]] = None
    ) -> FusionItinerary:
        """Génère un itinéraire basé sur la fusion des recommandations."""
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

        # Récupération des informations des créateurs
        creators_info = await self._get_creators_info(creator_ids)
        creators_scores = await self._calculate_creators_scores(creator_ids)

        # Calcul des poids de fusion basés sur les scores des créateurs
        fusion_weights = self._calculate_fusion_weights(creators_scores)

        # Récupération des lieux recommandés par chaque créateur
        all_places = await self._get_all_places(
            creator_ids,
            excluded_places
        )

        # Fusion et scoring des lieux
        scored_places = await self._score_places(
            all_places,
            creators_scores,
            fusion_weights,
            preferences,
            start_time
        )

        # Sélection des lieux pour l'itinéraire
        selected_places = self._select_places(
            scored_places,
            duration,
            start_time
        )

        # Calcul du score global de l'itinéraire
        itinerary_score = self._calculate_itinerary_score(
            selected_places,
            creators_scores,
            fusion_weights
        )

        # Construction de l'objet itinéraire
        return FusionItinerary(
            itinerary_id=uuid4(),
            creator_ids=creator_ids,
            creator_names=[info["name"] for info in creators_info],
            creator_expertises=[info["expertise"] for info in creators_info],
            places=selected_places,
            total_duration=sum(place.visit_duration for place in selected_places),
            total_distance=self._calculate_total_distance(selected_places),
            score=itinerary_score,
            fusion_weights=fusion_weights
        )

    async def _get_creators_info(self, creator_ids: List[UUID]) -> List[Dict]:
        """Récupère les informations des créateurs."""
        creators_info = []
        for creator_id in creator_ids:
            # Pour les tests, nous retournons des données factices
            creators_info.append({
                "id": creator_id,
                "name": f"Créateur {len(creators_info) + 1}",
                "expertise": ["temples", "culture", "gastronomie"]
            })
        return creators_info

    async def _calculate_creators_scores(self, creator_ids: List[UUID]) -> Dict[UUID, float]:
        """Calcule les scores des créateurs."""
        scores = {}
        for creator_id in creator_ids:
            # Pour les tests, nous retournons un score basé sur l'index
            scores[creator_id] = 0.7 + (0.1 * (len(scores) % 3))
        return scores

    def _calculate_fusion_weights(self, creators_scores: Dict[UUID, float]) -> Dict[UUID, float]:
        """Calcule les poids de fusion basés sur les scores des créateurs."""
        total_score = sum(creators_scores.values())
        if total_score == 0:
            # Si tous les scores sont 0, distribution uniforme
            weight = 1.0 / len(creators_scores)
            return {creator_id: weight for creator_id in creators_scores}
        
        return {
            creator_id: score / total_score
            for creator_id, score in creators_scores.items()
        }

    async def _get_all_places(
        self,
        creator_ids: List[UUID],
        excluded_places: List[UUID]
    ) -> Dict[UUID, List[Dict]]:
        """Récupère les lieux recommandés par chaque créateur."""
        all_places = {}
        for creator_id in creator_ids:
            places = await self.signature_template._get_creator_places(
                creator_id,
                excluded_places
            )
            all_places[creator_id] = places
        return all_places

    async def _score_places(
        self,
        all_places: Dict[UUID, List[Dict]],
        creators_scores: Dict[UUID, float],
        fusion_weights: Dict[UUID, float],
        preferences: Dict[str, float],
        start_time: datetime
    ) -> List[Dict]:
        """Calcule les scores fusionnés pour chaque lieu."""
        # Regroupement des lieux par ID pour éviter les doublons
        unique_places: Dict[UUID, Dict] = {}
        creator_recommendations: Dict[UUID, Set[UUID]] = {
            creator_id: set() for creator_id in creators_scores
        }

        # Collecte des lieux uniques et des recommandations
        for creator_id, places in all_places.items():
            for place in places:
                place_id = place["place_id"]
                creator_recommendations[creator_id].add(place_id)
                if place_id not in unique_places:
                    unique_places[place_id] = place.copy()
                    unique_places[place_id]["recommending_creators"] = set()
                unique_places[place_id]["recommending_creators"].add(creator_id)

        # Calcul des scores
        scored_places = []
        current_time = start_time

        for place_id, place in unique_places.items():
            # Score de base
            base_score = await self.base_scorer.calculate_score(place)
            
            # Score créateur fusionné
            creator_score = 0.0
            for creator_id in place["recommending_creators"]:
                creator_influence = creators_scores[creator_id] * fusion_weights[creator_id]
                creator_score += creator_influence
            
            # Normalisation du score créateur
            if place["recommending_creators"]:
                creator_score /= len(place["recommending_creators"])
            
            # Score de préférence
            preference_score = 0.0
            category_count = 0
            for category in place["categories"]:
                if category in preferences:
                    preference_score += preferences[category]
                    category_count += 1
            
            if category_count > 0:
                preference_score /= category_count
            
            # Score contextuel
            context_score = await self.context_scorer.calculate_score({
                "time_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "month": current_time.month,
                "duration": place["visit_duration"]
            })
            
            # Score final
            final_score = (
                base_score * 0.25 +
                creator_score * 0.35 +
                preference_score * 0.2 +
                context_score * 0.2
            )
            
            # Ajout des informations de timing
            scored_place = place.copy()
            scored_place["score"] = final_score
            scored_place["recommended_time"] = current_time
            scored_place.pop("recommending_creators")  # Nettoyage
            
            scored_places.append(scored_place)
            current_time += timedelta(minutes=place["visit_duration"])

        return sorted(scored_places, key=lambda x: x["score"], reverse=True)

    def _select_places(
        self,
        scored_places: List[Dict],
        duration: int,
        start_time: datetime
    ) -> List[ItineraryPlace]:
        """Sélectionne les lieux pour l'itinéraire."""
        selected_places = []
        current_time = start_time
        total_duration = 0

        for place in scored_places:
            if total_duration + place["visit_duration"] <= duration:
                selected_places.append(ItineraryPlace(
                    place_id=place["place_id"],
                    name=place["name"],
                    description=place["description"],
                    visit_duration=place["visit_duration"],
                    recommended_time=current_time,
                    creator_notes=place.get("creator_notes"),
                    score=place["score"],
                    adjustments={},  # Pour de futures optimisations
                    latitude=place["latitude"],
                    longitude=place["longitude"]
                ))
                total_duration += place["visit_duration"]
                current_time += timedelta(minutes=place["visit_duration"])

            if total_duration >= duration or len(selected_places) >= self.max_places:
                break

        if len(selected_places) < self.min_places:
            raise ValueError(f"Impossible de générer un itinéraire avec au moins {self.min_places} lieux")

        return selected_places

    def _calculate_itinerary_score(
        self,
        places: List[ItineraryPlace],
        creators_scores: Dict[UUID, float],
        fusion_weights: Dict[UUID, float]
    ) -> float:
        """Calcule le score global de l'itinéraire."""
        if not places:
            return 0.0

        # Moyenne pondérée des scores des lieux
        place_scores = [place.score for place in places]
        avg_place_score = sum(place_scores) / len(place_scores)

        # Score moyen des créateurs pondéré par leurs poids de fusion
        avg_creator_score = sum(
            score * fusion_weights[creator_id]
            for creator_id, score in creators_scores.items()
        )

        # Le score final combine les scores des lieux et des créateurs
        return min(1.0, avg_place_score * 0.7 + avg_creator_score * 0.3)

    def _calculate_total_distance(self, places: List[ItineraryPlace]) -> float:
        """Calcule la distance totale de l'itinéraire."""
        # Pour les tests, nous utilisons une distance fictive
        if not places:
            return 0.0
        return len(places) * 1.5  # 1.5 km entre chaque lieu en moyenne 