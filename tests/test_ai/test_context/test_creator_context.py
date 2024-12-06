import pytest
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4
from ai.context.creator_context import CreatorContext, CreatorStats, CreatorExpertise, CreatorPerformance
from database.postgres import PostgresDB

@pytest.fixture
async def db():
    """Fixture pour la base de données."""
    await PostgresDB.init_tables()
    yield PostgresDB()
    await PostgresDB.close_pool()

@pytest.fixture
def creator_id() -> UUID:
    """Fixture pour générer un ID créateur."""
    return uuid4()

@pytest.fixture
async def creator_context(creator_id: UUID, db) -> CreatorContext:
    """Fixture pour créer un contexte créateur."""
    return await CreatorContext.create(creator_id)

@pytest.fixture
def sample_stats() -> dict:
    """Fixture pour des statistiques créateur de test."""
    return {
        "total_places": 50,
        "total_itineraries": 25,
        "average_rating": 4.8,
        "total_reviews": 150,
        "completion_rate": 0.95,
        "last_activity": datetime.now(UTC).isoformat()
    }

@pytest.fixture
def sample_expertise() -> dict:
    """Fixture pour une expertise créateur de test."""
    return {
        "regions": ["Tokyo", "Kyoto", "Osaka"],
        "categories": ["temples", "restaurants", "parks"],
        "languages": ["fr", "en", "ja"],
        "specialties": ["traditional", "cultural", "food"],
        "certification_level": "expert",
        "years_experience": 5.5
    }

@pytest.fixture
def sample_performance() -> dict:
    """Fixture pour des performances créateur de test."""
    return {
        "success_rate": 0.92,
        "response_time": 2.5,
        "user_satisfaction": 0.89,
        "content_quality": 0.95,
        "reliability_score": 0.91
    }

@pytest.mark.asyncio
async def test_creator_context_initialization(creator_context: CreatorContext, creator_id: UUID):
    """Teste l'initialisation correcte du contexte créateur."""
    assert creator_context.creator_id == creator_id
    assert isinstance(creator_context.stats, CreatorStats)
    assert isinstance(creator_context.expertise, CreatorExpertise)
    assert isinstance(creator_context.performance, CreatorPerformance)
    assert isinstance(creator_context._last_update, datetime)

@pytest.mark.asyncio
async def test_creator_context_crud(creator_id: UUID, db):
    """Teste les opérations CRUD du contexte créateur."""
    # Création
    creator_context = await CreatorContext.create(creator_id)
    assert creator_context is not None
    
    # Lecture
    loaded_context = await CreatorContext.get(creator_id)
    assert loaded_context is not None
    assert loaded_context.creator_id == creator_id
    
    # Non-existence
    non_existent = await CreatorContext.get(uuid4())
    assert non_existent is None

@pytest.mark.asyncio
async def test_update_stats(creator_context: CreatorContext, sample_stats: dict):
    """Teste la mise à jour des statistiques créateur."""
    original_update = creator_context._last_update
    
    # Attendre un moment pour s'assurer que la date de mise à jour change
    import time
    time.sleep(0.1)
    
    await creator_context.update_stats(sample_stats)
    
    # Vérifier les changements en mémoire
    assert creator_context.stats.total_places == sample_stats["total_places"]
    assert creator_context.stats.total_itineraries == sample_stats["total_itineraries"]
    assert creator_context.stats.average_rating == sample_stats["average_rating"]
    assert creator_context.stats.total_reviews == sample_stats["total_reviews"]
    assert creator_context.stats.completion_rate == sample_stats["completion_rate"]
    assert creator_context._last_update > original_update
    
    # Vérifier la persistance
    loaded_context = await CreatorContext.get(creator_context.creator_id)
    assert loaded_context is not None
    assert loaded_context.stats.model_dump() == creator_context.stats.model_dump()

