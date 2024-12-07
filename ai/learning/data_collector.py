from datetime import datetime, UTC
from typing import Dict, List
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import UuidRepresentation

class DataCollector:
    """
    Collecte les données d'utilisation, retours et succès/échecs des recommandations
    pour nourrir l'apprentissage.
    """

    def __init__(self, mongodb_uri: str) -> None:
        self.client = AsyncIOMotorClient(
            mongodb_uri,
            uuidRepresentation='standard'
        )
        self.db = self.client["anabai-ml"]
        self.feedback_collection = self.db["feedback"]
        self.usage_collection = self.db["usage"]
        self.metrics_collection = self.db["metrics"]

    async def collect_feedback(
        self,
        user_id: UUID,
        itinerary_id: UUID,
        rating: float,
        comments: str | None = None,
        context: Dict[str, float] | None = None
    ) -> None:
        """
        Collecte le feedback utilisateur sur un itinéraire.
        """
        if not 0.0 <= rating <= 5.0:
            raise ValueError("La note doit être entre 0 et 5")

        feedback_data = {
            "user_id": user_id,
            "itinerary_id": itinerary_id,
            "rating": rating,
            "comments": comments,
            "context": context or {},
            "timestamp": datetime.now(UTC)
        }
        
        await self.feedback_collection.insert_one(feedback_data)

    async def collect_usage_data(
        self,
        user_id: UUID,
        action_type: str,
        data: Dict[str, float | str | bool]
    ) -> None:
        """
        Collecte les données d'utilisation (clics, temps passé, etc.).
        """
        usage_data = {
            "user_id": user_id,
            "action_type": action_type,
            "data": data,
            "timestamp": datetime.now(UTC)
        }
        
        await self.usage_collection.insert_one(usage_data)

    async def collect_recommendation_metrics(
        self,
        recommendation_id: UUID,
        metrics: Dict[str, float]
    ) -> None:
        """
        Collecte les métriques de performance des recommandations.
        """
        metrics_data = {
            "recommendation_id": recommendation_id,
            "metrics": metrics,
            "timestamp": datetime.now(UTC)
        }
        
        await self.metrics_collection.insert_one(metrics_data)

    async def get_user_feedback_history(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, float | str | Dict]]:
        """
        Récupère l'historique des feedbacks d'un utilisateur.
        """
        cursor = self.feedback_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)

    async def get_recommendation_performance(
        self,
        recommendation_id: UUID
    ) -> Dict[str, float]:
        """
        Récupère les métriques de performance d'une recommandation.
        """
        metrics = await self.metrics_collection.find_one(
            {"recommendation_id": recommendation_id}
        )
        
        return metrics["metrics"] if metrics else {} 