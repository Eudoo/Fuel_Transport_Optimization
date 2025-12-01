import json
import random
import math
import os

class VRPInstanceGenerator:
    def __init__(self, config):
        """
        Initialise le générateur avec une configuration spécifique.
        config: dict contenant les paramètres (nb_garages, nb_stations, etc.)
        """
        self.conf = config
        self.width = config.get('grid_size', 100)
        self.height = config.get('grid_size', 100)
        self.products = ["Essence", "Gasoil"]
        
    def _generate_coords(self):
        """Génère des coordonnées (x, y) aléatoires."""
        return {
            "x": round(random.uniform(0, self.width), 2),
            "y": round(random.uniform(0, self.height), 2)
        }

    def _dist(self, p1, p2):
        """Distance Euclidienne entre deux points."""
        return round(math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2), 2)

    def _build_distance_matrix(self, all_sites):
        """
        Construit la matrice de distances pré-calculée entre tous les sites.
        Cette approche respecte l'énoncé : "Les distances [...] sont connues"
        et évite les erreurs d'arrondi entre générateur et solveur.
        """
        n = len(all_sites)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self._dist(all_sites[i], all_sites[j])
        
        return matrix

    def generate(self, filename):
        """Génère l'instance, valide la faisabilité et sauvegarde en JSON."""
        data = {
            "meta": {
                "difficulty": self.conf['difficulty'],
                "description": f"Instance {self.conf['difficulty']} générée aléatoirement."
            },
            "sites": {
                "garages": [],
                "depots": [],
                "stations": [] # Ces sont les demandes clients (potentiellement multi-produits)
            },
            "flotte": [],
            "distance_matrix": []
        }

        # 1. Génération des Garages
        for i in range(self.conf['num_garages']):
            data["sites"]["garages"].append({
                "id": f"G{i+1}",
                **self._generate_coords()
            })

        # 2. Génération des Stations avec support MULTI-PRODUITS
        # Correction Point 3 : Chaque station peut demander Essence ET/OU Gasoil
        total_demand = {"Essence": 0, "Gasoil": 0}
        station_coords = {}  # Mémoriser les coords de chaque station physique
        
        for i in range(self.conf['num_stations']):
            # Générer les coords UNE FOIS pour la station physique
            coords = self._generate_coords()
            station_coords[i] = coords
            
            # Déterminer les demandes pour cette station
            # Chaque station a une probabilité d'avoir Essence et/ou Gasoil
            demands = {}
            
            for prod in self.products:
                # Probabilité d'avoir une demande pour ce produit : 60%
                if random.random() < 0.6:
                    qty = random.randint(self.conf['min_demand'], self.conf['max_demand'])
                    demands[prod] = qty
                    total_demand[prod] += qty
            
            # Si la station n'a aucune demande, lui en attribuer au moins une
            if not demands:
                prod = random.choice(self.products)
                qty = random.randint(self.conf['min_demand'], self.conf['max_demand'])
                demands[prod] = qty
                total_demand[prod] += qty
            
            # Créer un nœud pour chaque demande de produit
            # Correction Point 2 : S1_E et S1_G partagent les mêmes coordonnées
            for prod, qty in demands.items():
                data["sites"]["stations"].append({
                    "id": f"S{i+1}_{prod[0]}",  # S1_E, S1_G, S2_E, etc.
                    "station_physique": i + 1,  # Référence à la station physique
                    "type_produit": prod,
                    "demande": qty,
                    **coords  # Mêmes coords pour les demandes de la même station
                })

        # 3. Génération des Dépôts et Stocks (Garantie de Faisabilité)
        # Logique : on calcule la demande PUIS on dimensionne les stocks
        # Cela garantit mathématiquement que Stock >= Demande
        stock_buffer = 1.5  # 50% de marge de sécurité
        avg_stock_per_depot_E = int((total_demand["Essence"] * stock_buffer) / self.conf['num_depots'])
        avg_stock_per_depot_G = int((total_demand["Gasoil"] * stock_buffer) / self.conf['num_depots'])

        for i in range(self.conf['num_depots']):
            data["sites"]["depots"].append({
                "id": f"D{i+1}",
                "stock_essence": avg_stock_per_depot_E,
                "stock_gasoil": avg_stock_per_depot_G,
                **self._generate_coords()
            })

        # 4. Génération de la Flotte (Garantie de Faisabilité)
        # On s'assure que Capacité Flotte >= Demande Totale Globale
        total_global_demand = sum(total_demand.values())
        min_trucks_needed = math.ceil(total_global_demand / self.conf['truck_capacity'])
        
        # On ajoute des camions selon la difficulté
        margin_trucks = self.conf.get('truck_margin', 2)
        num_trucks = min_trucks_needed + margin_trucks

        garages_ids = [g['id'] for g in data["sites"]["garages"]]

        # Correction Point 4 : Distribution Round-Robin pour équilibrer les garages
        for i in range(num_trucks):
            garage_idx = i % len(garages_ids)  # Round-robin : K1->G1, K2->G2, K3->G1, ...
            data["flotte"].append({
                "id": f"K{i+1}",
                "capacite": self.conf['truck_capacity'],
                "garage_depart": garages_ids[garage_idx]
            })

        # 5. Construction de la matrice de distances PRÉ-CALCULÉE
        # Correction Point 1 : Respecte l'énoncé "distances sont connues"
        all_sites = (
            data["sites"]["garages"] + 
            data["sites"]["depots"] + 
            data["sites"]["stations"]
        )
        data["distance_matrix"] = self._build_distance_matrix(all_sites)

        # Mapping des indices pour retrouver les sites dans la matrice
        data["site_index_map"] = {
            "garages": {g["id"]: i for i, g in enumerate(data["sites"]["garages"])},
            "depots": {d["id"]: len(data["sites"]["garages"]) + i 
                       for i, d in enumerate(data["sites"]["depots"])},
            "stations": {s["id"]: len(data["sites"]["garages"]) + len(data["sites"]["depots"]) + i 
                         for i, s in enumerate(data["sites"]["stations"])}
        }

        # Sauvegarde
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"[OK] Instance générée : {filename}")
        print(f"     Demande Totale: {total_global_demand} | Capacité Flotte: {num_trucks * self.conf['truck_capacity']}")
        print(f"     Essence: {total_demand['Essence']} | Gasoil: {total_demand['Gasoil']}")
        print(f"     Stations physiques: {self.conf['num_stations']} | Nœuds demande: {len(data['sites']['stations'])}")

