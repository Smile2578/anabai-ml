# anabai-ml/run_tests.ps1

# Activer l'environnement virtuel si nécessaire
if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

# Exécuter les tests avec pytest
python -m pytest tests -v --cov=anabai_ml 