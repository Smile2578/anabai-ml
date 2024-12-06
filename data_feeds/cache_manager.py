from datetime import datetime, UTC, timedelta
from typing import Any, Dict, Optional
import json
import redis.asyncio as redis
from config.config_manager import config_manager

class CacheManager:
    """Gestionnaire de cache utilisant Redis pour stocker les données externes."""
    
    def __init__(self):
        """Initialise la connexion Redis."""
        redis_config = config_manager.get("database.redis_ml", {})
        self.redis_url = redis_config.get("url", "redis://localhost:6379/0")
        if redis_config.get("ssl", False):
            self.redis_url = self.redis_url.replace("redis://", "rediss://")
        
        self.redis_client = redis.from_url(
            self.redis_url,
            decode_responses=True,
            encoding="utf-8",
            password=redis_config.get("password"),
            db=redis_config.get("db", 0)
        )

    async def __aenter__(self):
        """Initialise la connexion Redis de manière asynchrone."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ferme la connexion Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def ensure_connection(self):
        """S'assure qu'une connexion Redis est disponible."""
        if self.redis_client is None:
            redis_config = config_manager.get("database.redis_ml", {})
            if redis_config.get("ssl", False):
                self.redis_url = self.redis_url.replace("redis://", "rediss://")
            
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8",
                password=redis_config.get("password"),
                db=redis_config.get("db", 0)
            )

    async def set_with_ttl(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Stocke une valeur dans le cache avec un TTL."""
        try:
            serialized_value = json.dumps({
                "data": value,
                "timestamp": datetime.now(UTC).isoformat()
            })
            return await self.redis_client.setex(key, ttl_seconds, serialized_value)
        except Exception as e:
            print(f"Erreur lors du stockage dans le cache : {e}")
            return False

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Récupère une valeur du cache."""
        try:
            value = await self.redis_client.get(key)
            if value:
                cached_data = json.loads(value)
                return {
                    "data": cached_data["data"],
                    "timestamp": datetime.fromisoformat(cached_data["timestamp"])
                }
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération depuis le cache : {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache."""
        try:
            return bool(await self.redis_client.delete(key))
        except Exception as e:
            print(f"Erreur lors de la suppression du cache : {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache."""
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            print(f"Erreur lors de la vérification d'existence dans le cache : {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """Récupère le TTL d'une clé en secondes."""
        try:
            ttl = await self.redis_client.ttl(key)
            return ttl if ttl > -1 else None
        except Exception as e:
            print(f"Erreur lors de la récupération du TTL : {e}")
            return None

    async def set_many(self, items: Dict[str, Any], ttl_seconds: int) -> bool:
        """Stocke plusieurs valeurs dans le cache avec un TTL."""
        try:
            pipeline = self.redis_client.pipeline()
            timestamp = datetime.now(UTC).isoformat()
            
            for key, value in items.items():
                serialized_value = json.dumps({
                    "data": value,
                    "timestamp": timestamp
                })
                pipeline.setex(key, ttl_seconds, serialized_value)
            
            await pipeline.execute()
            return True
        except Exception as e:
            print(f"Erreur lors du stockage multiple dans le cache : {e}")
            return False

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """Récupère plusieurs valeurs du cache."""
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value:
                    cached_data = json.loads(value)
                    result[key] = {
                        "data": cached_data["data"],
                        "timestamp": datetime.fromisoformat(cached_data["timestamp"])
                    }
            
            return result
        except Exception as e:
            print(f"Erreur lors de la récupération multiple depuis le cache : {e}")
            return {} 