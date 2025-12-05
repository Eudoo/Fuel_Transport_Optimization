import json
import random
import math
import os

class VRPInstanceGenerator:
    def __init__(self, config):
        self.conf = config
        self.width = config.get('grid_size', 100)
        self.height = config.get('grid_size', 100)
        self.products = ["Essence", "Gasoil"]
        
    def _generate_coords(self):
        return {
            "x": round(random.uniform(0, self.width), 2),
            "y": round(random.uniform(0, self.height), 2)
        }

    def _dist(self, p1, p2):
        """Distance Euclidienne arrondie."""
        return round(math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2), 2)

    def generate(self, filename):
        data = {
            "meta": {
                "difficulty": self.conf['difficulty'],
                "description": f"Instance {self.conf['difficulty']} avec flotte hétérogène."
            },
            "sites": {
                "garages": [],
                "depots": [],
                "stations": [] 
            },
            "flotte": [],
            "distances": {} # Format dictionnaire pour lecture facile
        }

        # ---------------------------------------------------------
        # 1. SITES PHYSIQUES (Garages & Dépôts)
        # ---------------------------------------------------------
        for i in range(self.conf['num_garages']):
            data["sites"]["garages"].append({
                "id": f"G{i+1}",
                **self._generate_coords()
            })

        for i in range(self.conf['num_depots']):
            data["sites"]["depots"].append({
                "id": f"D{i+1}",
                "stock_essence": 0, "stock_gasoil": 0, # Calculé plus tard
                **self._generate_coords()
            })

        # ---------------------------------------------------------
        # 2. STATIONS (Multi-produits + Coordonnées partagées)
        # ---------------------------------------------------------
        total_demand = {"Essence": 0, "Gasoil": 0}
        
        for i in range(self.conf['num_stations']):
            # Coordonnées physiques uniques pour ce lieu client
            coords = self._generate_coords()
            
            # Logique de probabilité
            has_essence = random.random() < 0.6
            has_gasoil = random.random() < 0.6
            
            # Sécurité : la station doit vouloir au moins un truc
            if not has_essence and not has_gasoil:
                if random.random() < 0.5: has_essence = True
                else: has_gasoil = True
            
            # Création des nœuds virtuels
            if has_essence:
                qty = random.randint(self.conf['min_demand'], self.conf['max_demand'])
                total_demand["Essence"] += qty
                data["sites"]["stations"].append({
                    "id": f"S{i+1}_E", 
                    "station_physique": i+1,
                    "type_produit": "Essence",
                    "demande": qty,
                    **coords
                })

            if has_gasoil:
                qty = random.randint(self.conf['min_demand'], self.conf['max_demand'])
                total_demand["Gasoil"] += qty
                data["sites"]["stations"].append({
                    "id": f"S{i+1}_G", 
                    "station_physique": i+1,
                    "type_produit": "Gasoil",
                    "demande": qty,
                    **coords
                })

        # ---------------------------------------------------------
        # 3. STOCKS (Garantie Faisabilité)
        # ---------------------------------------------------------
        margin = 1.5
        for depot in data["sites"]["depots"]:
            depot["stock_essence"] = int((total_demand["Essence"] * margin) / self.conf['num_depots'])
            depot["stock_gasoil"] = int((total_demand["Gasoil"] * margin) / self.conf['num_depots'])

        # ---------------------------------------------------------
        # 4. FLOTTE HÉTÉROGÈNE (Correction Majeure)
        # ---------------------------------------------------------
        total_global_demand = sum(total_demand.values())
        target_capacity = total_global_demand * (1.0 + (self.conf['truck_margin'] * 0.1))
        
        current_cap = 0
        k_id = 1
        garages = data["sites"]["garages"]
        
        while current_cap < target_capacity:
            # Choix aléatoire d'un type de camion (Petit, Moyen, Gros)
            cap = random.choice(self.conf['truck_types'])
            
            # Round Robin pour les garages
            g_idx = (k_id - 1) % len(garages)
            
            data["flotte"].append({
                "id": f"K{k_id}",
                "capacite": cap,
                "garage_depart": garages[g_idx]["id"]
            })
            current_cap += cap
            k_id += 1

        # ---------------------------------------------------------
        # 5. MATRICE DE DISTANCES (Dictionnaire)
        # ---------------------------------------------------------
        all_nodes = data["sites"]["garages"] + data["sites"]["depots"] + data["sites"]["stations"]
        
        matrix = {}
        for n1 in all_nodes:
            matrix[n1["id"]] = {}
            for n2 in all_nodes:
                if n1["id"] == n2["id"]:
                    dist = 0.0
                else:
                    dist = self._dist(n1, n2)
                matrix[n1["id"]][n2["id"]] = dist
        
        data["distances"] = matrix

        # Sauvegarde
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"[OK] {filename} | Dmd: {total_global_demand} | Cap: {current_cap} | Camions: {len(data['flotte'])}")

# --- CONFIGURATION MISE A JOUR (Avec truck_types) ---

scenarios = [
    {
        "difficulty": "FACILE",
        "num_garages": 1, "num_depots": 1, "num_stations": 5,
        "min_demand": 1000, "max_demand": 3000,
        "truck_types": [15000], # Un seul type pour facile
        "truck_margin": 3,
        "grid_size": 50
    },
    {
        "difficulty": "MOYEN",
        "num_garages": 2, "num_depots": 2, "num_stations": 8,
        "min_demand": 2000, "max_demand": 5000,
        "truck_types": [15000, 20000, 25000], # Mixte
        "truck_margin": 1.5,
        "grid_size": 100
    },
    {
        "difficulty": "DIFFICILE",
        "num_garages": 3, "num_depots": 3, "num_stations": 20,
        "min_demand": 3000, "max_demand": 8000,
        "truck_types": [20000, 25000, 30000], # Gros camions
        "truck_margin": 0, # Tendu
        "grid_size": 200
    }
]

if __name__ == "__main__":
    if not os.path.exists("instances"): os.makedirs("instances")
    
    # Génération des 5 instances demandées
    gen = VRPInstanceGenerator(scenarios[0])
    #gen.generate("instances/instance_facile_1.json")
    #gen.generate("instances/instance_facile_2.json")
    #gen.generate("instances/instance_facile_3.json")

    gen = VRPInstanceGenerator(scenarios[1])
    #gen.generate("instances/instance_moyen_1.json")
    #gen.generate("instances/instance_moyen_2.json")
    #gen.generate("instances/instance_moyen_3.json")
    
    gen = VRPInstanceGenerator(scenarios[2])
    gen.generate("instances/instance_difficile_1.json")
    gen.generate("instances/instance_difficile_2.json")
    gen.generate("instances/instance_difficile_3.json")