from datetime import datetime, UTC, timedelta
from typing import Dict, List, Literal, Tuple
from uuid import UUID
import numpy as np
from ai.learning.data_collector import DataCollector
from ai.monitoring.metrics_tracker import MetricsTracker

FeedbackType = Literal[
    "rating",
    "comment",
    "suggestion",
    "bug_report",
    "feature_request"
]

FeedbackStatus = Literal[
    "pending",
    "processed",
    "integrated",
    "rejected"
]

class FeedbackError(Exception):
    """Erreur personnalisée pour la gestion du feedback."""
    def __init__(self, message: str, error_type: str, context: Dict[str, str | float] | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.context = context or {}
        self.timestamp = datetime.now(UTC)

class FeedbackIntegration:
    """
    Intègre le feedback utilisateur (notes, commentaires) dans le cycle d'apprentissage,
    influençant le pattern_analyzer et le formula_evolver.
    """

    FEEDBACK_TYPES: List[FeedbackType] = [
        "rating",
        "comment",
        "suggestion",
        "bug_report",
        "feature_request"
    ]

    def __init__(
        self,
        data_collector: DataCollector,
        metrics_tracker: MetricsTracker,
        min_confidence: float = 0.7,
        error_threshold: int = 100
    ) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("La confiance minimale doit être entre 0 et 1")

        self.data_collector = data_collector
        self.metrics_tracker = metrics_tracker
        self.min_confidence = min_confidence
        self.error_threshold = error_threshold
        self.feedback_weights: Dict[FeedbackType, float] = {
            "rating": 1.0,
            "comment": 0.8,
            "suggestion": 0.6,
            "bug_report": 0.9,
            "feature_request": 0.5
        }
        self.error_counts: Dict[str, int] = {}
        self._last_error_check = datetime.now(UTC)

    async def process_feedback(
        self,
        feedback_type: FeedbackType,
        content: str | float,
        user_id: UUID,
        context: Dict[str, float | str] | None = None,
        confidence: float | None = None
    ) -> Dict[str, float | str]:
        """
        Traite un nouveau feedback et l'intègre dans le système.
        """
        start_time = datetime.now(UTC)
        try:
            if feedback_type not in self.FEEDBACK_TYPES:
                raise FeedbackError(
                    f"Type de feedback invalide : {feedback_type}",
                    "invalid_feedback_type",
                    {"feedback_type": feedback_type}
                )

            if feedback_type == "rating" and not isinstance(content, (int, float)):
                raise FeedbackError(
                    "Le contenu d'une note doit être numérique",
                    "invalid_rating_content",
                    {"content_type": str(type(content))}
                )
            elif feedback_type != "rating" and not isinstance(content, str):
                raise FeedbackError(
                    "Le contenu doit être une chaîne de caractères",
                    "invalid_content_type",
                    {"content_type": str(type(content))}
                )

            feedback_data = {
                "type": feedback_type,
                "content": content,
                "user_id": user_id,
                "context": context or {},
                "confidence": confidence or self.calculate_confidence(feedback_type, content),
                "status": "pending",
                "timestamp": datetime.now(UTC)
            }

            # Enregistrer le feedback
            await self.data_collector.feedback_collection.insert_one(feedback_data)

            # Mettre à jour les métriques si c'est une note
            if feedback_type == "rating":
                await self.metrics_tracker.track_metric(
                    metric_type="user_satisfaction",
                    value=float(content),
                    context=context
                )

            # Enregistrer le temps de traitement
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            await self.metrics_tracker.track_metric(
                metric_type="response_time",
                value=processing_time,
                context={"operation": "process_feedback"}
            )

            return feedback_data

        except FeedbackError as e:
            await self._handle_error(e)
            raise
        except Exception as e:
            error = FeedbackError(
                str(e),
                "unexpected_error",
                {"original_error": str(type(e).__name__)}
            )
            await self._handle_error(error)
            raise error

    async def _handle_error(self, error: FeedbackError) -> None:
        """
        Gère une erreur de feedback.
        """
        # Incrémenter le compteur d'erreurs
        self.error_counts[error.error_type] = self.error_counts.get(error.error_type, 0) + 1

        # Enregistrer l'erreur dans les métriques
        await self.metrics_tracker.track_error(error.error_type)

        # Vérifier le seuil d'erreurs
        if self.error_counts[error.error_type] >= self.error_threshold:
            await self.metrics_tracker.track_metric(
                metric_type="error_rate",
                value=1.0,
                context={
                    "error_type": error.error_type,
                    "count": self.error_counts[error.error_type]
                }
            )

    async def check_error_patterns(self) -> Dict[str, Dict[str, int | float]]:
        """
        Analyse les patterns d'erreurs.
        """
        now = datetime.now(UTC)
        if (now - self._last_error_check).total_seconds() < 300:  # 5 minutes
            return {}

        patterns = {}
        for error_type, count in self.error_counts.items():
            patterns[error_type] = {
                "count": count,
                "rate": count / max(1, sum(self.error_counts.values())),
                "threshold_exceeded": count >= self.error_threshold
            }

        self._last_error_check = now
        return patterns

    async def get_feedback_summary(
        self,
        days: int = 30
    ) -> Dict[str, Dict[str, float | int]]:
        """
        Génère un résumé des feedbacks sur une période donnée.
        """
        if days < 1:
            raise ValueError("La période doit être d'au moins 1 jour")

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        
        cursor = await self.data_collector.feedback_collection.find({
            "timestamp": {"$gte": cutoff_date}
        })
        feedbacks = await cursor.to_list(length=None)

        if not feedbacks:
            return {}

        summary: Dict[str, Dict[str, float | int]] = {}
        
        for feedback_type in self.FEEDBACK_TYPES:
            type_feedbacks = [
                f for f in feedbacks
                if f["type"] == feedback_type
            ]
            
            if type_feedbacks:
                if feedback_type == "rating":
                    ratings = [float(f["content"]) for f in type_feedbacks]
                    summary[feedback_type] = {
                        "count": len(ratings),
                        "mean": float(np.mean(ratings)),
                        "std": float(np.std(ratings)),
                        "min": float(np.min(ratings)),
                        "max": float(np.max(ratings))
                    }
                else:
                    summary[feedback_type] = {
                        "count": len(type_feedbacks),
                        "avg_confidence": float(np.mean([
                            f["confidence"] for f in type_feedbacks
                        ]))
                    }

        return summary

    async def get_high_confidence_feedback(
        self,
        feedback_type: FeedbackType | None = None,
        min_confidence: float | None = None
    ) -> List[Dict[str, float | str]]:
        """
        Récupère les feedbacks avec un niveau de confiance élevé.
        """
        min_conf = min_confidence or self.min_confidence
        
        if not 0.0 <= min_conf <= 1.0:
            raise ValueError("La confiance minimale doit être entre 0 et 1")

        query = {"confidence": {"$gte": min_conf}}
        if feedback_type:
            if feedback_type not in self.FEEDBACK_TYPES:
                raise ValueError(f"Type de feedback invalide : {feedback_type}")
            query["type"] = feedback_type

        cursor = await self.data_collector.feedback_collection.find(query)
        return await cursor.to_list(length=None)

    def calculate_confidence(
        self,
        feedback_type: FeedbackType,
        content: str | float
    ) -> float:
        """
        Calcule un score de confiance pour un feedback.
        """
        if feedback_type not in self.FEEDBACK_TYPES:
            raise ValueError(f"Type de feedback invalide : {feedback_type}")
            
        base_weight = self.feedback_weights[feedback_type]
        
        if feedback_type == "rating":
            if not isinstance(content, (int, float)):
                return 0.0
            # Plus de confiance dans les notes extrêmes
            rating = float(content)
            if not 0.0 <= rating <= 5.0:
                return 0.0
            extremity = abs(rating - 2.5) / 2.5
            return min(1.0, base_weight * (0.5 + 0.5 * extremity))
        else:
            if not isinstance(content, str):
                return 0.0
            # Plus de confiance dans les feedbacks détaillés
            content_length = len(content.strip())
            if content_length < 10:
                return base_weight * 0.5
            elif content_length < 50:
                return base_weight * 0.7
            else:
                return base_weight

    async def update_feedback_status(
        self,
        feedback_id: UUID,
        new_status: FeedbackStatus,
        resolution_notes: str | None = None
    ) -> None:
        """
        Met à jour le statut d'un feedback.
        """
        update_data = {
            "status": new_status,
            "updated_at": datetime.now(UTC)
        }
        
        if resolution_notes:
            update_data["resolution_notes"] = resolution_notes

        await self.data_collector.feedback_collection.update_one(
            {"_id": feedback_id},
            {"$set": update_data}
        ) 