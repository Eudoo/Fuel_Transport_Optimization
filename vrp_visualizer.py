"""
Module de visualisation pour le problème VRP de distribution de carburants.
Permet de visualiser :
1. L'instance chargée (garages, dépôts, stations)
2. Les tournées à partir d'un fichier de solution sauvegardé (sans relancer le solveur)
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.lines import Line2D
import os


class VRPVisualizer:
    """
    Classe pour visualiser les instances VRP et leurs solutions.
    """
    
    # Couleurs pour les différents types de nœuds
    COLORS = {
        'garage': '#2E86AB',      # Bleu
        'depot': '#A23B72',       # Violet/Magenta
        'essence': '#F18F01',     # Orange
        'gasoil': '#C73E1D',      # Rouge
    }
    
    # Couleurs pour les tournées (jusqu'à 12 camions)
    TRUCK_COLORS = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        '#bcbd22', '#17becf', '#aec7e8', '#ffbb78'
    ]
    
    def __init__(self, instance_file):
        """
        Initialise le visualiseur avec un fichier d'instance.
        
        Args:
            instance_file (str): Chemin vers le fichier JSON de l'instance
        """
        self.instance_file = instance_file
        self.data = None
        self.coords = {}  # Coordonnées de tous les nœuds
        self.solution_data = None  # Données de la solution chargée
        
        self._load_instance()
    
    def _load_instance(self):
        """Charge l'instance JSON."""
        with open(self.instance_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Extraire les coordonnées de tous les nœuds
        for garage in self.data['sites']['garages']:
            self.coords[garage['id']] = (garage['x'], garage['y'])
        
        for depot in self.data['sites']['depots']:
            self.coords[depot['id']] = (depot['x'], depot['y'])
        
        for station in self.data['sites']['stations']:
            self.coords[station['id']] = (station['x'], station['y'])
    
    def load_solution(self, solution_file):
        """
        Charge un fichier de solution JSON.
        
        Args:
            solution_file (str): Chemin vers le fichier JSON de la solution
        """
        with open(solution_file, 'r', encoding='utf-8') as f:
            self.solution_data = json.load(f)
        print(f"[OK] Solution chargée: {solution_file}")
        return self.solution_data
    
    def plot_instance(self, title=None, figsize=(12, 10), save_path=None):
        """
        Visualise l'instance : garages, dépôts et stations.
        
        Args:
            title (str): Titre du graphique
            figsize (tuple): Taille de la figure
            save_path (str): Chemin pour sauvegarder l'image (optionnel)
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Extraire les données
        garages = self.data['sites']['garages']
        depots = self.data['sites']['depots']
        stations = self.data['sites']['stations']
        
        # Plot des garages (carrés bleus)
        for g in garages:
            ax.scatter(g['x'], g['y'], c=self.COLORS['garage'], 
                      marker='s', s=200, zorder=5, edgecolors='black', linewidths=2)
            ax.annotate(g['id'], (g['x'], g['y']), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
        
        # Plot des dépôts (triangles violets)
        for d in depots:
            ax.scatter(d['x'], d['y'], c=self.COLORS['depot'], 
                      marker='^', s=250, zorder=5, edgecolors='black', linewidths=2)
            ax.annotate(d['id'], (d['x'], d['y']), textcoords="offset points", 
                       xytext=(0, 12), ha='center', fontsize=9, fontweight='bold')
            # Afficher les stocks
            stock_text = f"E:{d['stock_essence']//1000}k\nG:{d['stock_gasoil']//1000}k"
            ax.annotate(stock_text, (d['x'], d['y']), textcoords="offset points", 
                       xytext=(15, -5), ha='left', fontsize=7, color='gray')
        
        # Plot des stations (cercles orange/rouge selon le produit)
        for s in stations:
            color = self.COLORS['essence'] if s['type_produit'] == 'Essence' else self.COLORS['gasoil']
            ax.scatter(s['x'], s['y'], c=color, 
                      marker='o', s=100, zorder=4, edgecolors='black', linewidths=1)
            # Label avec demande
            label = f"{s['id']}\n({s['demande']//1000}k)"
            ax.annotate(label, (s['x'], s['y']), textcoords="offset points", 
                       xytext=(8, 0), ha='left', fontsize=7)
        
        # Légende
        legend_elements = [
            Line2D([0], [0], marker='s', color='w', markerfacecolor=self.COLORS['garage'], 
                   markersize=12, label='Garage', markeredgecolor='black'),
            Line2D([0], [0], marker='^', color='w', markerfacecolor=self.COLORS['depot'], 
                   markersize=12, label='Dépôt', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.COLORS['essence'], 
                   markersize=10, label='Station Essence', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.COLORS['gasoil'], 
                   markersize=10, label='Station Gasoil', markeredgecolor='black'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        
        # Titre et labels
        difficulty = self.data.get('meta', {}).get('difficulty', 'N/A')
        if title is None:
            title = f"Instance VRP - {difficulty}"
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('X (km)', fontsize=11)
        ax.set_ylabel('Y (km)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        # Statistiques
        stats_text = (f"Garages: {len(garages)} | Dépôts: {len(depots)} | "
                     f"Stations: {len(stations)} | Camions: {len(self.data['flotte'])}")
        ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[OK] Figure sauvegardée: {save_path}")
        
        plt.show()
        return fig, ax
    
    def plot_solution_from_file(self, solution_file=None, title=None, figsize=(14, 11), save_path=None):
        """
        Visualise la solution à partir d'un fichier de solution sauvegardé.
        
        Args:
            solution_file (str): Chemin vers le fichier JSON de la solution
                                 (si None, utilise la dernière solution chargée)
            title (str): Titre du graphique
            figsize (tuple): Taille de la figure
            save_path (str): Chemin pour sauvegarder l'image (optionnel)
        """
        # Charger la solution si nécessaire
        if solution_file:
            self.load_solution(solution_file)
        
        if not self.solution_data:
            raise ValueError("Aucune solution chargée. Utilisez load_solution() ou passez solution_file.")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # D'abord, dessiner les nœuds (comme dans plot_instance)
        garages = self.data['sites']['garages']
        depots = self.data['sites']['depots']
        stations = self.data['sites']['stations']
        
        # Plot des garages
        for g in garages:
            ax.scatter(g['x'], g['y'], c=self.COLORS['garage'], 
                      marker='s', s=200, zorder=5, edgecolors='black', linewidths=2)
            ax.annotate(g['id'], (g['x'], g['y']), textcoords="offset points", 
                       xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')
        
        # Plot des dépôts
        for d in depots:
            ax.scatter(d['x'], d['y'], c=self.COLORS['depot'], 
                      marker='^', s=250, zorder=5, edgecolors='black', linewidths=2)
            ax.annotate(d['id'], (d['x'], d['y']), textcoords="offset points", 
                       xytext=(0, 12), ha='center', fontsize=9, fontweight='bold')
        
        # Plot des stations
        for s in stations:
            color = self.COLORS['essence'] if s['type_produit'] == 'Essence' else self.COLORS['gasoil']
            ax.scatter(s['x'], s['y'], c=color, 
                      marker='o', s=100, zorder=4, edgecolors='black', linewidths=1)
            ax.annotate(s['id'], (s['x'], s['y']), textcoords="offset points", 
                       xytext=(8, 0), ha='left', fontsize=7)
        
        # Dessiner les tournées depuis le fichier de solution
        legend_trucks = []
        truck_idx = 0
        
        for tournee in self.solution_data.get('tournees', []):
            route = tournee.get('route', [])
            
            if len(route) < 2:
                continue
            
            # Couleur du camion
            color = self.TRUCK_COLORS[truck_idx % len(self.TRUCK_COLORS)]
            
            # Dessiner la route
            for i in range(len(route) - 1):
                start_node = route[i]
                end_node = route[i + 1]
                
                if start_node in self.coords and end_node in self.coords:
                    x1, y1 = self.coords[start_node]
                    x2, y2 = self.coords[end_node]
                    
                    # Dessiner la flèche
                    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                               arrowprops=dict(arrowstyle='->', color=color, lw=2, 
                                             shrinkA=8, shrinkB=8))
            
            # Infos pour la légende
            camion = tournee.get('camion', '?')
            produit = tournee.get('produit', '?')[:3] if tournee.get('produit') else '?'
            distance = tournee.get('distance_km', 0)
            charge = tournee.get('charge_L', 0)
            
            legend_trucks.append(
                Line2D([0], [0], color=color, lw=2, 
                       label=f"{camion} ({produit}) - {distance:.1f}km - {charge:.0f}L")
            )
            
            truck_idx += 1
        
        # Légendes
        # Légende des nœuds
        node_legend = [
            Line2D([0], [0], marker='s', color='w', markerfacecolor=self.COLORS['garage'], 
                   markersize=10, label='Garage', markeredgecolor='black'),
            Line2D([0], [0], marker='^', color='w', markerfacecolor=self.COLORS['depot'], 
                   markersize=10, label='Dépôt', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.COLORS['essence'], 
                   markersize=8, label='Essence', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=self.COLORS['gasoil'], 
                   markersize=8, label='Gasoil', markeredgecolor='black'),
        ]
        
        # Légende principale (nœuds)
        leg1 = ax.legend(handles=node_legend, loc='upper right', fontsize=8, title='Sites')
        ax.add_artist(leg1)
        
        # Légende des camions
        if legend_trucks:
            ax.legend(handles=legend_trucks, loc='upper left', fontsize=8, 
                     title='Tournées', ncol=1)
        
        # Titre
        difficulty = self.data.get('meta', {}).get('difficulty', 'N/A')
        if title is None:
            title = f"Solution VRP - {difficulty}"
        
        # Extraire les infos de la solution
        resultats = self.solution_data.get('resultats', {})
        total_dist = resultats.get('distance_totale_km', 0)
        statut = self.solution_data.get('meta', {}).get('statut', 'N/A')
        temps = self.solution_data.get('meta', {}).get('temps_resolution_sec', 0)
        
        ax.set_title(f"{title}\nDistance totale: {total_dist:.2f} km | Statut: {statut} | Temps: {temps:.2f}s", 
                    fontsize=14, fontweight='bold')
        
        ax.set_xlabel('X (km)', fontsize=11)
        ax.set_ylabel('Y (km)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        # Statistiques en bas
        nb_camions = resultats.get('camions_utilises', 0)
        nb_dispo = resultats.get('camions_disponibles', 0)
        charge_totale = resultats.get('charge_totale_L', 0)
        utilisation = resultats.get('utilisation_capacite_pct', 0)
        
        stats_text = (f"Camions: {nb_camions}/{nb_dispo} | "
                     f"Charge totale: {charge_totale:.0f}L | "
                     f"Utilisation: {utilisation:.1f}%")
        ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[OK] Figure sauvegardée: {save_path}")
        
        plt.show()
        return fig, ax
    
    def print_solution_summary(self):
        """Affiche un résumé de la solution chargée."""
        if not self.solution_data:
            print("Aucune solution chargée.")
            return
        
        print("\n" + "="*60)
        print("RÉSUMÉ DE LA SOLUTION")
        print("="*60)
        
        meta = self.solution_data.get('meta', {})
        print(f"\nInstance: {meta.get('instance', 'N/A')}")
        print(f"Date: {meta.get('date_resolution', 'N/A')}")
        print(f"Statut: {meta.get('statut', 'N/A')}")
        print(f"Temps de résolution: {meta.get('temps_resolution_sec', 0):.2f}s")
        
        resultats = self.solution_data.get('resultats', {})
        print(f"\nDistance totale: {resultats.get('distance_totale_km', 0):.2f} km")
        print(f"Camions utilisés: {resultats.get('camions_utilises', 0)}/{resultats.get('camions_disponibles', 0)}")
        print(f"Charge totale: {resultats.get('charge_totale_L', 0):.0f} L")
        print(f"Utilisation capacité: {resultats.get('utilisation_capacite_pct', 0):.1f}%")
        
        print("\n" + "-"*60)
        print("TOURNÉES")
        print("-"*60)
        
        for t in self.solution_data.get('tournees', []):
            print(f"\n{t.get('camion', '?')} ({t.get('produit', '?')}):")
            print(f"  Route: {' -> '.join(t.get('route', []))}")
            print(f"  Stations: {t.get('nb_stations', 0)}")
            print(f"  Distance: {t.get('distance_km', 0):.2f} km")
            print(f"  Charge: {t.get('charge_L', 0):.0f} L ({t.get('taux_remplissage_pct', 0):.1f}%)")
        
        print("\n" + "="*60)


def list_solutions(results_dir="results"):
    """
    Liste tous les fichiers de solution disponibles.
    
    Args:
        results_dir (str): Dossier contenant les solutions
    
    Returns:
        list: Liste des fichiers de solution
    """
    if not os.path.exists(results_dir):
        print(f"Le dossier '{results_dir}' n'existe pas.")
        return []
    
    solutions = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    solutions.sort(reverse=True)  # Plus récent en premier
    
    print(f"\n{'='*60}")
    print(f"SOLUTIONS DISPONIBLES ({len(solutions)})")
    print(f"{'='*60}\n")
    
    for i, sol in enumerate(solutions, 1):
        print(f"  [{i}] {sol}")
    
    print()
    return solutions


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def select_solution(solutions):
    """
    Permet à l'utilisateur de sélectionner une solution dans la liste.
    
    Args:
        solutions (list): Liste des fichiers de solution
    
    Returns:
        str: Nom du fichier sélectionné
    """
    while True:
        try:
            choice = input(f"Sélectionnez une solution (1-{len(solutions)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(solutions):
                return solutions[idx]
            print(f"[ERREUR] Veuillez entrer un nombre entre 1 et {len(solutions)}")
        except ValueError:
            print("[ERREUR] Veuillez entrer un nombre valide")


def extract_instance_name_from_solution(solution_filename):
    """
    Extrait le nom de l'instance à partir du nom du fichier solution.
    
    Format attendu: solution_<nom_instance>.json
    Exemple: solution_instance_facile_3.json -> instance_facile_3.json
    
    (Supporte aussi l'ancien format avec horodatage: solution_<nom_instance>_<date>_<heure>.json)
    
    Args:
        solution_filename (str): Nom du fichier solution
    
    Returns:
        str: Nom du fichier d'instance correspondant
    """
    # Enlever "solution_" au début et ".json" à la fin
    name = solution_filename.replace("solution_", "").replace(".json", "")
    
    # Vérifier si l'ancien format avec horodatage est utilisé
    # Format: instance_xxx_YYYYMMDD_HHMMSS
    parts = name.split("_")
    
    # Chercher si les 2 derniers segments sont date (8 chiffres) et heure (6 chiffres)
    if len(parts) >= 3:
        last = parts[-1]
        second_last = parts[-2]
        
        # Si c'est l'ancien format avec horodatage
        if (len(second_last) == 8 and second_last.isdigit() and 
            len(last) == 6 and last.isdigit()):
            # Enlever les 2 derniers segments (date et heure)
            name = "_".join(parts[:-2])
    
    return f"{name}.json"


def verify_solution_instance_coherence(solution_data, instance_data):
    """
    Vérifie la cohérence entre un fichier de solution et un fichier d'instance.
    
    Vérifie que:
    - Les mêmes nœuds (garages, dépôts, stations) existent
    - Les coordonnées correspondent
    - Les camions correspondent
    
    Args:
        solution_data (dict): Données de la solution
        instance_data (dict): Données de l'instance
    
    Returns:
        tuple: (bool, list) - (succès, liste des erreurs)
    """
    errors = []
    warnings = []
    
    print("\n" + "-"*60)
    print("VÉRIFICATION DE COHÉRENCE")
    print("-"*60)
    
    # 1. Extraire les nœuds de l'instance
    instance_nodes = {}
    
    for g in instance_data['sites']['garages']:
        instance_nodes[g['id']] = {'type': 'garage', 'x': g['x'], 'y': g['y']}
    
    for d in instance_data['sites']['depots']:
        instance_nodes[d['id']] = {'type': 'depot', 'x': d['x'], 'y': d['y']}
    
    for s in instance_data['sites']['stations']:
        instance_nodes[s['id']] = {'type': 'station', 'x': s['x'], 'y': s['y']}
    
    # 2. Vérifier que tous les nœuds des tournées existent dans l'instance
    solution_nodes = set()
    for tournee in solution_data.get('tournees', []):
        for node in tournee.get('route', []):
            solution_nodes.add(node)
    
    # Nœuds dans solution mais pas dans instance
    missing_in_instance = solution_nodes - set(instance_nodes.keys())
    if missing_in_instance:
        errors.append(f"Nœuds dans la solution mais absents de l'instance: {missing_in_instance}")
    
    # 3. Vérifier les statistiques générales
    sol_stats = solution_data.get('resultats', {})
    
    # Nombre de camions
    nb_camions_solution = sol_stats.get('camions_disponibles', 0)
    nb_camions_instance = len(instance_data.get('flotte', []))
    if nb_camions_solution != nb_camions_instance:
        warnings.append(f"Nombre de camions différent: solution={nb_camions_solution}, instance={nb_camions_instance}")
    
    # Nombre de stations
    nb_stations_instance = len(instance_data['sites']['stations'])
    
    # 4. Afficher les résultats
    print(f"\n[INFO] Nœuds dans l'instance: {len(instance_nodes)}")
    print(f"  - Garages: {len(instance_data['sites']['garages'])}")
    print(f"  - Dépôts: {len(instance_data['sites']['depots'])}")
    print(f"  - Stations: {nb_stations_instance}")
    print(f"[INFO] Nœuds référencés dans la solution: {len(solution_nodes)}")
    print(f"[INFO] Camions dans l'instance: {nb_camions_instance}")
    
    if errors:
        print("\n[ERREUR] Incohérences détectées:")
        for err in errors:
            print(f"  ❌ {err}")
        return False, errors
    
    if warnings:
        print("\n[ATTENTION] Avertissements:")
        for warn in warnings:
            print(f"  ⚠️ {warn}")
    
    print("\n[OK] ✅ Vérification réussie - Solution et instance sont cohérentes")
    return True, []


# ============================================================================
# MAIN - Programme principal
# ============================================================================

if __name__ == "__main__":
    
    print("\n" + "="*60)
    print("    VRP VISUALIZER - Visualisation des solutions")
    print("="*60)
    
    # 1. Lister les solutions disponibles
    solutions = list_solutions("results")
    
    if not solutions:
        print("[ERREUR] Aucune solution trouvée dans 'results/'.")
        print("Exécutez d'abord vrp_model.py pour générer une solution.")
        exit()
    
    # 2. L'utilisateur sélectionne explicitement une solution
    selected_solution = select_solution(solutions)
    solution_file = f"results/{selected_solution}"
    print(f"\n[OK] Solution sélectionnée: {solution_file}")
    
    # 3. Extraire le nom de l'instance depuis le nom de la solution
    instance_name = extract_instance_name_from_solution(selected_solution)
    instance_file = f"instances/{instance_name}"
    print(f"[INFO] Instance déduite: {instance_file}")
    
    # 4. Vérifier que l'instance existe
    if not os.path.exists(instance_file):
        print(f"\n[ERREUR] ❌ Le fichier d'instance n'existe pas: {instance_file}")
        print("Vérifiez que l'instance est dans le dossier 'instances/'")
        exit()
    
    print(f"[OK] Fichier d'instance trouvé")
    
    # 5. Charger les deux fichiers
    with open(solution_file, 'r', encoding='utf-8') as f:
        solution_data = json.load(f)
    
    with open(instance_file, 'r', encoding='utf-8') as f:
        instance_data = json.load(f)
    
    # 6. Vérifier la cohérence entre solution et instance
    is_coherent, errors = verify_solution_instance_coherence(solution_data, instance_data)
    
    if not is_coherent:
        print("\n[ERREUR] La solution et l'instance ne sont pas cohérentes.")
        print("Veuillez vérifier que vous avez sélectionné la bonne solution.")
        user_choice = input("\nContinuer quand même ? (o/n): ").strip().lower()
        if user_choice != 'o':
            exit()
    
    # 7. Créer le visualiseur et charger la solution
    viz = VRPVisualizer(instance_file)
    viz.load_solution(solution_file)
    
    # 8. Afficher le résumé de la solution
    viz.print_solution_summary()
    
    # 9. Visualiser l'instance
    print("\n" + "="*60)
    print("VISUALISATION DE L'INSTANCE")
    print("="*60)
    viz.plot_instance()
    
    # 10. Visualiser la solution
    print("\n" + "="*60)
    print("VISUALISATION DE LA SOLUTION")
    print("="*60)
    viz.plot_solution_from_file()
    
    print("\n[OK] Visualisation terminée.")
    
    # Optionnel: sauvegarder les figures
    # viz.plot_instance(save_path="figures/instance.png")
    # viz.plot_solution_from_file(save_path="figures/solution.png")
