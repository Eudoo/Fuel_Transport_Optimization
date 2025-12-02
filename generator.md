# Documentation - Générateur d'Instances VRP

## Vue d'ensemble

Ce module Python génère des instances de problèmes de tournées de véhicules (VRP - Vehicle Routing Problem) pour la livraison de carburants. Il crée des fichiers JSON contenant des garages, des dépôts, des stations-service, une flotte de camions et les distances entre tous les points.

## Architecture du Code

### Classe `VRPInstanceGenerator`

La classe principale qui gère la génération des instances.

#### Constructeur

```python
def __init__(self, config)
```

Initialise le générateur avec une configuration donnée.

**Paramètres:**
- `config` (dict): Dictionnaire de configuration contenant les paramètres de l'instance

**Attributs initialisés:**
- `conf`: Configuration complète
- `width`: Largeur de la grille (défaut: 100)
- `height`: Hauteur de la grille (défaut: 100)
- `products`: Liste des produits disponibles (["Essence", "Gasoil"])

#### Méthodes privées

##### `_generate_coords()`

Génère des coordonnées aléatoires dans la grille.

**Retourne:** Un dictionnaire `{"x": float, "y": float}` avec des valeurs arrondies à 2 décimales.

##### `_dist(p1, p2)`

Calcule la distance euclidienne entre deux points.

**Paramètres:**
- `p1`, `p2`: Dictionnaires contenant les clés `x` et `y`

**Retourne:** Distance arrondie à 2 décimales.

**Formule:** √((x₁ - x₂)² + (y₁ - y₂)²)

#### Méthode principale

##### `generate(filename)`

Génère une instance complète et la sauvegarde dans un fichier JSON.

**Paramètres:**
- `filename` (str): Chemin du fichier de sortie

## Structure des Données Générées

### Format du fichier JSON

```json
{
  "meta": { ... },
  "sites": {
    "garages": [...],
    "depots": [...],
    "stations": [...]
  },
  "flotte": [...],
  "distances": { ... }
}
```

### 1. Métadonnées (`meta`)

Contient des informations descriptives sur l'instance:
- `difficulty`: Niveau de difficulté (FACILE, MOYEN, DIFFICILE)
- `description`: Description textuelle

### 2. Sites Physiques

#### Garages (`sites.garages`)

Points de départ et d'arrivée des camions.

**Structure:**
```json
{
  "id": "G1",
  "x": 45.23,
  "y": 67.89
}
```

#### Dépôts (`sites.depots`)

Sources d'approvisionnement en carburants.

**Structure:**
```json
{
  "id": "D1",
  "stock_essence": 15000,
  "stock_gasoil": 15000,
  "x": 23.45,
  "y": 78.90
}
```

**Calcul des stocks:** Les stocks sont calculés avec une marge de sécurité de 1.5 fois la demande totale, répartie équitablement entre les dépôts.

#### Stations (`sites.stations`)

Points de livraison avec nœuds virtuels par produit.

**Structure:**
```json
{
  "id": "S1_E",
  "station_physique": 1,
  "type_produit": "Essence",
  "demande": 2500,
  "x": 34.56,
  "y": 89.01
}
```

**Logique multi-produits:**
- Chaque station physique peut demander Essence (60% de probabilité) et/ou Gasoil (60%)
- Si aucun produit n'est sélectionné, un produit est forcé aléatoirement
- Chaque produit demandé crée un nœud virtuel distinct partageant les mêmes coordonnées
- Nomenclature: `S{numéro}_E` pour Essence, `S{numéro}_G` pour Gasoil

### 3. Flotte (`flotte`)

Collection de camions avec capacités hétérogènes.

**Structure:**
```json
{
  "id": "K1",
  "capacite": 25000,
  "garage_depart": "G1"
}
```

**Algorithme de génération:**
1. Calcul de la capacité cible: `demande_totale × (1 + truck_margin × 0.1)`
2. Ajout itératif de camions jusqu'à atteindre la capacité cible
3. Type de camion choisi aléatoirement parmi `truck_types`
4. Attribution round-robin des garages de départ

### 4. Matrice de Distances (`distances`)

Format dictionnaire à deux niveaux pour un accès rapide.

