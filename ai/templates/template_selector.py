"""Module de sélection du template d'itinéraire approprié."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from config.config_manager import ConfigManager
from .signature_template import SignatureTemplate
from .fusion_template import FusionTemplate
from .ai_plus_template import AIPlusTemplate

class TemplateSelectionCriteria(BaseModel):
    """Critères pour la sélection du template."""
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    creator_ids: List[UUID]
    preferences: Dict[str, float]
    start_time: datetime
    duration: int
    excluded_places: Optional[List[UUID]] = None
    min_creator_score: float = Field(ge=0.0, le=1.0, default=0.7)
    min_ai_confidence: float = Field(ge=0.0, le=1.0, default=0.8)

class TemplateSelector:
    """Sélecteur de template d'itinéraire."""

    def __init__(self):
        self.config = ConfigManager()
        self.signature_template = SignatureTemplate()
        self.fusion_template = FusionTemplate()
        self.ai_plus_template = AIPlusTemplate()
        self._load_config()

    def _load_config(self) -> None:
        """Charge la configuration du sélecteur."""
        self.min_creators_for_fusion = self.config.get(
            "templates.fusion.min_creators", 2
        )
        self.max_creators_for_fusion = self.config.get(
            "templates.fusion.max_creators", 5
        )
        self.min_creators_for_ai_plus = self.config.get(
            "templates.ai_plus.min_creators", 3
        )

    async def select_template(self, criteria: TemplateSelectionCriteria):
        """Sélectionne le template le plus approprié."""
        num_creators = len(criteria.creator_ids)

        # Si un seul créateur, utiliser SignatureTemplate
        if num_creators == 1:
            return self.signature_template

        # Si entre 2 et 5 créateurs, utiliser FusionTemplate
        if self.min_creators_for_fusion <= num_creators <= self.max_creators_for_fusion:
            return self.fusion_template

        # Si plus de 5 créateurs, utiliser AIPlusTemplate
        if num_creators >= self.min_creators_for_ai_plus:
            return self.ai_plus_template

        # Par défaut, utiliser FusionTemplate
        return self.fusion_template

    async def generate_itinerary(self, criteria: TemplateSelectionCriteria):
        """Génère un itinéraire en utilisant le template le plus approprié."""
        template = await self.select_template(criteria)

        # Pour SignatureTemplate, on prend le premier créateur
        if isinstance(template, SignatureTemplate):
            return await template.generate(
                creator_id=criteria.creator_ids[0],
                preferences=criteria.preferences,
                start_time=criteria.start_time,
                duration=criteria.duration,
                excluded_places=criteria.excluded_places or []
            )
        
        # Pour les autres templates, on passe la liste complète
        return await template.generate(
            creator_ids=criteria.creator_ids,
            preferences=criteria.preferences,
            start_time=criteria.start_time,
            duration=criteria.duration,
            excluded_places=criteria.excluded_places or []
        ) 