import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Métriques personnalisées
const errorRate = new Rate('errors');
const generateTrend = new Trend('generate_duration');

// Configuration du test
export const options = {
    stages: [
        { duration: '1m', target: 10 },  // Montée progressive à 10 utilisateurs
        { duration: '3m', target: 50 },  // Montée à 50 utilisateurs
        { duration: '5m', target: 100 }, // Test de charge à 100 utilisateurs
        { duration: '1m', target: 0 },   // Retour au calme
    ],
    thresholds: {
        'http_req_duration': ['p(95)<1000'], // 95% des requêtes sous 1s
        'errors': ['rate<0.01'],             // Moins de 1% d'erreurs
        'generate_duration': ['p(95)<2000'],  // 95% des générations sous 2s
    },
};

// Données de test
const testData = {
    preferences: {
        style: ['culturel', 'gastronomique', 'historique'],
        budget: 'moyen',
        duration: 'journée',
        accessibility: 'standard'
    },
    constraints: {
        startTime: '09:00',
        endTime: '18:00',
        maxDistance: 5000,
        excludedPlaces: []
    },
    context: {
        weather: 'ensoleillé',
        season: 'printemps',
        crowdLevel: 'modéré'
    }
};

// Fonction principale de test
export default function() {
    const url = 'http://localhost:8000/generate';
    const payload = JSON.stringify(testData);
    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
        }
    };

    // Envoi de la requête
    const startTime = new Date();
    const response = http.post(url, payload, params);
    const duration = new Date() - startTime;

    // Enregistrement des métriques
    generateTrend.add(duration);
    errorRate.add(response.status !== 200);

    // Vérifications
    check(response, {
        'status is 200': (r) => r.status === 200,
        'response has itinerary': (r) => r.json('itinerary') !== undefined,
        'response time OK': (r) => r.timings.duration < 1000,
    });

    // Pause entre les requêtes
    sleep(1);
}

// Fonction de nettoyage
export function teardown(data) {
    console.log('Test de charge terminé');
}

// Fonction de configuration
export function setup() {
    // Vérification que le service est disponible
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
            'average_generate_time': data.metrics.generate_duration.values.avg,
        }, null, 2),
        'load_test_summary.json': JSON.stringify(data, null, 2),
    };
} 