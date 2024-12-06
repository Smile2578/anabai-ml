from typing import Optional, Any
import json
from datetime import datetime, UTC
from uuid import UUID
import asyncpg
from asyncpg.pool import Pool
from config.config_manager import config_manager

class PostgresDB:
    """Gestionnaire de connexion PostgreSQL."""
    
    _instance: Optional['PostgresDB'] = None
    _pool: Optional[Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_pool(cls) -> Pool:
        """Récupère ou crée le pool de connexions."""
        if cls._pool is None:
            try:
                cls._pool = await asyncpg.create_pool(
                    host=config_manager.get("database.postgres.host"),
                    port=config_manager.get("database.postgres.port"),
                    database=config_manager.get("database.postgres.db"),
                    user=config_manager.get("database.postgres.user"),
                    password=config_manager.get("database.postgres.password"),
                    min_size=5,
                    max_size=20
                )
            except Exception as e:
                raise ConnectionError(f"Erreur de connexion à PostgreSQL: {str(e)}")
        return cls._pool
    
    @classmethod
    async def close_pool(cls) -> None:
        """Ferme le pool de connexions."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
    
    @staticmethod
    def _prepare_args(*args) -> tuple:
        """Prépare les arguments pour PostgreSQL."""
        def convert_arg(arg: Any) -> Any:
            if isinstance(arg, dict):
                # Convertir les datetime en chaînes ISO
                converted_dict = {}
                for key, value in arg.items():
                    if isinstance(value, datetime):
                        converted_dict[key] = value.isoformat()
                    elif isinstance(value, tuple):
                        # Convertir les tuples en listes pour la sérialisation JSON
                        converted_dict[key] = list(value)
                    elif isinstance(value, UUID):
                        # Convertir les UUID en chaînes
                        converted_dict[key] = str(value)
                    elif isinstance(value, list):
                        # Convertir les UUID dans les listes
                        converted_dict[key] = [str(v) if isinstance(v, UUID) else v for v in value]
                    elif isinstance(value, dict):
                        # Convertir les UUID dans les dictionnaires imbriqués
                        converted_dict[key] = {
                            str(k) if isinstance(k, UUID) else k: str(v) if isinstance(v, UUID) else v
                            for k, v in value.items()
                        }
                    else:
                        converted_dict[key] = value
                return json.dumps(converted_dict)
            elif isinstance(arg, datetime):
                return arg.isoformat()
            elif isinstance(arg, UUID):
                return str(arg)
            return arg
        return tuple(convert_arg(arg) for arg in args)
    
    @staticmethod
    def _process_row(row: dict) -> dict:
        """Traite une ligne de résultat PostgreSQL."""
        if not row:
            return row
            
        result = dict(row)
        for key, value in result.items():
            if isinstance(value, str) and key in ['preferences', 'history', 'stats', 'expertise', 'performance']:
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return result
    
    @classmethod
    async def execute(cls, query: str, *args) -> str:
        """Exécute une requête SQL."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *cls._prepare_args(*args))
    
    @classmethod
    async def fetch(cls, query: str, *args) -> list:
        """Exécute une requête SQL et retourne tous les résultats."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *cls._prepare_args(*args))
            return [cls._process_row(dict(row)) for row in rows]
    
    @classmethod
    async def fetchrow(cls, query: str, *args) -> Optional[dict]:
        """Exécute une requête SQL et retourne la première ligne."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *cls._prepare_args(*args))
            return cls._process_row(dict(row)) if row else None
    
    @classmethod
    async def init_tables(cls) -> None:
        """Initialise les tables nécessaires."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            # Table des utilisateurs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                    history JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table des créateurs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS creators (
                    id UUID PRIMARY KEY,
                    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
                    expertise JSONB NOT NULL DEFAULT '{}'::jsonb,
                    performance JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trigger pour mettre à jour updated_at
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Ajout des triggers aux tables
            for table in ['users', 'creators']:
                await conn.execute(f"""
                    DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                    CREATE TRIGGER update_{table}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """) 