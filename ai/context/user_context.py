from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from database.postgres import PostgresDB

class UserPreferences(BaseModel):
    """Modèle pour les préférences utilisateur."""
    model_config = ConfigDict(from_attributes=True)

    budget_range: tuple[float, float] = Field(default=(0.0, 1000000.0))
    preferred_categories: List[str] = Field(default_factory=list)
    accessibility_requirements: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    preferred_times: Dict[str, List[str]] = Field(default_factory=dict)
    language: str = Field(default="fr")
    travel_style: str = Field(default="balanced")

class UserHistory(BaseModel):
    """Modèle pour l'historique des visites utilisateur."""
    model_config = ConfigDict(from_attributes=True)

    visited_places: List[UUID] = Field(default_factory=list)
    favorite_places: List[UUID] = Field(default_factory=list)
    last_visit_dates: Dict[UUID, datetime] = Field(default_factory=dict)
    ratings: Dict[UUID, float] = Field(default_factory=dict)

    @field_validator('visited_places', 'favorite_places', mode='before')
    @classmethod
    def convert_str_to_uuid(cls, v: List[str | UUID]) -> List[UUID]:
        """Convertit les chaînes en UUID."""
        return [UUID(x) if isinstance(x, str) else x for x in v]

    @field_validator('last_visit_dates', mode='before')
    @classmethod
    def convert_str_to_uuid_and_datetime(cls, v: Dict[str | UUID, str | datetime]) -> Dict[UUID, datetime]:
        """Convertit les chaînes en UUID et datetime."""
        result = {}
        for key, value in v.items():
            uuid_key = UUID(key) if isinstance(key, str) else key
            datetime_value = datetime.fromisoformat(value) if isinstance(value, str) else value
            result[uuid_key] = datetime_value
        return result

    @field_validator('ratings', mode='before')
    @classmethod
    def convert_str_to_uuid_for_ratings(cls, v: Dict[str | UUID, float]) -> Dict[UUID, float]:
        """Convertit les chaînes en UUID pour les notes."""
        return {UUID(k) if isinstance(k, str) else k: v for k, v in v.items()}

    def model_dump(self, **kwargs: Any) -> Dict:
        """Sérialise le modèle en dictionnaire."""
        data = super().model_dump(**kwargs)
        # Convertir les UUID en chaînes
        data["visited_places"] = [str(x) for x in data["visited_places"]]
        data["favorite_places"] = [str(x) for x in data["favorite_places"]]
        # Convertir les UUID et datetime en chaînes
        data["last_visit_dates"] = {
            str(k): v.isoformat() for k, v in data["last_visit_dates"].items()
        }
        # Convertir les UUID en chaînes pour les notes
        data["ratings"] = {str(k): v for k, v in data["ratings"].items()}
        return data

class UserContext:
    """Gestionnaire du contexte utilisateur."""
    
    def __init__(self, user_id: UUID):
        self.user_id = user_id
        self.preferences = UserPreferences()
        self.history = UserHistory()
        self._last_update = datetime.now(UTC)

    @classmethod
    async def create(cls, user_id: UUID) -> 'UserContext':
        """Crée un nouveau contexte utilisateur."""
        instance = cls(user_id)
        await PostgresDB.execute(
            """
            INSERT INTO users (id, preferences, history)
            VALUES ($1, $2, $3)
            """,
            user_id,
            instance.preferences.model_dump(),
            instance.history.model_dump()
        )
        return instance

    @classmethod
    async def get(cls, user_id: UUID) -> Optional['UserContext']:
        """Récupère un contexte utilisateur existant."""
        data = await PostgresDB.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        if not data:
            return None
            
        instance = cls(user_id)
        instance.preferences = UserPreferences(**data["preferences"])
        instance.history = UserHistory(**data["history"])
        instance._last_update = data["updated_at"]
        return instance

    async def update_preferences(self, preferences: Dict) -> None:
        """Met à jour les préférences utilisateur."""
        self.preferences = UserPreferences(**preferences)
        self._last_update = datetime.now(UTC)
        
        await PostgresDB.execute(
            """
            UPDATE users
            SET preferences = $2
            WHERE id = $1
            """,
            self.user_id,
            self.preferences.model_dump()
        )

    async def update_history(self, history: Dict) -> None:
        """Met à jour l'historique utilisateur."""
        self.history = UserHistory(**history)
        self._last_update = datetime.now(UTC)
        
        await PostgresDB.execute(
            """
            UPDATE users
            SET history = $2
            WHERE id = $1
            """,
            self.user_id,
            self.history.model_dump()
        )

    def get_travel_profile(self) -> Dict:
        """Retourne le profil de voyage complet de l'utilisateur."""
        return {
            "user_id": str(self.user_id),
            "preferences": self.preferences.model_dump(),
            "history": self.history.model_dump(),
            "last_update": self._last_update.isoformat()
        }

    def has_visited(self, place_id: UUID) -> bool:
        """Vérifie si l'utilisateur a déjà visité un lieu."""
        return place_id in self.history.visited_places

    def get_place_rating(self, place_id: UUID) -> float:
        """Récupère la note donnée par l'utilisateur pour un lieu."""
        return self.history.ratings.get(place_id, 0.0)

    def is_favorite(self, place_id: UUID) -> bool:
        """Vérifie si un lieu est dans les favoris de l'utilisateur."""
        return place_id in self.history.favorite_places

    def get_last_visit(self, place_id: UUID) -> datetime | None:
        """Récupère la date de dernière visite d'un lieu."""
        return self.history.last_visit_dates.get(place_id) 