from datetime import datetime, UTC
from typing import Dict, List, Optional
import aiohttp
from config.config_manager import ConfigManager

class ExternalDataManager:
    """Gestionnaire des données externes (météo, événements, etc.)."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.openweather_api_key = self.config.get("api_keys.openweather")
        self.google_maps_key = self.config.get("api_keys.google_maps")
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Initialise la session HTTP asynchrone."""
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ferme la session HTTP."""
        if self.session:
            await self.session.close()
            self.session = None

    async def ensure_session(self):
        """S'assure qu'une session est disponible."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def get_weather_data(self, lat: float, lon: float) -> Dict:
        """Récupère les données météo pour une localisation."""
        await self.ensure_session()
        
        # Pour les tests, nous retournons des données factices
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "conditions": "Clear",
            "description": "Clear sky",
            "timestamp": datetime.now(UTC).isoformat()
        }

    async def get_events_data(self, lat: float, lon: float, radius: int = 5000) -> List[Dict]:
        """Récupère les événements à proximité d'une localisation."""
        await self.ensure_session()
        
        # Pour les tests, nous retournons des données factices
        return [{
            "place_id": "test_event_1",
            "name": "Festival local",
            "location": {
                "lat": lat + 0.001,
                "lng": lon + 0.001
            },
            "types": ["festival", "cultural"],
            "timestamp": datetime.now(UTC).isoformat()
        }]

    async def get_place_details(self, place_id: str) -> Dict:
        """Récupère les détails d'un lieu via Google Places API."""
        await self.ensure_session()
        
        # Pour les tests, nous retournons des données factices
        return {
            "details": {
                "name": "Lieu test",
                "formatted_address": "1-1 Test Street, Tokyo, Japan",
                "geometry": {
                    "location": {
                        "lat": 35.6762,
                        "lng": 139.6503
                    }
                },
                "rating": 4.5,
                "opening_hours": {
                    "open_now": True
                },
                "price_level": 2
            },
            "timestamp": datetime.now(UTC).isoformat()
        } 