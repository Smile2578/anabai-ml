from datetime import datetime, UTC, timedelta
from typing import Dict, List, Tuple
from uuid import UUID
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from ai.learning.data_collector import DataCollector

class PatternAnalyzer:
    """
    Détecte des schémas dans les données collectées et identifie les corrélations
    pour affiner la compréhension de ce qui fonctionne ou non.
    """

    def __init__(self, data_collector: DataCollector) -> None:
        self.data_collector = data_collector
        self.scaler = StandardScaler()

    async def analyze_user_preferences(
        self,
        user_id: UUID,
        time_window_days: int = 30
    ) -> Dict[str, float]:
        """
        Analyse les préférences d'un utilisateur basées sur son historique récent.
        """
        feedbacks = await self.data_collector.get_user_feedback_history(user_id)
        
        if not feedbacks:
            return {}

        # Filtrer par fenêtre temporelle
        cutoff_date = datetime.now(UTC) - timedelta(days=time_window_days)
        recent_feedbacks = [
            f for f in feedbacks 
            if f["timestamp"] >= cutoff_date
        ]

        if not recent_feedbacks:
            return {}

        # Analyser les patterns de notation
        ratings = np.array([f["rating"] for f in recent_feedbacks])
        contexts = [f.get("context", {}) for f in recent_feedbacks]
        
        # Calculer les corrélations contexte-notation
        context_correlations: Dict[str, float] = {}
        
        for key in contexts[0].keys():
            context_values = np.array([
                ctx.get(key, 0.0) for ctx in contexts
            ])
            correlation = np.corrcoef(ratings, context_values)[0, 1]
            context_correlations[key] = float(correlation)

        return context_correlations

    async def detect_usage_patterns(
        self,
        time_window_days: int = 7
    ) -> List[Dict[str, float]]:
        """
        Détecte des patterns dans les données d'utilisation.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=time_window_days)
        
        # Récupérer les données d'utilisation via une nouvelle méthode du collector
        cursor = self.data_collector.usage_collection.find({
            "timestamp": {"$gte": cutoff_date}
        })
        usage_data = await cursor.to_list(length=1000)

        if not usage_data:
            return []

        # Préparer les features pour le clustering
        features = []
        for data in usage_data:
            if "data" in data:
                numeric_features = [
                    float(v) for v in data["data"].values()
                    if isinstance(v, (int, float))
                ]
                if numeric_features:
                    features.append(numeric_features)

        if not features:
            return []

        # Normaliser les features
        features_array = np.array(features)
        normalized_features = self.scaler.fit_transform(features_array)

        # Clustering avec DBSCAN
        clustering = DBSCAN(eps=0.3, min_samples=5)
        clusters = clustering.fit_predict(normalized_features)

        # Analyser les clusters
        patterns = []
        for cluster_id in set(clusters):
            if cluster_id == -1:  # Points de bruit
                continue
                
            cluster_mask = clusters == cluster_id
            cluster_features = features_array[cluster_mask]
            
            pattern = {
                "cluster_id": int(cluster_id),
                "size": int(cluster_mask.sum()),
                "mean_values": cluster_features.mean(axis=0).tolist(),
                "std_values": cluster_features.std(axis=0).tolist()
            }
            patterns.append(pattern)

        return patterns

    async def find_successful_combinations(
        self,
        min_rating: float = 4.0,
        min_samples: int = 5
    ) -> List[Dict[str, float]]:
        """
        Identifie les combinaisons de facteurs qui mènent à des recommandations réussies.
        """
        # Récupérer les feedbacks positifs
        cursor = self.data_collector.feedback_collection.find({
            "rating": {"$gte": min_rating}
        })
        successful_feedbacks = await cursor.to_list(length=1000)

        if len(successful_feedbacks) < min_samples:
            return []

        # Extraire les contextes
        contexts = [
            feedback.get("context", {})
            for feedback in successful_feedbacks
        ]

        if not contexts:
            return []

        # Préparer les données pour l'analyse
        feature_names = list(contexts[0].keys())
        features = np.array([
            [ctx.get(key, 0.0) for key in feature_names]
            for ctx in contexts
        ])

        # Normaliser et clustering
        normalized_features = self.scaler.fit_transform(features)
        clustering = DBSCAN(eps=0.3, min_samples=min_samples)
        clusters = clustering.fit_predict(normalized_features)

        # Analyser les combinaisons réussies
        successful_combinations = []
        for cluster_id in set(clusters):
            if cluster_id == -1:
                continue
                
            cluster_mask = clusters == cluster_id
            cluster_features = features[cluster_mask]
            
            combination = {
                feature_names[i]: float(cluster_features.mean(axis=0)[i])
                for i in range(len(feature_names))
            }
            combination["frequency"] = float(cluster_mask.sum() / len(clusters))
            successful_combinations.append(combination)

        return successful_combinations 