from datetime import datetime, UTC, timedelta
from typing import Dict, List, Tuple
from uuid import UUID
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from ai.learning.data_collector import DataCollector
from ai.learning.pattern_analyzer import PatternAnalyzer

class FormulaEvolver:
    """
    Ajuste dynamiquement les paramètres de scoring, les poids et multiplicateurs,
    en testant et adoptant les modifications les plus efficaces.
    """

    def __init__(
        self,
        data_collector: DataCollector,
        pattern_analyzer: PatternAnalyzer,
        learning_rate: float = 0.01,
        min_improvement: float = 0.05
    ) -> None:
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("Le taux d'apprentissage doit être entre 0 et 1")
        if not 0.0 < min_improvement <= 1.0:
            raise ValueError("L'amélioration minimale doit être entre 0 et 1")

        self.data_collector = data_collector
        self.pattern_analyzer = pattern_analyzer
        self.learning_rate = learning_rate
        self.min_improvement = min_improvement
        self.model = GradientBoostingRegressor(
            learning_rate=learning_rate,
            n_estimators=100,
            max_depth=3
        )
        self.current_weights: Dict[str, float] = {}
        self.evolution_history: List[Dict[str, float]] = []

    async def train_on_historical_data(
        self,
        time_window_days: int = 30
    ) -> Dict[str, float]:
        """
        Entraîne le modèle sur les données historiques pour trouver
        les meilleurs poids.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=time_window_days)
        
        # Récupérer les feedbacks récents
        cursor = self.data_collector.feedback_collection.find({
            "timestamp": {"$gte": cutoff_date}
        })
        feedbacks = await cursor.to_list(length=1000)

        if not feedbacks:
            return self.current_weights

        # Préparer les données d'entraînement
        X = []  # Features (contexte et facteurs)
        y = []  # Target (ratings)

        for feedback in feedbacks:
            features = []
            context = feedback.get("context", {})
            
            # Ajouter les features de contexte
            for factor in ["weather", "crowd", "time_of_day", "seasonal"]:
                features.append(context.get(factor, 0.5))
            
            X.append(features)
            y.append(feedback["rating"])

        if len(X) < 10:  # Pas assez de données
            return self.current_weights

        # Diviser en train/test
        X_train, X_test, y_train, y_test = train_test_split(
            np.array(X), np.array(y), test_size=0.2, random_state=42
        )

        # Entraîner le modèle
        self.model.fit(X_train, y_train)

        # Calculer les nouveaux poids
        feature_importance = self.model.feature_importances_
        factors = ["weather", "crowd", "time_of_day", "seasonal"]
        new_weights = {
            factor: float(importance)
            for factor, importance in zip(factors, feature_importance)
        }

        # Vérifier l'amélioration
        if self._evaluate_improvement(new_weights, X_test, y_test):
            self.current_weights = new_weights
            self.evolution_history.append({
                "weights": new_weights.copy(),
                "timestamp": datetime.now(UTC),
                "score": float(self.model.score(X_test, y_test))
            })

        return self.current_weights

    async def evolve_contextual_multipliers(
        self,
        min_rating: float = 4.0
    ) -> Dict[str, float]:
        """
        Fait évoluer les multiplicateurs contextuels en fonction
        des combinaisons réussies.
        """
        if not 0.0 <= min_rating <= 5.0:
            raise ValueError("La note minimale doit être entre 0 et 5")

        successful_combinations = await self.pattern_analyzer.find_successful_combinations(
            min_rating=min_rating
        )

        if not successful_combinations:
            return {}

        # Calculer les nouveaux multiplicateurs
        multipliers: Dict[str, List[float]] = {}
        frequencies: Dict[str, List[float]] = {}
        
        for combination in successful_combinations:
            frequency = combination.get("frequency", 1.0)
            for factor, value in combination.items():
                if factor != "frequency":
                    if factor not in multipliers:
                        multipliers[factor] = []
                        frequencies[factor] = []
                    multipliers[factor].append(value)
                    frequencies[factor].append(frequency)

        # Moyenner les multiplicateurs pondérés par la fréquence
        final_multipliers = {}
        for factor, values in multipliers.items():
            weights = np.array(frequencies[factor])
            values_array = np.array(values)
            final_multipliers[factor] = float(np.average(values_array, weights=weights))

        return final_multipliers

    def _evaluate_improvement(
        self,
        new_weights: Dict[str, float],
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> bool:
        """
        Évalue si les nouveaux poids apportent une amélioration significative.
        """
        if not self.current_weights:
            return True

        # Prédire avec les anciens poids
        old_predictions = np.zeros_like(y_test)
        for i, factor in enumerate(self.current_weights.keys()):
            old_predictions += X_test[:, i] * self.current_weights[factor]

        # Prédire avec les nouveaux poids
        new_predictions = np.zeros_like(y_test)
        for i, factor in enumerate(new_weights.keys()):
            new_predictions += X_test[:, i] * new_weights[factor]

        # Calculer l'amélioration
        old_mse = np.mean((y_test - old_predictions) ** 2)
        new_mse = np.mean((y_test - new_predictions) ** 2)
        
        improvement = (old_mse - new_mse) / old_mse
        return improvement >= self.min_improvement

    async def get_evolution_history(
        self,
        limit: int = 10
    ) -> List[Dict[str, float]]:
        """
        Récupère l'historique des évolutions des poids.
        """
        if limit < 1:
            raise ValueError("La limite doit être positive")
            
        return self.evolution_history[-limit:] 