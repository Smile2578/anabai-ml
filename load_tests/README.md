# Tests de Charge AnabAI

Ce dossier contient les scripts et configurations nécessaires pour exécuter des tests de charge sur l'API AnabAI.

## Prérequis

1. Installation de k6 :
   ```bash
   # Pour Windows (avec chocolatey)
   choco install k6

   # Pour macOS
   brew install k6

   # Pour Linux
   sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6
   ```

2. Dépendances Python :
   ```bash
   pip install pandas matplotlib
   ```

## Structure des Tests

- `load_test_scenarios.js` : Définition des scénarios de test k6
- `run_load_tests.py` : Script Python pour exécuter et analyser les tests
- `results/` : Dossier contenant les résultats des tests

## Scénarios de Test

1. **Charge Constante (constant_load)**
   - 10 utilisateurs virtuels constants
   - Durée : 30 secondes

2. **Montée en Charge (ramping_load)**
   - Démarre avec 0 utilisateur
   - Monte jusqu'à 20 utilisateurs sur 30 secondes
   - Maintient 20 utilisateurs pendant 1 minute
   - Redescend à 0 sur 30 secondes

3. **Test de Stress (stress_test)**
   - Démarre avec 1 requête par seconde
   - Monte jusqu'à 25 requêtes par seconde
   - Durée totale : 9 minutes

## Exécution des Tests

1. Démarrer votre API AnabAI en local ou spécifier l'URL de l'API :
   ```bash
   export API_URL=http://votre-api-url
   ```

2. Exécuter tous les scénarios de test :
   ```bash
   python run_load_tests.py
   ```

3. Exécuter un scénario spécifique avec k6 directement :
   ```bash
   k6 run --scenario constant_load load_test_scenarios.js
   ```

## Analyse des Résultats

Les résultats sont automatiquement analysés et des graphiques sont générés dans le dossier `results/`. Pour chaque scénario, vous trouverez :

- Fichiers JSON avec les données brutes
- Graphiques des métriques clés :
  - Nombre de requêtes
  - Durée des requêtes
  - Nombre d'utilisateurs virtuels
  - Taux d'erreur

## Métriques Surveillées

- **http_reqs** : Nombre total de requêtes HTTP
- **http_req_duration** : Durée des requêtes HTTP
- **vus** : Nombre d'utilisateurs virtuels actifs
- **errors** : Nombre d'erreurs rencontrées

## Interprétation des Résultats

- Moyenne : Valeur moyenne de la métrique
- Médiane : Valeur médiane (50e percentile)
- 95e percentile : Valeur en dessous de laquelle se trouvent 95% des mesures 