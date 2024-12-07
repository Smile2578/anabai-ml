"""Module d'adaptation des itinéraires en temps réel."""

from .real_time_adapter import (
    RealTimeAdapter,
    WeatherCondition,
    CrowdLevel,
    LocalEvent,
    AdaptationResult as RealTimeAdaptationResult
)
from .adaptation_engine import (
    AdaptationEngine,
    AdaptationDecision,
    AdaptationResult as EngineAdaptationResult
)

__all__ = [
    'RealTimeAdapter',
    'WeatherCondition',
    'CrowdLevel',
    'LocalEvent',
    'RealTimeAdaptationResult',
    'AdaptationEngine',
    'AdaptationDecision',
    'EngineAdaptationResult'
] 