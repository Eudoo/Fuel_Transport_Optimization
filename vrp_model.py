import json
import math
import time as time_module
from pulp import *
from pathlib import Path


class VRPModel:
    """
    Modèle d'optimisation pour le Problème de Tournées de Véhicules Multi-Dépôts et Multi-Produits.
    Basé sur la modélisation mathématique du README.
    """
    
    def __init__(self, instance_file):
        """
        Initialise le modèle avec une instance JSON.
        
        Args:
            instance_file (str): Chemin vers le fichier JSON de l'instance
        """
        self.instance_file = instance_file
        self.instance_data = None
        self.prob = None
        
        # Ensembles (seront remplis lors du chargement)
        self.V = []      # Tous les nœuds
        self.G = []      # Garages
        self.D = []      # Dépôts
        self.S = []      # Stations
        self.K = []      # Camions
        self.P = []      # Produits
        
        # Paramètres (seront remplis lors du chargement)
        self.d = {}      # Distances d_ij
        self.Q = {}      # Capacités Q_k
        self.q = {}      # Demandes q_i
        self.type_i = {} # Type de produit par station
        self.start_k = {} # Garage de départ par camion
        self.stock = {}  # Stock disponible
        
        # Variables de décision (seront créées lors de la build)
        self.x = {}      # x_ijk : routage
        self.y = {}      # y_kd : affectation dépôt
        self.z = {}      # z_kp : affectation produit
        self.u = {}      # u_ik : ordre de passage (MTZ)
        self.L = {}      # L_kdp : charge au dépôt
        
    def load_instance(self):
        """
        Charge l'instance JSON et initialise les ensembles et paramètres.
        """
        print(f"Chargement de l'instance : {self.instance_file}")
        
        with open(self.instance_file, 'r') as f:
            self.instance_data = json.load(f)
        
        # Extraction des ensembles (structure: "sites" → "garages", "depots", "stations")
        sites = self.instance_data.get("sites", {})
        self.G = [g["id"] for g in sites.get("garages", [])]
        self.D = [d["id"] for d in sites.get("depots", [])]
        self.S = [s["id"] for s in sites.get("stations", [])]
        self.K = [t["id"] for t in self.instance_data.get("flotte", [])]
        self.P = self.instance_data.get("products", ["Essence", "Gasoil"])
        
        self.V = self.G + self.D + self.S
        
        print(f"  Garages: {len(self.G)} - {self.G}")
        print(f"  Dépôts: {len(self.D)} - {self.D}")
        print(f"  Stations: {len(self.S)} - {self.S}")
        print(f"  Camions: {len(self.K)} - {self.K}")
        print(f"  Produits: {self.P}")
        
        # Extraction des paramètres
        self._load_distances()
        self._load_truck_capacities()
        self._load_demands()
        self._load_stocks()
        
        # Créer le problème PuLP
        self.prob = LpProblem("VRP_Carburants", LpMinimize)
        
        print("[OK] Instance chargée avec succès\n")
    
    def _load_distances(self):
        """Extrait la matrice de distances pré-calculée."""
        distances = self.instance_data.get("distances", {})
        for origin, destinations in distances.items():
            for destination, distance in destinations.items():
                self.d[(origin, destination)] = distance
    
    def _load_truck_capacities(self):
        """Extrait les capacités des camions."""
        for truck in self.instance_data.get("flotte", []):
            self.Q[truck["id"]] = truck["capacite"]
            self.start_k[truck["id"]] = truck.get("garage_depart", self.G[0] if self.G else None)
    
    def _load_demands(self):
        """Extrait les demandes des stations."""
        sites = self.instance_data.get("sites", {})
        for station in sites.get("stations", []):
            node_id = station["id"]
            self.q[node_id] = station["demande"]
            self.type_i[node_id] = station["type_produit"]
    
    def _load_stocks(self):
        """Extrait les stocks disponibles aux dépôts."""
        sites = self.instance_data.get("sites", {})
        for depot in sites.get("depots", []):
            depot_id = depot["id"]
            self.stock[(depot_id, "Essence")] = depot.get("stock_essence", 0)
            self.stock[(depot_id, "Gasoil")] = depot.get("stock_gasoil", 0)
    
    # =========================================================================
    # SECTION 1 : CRÉATION DES VARIABLES DE DÉCISION
    # =========================================================================
    
    def build_variables(self):
        """
        Crée toutes les variables de décision selon le modèle mathématique.
        
        À IMPLÉMENTER :
        - x_ijk : Variables binaires de routage (i,j ∈ V, k ∈ K)
        - y_kd : Variables binaires d'affectation au dépôt (k ∈ K, d ∈ D)
        - z_kp : Variables binaires d'affectation au produit (k ∈ K, p ∈ P)
        - u_ik : Variables continues d'ordre de passage (i ∈ S, k ∈ K)
        - L_kdp : Variables continues de charge au dépôt (k ∈ K, d ∈ D, p ∈ P)
        """
        print("Création des variables de décision...")
        
        # x_ijk : Variables binaires de routage
        # Indice: (i, j) ∈ V × V, k ∈ K
        for i in self.V:
            for j in self.V:
                for k in self.K:
                    self.x[(i, j, k)] = LpVariable(f"x_{i}_{j}_{k}", cat='Binary')
        
        # y_kd : Variables binaires d'affectation au dépôt
        # Indice: k ∈ K, d ∈ D
        for k in self.K:
            for d in self.D:
                self.y[(k, d)] = LpVariable(f"y_{k}_{d}", cat='Binary')
        
        # z_kp : Variables binaires d'affectation au produit
        # Indice: k ∈ K, p ∈ P
        for k in self.K:
            for p in self.P:
                self.z[(k, p)] = LpVariable(f"z_{k}_{p}", cat='Binary')
        
        # u_ik : Variables continues d'ordre de passage (MTZ)
        # Indice: i ∈ S, k ∈ K
        # Borne: q_i <= u_ik <= Q_k
        for i in self.S:
            for k in self.K:
                lower = self.q.get(i, 0)
                upper = self.Q.get(k, 0)
                self.u[(i, k)] = LpVariable(f"u_{i}_{k}", 
                                           lowBound=lower, 
                                           upBound=upper, 
                                           cat='Continuous')
        
        # L_kdp : Variables continues de charge au dépôt
        # Indice: k ∈ K, d ∈ D, p ∈ P
        # Borne: L_kdp >= 0 (max limité par stock)
        for k in self.K:
            for d in self.D:
                for p in self.P:
                    max_stock = self.stock.get((d, p), 0)
                    self.L[(k, d, p)] = LpVariable(f"L_{k}_{d}_{p}", 
                                                   lowBound=0, 
                                                   upBound=max_stock, 
                                                   cat='Continuous')
        
        print("[OK] Variables de décision créées\n")
    
    # =========================================================================
    # SECTION 2 : CRÉATION DE LA FONCTION OBJECTIF
    # =========================================================================
    
    def build_objective(self):
        """
        Minimiser la distance totale parcourue par tous les camions.
        
        Objectif : min Σ_k Σ_i Σ_j d_ij * x_ijk
        """
        print("Création de la fonction objectif...")
        
        objective = lpSum([self.d.get((i, j), 0) * self.x[(i, j, k)]
                          for i in self.V
                          for j in self.V
                          for k in self.K])
        
        # Ajouter la fonction objectif au problème
        self.prob += objective, "Distance_Totale"
        
        print("[OK] Objectif créé\n")
    
    # =========================================================================
    # SECTION 3 : CONTRAINTES DE FLOT (Sections 3.1)
    # =========================================================================
    
    def add_flow_constraints(self):
        """
        Contraintes de conservation du flot.
        
        À IMPLÉMENTER :
        3.1.1 : Sortie du garage (chaque camion part de son garage)
        3.1.2 : Conservation du flot (continuité des routes)
        3.1.3 : Retour au garage
        """
        print("Ajout des contraintes de flot...")
        
        # Interdire les boucles (arcs i → i)
        # x_iik = 0 pour tout i ∈ V, k ∈ K
        for i in self.V:
            for k in self.K:
                self.prob += self.x[(i, i, k)] == 0, f"Pas_boucle_{i}_{k}"
        
        # 3.1.1 - Sortie du garage
        # Chaque camion peut quitter son garage au maximum une fois
        # Σ_j x_(start_k, j, k) <= 1  pour tout k
        for k in self.K:
            start_garage = self.start_k.get(k)
            if start_garage:
                self.prob += lpSum([self.x[(start_garage, j, k)] for j in self.V if j != start_garage]) <= 1, f"Sortie_garage_{k}"
        
        # 3.1.2 - Conservation du flot
        # Pour tout nœud h (dépôt ou station), si un camion entre, il doit sortir
        # Σ_i x_(i, h, k) = Σ_j x_(h, j, k)  pour tout h ∈ D∪S, k ∈ K
        for h in self.D + self.S:
            for k in self.K:
                # Entrées = sorties (en excluant les boucles)
                self.prob += lpSum([self.x[(i, h, k)] for i in self.V if i != h]) == \
                             lpSum([self.x[(h, j, k)] for j in self.V if j != h]), f"Conservation_flot_{h}_{k}"
        
        # 3.1.3 - Retour au garage
        # Si un camion sort de son garage, il doit retourner à un garage
        # Σ_g Σ_i x_(i, g, k) = Σ_j x_(start_k, j, k)  pour tout k
        for k in self.K:
            start_garage = self.start_k.get(k)
            if start_garage:
                # Sorties du garage = retours aux garages
                self.prob += lpSum([self.x[(i, g, k)] for g in self.G for i in self.V if i != g]) == \
                             lpSum([self.x[(start_garage, j, k)] for j in self.V if j != start_garage]), f"Retour_garage_{k}"
        
        print("[OK] Contraintes de flot ajoutées\n")
    
    # =========================================================================
    # SECTION 3.2 : CONTRAINTES OPÉRATIONNELLES
    # =========================================================================
    
    def add_operational_constraints(self):
        """
        Contraintes opérationnelles du problème.
        
        À IMPLÉMENTER :
        3.2.1 : Affectation à un seul dépôt
        3.2.2 : Lien entre Routage et Choix du Dépôt
        3.2.3 : Affectation à un seul produit
        3.2.4 : Cohérence Produit / Station (Compatibilité)
        3.2.5 : Séquence Garage → Dépôt
        """
        print("Ajout des contraintes opérationnelles...")
        
        # 3.2.1 - Affectation à un seul dépôt
        # Un camion ne peut charger que dans, au maximum, un seul dépôt
        # Σ_d y_kd <= 1 pour tout k
        for k in self.K:
            self.prob += lpSum([self.y[(k, d)] for d in self.D]) <= 1, f"Un_seul_depot_{k}"
        
        # 3.2.2 - Lien entre Routage et Choix du Dépôt
        # Si un camion k visite le dépôt d (s'il en sort), alors y_kd doit être 1
        # Σ_j x_djk <= y_kd pour tout d ∈ D, k ∈ K
        for d in self.D:
            for k in self.K:
                self.prob += (lpSum([self.x[(d, j, k)] for j in self.V]) <= 
                             self.y[(k, d)]), f"Lien_depot_routage_{d}_{k}"
        
        # 3.2.3 - Affectation à un seul produit
        # Un camion ne peut transporter qu'un type de produit par tournée
        # Σ_p z_kp <= 1 pour tout k
        for k in self.K:
            self.prob += lpSum([self.z[(k, p)] for p in self.P]) <= 1, f"Un_seul_produit_{k}"
        
        # 3.2.4 - Cohérence Produit / Station (Compatibilité)
        # Un camion k ne peut visiter une station i que si le produit correspond
        # Σ_j x_jik <= z_k,type_i pour tout i ∈ S, k ∈ K
        # NOTE: On vérifie les ENTRÉES dans la station (cohérent avec 3.3.1)
        for i in self.S:
            product_type = self.type_i.get(i)
            if product_type:
                for k in self.K:
                    self.prob += (lpSum([self.x[(j, i, k)] for j in self.V]) <= 
                                 self.z[(k, product_type)]), f"Compatibilite_produit_{i}_{k}"
        
        # 3.2.5 - Séquence Garage → Dépôt
        # Un camion ne peut pas aller directement du garage à une station (obligation de passer par dépôt)
        # x_(start_k, j, k) = 0 pour tout j ∈ S, k ∈ K
        for k in self.K:
            start_garage = self.start_k.get(k)
            if start_garage:
                for j in self.S:
                    self.prob += self.x[(start_garage, j, k)] == 0, f"Pas_direct_G_S_{k}_{j}"
        
        # 3.2.6 - Lien entre utilisation dépôt et sortie du garage
        # Si un camion utilise un dépôt, il doit sortir de son garage
        # y_kd <= Σ_j x_(start_k, j, k) pour tout k ∈ K, d ∈ D
        for k in self.K:
            start_garage = self.start_k.get(k)
            if start_garage:
                for d in self.D:
                    self.prob += (self.y[(k, d)] <= 
                                 lpSum([self.x[(start_garage, j, k)] for j in self.V if j != start_garage])), \
                                f"Depot_implique_sortie_garage_{k}_{d}"
        
        # 3.2.7 - Le camion doit aller du garage au dépôt (pas d'autre entrée dans le dépôt depuis le début)
        # Si y_kd = 1, alors le camion doit entrer dans le dépôt depuis le garage
        # Pour simplifier: l'entrée dans le dépôt doit venir du garage ou d'une station
        # Mais au début de la tournée, seul le garage est possible
        for k in self.K:
            start_garage = self.start_k.get(k)
            if start_garage:
                for d in self.D:
                    # Si le camion utilise ce dépôt, il doit y arriver depuis le garage
                    self.prob += (self.y[(k, d)] <= self.x[(start_garage, d, k)]), \
                                f"Garage_vers_depot_{k}_{d}"
        
        print("[OK] Contraintes opérationnelles ajoutées\n")
    
    # =========================================================================
    # SECTION 3.3 : CONTRAINTES DE DEMANDE ET CAPACITÉ
    # =========================================================================
    
    def add_capacity_constraints(self):
        """
        Contraintes de demande et capacité.
        
        À IMPLÉMENTER :
        3.3.1 : Satisfaction complète des demandes (visite unique)
        3.3.2 : Respect de la capacité des camions
        """
        print("Ajout des contraintes de demande et capacité...")
        
        # 3.3.1 - Satisfaction complète des demandes (chaque station visitée exactement une fois)
        # Σ_k Σ_i x_ijk = 1 pour tout j ∈ S (en excluant i=j)
        for j in self.S:
            self.prob += (lpSum([self.x[(i, j, k)] for i in self.V for k in self.K if i != j]) == 1), \
                        f"Satisfaction_demande_{j}"
        
        # 3.3.2 - Respect de la capacité des camions
        # Σ_i∈S q_i * (Σ_j x_ijk) <= Q_k pour tout k (en excluant i=j)
        for k in self.K:
            self.prob += (lpSum([self.q.get(i, 0) * lpSum([self.x[(i, j, k)] for j in self.V if j != i]) 
                                for i in self.S]) <= self.Q.get(k, 0)), f"Capacite_{k}"
        
        print("[OK] Contraintes de demande/capacité ajoutées\n")
    
    # =========================================================================
    # SECTION 3.4 : CONTRAINTES D'ÉLIMINATION DES SOUS-TOURS (MTZ)
    # =========================================================================
    
    def add_subtour_elimination(self):
        """
        Contraintes MTZ (Miller-Tucker-Zemlin) pour éliminer les sous-tours.
        
        À IMPLÉMENTER :
        3.4.1 : Gestion de l'ordre de passage
        3.4.2 : Bornes des variables u (déjà imposées lors de la création des variables)
        """
        print("Ajout des contraintes MTZ (sous-tours)...")
        
        # 3.4.1 - Gestion de l'ordre de passage (contrainte MTZ)
        # u_ik - u_jk + Q_k * x_ijk <= Q_k - q_j  pour tout i,j ∈ S, i ≠ j, k ∈ K
        for i in self.S:
            for j in self.S:
                if i != j:
                    for k in self.K:
                        capacity = self.Q.get(k, 0)
                        demand_j = self.q.get(j, 0)
                        self.prob += (self.u[(i, k)] - self.u[(j, k)] + 
                                     capacity * self.x[(i, j, k)] <= 
                                     capacity - demand_j), f"MTZ_{i}_{j}_{k}"
        
        # 3.4.2 - Bornes des variables u
        # Les bornes ont été imposées lors de la création des variables :
        # q_i <= u_ik <= Q_k pour tout i ∈ S, k ∈ K
        # (Déjà gérées dans build_variables())
        
        print("[OK] Contraintes MTZ ajoutées\n")
    
    # =========================================================================
    # SECTION 3.5 : CONTRAINTES DE STOCK
    # =========================================================================
    
    def add_stock_constraints(self):
        """
        Contraintes de stock au dépôt.
        
        À IMPLÉMENTER :
        3.5.1 : Stock limité au dépôt
        3.5.2 : Conservation de charge (chargement = livraison)
        """
        print("Ajout des contraintes de stock...")
        
        # 3.5.1 - Stock limité au dépôt
        # Le stock total prélevé dans le dépôt d pour le produit p ne doit pas dépasser le stock initial
        # Σ_k L_kdp <= Stock_dp pour tout d ∈ D, p ∈ P
        for d in self.D:
            for p in self.P:
                max_stock = self.stock.get((d, p), 0)
                self.prob += (lpSum([self.L[(k, d, p)] for k in self.K]) <= max_stock), \
                            f"Stock_limite_{d}_{p}"
        
        # 3.5.2 - Conservation de charge (charge = livraison)
        # La quantité chargée au dépôt doit égaler la quantité livrée
        # Σ_d L_kdp = Σ_i∈S,type_i=p q_i * (Σ_j x_ijk) pour tout k ∈ K, p ∈ P
        for k in self.K:
            for p in self.P:
                # Charge totale depuis tous les dépôts
                charge_totale = lpSum([self.L[(k, d, p)] for d in self.D])
                
                # Livraison totale : somme des demandes des stations du produit p visitées par k
                # (en excluant les boucles i=j)
                livraison_totale = lpSum([self.q.get(i, 0) * lpSum([self.x[(i, j, k)] for j in self.V if j != i])
                                         for i in self.S if self.type_i.get(i) == p])
                
                self.prob += charge_totale == livraison_totale, f"Conservation_charge_{k}_{p}"
        
        print("[OK] Contraintes de stock ajoutées\n")
    
    # =========================================================================
    # RÉSOLUTION
    # =========================================================================
    
    def solve(self, time_limit=300):
        """
        Résout le problème d'optimisation.
        
        Args:
            time_limit (int): Limite de temps en secondes
        """
        print(f"Résolution du problème (limite: {time_limit}s)...")
        print("-" * 60)
        
        # Mesurer le temps de résolution
        start_time = time_module.time()
        
        # Résoudre avec le solveur CBC et limite de temps
        self.prob.solve(PULP_CBC_CMD(timeLimit=time_limit, msg=0))
        
        # Calculer le temps écoulé
        self.solve_time = time_module.time() - start_time
        
        print("-" * 60)
        print(f"Statut: {LpStatus[self.prob.status]}")
        print(f"Temps de résolution: {self.solve_time:.2f} secondes")
        print()

    def print_summary(self):
        """Affiche un résumé général de la solution."""
        print(f"Distance totale: {value(self.prob.objective):.2f} km")
        
        # Nombre de camions utilisés
        trucks_used = sum(1 for k in self.K 
                          if any(value(self.x[(i, j, k)]) and value(self.x[(i, j, k)]) > 0.5 
                                for i in self.V for j in self.V))
        print(f"Camions utilises: {trucks_used}/{len(self.K)}")
        
        # Charge totale
        total_load = sum(value(self.L[(k, d, p)]) 
                        for k in self.K for d in self.D for p in self.P)
        print(f"Charge totale: {total_load:.0f} L")
        
        # Utilisation moyenne des camions
        if trucks_used > 0:
            avg_load = total_load / trucks_used
            print(f"Charge moyenne: {avg_load:.0f} L")
        
        # Capacité totale utilisée
        total_capacity = sum(self.Q.get(k, 0) for k in self.K)
        utilization = (total_load / total_capacity * 100) if total_capacity > 0 else 0
        print(f"Utilisation capacite: {utilization:.1f}%")
        
        # Depots utilisés
        depots_used = set()
        for k in self.K:
            for d in self.D:
                if value(self.y[(k, d)]) and value(self.y[(k, d)]) > 0.5:
                    depots_used.add(d)
        print(f"Depots utilises: {depots_used if depots_used else 'Aucun'}")
        
    def print_solution(self):
        """Affiche la solution du problème."""
        print("\n" + "="*60)
        print("RESULTATS DE LA SOLUTION")
        print("="*60 + "\n")
        
        # Résumé général
        self.print_summary()
        
        # Afficher les routes actives par camion
        print("\n" + "-"*60)
        print("TOURNEES PAR CAMION")
        print("-"*60 + "\n")
        
        for k in self.K:
            # Collecter tous les arcs utilisés par ce camion
            arcs = {}
            for i in self.V:
                for j in self.V:
                    if i != j and value(self.x[(i, j, k)]) and value(self.x[(i, j, k)]) > 0.5:
                        arcs[i] = j
            
            if arcs:
                print(f"Camion {k}:")
                
                # Construire la tournée à partir du garage de départ
                start = self.start_k.get(k)
                if start and start in arcs:
                    visited = [start]
                    current = start
                    total_distance = 0
                    
                    # Parcourir les arcs en suivant le chemin
                    while current in arcs:
                        next_node = arcs[current]
                        total_distance += self.d.get((current, next_node), 0)
                        visited.append(next_node)
                        current = next_node
                        
                        # Arrêter si on revient au garage ou si boucle infinie
                        if current in self.G or len(visited) > len(self.V) + 2:
                            break
                    
                    # Afficher la tournée
                    print(f"  Route: {' -> '.join(visited)}")
                    print(f"  Distance: {total_distance:.2f} km")
                    
                    # Stations visitées
                    stations_visitees = [n for n in visited if n in self.S]
                    print(f"  Stations: {stations_visitees}")
                    
                    # Afficher les produits et dépôt
                    for d in self.D:
                        if value(self.y[(k, d)]) and value(self.y[(k, d)]) > 0.5:
                            print(f"  Depot: {d}")
                    
                    for p in self.P:
                        if value(self.z[(k, p)]) and value(self.z[(k, p)]) > 0.5:
                            print(f"  Produit: {p}")
                            charge = sum(value(self.L[(k, d, p)]) for d in self.D)
                            print(f"  Charge: {charge:.0f} L")
                    
                    print()
            else:
                # Camion non utilisé
                pass
        
        print("-"*60)
        print("FIN DE LA SOLUTION")
        print("="*60 + "\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Charger et résoudre l'instance 
    model = VRPModel("instances/instance_facile.json")
    #model = VRPModel("instances/instance_moyen.json")
    #model = VRPModel("instances/instance_difficile_1.json")
    #model = VRPModel("instances/instance_difficile_2.json")
    #model = VRPModel("instances/instance_difficile_3.json")
    model.load_instance()
    
    print("\n" + "="*60)
    print("CONSTRUCTION DU MODÈLE")
    print("="*60 + "\n")
    
    model.build_variables()
    model.build_objective()
    model.add_flow_constraints()
    model.add_operational_constraints()
    model.add_capacity_constraints()
    model.add_subtour_elimination()
    model.add_stock_constraints()
    
    print("\n" + "="*60)
    print("RÉSOLUTION")
    print("="*60 + "\n")
    
    model.solve(time_limit=600)
    model.print_solution()
