from datetime import datetime, UTC
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ItineraryPlace(BaseModel):
    """Modèle pour un lieu dans un itinéraire."""
    model_config = ConfigDict(from_attributes=True)

    place_id: UUID
    name: str
    latitude: float
    longitude: float
    recommended_time: datetime
    duration: int  # minutes
    score: float = Field(ge=0.0, le=1.0)
    context: Dict[str, float] = Field(default_factory=dict)
    creator_id: Optional[UUID] = None 