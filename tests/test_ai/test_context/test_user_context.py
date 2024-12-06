import pytest
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4
from ai.context.user_context import UserContext, UserPreferences, UserHistory
from database.postgres import PostgresDB

@pytest.fixture
async def db():
    """Fixture pour la base de données."""
    await PostgresDB.init_tables()
    yield PostgresDB()
    await PostgresDB.close_pool()

@pytest.fixture
def user_id() -> UUID:
    """Fixture pour générer un ID utilisateur."""
    return uuid4()

@pytest.fixture
async def user_context(user_id: UUID, db) -> UserContext:
    """Fixture pour créer un contexte utilisateur."""
    return await UserContext.create(user_id)

@pytest.fixture
def sample_preferences() -> dict:
    """Fixture pour des préférences utilisateur de test."""
    return {
        "budget_range": (0.0, 1000.0),
        "preferred_categories": ["restaurant", "temple", "park"],
        "accessibility_requirements": ["wheelchair"],
        "dietary_restrictions": ["vegetarian"],
        "preferred_times": {
            "morning": ["8:00", "11:00"],
            "afternoon": ["14:00", "17:00"]
        },
        "language": "fr",
        "travel_style": "cultural"
    }

@pytest.fixture
def sample_history() -> dict:
    """Fixture pour un historique utilisateur de test."""
    place_id = str(uuid4())
    now = datetime.now(UTC)
    return {
        "visited_places": [place_id],
        "favorite_places": [place_id],
        "last_visit_dates": {place_id: now.isoformat()},
        "ratings": {place_id: 4.5}
    }

@pytest.mark.asyncio
async def test_user_context_initialization(user_context: UserContext, user_id: UUID):
    """Teste l'initialisation correcte du contexte utilisateur."""
    assert user_context.user_id == user_id
    assert isinstance(user_context.preferences, UserPreferences)
    assert isinstance(user_context.history, UserHistory)
    assert isinstance(user_context._last_update, datetime)

@pytest.mark.asyncio
async def test_user_context_crud(user_id: UUID, db):
    """Teste les opérations CRUD du contexte utilisateur."""
    # Création
    user_context = await UserContext.create(user_id)
    assert user_context is not None
    
    # Lecture
    loaded_context = await UserContext.get(user_id)
    assert loaded_context is not None
    assert loaded_context.user_id == user_id
    
    # Non-existence
    non_existent = await UserContext.get(uuid4())
    assert non_existent is None

@pytest.mark.asyncio
async def test_update_preferences(user_context: UserContext, sample_preferences: dict):
    """Teste la mise à jour des préférences utilisateur."""
    original_update = user_context._last_update
    
    # Attendre un moment pour s'assurer que la date de mise à jour change
    import time
    time.sleep(0.1)
    
    await user_context.update_preferences(sample_preferences)
    
    # Vérifier les changements en mémoire
    assert user_context.preferences.budget_range == sample_preferences["budget_range"]
    assert user_context.preferences.preferred_categories == sample_preferences["preferred_categories"]
    assert user_context.preferences.accessibility_requirements == sample_preferences["accessibility_requirements"]
    assert user_context.preferences.dietary_restrictions == sample_preferences["dietary_restrictions"]
    assert user_context.preferences.preferred_times == sample_preferences["preferred_times"]
    assert user_context.preferences.language == sample_preferences["language"]
    assert user_context.preferences.travel_style == sample_preferences["travel_style"]
    assert user_context._last_update > original_update
    
    # Vérifier la persistance
    loaded_context = await UserContext.get(user_context.user_id)
    assert loaded_context is not None
    assert loaded_context.preferences.model_dump() == user_context.preferences.model_dump()

@pytest.mark.asyncio
async def test_update_history(user_context: UserContext, sample_history: dict):
    """Teste la mise à jour de l'historique utilisateur."""
    original_update = user_context._last_update
    
    # Attendre un moment pour s'assurer que la date de mise à jour change
    import time
    time.sleep(0.1)
    
    await user_context.update_history(sample_history)
    
    # Vérifier les changements en mémoire
    place_id = UUID(sample_history["visited_places"][0])
    assert place_id in user_context.history.visited_places
    assert place_id in user_context.history.favorite_places
    assert user_context.history.ratings[place_id] == sample_history["ratings"][str(place_id)]
    assert user_context._last_update > original_update
    
    # Vérifier la persistance
    loaded_context = await UserContext.get(user_context.user_id)
    assert loaded_context is not None
    assert loaded_context.history.model_dump() == user_context.history.model_dump()

@pytest.mark.asyncio
async def test_get_travel_profile(user_context: UserContext, sample_preferences: dict, sample_history: dict):
    """Teste la récupération du profil de voyage complet."""
    await user_context.update_preferences(sample_preferences)
    await user_context.update_history(sample_history)
    
    profile = user_context.get_travel_profile()
    
    assert profile["user_id"] == str(user_context.user_id)
    assert profile["preferences"]["budget_range"] == sample_preferences["budget_range"]
    assert profile["preferences"]["preferred_categories"] == sample_preferences["preferred_categories"]
    assert isinstance(profile["last_update"], str)

@pytest.mark.asyncio
async def test_place_interactions(user_context: UserContext):
    """Teste les interactions avec les lieux."""
    place_id = uuid4()
    now = datetime.now(UTC)
    
    # Test initial - le lieu n'existe pas encore
    assert not user_context.has_visited(place_id)
    assert not user_context.is_favorite(place_id)
    assert user_context.get_place_rating(place_id) == 0.0
    assert user_context.get_last_visit(place_id) is None
    
    # Ajout du lieu dans l'historique
    history = {
        "visited_places": [str(place_id)],
        "favorite_places": [str(place_id)],
        "last_visit_dates": {str(place_id): now.isoformat()},
        "ratings": {str(place_id): 4.5}
    }
    await user_context.update_history(history)
    
    # Test après ajout
    assert user_context.has_visited(place_id)
    assert user_context.is_favorite(place_id)
    assert user_context.get_place_rating(place_id) == 4.5
    assert isinstance(user_context.get_last_visit(place_id), datetime)