@pytest.mark.asyncio
async def test_update_expertise(creator_context: CreatorContext, sample_expertise: dict):
    """Teste la mise à jour de l'expertise créateur."""
    original_update = creator_context._last_update
    
    # Attendre un moment pour s'assurer que la date de mise à jour change
    import time
    time.sleep(0.1)
    
    await creator_context.update_expertise(sample_expertise)
    
    # Vérifier les changements en mémoire
    assert creator_context.expertise.regions == sample_expertise["regions"]
    assert creator_context.expertise.categories == sample_expertise["categories"]
    assert creator_context.expertise.languages == sample_expertise["languages"]
    assert creator_context.expertise.specialties == sample_expertise["specialties"]
    assert creator_context.expertise.certification_level == sample_expertise["certification_level"]
    assert creator_context.expertise.years_experience == sample_expertise["years_experience"]
    assert creator_context._last_update > original_update
    
    # Vérifier la persistance
    loaded_context = await CreatorContext.get(creator_context.creator_id)
    assert loaded_context is not None
    assert loaded_context.expertise.model_dump() == creator_context.expertise.model_dump()

@pytest.mark.asyncio
async def test_update_performance(creator_context: CreatorContext, sample_performance: dict):
    """Teste la mise à jour des performances créateur."""
    original_update = creator_context._last_update
    
    # Attendre un moment pour s'assurer que la date de mise à jour change
    import time
    time.sleep(0.1)
    
    await creator_context.update_performance(sample_performance)
    
    # Vérifier les changements en mémoire
    assert creator_context.performance.success_rate == sample_performance["success_rate"]
    assert creator_context.performance.response_time == sample_performance["response_time"]
    assert creator_context.performance.user_satisfaction == sample_performance["user_satisfaction"]
    assert creator_context.performance.content_quality == sample_performance["content_quality"]
    assert creator_context.performance.reliability_score == sample_performance["reliability_score"]
    assert creator_context._last_update > original_update
    
    # Vérifier la persistance
    loaded_context = await CreatorContext.get(creator_context.creator_id)
    assert loaded_context is not None
    assert loaded_context.performance.model_dump() == creator_context.performance.model_dump()

@pytest.mark.asyncio
async def test_get_creator_profile(creator_context: CreatorContext, sample_stats: dict, 
                                 sample_expertise: dict, sample_performance: dict):
    """Teste la récupération du profil créateur complet."""
    await creator_context.update_stats(sample_stats)
    await creator_context.update_expertise(sample_expertise)
    await creator_context.update_performance(sample_performance)
    
    profile = creator_context.get_creator_profile()
    
    assert profile["creator_id"] == str(creator_context.creator_id)
    assert profile["stats"]["total_places"] == sample_stats["total_places"]
    assert profile["expertise"]["regions"] == sample_expertise["regions"]
    assert profile["performance"]["success_rate"] == sample_performance["success_rate"]
    assert isinstance(profile["last_update"], str)

@pytest.mark.asyncio
async def test_expertise_checks(creator_context: CreatorContext, sample_expertise: dict):
    """Teste les vérifications d'expertise."""
    await creator_context.update_expertise(sample_expertise)
    
    assert creator_context.is_expert_in_region("Tokyo")
    assert not creator_context.is_expert_in_region("Sapporo")
    assert creator_context.is_expert_in_category("temples")
    assert not creator_context.is_expert_in_category("museums")
    assert creator_context.speaks_language("fr")
    assert not creator_context.speaks_language("es")

@pytest.mark.asyncio
async def test_reliability_score(creator_context: CreatorContext, sample_stats: dict, sample_performance: dict):
    """Teste le calcul du score de fiabilité."""
    await creator_context.update_stats(sample_stats)
    await creator_context.update_performance(sample_performance)
    
    reliability_score = creator_context.get_reliability_score()
    
    assert isinstance(reliability_score, float)
    assert 0.0 <= reliability_score <= 1.0
    
    # Test avec des valeurs parfaites
    perfect_stats = {**sample_stats, "completion_rate": 1.0}
    perfect_performance = {
        "success_rate": 1.0,
        "response_time": 1.0,
        "user_satisfaction": 1.0,
        "content_quality": 1.0,
        "reliability_score": 1.0
    }
    
    await creator_context.update_stats(perfect_stats)
    await creator_context.update_performance(perfect_performance)
    
    perfect_score = creator_context.get_reliability_score()
    assert perfect_score == 1.0