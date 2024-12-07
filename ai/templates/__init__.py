"""Module de gestion des templates d'itinéraires."""

from .signature_template import SignatureTemplate, SignatureItinerary, ItineraryPlace
from .fusion_template import FusionTemplate, FusionItinerary
from .ai_plus_template import AIPlusTemplate, AIPlusItinerary, AIRecommendation
from .template_selector import TemplateSelector, TemplateSelectionCriteria

__all__ = [
    'SignatureTemplate',
    'SignatureItinerary',
    'ItineraryPlace',
    'FusionTemplate',
    'FusionItinerary',
    'AIPlusTemplate',
    'AIPlusItinerary',
    'AIRecommendation',
    'TemplateSelector',
    'TemplateSelectionCriteria'
] 