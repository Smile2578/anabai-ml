import os
import pytest
import json
from typing import Dict, Union, List
from config.config_manager import ConfigManager

@pytest.fixture
def config_manager() -> ConfigManager:
    """Fixture pour créer une instance de ConfigManager pour les tests."""
    return ConfigManager()

@pytest.fixture
def test_config_file(tmp_path) -> str:
    """Fixture pour créer un fichier de configuration temporaire."""
    config_path = tmp_path / "test_config.json"
    test_config = {
        "test": {
            "key1": "value1",
            "key2": 123,
            "key3": {
                "nested": "value"
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(test_config, f)
    return str(config_path)

def test_config_initialization(config_manager: ConfigManager) -> None:
    """Teste l'initialisation correcte du ConfigManager."""
    assert isinstance(config_manager.config, dict)
    assert "database" in config_manager.config
    assert "api_keys" in config_manager.config
    assert "paths" in config_manager.config
    assert "limits" in config_manager.config
    assert "scoring" in config_manager.config

def test_get_existing_value(config_manager: ConfigManager) -> None:
    """Teste la récupération d'une valeur existante."""
    value = config_manager.get("database.postgres.host")
    assert value == "localhost"  # Valeur par défaut

def test_get_nested_value(config_manager: ConfigManager) -> None:
    """Teste la récupération d'une valeur imbriquée."""
    value = config_manager.get("scoring.base_weights.popularity")
    assert isinstance(value, float)
    assert value == 0.3

def test_get_nonexistent_value(config_manager: ConfigManager) -> None:
    """Teste la récupération d'une valeur inexistante."""
    value = config_manager.get("nonexistent.key", default="default")
    assert value == "default"

def test_set_value(config_manager: ConfigManager) -> None:
    """Teste la définition d'une nouvelle valeur."""
    config_manager.set("test.new_key", "new_value")
    value = config_manager.get("test.new_key")
    assert value == "new_value"

def test_set_nested_value(config_manager: ConfigManager) -> None:
    """Teste la définition d'une valeur imbriquée."""
    config_manager.set("test.nested.key", {"inner": "value"})
    value = config_manager.get("test.nested.key.inner")
    assert value == "value"

def test_save_and_load_config(config_manager: ConfigManager, test_config_file: str) -> None:
    """Teste la sauvegarde et le chargement de la configuration."""
    # Définir les données de test
    config_manager.set("test.key1", "value1")
    config_manager.set("test.key2", 123)
    config_manager.set("test.key3.nested", "value")
    
    # Test de sauvegarde
    config_manager.save_to_file(test_config_file)
    assert os.path.exists(test_config_file)

    # Test de chargement
    new_config = ConfigManager()
    new_config.load_from_file(test_config_file)
    assert new_config.get("test.key1") == "value1"
    assert new_config.get("test.key2") == 123
    assert new_config.get("test.key3.nested") == "value"

def test_config_immutability(config_manager: ConfigManager) -> None:
    """Teste l'immutabilité de la configuration retournée."""
    config = config_manager.config
    config["new_key"] = "new_value"  # Modifie la copie
    assert "new_key" not in config_manager.config  # La configuration originale ne doit pas être modifiée

def test_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Teste la prise en compte des variables d'environnement."""
    # Simule des variables d'environnement
    monkeypatch.setenv("POSTGRES_HOST", "test_host")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    
    # Crée une nouvelle instance pour prendre en compte les nouvelles variables
    config = ConfigManager()
    
    assert config.get("database.postgres.host") == "test_host"
    assert config.get("database.postgres.port") == 5433