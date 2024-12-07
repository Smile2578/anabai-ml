import pytest
from datetime import datetime, UTC
from uuid import uuid4
from ai.learning.data_collector import DataCollector
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mongodb_uri():
    return "mongodb://localhost:27017"

@pytest.fixture
async def data_collector(mongodb_uri):
    collector = DataCollector(mongodb_uri)
    # Remplacer les collections par des mocks
    collector.feedback_collection = AsyncMock()
    collector.usage_collection = AsyncMock()
    collector.metrics_collection = AsyncMock()
    return collector

@pytest.mark.asyncio
async def test_collect_feedback(data_collector):
    """Teste la collecte de feedback utilisateur."""
    user_id = uuid4()
    itinerary_id = uuid4()
    
    await data_collector.collect_feedback(
        user_id=user_id,
        itinerary_id=itinerary_id,
        rating=4.5,
        comments="Super itinéraire !",
        context={"weather": 0.8, "crowd": 0.3}
    )
    
    data_collector.feedback_collection.insert_one.assert_called_once()
    call_args = data_collector.feedback_collection.insert_one.call_args[0][0]
    
    assert call_args["user_id"] == user_id
    assert call_args["itinerary_id"] == itinerary_id
    assert call_args["rating"] == 4.5
    assert call_args["comments"] == "Super itinéraire !"
    assert isinstance(call_args["timestamp"], datetime)

@pytest.mark.asyncio
async def test_collect_invalid_feedback(data_collector):
    """Teste la validation des notes de feedback."""
    with pytest.raises(ValueError):
        await data_collector.collect_feedback(
            user_id=uuid4(),
            itinerary_id=uuid4(),
            rating=6.0  # Note invalide
        )

@pytest.mark.asyncio
async def test_collect_usage_data(data_collector):
    """Teste la collecte des données d'utilisation."""
    user_id = uuid4()
    
    await data_collector.collect_usage_data(
        user_id=user_id,
        action_type="view_place",
        data={
            "place_id": str(uuid4()),
            "duration": 120.5,
            "scrolled": True
        }
    )
    
    data_collector.usage_collection.insert_one.assert_called_once()
    call_args = data_collector.usage_collection.insert_one.call_args[0][0]
    
    assert call_args["user_id"] == user_id
    assert call_args["action_type"] == "view_place"
    assert isinstance(call_args["timestamp"], datetime)

@pytest.mark.asyncio
async def test_collect_recommendation_metrics(data_collector):
    """Teste la collecte des métriques de recommandation."""
    recommendation_id = uuid4()
    metrics = {
        "accuracy": 0.85,
        "relevance": 0.92,
        "diversity": 0.78
    }
    
    await data_collector.collect_recommendation_metrics(
        recommendation_id=recommendation_id,
        metrics=metrics
    )
    
    data_collector.metrics_collection.insert_one.assert_called_once()
    call_args = data_collector.metrics_collection.insert_one.call_args[0][0]
    
    assert call_args["recommendation_id"] == recommendation_id
    assert call_args["metrics"] == metrics
    assert isinstance(call_args["timestamp"], datetime)

@pytest.mark.asyncio
async def test_get_user_feedback_history(data_collector):
    """Teste la récupération de l'historique des feedbacks."""
    user_id = uuid4()
    mock_feedback = [
        {"rating": 4.5, "timestamp": datetime.now(UTC)},
        {"rating": 3.8, "timestamp": datetime.now(UTC)}
    ]
    
    # Configuration du mock pour la chaîne d'appels MongoDB
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=mock_feedback)
    
    data_collector.feedback_collection.find = MagicMock(return_value=mock_cursor)
    
    history = await data_collector.get_user_feedback_history(user_id)
    
    assert history == mock_feedback
    data_collector.feedback_collection.find.assert_called_once_with({"user_id": user_id})
    mock_cursor.sort.assert_called_once_with("timestamp", -1)
    mock_cursor.limit.assert_called_once_with(100)

@pytest.mark.asyncio
async def test_get_recommendation_performance(data_collector):
    """Teste la récupération des métriques de performance."""
    recommendation_id = uuid4()
    mock_metrics = {
        "accuracy": 0.85,
        "relevance": 0.92
    }
    
    data_collector.metrics_collection.find_one.return_value = {
        "metrics": mock_metrics
    }
    
    metrics = await data_collector.get_recommendation_performance(recommendation_id)
    
    assert metrics == mock_metrics
    data_collector.metrics_collection.find_one.assert_called_once_with(
        {"recommendation_id": recommendation_id}
    ) 