# --- CONFIGURATION DES SCENARIOS (3 Niveaux) ---

scenarios = [
    {
        "difficulty": "FACILE",
        "num_garages": 1,
        "num_depots": 1,
        "num_stations": 5,
        "min_demand": 1000,
        "max_demand": 3000,
        "truck_capacity": 15000,
        "truck_margin": 3,
        "grid_size": 50
    },
    {
        "difficulty": "MOYEN",
        "num_garages": 2,
        "num_depots": 2,
        "num_stations": 15,
        "min_demand": 2000,
        "max_demand": 5000,
        "truck_capacity": 20000,
        "truck_margin": 2,
        "grid_size": 100
    },
    {
        "difficulty": "DIFFICILE",
        "num_garages": 3,
        "num_depots": 3,
        "num_stations": 40,
        "min_demand": 3000,
        "max_demand": 8000,
        "truck_capacity": 25000,
        "truck_margin": 0,
        "grid_size": 200
    }
]

# Exécution
if __name__ == "__main__":
    if not os.path.exists("instances"):
        os.makedirs("instances")
        
    gen_easy = VRPInstanceGenerator(scenarios[0])
    gen_easy.generate("instances/instance_facile.json")

    gen_medium = VRPInstanceGenerator(scenarios[1])
    gen_medium.generate("instances/instance_moyen.json")
    
    gen_hard = VRPInstanceGenerator(scenarios[2])
    gen_hard.generate("instances/instance_difficile_1.json")
    gen_hard.generate("instances/instance_difficile_2.json")
    gen_hard.generate("instances/instance_difficile_3.json")