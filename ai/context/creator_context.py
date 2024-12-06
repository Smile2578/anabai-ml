from datetime import datetime, UTC
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from database.postgres import PostgresDB

class CreatorStats(BaseModel):
    """Modèle pour les statistiques du créateur."""
    model_config = ConfigDict(from_attributes=True)

    total_places: int = Field(default=0)
    total_itineraries: int = Field(default=0)
    average_rating: float = Field(default=0.0)
    total_reviews: int = Field(default=0)
    completion_rate: float = Field(default=0.0)
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))

class CreatorExpertise(BaseModel):
    """Modèle pour l'expertise du créateur."""
    model_config = ConfigDict(from_attributes=True)

    regions: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    certification_level: str = Field(default="standard")
    years_experience: float = Field(default=0.0)

class CreatorPerformance(BaseModel):
    """Modèle pour les performances du créateur."""
    model_config = ConfigDict(from_attributes=True)

    success_rate: float = Field(default=0.0)
    response_time: float = Field(default=0.0)  # en heures
    user_satisfaction: float = Field(default=0.0)
    content_quality: float = Field(default=0.0)
    reliability_score: float = Field(default=0.0)

class CreatorContext:
    """Gestionnaire du contexte créateur."""
    
    def __init__(self, creator_id: UUID):
        self.creator_id = creator_id
        self.stats = CreatorStats()
        self.expertise = CreatorExpertise()
        self.performance = CreatorPerformance()
        self._last_update = datetime.now(UTC)

    @classmethod
    async def create(cls, creator_id: UUID) -> 'CreatorContext':
        """Crée un nouveau contexte créateur."""
        instance = cls(creator_id)
        await PostgresDB.execute(
            """
            INSERT INTO creators (id, stats, expertise, performance)
            VALUES ($1, $2, $3, $4)
            """,
            creator_id,
            instance.stats.model_dump(),
            instance.expertise.model_dump(),
            instance.performance.model_dump()
        )
        return instance

    @classmethod
    async def get(cls, creator_id: UUID) -> Optional['CreatorContext']:
        """Récupère un contexte créateur existant."""
        data = await PostgresDB.fetchrow(
            "SELECT * FROM creators WHERE id = $1",
            creator_id
        )
        if not data:
            return None
            
        instance = cls(creator_id)
        instance.stats = CreatorStats(**data["stats"])
        instance.expertise = CreatorExpertise(**data["expertise"])
        instance.performance = CreatorPerformance(**data["performance"])
        instance._last_update = data["updated_at"]
        return instance

    async def update_stats(self, stats: Dict) -> None:
        """Met à jour les statistiques du créateur."""
        self.stats = CreatorStats(**stats)
        self._last_update = datetime.now(UTC)
        
        await PostgresDB.execute(
            """
            UPDATE creators
            SET stats = $2
            WHERE id = $1
            """,
            self.creator_id,
            self.stats.model_dump()
        )

    async def update_expertise(self, expertise: Dict) -> None:
        """Met à jour l'expertise du créateur."""
        self.expertise = CreatorExpertise(**expertise)
        self._last_update = datetime.now(UTC)
        
        await PostgresDB.execute(
            """
            UPDATE creators
            SET expertise = $2
            WHERE id = $1
            """,
            self.creator_id,
            self.expertise.model_dump()
        )

    async def update_performance(self, performance: Dict) -> None:
        """Met à jour les performances du créateur."""
        self.performance = CreatorPerformance(**performance)
        self._last_update = datetime.now(UTC)
        
        await PostgresDB.execute(
            """
            UPDATE creators
            SET performance = $2
            WHERE id = $1
            """,
            self.creator_id,
            self.performance.model_dump()
        )

    def get_creator_profile(self) -> Dict:
        """Retourne le profil complet du créateur."""
        return {
            "creator_id": str(self.creator_id),
            "stats": self.stats.model_dump(),
            "expertise": self.expertise.model_dump(),
            "performance": self.performance.model_dump(),
            "last_update": self._last_update.isoformat()
        }

    def is_expert_in_region(self, region: str) -> bool:
        """Vérifie si le créateur est expert dans une région."""
        return region in self.expertise.regions

    def is_expert_in_category(self, category: str) -> bool:
        """Vérifie si le créateur est expert dans une catégorie."""
        return category in self.expertise.categories

    def speaks_language(self, language: str) -> bool:
        """Vérifie si le créateur parle une langue."""
        return language in self.expertise.languages

    def get_reliability_score(self) -> float:
        """Calcule un score de fiabilité global."""
        weights = {
            "success_rate": 0.3,
            "user_satisfaction": 0.3,
            "content_quality": 0.2,
            "response_time": 0.1,
            "completion_rate": 0.1
        }
        
        score = (
            weights["success_rate"] * self.performance.success_rate +
            weights["user_satisfaction"] * self.performance.user_satisfaction +
            weights["content_quality"] * self.performance.content_quality +
            weights["response_time"] * min(1.0, 24.0 / max(1.0, self.performance.response_time)) +
            weights["completion_rate"] * self.stats.completion_rate
        )
        
        return round(score, 2) 