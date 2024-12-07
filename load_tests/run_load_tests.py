import subprocess
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
from typing import Dict, List

class LoadTestRunner:
    def __init__(self, test_file: str, output_dir: str):
        self.test_file = test_file
        self.output_dir = output_dir
        self.results: Dict[str, Dict] = {}
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def run_test(self, scenario_name: str) -> None:
        """Exécute un scénario de test spécifique"""
        output_file = f"{self.output_dir}/{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        command = [
            "k6",
            "run",
            "--out",
            f"json={output_file}",
            f"--scenario",
            scenario_name,
            self.test_file
        ]
        
        print(f"Exécution du scénario: {scenario_name}")
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            print(f"Erreur lors de l'exécution du test: {process.stderr}")
            return
            
        self.results[scenario_name] = self._parse_results(output_file)

    def _parse_results(self, result_file: str) -> Dict:
        """Parse les résultats du test de charge"""
        with open(result_file, 'r') as f:
            data = [json.loads(line) for line in f]
            
        metrics = {
            'http_reqs': [],
            'http_req_duration': [],
            'vus': [],
            'errors': []
        }
        
        for point in data:
            if 'type' in point and point['type'] == 'Point':
                metric = point['metric']
                if metric in metrics:
                    metrics[metric].append({
                        'timestamp': point['data']['time'],
                        'value': point['data']['value']
                    })
                    
        return metrics

    def analyze_results(self) -> None:
        """Analyse et affiche les résultats des tests"""
        for scenario_name, metrics in self.results.items():
            print(f"\nAnalyse des résultats pour {scenario_name}:")
            
            # Conversion en DataFrame pour l'analyse
            for metric_name, data in metrics.items():
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    print(f"\n{metric_name}:")
                    print(f"Moyenne: {df['value'].mean():.2f}")
                    print(f"Médiane: {df['value'].median():.2f}")
                    print(f"95e percentile: {df['value'].quantile(0.95):.2f}")
                    
                    # Création du graphique
                    plt.figure(figsize=(10, 6))
                    plt.plot(df['timestamp'], df['value'])
                    plt.title(f"{scenario_name} - {metric_name}")
                    plt.xlabel("Temps")
                    plt.ylabel("Valeur")
                    plt.grid(True)
                    plt.savefig(f"{self.output_dir}/{scenario_name}_{metric_name}.png")
                    plt.close()

def main() -> None:
    runner = LoadTestRunner(
        test_file="load_test_scenarios.js",
        output_dir="./results"
    )
    
    scenarios: List[str] = ["constant_load", "ramping_load", "stress_test"]
    
    for scenario in scenarios:
        runner.run_test(scenario)
    
    runner.analyze_results()

if __name__ == "__main__":
    main() 