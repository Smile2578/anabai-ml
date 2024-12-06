import pytest
from uuid import uuid4
from datetime import datetime, UTC
import json
from database.postgres import PostgresDB

@pytest.fixture
async def db():
    """Fixture pour la base de données."""
    await PostgresDB.init_tables()
    yield PostgresDB()
    await PostgresDB.close_pool()

@pytest.mark.asyncio
async def test_connection(db):
    """Teste la connexion à la base de données."""
    pool = await PostgresDB.get_pool()
    assert pool is not None
    
    # Test de la connexion avec une requête simple
    result = await PostgresDB.fetch("SELECT 1 as value")
    assert result[0]["value"] == 1

@pytest.mark.asyncio
async def test_user_operations(db):
    """Teste les opérations CRUD sur la table users."""
    user_id = uuid4()
    preferences = {
        "budget_range": [0, 1000],
        "preferred_categories": ["restaurants", "temples"]
    }
    history = {
        "visited_places": [],
        "favorite_places": []
    }
    
    # Création
    await PostgresDB.execute(
        """
        INSERT INTO users (id, preferences, history)
        VALUES ($1, $2, $3)
        """,
        user_id, preferences, history
    )
    
    # Lecture
    user = await PostgresDB.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
    assert user is not None
    assert user["id"] == user_id
    assert user["preferences"] == preferences
    assert user["history"] == history
    
    # Mise à jour
    new_preferences = {
        "budget_range": [0, 2000],
        "preferred_categories": ["restaurants", "temples", "parks"]
    }
    await PostgresDB.execute(
        """
        UPDATE users
        SET preferences = $2
        WHERE id = $1
        """,
        user_id, new_preferences
    )
    
    updated_user = await PostgresDB.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
    assert updated_user["preferences"] == new_preferences
    assert updated_user["updated_at"] > updated_user["created_at"]
    
    # Suppression
    await PostgresDB.execute(
        "DELETE FROM users WHERE id = $1",
        user_id
    )
    
    deleted_user = await PostgresDB.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
    assert deleted_user is None

@pytest.mark.asyncio
async def test_creator_operations(db):
    """Teste les opérations CRUD sur la table creators."""
    creator_id = uuid4()
    stats = {
        "total_places": 50,
        "average_rating": 4.8
    }
    expertise = {
        "regions": ["Tokyo", "Kyoto"],
        "categories": ["temples", "restaurants"]
    }
    performance = {
        "success_rate": 0.95,
        "user_satisfaction": 0.92
    }
    
    # Création
    await PostgresDB.execute(
        """
        INSERT INTO creators (id, stats, expertise, performance)
        VALUES ($1, $2, $3, $4)
        """,
        creator_id, stats, expertise, performance
    )
    
    # Lecture
    creator = await PostgresDB.fetchrow(
        "SELECT * FROM creators WHERE id = $1",
        creator_id
    )
    assert creator is not None
    assert creator["id"] == creator_id
    assert creator["stats"] == stats
    assert creator["expertise"] == expertise
    assert creator["performance"] == performance
    
    # Mise à jour
    new_stats = {
        "total_places": 51,
        "average_rating": 4.9
    }
    await PostgresDB.execute(
        """
        UPDATE creators
        SET stats = $2
        WHERE id = $1
        """,
        creator_id, new_stats
    )
    
    updated_creator = await PostgresDB.fetchrow(
        "SELECT * FROM creators WHERE id = $1",
        creator_id
    )
    assert updated_creator["stats"] == new_stats
    assert updated_creator["updated_at"] > updated_creator["created_at"]
    
    # Suppression
    await PostgresDB.execute(
        "DELETE FROM creators WHERE id = $1",
        creator_id
    )
    
    deleted_creator = await PostgresDB.fetchrow(
        "SELECT * FROM creators WHERE id = $1",
        creator_id
    )
    assert deleted_creator is None 