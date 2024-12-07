import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

// Configuration des scénarios de test
export const options = {
  scenarios: {
    // Test de charge constant
    constant_load: {
      executor: 'constant-vus',
      vus: 10,
      duration: '30s',
    },
    // Test de montée en charge
    ramping_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 },
        { duration: '1m', target: 20 },
        { duration: '30s', target: 0 },
      ],
    },
    // Test de stress
    stress_test: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 100,
      stages: [
        { duration: '2m', target: 10 },
        { duration: '5m', target: 25 },
        { duration: '2m', target: 5 },
      ],
    },
  },
};

// Configuration de l'environnement
const BASE_URL = __ENV.API_URL || 'http://localhost:8000';

// Fonctions utilitaires
function checkResponse(response) {
  return check(response, {
    'status est 200': (r) => r.status === 200,
    'temps de réponse < 2000ms': (r) => r.timings.duration < 2000,
  });
}

// Scénarios de test
export default function () {
  // Test du endpoint de base score
  const baseScoreResponse = http.post(`${BASE_URL}/score/base`, {
    text: 'Exemple de texte pour le test de charge',
    context: 'Test de performance',
  });
  
  let checksBaseScore = checkResponse(baseScoreResponse);
  errorRate.add(!checksBaseScore);

  sleep(1);

  // Test du endpoint de score contextuel
  const contextualScoreResponse = http.post(`${BASE_URL}/score/contextual`, {
    text: 'Exemple de texte pour le test de charge',
    context: 'Test de performance',
    additionalContext: 'Contexte supplémentaire',
  });

  let checksContextual = checkResponse(contextualScoreResponse);
  errorRate.add(!checksContextual);

  sleep(1);

  // Test du endpoint de recommandation
  const recommendationResponse = http.post(`${BASE_URL}/recommendations`, {
    userId: 'test-user',
    text: 'Exemple de texte pour le test de charge',
  });

  let checksRecommendation = checkResponse(recommendationResponse);
  errorRate.add(!checksRecommendation);

  sleep(1);
} 