import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Métriques personnalisées
const errorRate = new Rate('errors');
const scoreBaseTrend = new Trend('score_base_duration');
const scoreContextualTrend = new Trend('score_contextual_duration');
const recommendationsTrend = new Trend('recommendations_duration');

// Configuration du test
export const options = {
    stages: [
        { duration: '30s', target: 5 },   // Montée progressive à 5 utilisateurs
        { duration: '1m', target: 20 },   // Montée à 20 utilisateurs
        { duration: '2m', target: 50 },   // Test de charge à 50 utilisateurs
        { duration: '30s', target: 0 },   // Retour au calme
    ],
    thresholds: {
        'http_req_duration': ['p(95)<1000'], // 95% des requêtes sous 1s
        'errors': ['rate<0.01'],             // Moins de 1% d'erreurs
    },
};

// Données de test
const scoreRequest = {
    text: "Ceci est un texte de test pour le calcul du score",
    context: "Contexte de test pour l'analyse"
};

const recommendationRequest = {
    user_id: "test-user-123",
    text: "Texte pour obtenir des recommandations"
};

// Fonction principale de test
export default function() {
    const baseUrl = 'http://localhost:8000';
    const params = {
        headers: {
            'Content-Type': 'application/json',
        }
    };

    // Test du score de base
    const scoreBaseStart = new Date();
    const scoreBaseResponse = http.post(
        `${baseUrl}/score/base`,
        JSON.stringify(scoreRequest),
        params
    );
    scoreBaseTrend.add(new Date() - scoreBaseStart);

    // Test du score contextuel
    const scoreContextualStart = new Date();
    const scoreContextualResponse = http.post(
        `${baseUrl}/score/contextual`,
        JSON.stringify(scoreRequest),
        params
    );
    scoreContextualTrend.add(new Date() - scoreContextualStart);

    // Test des recommandations
    const recommendationsStart = new Date();
    const recommendationsResponse = http.post(
        `${baseUrl}/recommendations`,
        JSON.stringify(recommendationRequest),
        params
    );
    recommendationsTrend.add(new Date() - recommendationsStart);

    // Vérifications
    check(scoreBaseResponse, {
        'score base status is 200': (r) => r.status === 200,
        'score base has score': (r) => r.json('score') !== undefined,
    });

    check(scoreContextualResponse, {
        'score contextual status is 200': (r) => r.status === 200,
        'score contextual has score': (r) => r.json('score') !== undefined,
    });

    check(recommendationsResponse, {
        'recommendations status is 200': (r) => r.status === 200,
        'recommendations has recommendations': (r) => r.json('recommendations') !== undefined,
    });

    // Enregistrement des erreurs
    errorRate.add(scoreBaseResponse.status !== 200);
    errorRate.add(scoreContextualResponse.status !== 200);
    errorRate.add(recommendationsResponse.status !== 200);

    // Pause entre les requêtes
    sleep(1);
}

// Fonction de configuration
export function setup() {
    const healthCheck = http.get('http://localhost:8000/health');
    check(healthCheck, {
        'health check passed': (r) => r.status === 200,
    });
}

// Fonction de gestion des erreurs
export function handleSummary(data) {
    return {
        'stdout': JSON.stringify({
            'total_requests': data.metrics.http_reqs.values.count,
            'error_rate': data.metrics.errors.values.rate,
            'p95_response_time': data.metrics.http_req_duration.values['p(95)'],
            'p95_score_base_time': data.metrics.score_base_duration.values['p(95)'],
            'p95_score_contextual_time': data.metrics.score_contextual_duration.values['p(95)'],
            'p95_recommendations_time': data.metrics.recommendations_duration.values['p(95)'],
        }, null, 2),
        'load_test_summary.json': JSON.stringify(data, null, 2),
    };
} 