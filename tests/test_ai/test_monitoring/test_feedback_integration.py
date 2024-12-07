import asyncio
from datetime import datetime, UTC, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from ai.monitoring.feedback_integration import FeedbackIntegration

@pytest.fixture
def mock_data_collector():
    collector = MagicMock()
    collector.feedback_collection = AsyncMock()
    return collector

@pytest.fixture
def mock_metrics_tracker():
    return AsyncMock()

@pytest.fixture
def feedback_integration(mock_data_collector, mock_metrics_tracker):
    return FeedbackIntegration(
        data_collector=mock_data_collector,
        metrics_tracker=mock_metrics_tracker
    )

@pytest.mark.asyncio
async def test_process_feedback_rating(feedback_integration):
    user_id = uuid4()
    rating = 4.5
    context = {"book_id": str(uuid4())}
    
    result = await feedback_integration.process_feedback(
        feedback_type="rating",
        content=rating,
        user_id=user_id,
        context=context
    )
    
    assert result["type"] == "rating"
    assert result["content"] == rating
    assert result["user_id"] == user_id
    assert result["context"] == context
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["status"] == "pending"
    assert isinstance(result["timestamp"], datetime)
    
    feedback_integration.data_collector.feedback_collection.insert_one.assert_called_once()
    feedback_integration.metrics_tracker.track_metric.assert_called_once_with(
        metric_type="user_satisfaction",
        value=rating,
        context=context
    )

@pytest.mark.asyncio
async def test_process_feedback_comment(feedback_integration):
    user_id = uuid4()
    comment = "Excellent livre, très bien écrit !"
    
    result = await feedback_integration.process_feedback(
        feedback_type="comment",
        content=comment,
        user_id=user_id
    )
    
    assert result["type"] == "comment"
    assert result["content"] == comment
    assert result["user_id"] == user_id
    assert result["context"] == {}
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["status"] == "pending"
    
    feedback_integration.data_collector.feedback_collection.insert_one.assert_called_once()
    feedback_integration.metrics_tracker.track_metric.assert_not_called()

def test_calculate_confidence_rating(feedback_integration):
    # Test avec une note extrême (5.0)
    confidence_high = feedback_integration.calculate_confidence("rating", 5.0)
    assert confidence_high > 0.8  # Devrait avoir une confiance élevée
    
    # Test avec une note moyenne (2.5)
    confidence_mid = feedback_integration.calculate_confidence("rating", 2.5)
    assert confidence_mid < confidence_high  # Devrait avoir une confiance plus faible
    
    # Test avec une note invalide
    confidence_invalid = feedback_integration.calculate_confidence("rating", 6.0)
    assert confidence_invalid == 0.0

def test_calculate_confidence_comment(feedback_integration):
    # Test avec un commentaire court
    confidence_short = feedback_integration.calculate_confidence(
        "comment",
        "Court."
    )
    
    # Test avec un commentaire moyen
    confidence_medium = feedback_integration.calculate_confidence(
        "comment",
        "Un commentaire de taille moyenne pour tester."
    )
    
    # Test avec un commentaire long
    confidence_long = feedback_integration.calculate_confidence(
        "comment",
        "Un très long commentaire détaillé qui devrait avoir une confiance plus élevée "
        "car il contient beaucoup plus d'informations et montre que l'utilisateur a pris "
        "le temps d'écrire une réponse complète."
    )
    
    assert confidence_short < confidence_medium < confidence_long

@pytest.mark.asyncio
async def test_get_feedback_summary(feedback_integration):
    mock_feedbacks = [
        {
            "type": "rating",
            "content": 4.0,
            "timestamp": datetime.now(UTC),
            "confidence": 0.8
        },
        {
            "type": "rating",
            "content": 5.0,
            "timestamp": datetime.now(UTC),
            "confidence": 0.9
        },
        {
            "type": "comment",
            "content": "Super !",
            "timestamp": datetime.now(UTC),
            "confidence": 0.7
        }
    ]
    
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = mock_feedbacks
    feedback_integration.data_collector.feedback_collection.find.return_value = mock_cursor
    
    summary = await feedback_integration.get_feedback_summary(days=30)
    
    assert "rating" in summary
    assert summary["rating"]["count"] == 2
    assert summary["rating"]["mean"] == 4.5
    assert "comment" in summary
    assert summary["comment"]["count"] == 1
    assert summary["comment"]["avg_confidence"] == 0.7

@pytest.mark.asyncio
async def test_get_high_confidence_feedback(feedback_integration):
    mock_high_confidence_feedbacks = [
        {
            "type": "rating",
            "content": 5.0,
            "confidence": 0.9
        }
    ]
    
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = mock_high_confidence_feedbacks
    feedback_integration.data_collector.feedback_collection.find.return_value = mock_cursor
    
    feedbacks = await feedback_integration.get_high_confidence_feedback(
        feedback_type="rating",
        min_confidence=0.8
    )
    
    assert len(feedbacks) == 1
    assert feedbacks[0]["type"] == "rating"
    assert feedbacks[0]["content"] == 5.0
    assert feedbacks[0]["confidence"] == 0.9

@pytest.mark.asyncio
async def test_update_feedback_status(feedback_integration):
    feedback_id = uuid4()
    new_status = "processed"
    resolution_notes = "Feedback traité et intégré"
    
    await feedback_integration.update_feedback_status(
        feedback_id=feedback_id,
        new_status=new_status,
        resolution_notes=resolution_notes
    )
    
    feedback_integration.data_collector.feedback_collection.update_one.assert_called_once()
    call_args = feedback_integration.data_collector.feedback_collection.update_one.call_args
    assert call_args[0][0] == {"_id": feedback_id}
    assert call_args[0][1]["$set"]["status"] == new_status
    assert call_args[0][1]["$set"]["resolution_notes"] == resolution_notes
    assert isinstance(call_args[0][1]["$set"]["updated_at"], datetime)

def test_invalid_feedback_type(feedback_integration):
    with pytest.raises(ValueError, match="Type de feedback invalide"):
        feedback_integration.calculate_confidence("invalid_type", "content")

def test_invalid_content_type(feedback_integration):
    with pytest.raises(ValueError, match="Le contenu d'une note doit être numérique"):
        asyncio.run(feedback_integration.process_feedback(
            feedback_type="rating",
            content="not a number",
            user_id=uuid4()
        ))

def test_invalid_min_confidence(feedback_integration):
    with pytest.raises(ValueError, match="La confiance minimale doit être entre 0 et 1"):
        FeedbackIntegration(
            data_collector=MagicMock(),
            metrics_tracker=MagicMock(),
            min_confidence=1.5
        ) 