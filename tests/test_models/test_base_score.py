import pytest
from datetime import datetime
from uuid import UUID
from models.base_score import BaseScore

def test_base_score_creation():
    """Teste la création d'un score de base."""
    score = BaseScore(
        base_score=0.8,
        factors={
            "popularity": 0.9,
            "uniqueness": 0.7,
            "accessibility": 0.8,
            "seasonal": 0.6,
            "creator_reputation": 0.8
        }
    )
    
    assert isinstance(score.id, UUID)
    assert score.base_score == 0.8
    assert score.factors["popularity"] == 0.9
    assert score.factors["uniqueness"] == 0.7
    assert isinstance(score.created_at, datetime)
    assert isinstance(score.updated_at, datetime)

def test_base_score_validation():
    """Teste la validation des valeurs du score."""
    with pytest.raises(ValueError):
        BaseScore(base_score=1.5)  # Score trop élevé
    
    with pytest.raises(ValueError):
        BaseScore(base_score=-0.1)  # Score négatif

def test_base_score_default_factors():
    """Teste les valeurs par défaut des facteurs."""
    score = BaseScore(base_score=0.5)
    
    assert all(0.0 <= v <= 1.0 for v in score.factors.values())
    assert set(score.factors.keys()) == {
        "popularity",
        "uniqueness",
        "accessibility",
        "seasonal",
        "creator_reputation"
    }

def test_base_score_custom_factors():
    """Teste la personnalisation des facteurs."""
    custom_factors = {
        "popularity": 0.8,
        "uniqueness": 0.6,
        "accessibility": 0.7,
        "seasonal": 0.9,
        "creator_reputation": 0.5
    }
    
    score = BaseScore(
        base_score=0.7,
        factors=custom_factors
    )
    
    assert score.factors == custom_factors 