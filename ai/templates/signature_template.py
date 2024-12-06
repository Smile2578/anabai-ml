"""Module de génération d'itinéraires basés sur un créateur principal."""

from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager
from ai.scoring.base_score import BaseScoreCalculator
from ai.scoring.creator_score import CreatorScoreCalculator
from ai.scoring.place_score import PlaceScoreCalculator
from ai.scoring.contextual_multipliers import ContextualMultiplierCalculator

class ItineraryPlace(BaseModel):
    """Modèle pour un lieu dans l'itinéraire."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    visit_duration: int  # en minutes
    recommended_time: datetime
    creator_notes: Optional[str] = None
    score: float = Field(ge=0.0, le=1.0)
    adjustments: Dict[str, str] = Field(default_factory=dict)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

class SignatureItinerary(BaseModel):
    """Modèle pour un itinéraire signature."""
    model_config = ConfigDict(from_attributes=True)

    itinerary_id: UUID = Field(default_factory=uuid4)
    creator_id: UUID
    creator_name: str
    creator_expertise: List[str]
    places: List[ItineraryPlace]
    total_duration: int  # en minutes
    total_distance: float  # en kilomètres
    creation_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score: float = Field(ge=0.0, le=1.0)

class SignatureTemplate:
    """Générateur d'itinéraires basés sur un créateur principal."""

    def __init__(self):
        self.config = ConfigManager()
        self.base_scorer = BaseScoreCalculator()
        self.creator_scorer = CreatorScoreCalculator()
        self.place_scorer = PlaceScoreCalculator()
        self.context_scorer = ContextualMultiplierCalculator()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du template."""
        self.max_places = self.config.get("templates.signature.max_places", 8)
        self.min_places = self.config.get("templates.signature.min_places", 3)
        self.max_duration = self.config.get("templates.signature.max_duration", 480)  # 8 heures
        self.min_duration = self.config.get("templates.signature.min_duration", 180)  # 3 heures

    async def generate(
        self,
        creator_id: UUID,
        preferences: Dict[str, float],
        start_time: datetime,
        duration: Optional[int] = None,
        excluded_places: Optional[List[UUID]] = None
    ) -> SignatureItinerary:
        """Génère un itinéraire signature basé sur un créateur."""
        # Validation des paramètres
        if duration:
            if duration < self.min_duration or duration > self.max_duration:
                raise ValueError(f"La durée doit être entre {self.min_duration} et {self.max_duration} minutes")
        else:
            duration = self.max_duration

        excluded_places = excluded_places or []

        # Récupération des informations du créateur
        creator_info = await self._get_creator_info(creator_id)
        creator_score = await self._calculate_creator_score(creator_id)

        # Récupération des lieux recommandés par le créateur
        recommended_places = await self._get_creator_places(
            creator_id,
            excluded_places
        )

        # Calcul des scores et sélection des lieux
        scored_places = await self._score_places(
            recommended_places,
            creator_score,
            preferences,
            start_time
        )

        # Construction de l'itinéraire
        selected_places = self._select_places(
            scored_places,
            duration,
            start_time
        )

        # Calcul du score global de l'itinéraire
        itinerary_score = self._calculate_itinerary_score(
            selected_places,
            creator_score
        )

        # Construction de l'objet itinéraire
        return SignatureItinerary(
            itinerary_id=uuid4(),
            creator_id=creator_id,
            creator_name=creator_info["name"],
            creator_expertise=creator_info["expertise"],
            places=selected_places,
            total_duration=sum(place.visit_duration for place in selected_places),
            total_distance=self._calculate_total_distance(selected_places),
            score=itinerary_score
        )

    async def _get_creator_info(self, creator_id: UUID) -> Dict:
        """Récupère les informations du créateur."""
        # TODO: Implémenter la récupération depuis la base de données
        return {
            "name": "Nom du Créateur",
            "expertise": ["temples", "culture", "gastronomie"]
        }

    async def _calculate_creator_score(self, creator_id: UUID) -> float:
        """Calcule le score du créateur."""
        # TODO: Implémenter le calcul du score créateur
        return 0.85

    async def _get_creator_places(
        self,
        creator_id: UUID,
        excluded_places: List[UUID]
    ) -> List[Dict]:
        """Récupère les lieux recommandés par le créateur."""
        # Pour les tests, nous retournons des données factices
        mock_places = [
            {
                "place_id": uuid4(),
                "name": "Temple Historique",
                "description": "Un temple ancien avec une riche histoire",
                "visit_duration": 60,
                "categories": ["temples", "culture"],
                "creator_notes": "Magnifique au coucher du soleil",
                "latitude": 35.6895,
                "longitude": 139.6917
            },
            {
                "place_id": uuid4(),
                "name": "Restaurant Traditionnel",
                "description": "Restaurant servant des plats locaux authentiques",
                "visit_duration": 90,
                "categories": ["gastronomie", "culture"],
                "creator_notes": "Essayez le plat signature",
                "latitude": 35.6892,
                "longitude": 139.6920
            },
            {
                "place_id": uuid4(),
                "name": "Parc National",
                "description": "Un parc naturel préservé",
                "visit_duration": 120,
                "categories": ["nature"],
                "creator_notes": "Idéal pour la randonnée",
                "latitude": 35.6890,
                "longitude": 139.6915
            },
            {
                "place_id": uuid4(),
                "name": "Musée d'Art",
                "description": "Un musée présentant des œuvres d'art locales",
                "visit_duration": 90,
                "categories": ["culture", "art"],
                "creator_notes": "Collection unique d'art contemporain",
                "latitude": 35.6888,
                "longitude": 139.6918
            },
            {
                "place_id": uuid4(),
                "name": "Temple Moderne",
                "description": "Un temple contemporain avec une architecture unique",
                "visit_duration": 45,
                "categories": ["temples", "architecture"],
                "creator_notes": "Architecture impressionnante",
                "latitude": 35.6885,
                "longitude": 139.6922
            },
            {
                "place_id": uuid4(),
                "name": "Marché Local",
                "description": "Un marché traditionnel animé",
                "visit_duration": 60,
                "categories": ["culture", "gastronomie"],
                "creator_notes": "Meilleur moment: tôt le matin",
                "latitude": 35.6882,
                "longitude": 139.6925
            },
            {
                "place_id": uuid4(),
                "name": "Jardin Botanique",
                "description": "Un jardin avec des espèces rares",
                "visit_duration": 75,
                "categories": ["nature", "science"],
                "creator_notes": "Superbe collection d'orchidées",
                "latitude": 35.6880,
                "longitude": 139.6928
            },
            {
                "place_id": uuid4(),
                "name": "Centre Artisanal",
                "description": "Centre d'artisanat traditionnel",
                "visit_duration": 60,
                "categories": ["culture", "shopping"],
                "creator_notes": "Démonstrations d'artisans locaux",
                "latitude": 35.6878,
                "longitude": 139.6930
            }
        ]
        return [place for place in mock_places if place["place_id"] not in excluded_places]

    async def _score_places(
        self,
        places: List[Dict],
        creator_score: float,
        preferences: Dict[str, float],
        start_time: datetime
    ) -> List[Dict]:
        """Calcule les scores pour chaque lieu."""
        scored_places = []
        current_time = start_time

        for place in places:
            # Calcul du score de base
            base_score = await self.base_scorer.calculate_score(place)
            
            # Calcul du score créateur
            creator_influence = await self.creator_scorer.calculate_score({
                "creator_score": creator_score,
                "place_categories": place["categories"]
            })
            
            # Calcul du score de préférence
            preference_score = 0.0
            category_count = 0
            for category in place["categories"]:
                if category in preferences:
                    preference_score += preferences[category]
                    category_count += 1
            
            if category_count > 0:
                preference_score /= category_count
            
            # Calcul du score contextuel
            context_score = await self.context_scorer.calculate_score({
                "time_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "month": current_time.month,
                "duration": place["visit_duration"]
            })
            
            # Score final
            final_score = (
                base_score * 0.3 +
                creator_influence * 0.3 +
                preference_score * 0.2 +
                context_score * 0.2
            )
            
            # Ajout des informations de timing
            scored_place = place.copy()
            scored_place["score"] = final_score
            scored_place["recommended_time"] = current_time
            
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
        creator_score: float
    ) -> float:
        """Calcule le score global de l'itinéraire."""
        if not places:
            return 0.0

        # Moyenne pondérée des scores des lieux
        place_scores = [place.score for place in places]
        avg_place_score = sum(place_scores) / len(place_scores)

        # Le score final est influencé par le score du créateur
        return min(1.0, avg_place_score * (0.7 + creator_score * 0.3))

    def _calculate_total_distance(self, places: List[ItineraryPlace]) -> float:
        """Calcule la distance totale de l'itinéraire."""
        # Pour les tests, nous utilisons une distance fictive
        if not places:
            return 0.0
        return len(places) * 1.5  # 1.5 km entre chaque lieu en moyenne 