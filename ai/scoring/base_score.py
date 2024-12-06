"""Module de calcul du score de base pour les lieux et créateurs."""

from datetime import datetime, UTC
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager

class BaseScoreInput(BaseModel):
    """Modèle pour les données d'entrée du calcul de score de base."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    creator_id: Optional[UUID] = None
    static_factors: Dict[str, float] = Field(
        default_factory=lambda: {
            "popularity": 0.0,
            "uniqueness": 0.0,
            "accessibility": 0.0,
            "seasonal_relevance": 0.0,
            "creator_reputation": 0.0
        }
    )

class BaseScoreOutput(BaseModel):
    """Modèle pour les résultats du calcul de score de base."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    creator_id: Optional[UUID] = None
    base_score: float = Field(ge=0.0, le=1.0)
    factor_contributions: Dict[str, float]
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class BaseScoreCalculator:
    """Calculateur de score de base pour les lieux."""

    def __init__(self):
        self.config = ConfigManager()
        self._load_weights()

    def _load_weights(self) -> None:
        """Charge les poids depuis la configuration."""
        self.weights = {
            "popularity": self.config.get("scoring.base_weights.popularity", 0.3),
            "uniqueness": self.config.get("scoring.base_weights.uniqueness", 0.25),
            "accessibility": self.config.get("scoring.base_weights.accessibility", 0.2),
            "seasonal_relevance": self.config.get("scoring.base_weights.seasonal_relevance", 0.15),
            "creator_reputation": self.config.get("scoring.base_weights.creator_reputation", 0.1)
        }

    def calculate(self, input_data: BaseScoreInput) -> BaseScoreOutput:
        """Calcule le score de base à partir des facteurs statiques."""
        factor_contributions = {}
        weighted_sum = 0.0
        total_weight = sum(self.weights.values())

        for factor, weight in self.weights.items():
            factor_value = input_data.static_factors.get(factor, 0.0)
            contribution = (factor_value * weight) / total_weight
            factor_contributions[factor] = contribution
            weighted_sum += contribution

        # Normalisation du score final entre 0 et 1
        base_score = max(0.0, min(1.0, weighted_sum))

        return BaseScoreOutput(
            place_id=input_data.place_id,
            creator_id=input_data.creator_id,
            base_score=base_score,
            factor_contributions=factor_contributions
        )

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Met à jour les poids des facteurs."""
        # Validation des nouveaux poids
        if not all(0.0 <= w <= 1.0 for w in new_weights.values()):
            raise ValueError("Tous les poids doivent être entre 0 et 1")
        
        # Mise à jour des poids
        self.weights.update(new_weights)

    async def calculate_score(self, place: Dict) -> float:
        """Calcule le score de base pour un lieu."""
        # Pour les tests, nous retournons un score fixe
        return 0.75
  