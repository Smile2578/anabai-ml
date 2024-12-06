from typing import Any, Dict, Optional
import os
import json
from dotenv import load_dotenv

class ConfigManager:
    """Gestionnaire de configuration."""
    
    def __init__(self):
        """Initialise le gestionnaire de configuration."""
        self._config: Dict = {}
        self._load_env()
        self._init_config()

    def _load_env(self):
        """Charge les variables d'environnement."""
        load_dotenv()

    def _init_config(self):
        """Initialise la configuration par défaut."""
        self._config = {
            "database": {
                "postgres": {
                    "host": os.getenv("POSTGRES_HOST", "localhost"),
                    "port": int(os.getenv("POSTGRES_PORT", "5432")),
                    "name": os.getenv("POSTGRES_DB", "anabai"),
                    "user": os.getenv("POSTGRES_USER", "postgres"),
                    "password": os.getenv("POSTGRES_PASSWORD", ""),
                    "url": os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/anabai")
                },
                "mongodb": {
                    "uri": os.getenv("MONGODB_URI", "mongodb+srv://user:password@cluster.mongodb.net/anabai-ml")
                },
                "redis": {
                    "host": os.getenv("REDIS_HOST", "localhost"),
                    "port": int(os.getenv("REDIS_PORT", "6379")),
                    "password": os.getenv("REDIS_PASSWORD", ""),
                    "ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
                    "url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
                },
                "redis_ml": {
                    "host": os.getenv("REDIS_ML_HOST", "localhost"),
                    "port": int(os.getenv("REDIS_ML_PORT", "6379")),
                    "password": os.getenv("REDIS_ML_PASSWORD", ""),
                    "ssl": os.getenv("REDIS_ML_SSL", "false").lower() == "true",
                    "url": os.getenv("REDIS_ML_URL", "redis://localhost:6379/0"),
                    "db": int(os.getenv("REDIS_ML_DB", "0"))
                }
            },
            "api_keys": {
                "openweather": os.getenv("OPENWEATHER_API_KEY", ""),
                "google_maps": os.getenv("GOOGLE_MAPS_API_KEY", ""),
                "google_maps_server": os.getenv("GOOGLE_MAPS_SERVER_KEY", "")
            },
            "paths": {
                "models": os.getenv("ML_MODELS_PATH", "./models"),
                "cache": {
                    "tensorflow": os.getenv("TENSORFLOW_CACHE_DIR", "./cache/tensorflow"),
                    "torch": os.getenv("TORCH_HOME", "./cache/torch"),
                    "transformers": os.getenv("TRANSFORMERS_CACHE", "./cache/transformers")
                }
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "file": os.getenv("LOG_FILE", "logs/anabai.log")
            },
            "environment": os.getenv("ENVIRONMENT", "development"),
            "limits": {
                "max_places_per_itinerary": int(os.getenv("MAX_PLACES_PER_ITINERARY", "12")),
                "max_itineraries_per_user": int(os.getenv("MAX_ITINERARIES_PER_USER", "5")),
                "max_requests_per_minute": int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60")),
                "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30"))
            },
            "security": {
                "secret_key": os.getenv("SECRET_KEY", ""),
                "jwt": {
                    "secret": os.getenv("JWT_SECRET", ""),
                    "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
                    "expiration": int(os.getenv("JWT_EXPIRATION", "3600"))
                }
            },
            "scoring": {
                "base_weights": {
                    "popularity": 0.3,
                    "uniqueness": 0.2,
                    "accessibility": 0.2,
                    "seasonal": 0.15,
                    "creator_reputation": 0.15
                }
            }
        }

    @property
    def config(self) -> Dict[str, Any]:
        """Retourne une copie de la configuration."""
        return self._config.copy()

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Récupère une valeur de configuration."""
        try:
            value = self._config
            for k in key.split("."):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Définit une valeur de configuration."""
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def save_to_file(self, filepath: str) -> None:
        """Sauvegarde la configuration dans un fichier JSON."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def load_from_file(self, filepath: str) -> None:
        """Charge la configuration depuis un fichier JSON."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Le fichier de configuration {filepath} n'existe pas.")
        
        with open(filepath, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            self._config.update(loaded_config)

# Instance singleton pour une utilisation globale
config_manager = ConfigManager() 