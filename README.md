# AnabAI ML

Module d'Intelligence Artificielle pour AnabAI - Votre assistant de voyage intelligent pour le Japon.

## Description

AnabAI ML est le cœur intelligent d'AnabAI, combinant l'expertise des créateurs de contenu avec des algorithmes d'apprentissage automatique pour générer des itinéraires de voyage personnalisés au Japon.

## Fonctionnalités

- Génération d'itinéraires personnalisés
- Adaptation en temps réel aux conditions (météo, affluence, événements)
- Apprentissage continu basé sur les retours utilisateurs
- Intégration des connaissances des créateurs de contenu

## Structure du Projet

```
anabai-ml/
├── config/               # Configuration du projet
├── data_feeds/          # Gestion des données externes
├── ai/                  # Cœur de l'IA
│   ├── context/        # Gestion du contexte
│   ├── scoring/        # Système de scoring
│   ├── templates/      # Templates d'itinéraires
│   ├── adaptation/     # Adaptation en temps réel
│   ├── learning/       # Apprentissage continu
│   └── monitoring/     # Surveillance et métriques
└── tests/              # Tests unitaires et d'intégration
```

## Prérequis

- Python 3.9+
- PostgreSQL 13+
- MongoDB 5+
- Redis 6+

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-repo/anabai-ml.git
cd anabai-ml
```

2. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

## Tests

Exécuter les tests unitaires :
```bash
pytest
```

Exécuter les tests avec couverture :
```bash
pytest --cov=anabai_ml tests/
```

## Utilisation

```python
from anabai_ml.config import config_manager
from anabai_ml.ai.templates import TemplateSelector

# Charger la configuration
config = config_manager.config

# Créer un sélecteur de template
selector = TemplateSelector()

# Générer un itinéraire
itinerary = selector.generate_itinerary(user_preferences)
```

## Contribution

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Contact

- Email : contact@anabai.com
- Site Web : https://anabai.com 