**Structure:**
```json
{
  "G1": {
    "G1": 0.0,
    "D1": 45.67,
    "S1_E": 23.45
  }
}
```

**Propriétés:**
- Distance à soi-même = 0
- Distances symétriques entre tous les nœuds
- Inclut garages, dépôts et tous les nœuds virtuels des stations

## Configuration des Scénarios

### Paramètres de configuration

| Paramètre | Type | Description |
|-----------|------|-------------|
| `difficulty` | str | Niveau de difficulté |
| `num_garages` | int | Nombre de garages |
| `num_depots` | int | Nombre de dépôts |
| `num_stations` | int | Nombre de stations physiques |
| `min_demand` | int | Demande minimale par produit |
| `max_demand` | int | Demande maximale par produit |
| `truck_types` | list[int] | Capacités disponibles pour les camions |
| `truck_margin` | int | Marge de capacité (0-10, multiplié par 0.1) |
| `grid_size` | int | Taille de la grille de coordonnées |

### Scénarios prédéfinis

#### FACILE
- 1 garage, 1 dépôt, 5 stations
- Demande: 1000-3000 litres
- Camions: 15000L uniquement
- Marge capacité: 30%
- Grille: 50×50

#### MOYEN
- 2 garages, 2 dépôts, 15 stations
- Demande: 2000-5000 litres
- Camions mixtes: 15000L, 20000L, 25000L
- Marge capacité: 20%
- Grille: 100×100

#### DIFFICILE
- 3 garages, 3 dépôts, 40 stations
- Demande: 3000-8000 litres
- Gros camions: 20000L, 25000L, 30000L
- Marge capacité: 0% (très serré)
- Grille: 200×200

## Utilisation

### Génération des instances

```python
from vrp_generator import VRPInstanceGenerator, scenarios

# Créer le dossier de sortie
import os
if not os.path.exists("instances"):
    os.makedirs("instances")

# Générer une instance
gen = VRPInstanceGenerator(scenarios[0])  # FACILE
gen.generate("instances/instance_facile.json")
```

### Instances générées par défaut

Le script génère 5 fichiers lors de son exécution:
1. `instance_facile.json` (scénario FACILE)
2. `instance_moyen.json` (scénario MOYEN)
3. `instance_difficile_1.json` (scénario DIFFICILE)
4. `instance_difficile_2.json` (scénario DIFFICILE)
5. `instance_difficile_3.json` (scénario DIFFICILE)

### Sortie console

Pour chaque instance générée, affiche:
```
[OK] instances/instance_moyen.json | Dmd: 45000 | Cap: 54000 | Camions: 3
```

## Caractéristiques Techniques

### Garanties

- **Faisabilité**: Les stocks des dépôts sont toujours 1.5× la demande totale
- **Capacité suffisante**: La flotte totale dépasse la demande selon `truck_margin`
- **Coordonnées uniques**: Chaque station physique a une position unique
- **Nœuds virtuels**: Les produits d'une même station partagent les coordonnées

### Aléatoire

- Positions générées avec `random.uniform()`
- Demandes aléatoires dans l'intervalle `[min_demand, max_demand]`
- Sélection de produits probabiliste (60% par produit)
- Type de camion choisi aléatoirement dans `truck_types`

### Performance

- Complexité de la matrice de distances: O(n²) où n = garages + dépôts + nœuds virtuels
- Encodage JSON avec indentation pour lisibilité humaine

## Dépendances

- `json`: Sérialisation des données
- `random`: Génération aléatoire
- `math`: Calculs de distances
- `os`: Gestion des fichiers/dossiers

## Notes d'implémentation

### Pourquoi des nœuds virtuels?

Le modèle de nœuds virtuels permet de:
- Gérer les livraisons multi-produits avec un modèle VRP classique
- Distinguer clairement les demandes par produit
- Maintenir la contrainte d'un seul produit par voyage de camion
- Simplifier les algorithmes de résolution

### Évolutions possibles

- Ajouter des fenêtres horaires pour les livraisons
- Introduire des temps de service variables
- Implémenter des coûts différenciés par type de camion
- Ajouter des contraintes de compatibilité camion-produit
