import pytest
from datetime import datetime, timedelta, UTC
from uuid import UUID
from models.contextual_score import ContextualScore

def test_contextual_score_creation():
    """Teste la création d'un score contextuel."""
    now = datetime.now(UTC)
    score = ContextualScore(
        context_type="weather",
        multiplier=1.2,
        valid_from=now,
        valid_until=now + timedelta(hours=6),
        factors={
            "weather": 1.2,
            "crowd": 0.8,
            "events": 1.0,
            "time_of_day": 1.1
        }
    )
    
    assert isinstance(score.id, UUID)
    assert score.context_type == "weather"
    assert score.multiplier == 1.2
    assert isinstance(score.created_at, datetime)
    assert score.valid_from == now
    assert score.valid_until == now + timedelta(hours=6)

def test_contextual_score_validation():
    """Teste la validation des valeurs du score contextuel."""
    now = datetime.now(UTC)
    
    with pytest.raises(ValueError):
        ContextualScore(
            context_type="",  # Type vide non autorisé
            multiplier=1.0,
            valid_from=now,
            valid_until=now + timedelta(hours=1)
        )
    
    with pytest.raises(ValueError):
        ContextualScore(
            context_type="weather",
            multiplier=-0.1,  # Multiplicateur négatif non autorisé
            valid_from=now,
            valid_until=now + timedelta(hours=1)
        )

def test_contextual_score_validity():
    """Teste la validité temporelle du score contextuel."""
    now = datetime.now(UTC)
    score = ContextualScore(
        context_type="weather",
        multiplier=1.0,
        valid_from=now,
        valid_until=now + timedelta(hours=1)
    )
    
    # Test pendant la période de validité
    assert score.is_valid_at(now + timedelta(minutes=30))
    
    # Test avant la période de validité
    assert not score.is_valid_at(now - timedelta(minutes=1))
    
    # Test après la période de validité
    assert not score.is_valid_at(now + timedelta(hours=2))

def test_contextual_score_default_factors():
    """Teste les valeurs par défaut des facteurs contextuels."""
    now = datetime.now(UTC)
    score = ContextualScore(
        context_type="weather",
        multiplier=1.0,
        valid_from=now,
        valid_until=now + timedelta(hours=1)
    )
    
    assert all(v == 1.0 for v in score.factors.values())
    assert set(score.factors.keys()) == {
        "weather",
        "crowd",
        "events",
        "time_of_day"
    } 