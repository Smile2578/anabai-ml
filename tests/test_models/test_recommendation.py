import pytest
from datetime import datetime
from uuid import UUID
from models.recommendation import Recommendation, RecommendationStatus

def test_recommendation_creation():
    """Teste la création d'une recommandation."""
    recommendation = Recommendation(
        final_score=0.85,
        context={
            "weather_score": 0.9,
            "crowd_score": 0.8,
            "time_score": 0.7,
            "distance_score": 0.85,
            "user_preference_score": 0.9
        }
    )
    
    assert isinstance(recommendation.id, UUID)
    assert recommendation.final_score == 0.85
    assert recommendation.status == RecommendationStatus.PENDING
    assert isinstance(recommendation.created_at, datetime)
    assert isinstance(recommendation.updated_at, datetime)

def test_recommendation_validation():
    """Teste la validation des valeurs de la recommandation."""
    with pytest.raises(ValueError):
        Recommendation(final_score=1.5)  # Score trop élevé
    
    with pytest.raises(ValueError):
        Recommendation(final_score=-0.1)  # Score négatif

def test_recommendation_status_update():
    """Teste la mise à jour du statut de la recommandation."""
    recommendation = Recommendation(final_score=0.8)
    original_update_time = recommendation.updated_at
    
    # Attendre un moment pour s'assurer que updated_at change
    import time
    time.sleep(0.1)
    
    recommendation.update_status(RecommendationStatus.PROCESSING)
    assert recommendation.status == RecommendationStatus.PROCESSING
    assert recommendation.updated_at > original_update_time

def test_recommendation_default_context():
    """Teste les valeurs par défaut du contexte."""
    recommendation = Recommendation(final_score=0.7)
    
    assert all(0.0 <= v <= 1.0 for v in recommendation.context.values())
    assert set(recommendation.context.keys()) == {
        "weather_score",
        "crowd_score",
        "time_score",
        "distance_score",
        "user_preference_score"
    }

def test_recommendation_status_transitions():
    """Teste les transitions de statut valides."""
    recommendation = Recommendation(final_score=0.75)
    
    # Test de la séquence complète des statuts
    status_sequence = [
        RecommendationStatus.PROCESSING,
        RecommendationStatus.COMPLETED,
        RecommendationStatus.ACCEPTED
    ]
    
    for status in status_sequence:
        recommendation.update_status(status)
        assert recommendation.status == status 