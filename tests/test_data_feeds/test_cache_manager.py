import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch, call
from data_feeds.cache_manager import CacheManager
import json
import redis.asyncio as redis

@pytest.fixture
async def mock_redis_client():
    """Fixture pour créer un mock du client Redis."""
    mock_client = AsyncMock(spec=redis.Redis)
    mock_client.close = AsyncMock()
    mock_client.setex = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_client.exists = AsyncMock()
    mock_client.ttl = AsyncMock()
    mock_client.mget = AsyncMock()
    mock_client.pipeline = MagicMock()
    return mock_client

@pytest.fixture
async def mock_pipeline():
    """Fixture pour créer un mock du pipeline Redis."""
    mock = AsyncMock()
    mock.setex = AsyncMock()
    mock.execute = AsyncMock()
    return mock

@pytest.fixture
async def cache_manager(mock_redis_client, mock_pipeline):
    """Fixture pour créer une instance de CacheManager avec un mock Redis."""
    mock_redis_client.pipeline.return_value = mock_pipeline
    with patch('redis.asyncio.from_url', return_value=mock_redis_client):
        manager = CacheManager()
        await manager.__aenter__()
        yield manager
        await manager.__aexit__(None, None, None)

@pytest.mark.asyncio
async def test_set_with_ttl(cache_manager, mock_redis_client):
    """Teste le stockage d'une valeur avec TTL."""
    test_key = "test_key"
    test_value = {"name": "test", "value": 42}
    test_ttl = 3600

    mock_redis_client.setex.return_value = True
    result = await cache_manager.set_with_ttl(test_key, test_value, test_ttl)
    
    assert result is True
    mock_redis_client.setex.assert_called_once()

@pytest.mark.asyncio
async def test_get_existing_value(cache_manager, mock_redis_client):
    """Teste la récupération d'une valeur existante."""
    test_key = "test_key"
    test_timestamp = datetime.now(UTC)
    test_cached_data = {
        "data": {"name": "test", "value": 42},
        "timestamp": test_timestamp.isoformat()
    }

    mock_redis_client.get.return_value = json.dumps(test_cached_data)
    result = await cache_manager.get(test_key)
    
    assert result is not None
    assert "data" in result
    assert "timestamp" in result
    assert isinstance(result["timestamp"], datetime)

@pytest.mark.asyncio
async def test_get_nonexistent_value(cache_manager, mock_redis_client):
    """Teste la récupération d'une valeur inexistante."""
    test_key = "nonexistent_key"

    mock_redis_client.get.return_value = None
    result = await cache_manager.get(test_key)
    
    assert result is None

@pytest.mark.asyncio
async def test_delete_existing_key(cache_manager, mock_redis_client):
    """Teste la suppression d'une clé existante."""
    test_key = "test_key"

    mock_redis_client.delete.return_value = 1
    result = await cache_manager.delete(test_key)
    
    assert result is True
    mock_redis_client.delete.assert_called_once_with(test_key)

@pytest.mark.asyncio
async def test_delete_nonexistent_key(cache_manager, mock_redis_client):
    """Teste la suppression d'une clé inexistante."""
    test_key = "nonexistent_key"

    mock_redis_client.delete.return_value = 0
    result = await cache_manager.delete(test_key)
    
    assert result is False
    mock_redis_client.delete.assert_called_once_with(test_key)

@pytest.mark.asyncio
async def test_exists(cache_manager, mock_redis_client):
    """Teste la vérification d'existence d'une clé."""
    test_key = "test_key"

    mock_redis_client.exists.return_value = 1
    result = await cache_manager.exists(test_key)
    
    assert result is True
    mock_redis_client.exists.assert_called_once_with(test_key)

@pytest.mark.asyncio
async def test_get_ttl(cache_manager, mock_redis_client):
    """Teste la récupération du TTL d'une clé."""
    test_key = "test_key"
    test_ttl = 3600

    mock_redis_client.ttl.return_value = test_ttl
    result = await cache_manager.get_ttl(test_key)
    
    assert result == test_ttl
    mock_redis_client.ttl.assert_called_once_with(test_key)

@pytest.mark.asyncio
async def test_set_many(cache_manager, mock_redis_client, mock_pipeline):
    """Teste le stockage multiple de valeurs."""
    test_items = {
        "key1": {"name": "test1", "value": 42},
        "key2": {"name": "test2", "value": 84}
    }
    test_ttl = 3600

    mock_pipeline.execute.return_value = [True, True]
    result = await cache_manager.set_many(test_items, test_ttl)
    
    assert result is True
    mock_redis_client.pipeline.assert_called_once()
    assert mock_pipeline.execute.called
    
    # Vérifier que setex a été appelé pour chaque clé
    assert mock_pipeline.setex.call_count == len(test_items)
    
    # Vérifier que les appels contiennent les bonnes clés et valeurs
    for call_args in mock_pipeline.setex.call_args_list:
        key = call_args[0][0]
        ttl = call_args[0][1]
        value_dict = json.loads(call_args[0][2])
        
        assert key in test_items
        assert ttl == test_ttl
        assert "data" in value_dict
        assert "timestamp" in value_dict
        assert value_dict["data"] == test_items[key]

@pytest.mark.asyncio
async def test_get_many(cache_manager, mock_redis_client):
    """Teste la récupération multiple de valeurs."""
    test_keys = ["key1", "key2"]
    test_timestamp = datetime.now(UTC)
    test_values = [
        json.dumps({
            "data": {"name": "test1", "value": 42},
            "timestamp": test_timestamp.isoformat()
        }),
        json.dumps({
            "data": {"name": "test2", "value": 84},
            "timestamp": test_timestamp.isoformat()
        })
    ]

    mock_redis_client.mget.return_value = test_values
    result = await cache_manager.get_many(test_keys)
    
    assert isinstance(result, dict)
    assert len(result) == len(test_keys)
    mock_redis_client.mget.assert_called_once_with(test_keys)
  