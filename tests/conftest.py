import os
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir)) 