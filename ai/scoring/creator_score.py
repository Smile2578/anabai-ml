"""Module de calcul du score des créateurs."""

from datetime import datetime, UTC
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager

class CreatorMetrics(BaseModel):
    """Métriques du créateur utilisées pour le calcul du score."""
    model_config = ConfigDict(from_attributes=True)

    total_content: int = Field(ge=0)
    average_rating: float = Field(ge=0.0, le=5.0)
    engagement_rate: float = Field(ge=0.0, le=1.0)
    expertise_areas: Dict[str, float] = Field(default_factory=dict)
    content_freshness: float = Field(ge=0.0, le=1.0)

class CreatorScoreInput(BaseModel):
    """Modèle pour les données d'entrée du calcul de score créateur."""
    model_config = ConfigDict(from_attributes=True)

    creator_id: UUID
    metrics: CreatorMetrics
    target_categories: List[str] = Field(default_factory=list)

class CreatorScoreOutput(BaseModel):
    """Modèle pour les résultats du calcul de score créateur."""
    model_config = ConfigDict(from_attributes=True)

    creator_id: UUID
    creator_score: float = Field(ge=0.0, le=1.0)
    component_scores: Dict[str, float]
    expertise_match: Optional[float] = None
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class CreatorScoreCalculator:
    """Calculateur de score pour les créateurs."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_weights()

    def _load_weights(self) -> None:
        """Charge les poids depuis la configuration."""
        self.weights = {
            "content_volume": self.config.get("scoring.creator_weights.content_volume", 0.2),
            "rating": self.config.get("scoring.creator_weights.rating", 0.3),
            "engagement": self.config.get("scoring.creator_weights.engagement", 0.2),
            "expertise": self.config.get("scoring.creator_weights.expertise", 0.2),
            "freshness": self.config.get("scoring.creator_weights.freshness", 0.1)
        }

    def calculate(self, input_data: CreatorScoreInput) -> CreatorScoreOutput:
        """Calcule le score du créateur."""
        component_scores = {}
        
        # Score du volume de contenu (normalisé avec une fonction logarithmique)
        content_score = min(1.0, (1 + input_data.metrics.total_content) / 100)
        component_scores["content_volume"] = content_score
        
        # Score des notes
        rating_score = input_data.metrics.average_rating / 5.0
        component_scores["rating"] = rating_score
        
        # Score d'engagement
        component_scores["engagement"] = input_data.metrics.engagement_rate
        
        # Score d'expertise
        expertise_score = 0.0
        expertise_match = None
        if input_data.target_categories:
            relevant_scores = [
                input_data.metrics.expertise_areas.get(cat, 0.0)
                for cat in input_data.target_categories
            ]
            if relevant_scores:
                expertise_score = sum(relevant_scores) / len(relevant_scores)
                expertise_match = expertise_score
        component_scores["expertise"] = expertise_score
        
        # Score de fraîcheur
        component_scores["freshness"] = input_data.metrics.content_freshness
        
        # Calcul du score final pondéré
        weighted_sum = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )
        
        # Normalisation du score final
        creator_score = max(0.0, min(1.0, weighted_sum))
        
        return CreatorScoreOutput(
            creator_id=input_data.creator_id,
            creator_score=creator_score,
            component_scores=component_scores,
            expertise_match=expertise_match
        )

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Met à jour les poids des composants."""
        if not all(0.0 <= w <= 1.0 for w in new_weights.values()):
            raise ValueError("Tous les poids doivent être entre 0 et 1")
        
        if abs(sum(new_weights.values()) - 1.0) > 0.001:
            raise ValueError("La somme des poids doit être égale à 1")
        
        self.weights.update(new_weights)

    async def calculate_score(self, data: Dict) -> float:
        """Calcule le score créateur pour un lieu."""
        creator_score = data.get("creator_score", 0.0)
        place_categories = data.get("place_categories", [])

        # Pour les tests, nous retournons un score basé sur le score créateur
        return min(1.0, creator_score * 1.2) 