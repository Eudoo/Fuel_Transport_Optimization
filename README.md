# Modèle d'Optimisation - Fuel_Transport_Optimization

## 1. Notations et Ensembles

### Ensembles (Indices)

- **$V$** : L'ensemble de tous les nœuds (sommets) du graphe
- **$G \subset V$** : Ensemble des Garages
- **$D \subset V$** : Ensemble des Dépôts
- **$S \subset V$** : Ensemble des Stations (décomposées par demande produit, ex: Station1_Essence)
- **$K$** : Ensemble des Camions disponibles
- **$P$** : Ensemble des produits $\{Essence, Gasoil\}$

### Paramètres (Données connues)

- **$d_{ij}$** : Distance entre le nœud $i$ et le nœud $j$
- **$Q_k$** : Capacité maximale du camion $k$
- **$q_i$** : Demande du nœud $S_i$ (en quantité)
- **$type_i$** : Type de produit demandé par le nœud station $i$ ($\in P$)
- **$start_k$** : Garage de départ imposé du camion $k$
- **$Stock_{dp}$** : Stock initial du produit $p$ au dépôt $d$

---

## 2. Variables de Décision

### 2.1 Variables de Routage (Le trajet)

$$x_{ijk} \in \{0, 1\}$$

**Indices :** $i, j \in V$ (tous les sites : garages, dépôts, stations), $k \in K$ (camions)

**Signification :**
- Vaut 1 si le camion $k$ parcourt l'arc du nœud $i$ vers le nœud $j$
- Vaut 0 sinon

### 2.2 Variables d'Affectation au Dépôt

$$y_{kd} \in \{0, 1\}$$

**Indices :** $k \in K$ (camions), $d \in D$ (dépôts)

**Signification :**
- Vaut 1 si le camion $k$ choisit le dépôt $d$ pour se charger
- Vaut 0 sinon

**Note :** Cette variable facilite l'écriture de la contrainte "Chaque camion visite au plus un dépôt"

### 2.3 Variables d'Affectation de Produit

$$z_{kp} \in \{0, 1\}$$

**Indices :** $k \in K$ (camions), $p \in \{Essence, Gasoil\}$ (produits)

**Signification :**
- Vaut 1 si le camion $k$ est configuré pour transporter le produit $p$
- Vaut 0 sinon

### 2.4 Variables d'Ordre de Passage (Anti sous-tours)

$$u_{ik} \ge 0$$

**Indices :** $i \in S$ (stations), $k \in K$ (camions)

**Signification :**
Variable continue représentant l'ordre de passage (ou la charge cumulée) du camion $k$ lorsqu'il arrive à la station $i$. Sert uniquement à éliminer les boucles isolées via les contraintes MTZ.

### 2.5 Variable de Charge au Dépôt

$$L_{kdp} \ge 0$$

**Indices :** $k \in K$ (camions), $d \in D$ (dépôts), $p \in P$ (produits)

**Signification :** Quantité de produit $p$ chargé par le camion $k$ au dépôt $d$

---

## 3. Contraintes

### 3.1 Contraintes de Flot (Le parcours du camion)

Ces contraintes assurent que le camion se déplace physiquement de manière logique sur le graphe.

#### 3.1.1 Départ du Garage

Chaque camion $k$ peut quitter son garage de départ spécifique ($start_k$) au maximum une fois.

$$\sum_{j \in V, j \ne start_k} x_{(start_k)jk} \le 1 \quad \forall k \in K$$

*(Si la somme vaut 0, le camion n'est pas utilisé)*

#### 3.1.2 Conservation du Flot (Entrée = Sortie)

Pour tout site (Dépôt ou Station), si un camion y entre, il doit en sortir.

$$\sum_{i \in V, i \ne h} x_{ihk} = \sum_{j \in V, j \ne h} x_{hjk} \quad \forall h \in D \cup S, \forall k \in K$$

#### 3.1.3 Retour au Garage

Si un camion est sorti de son garage, il doit finir sa tournée dans un garage (n'importe lequel parmi l'ensemble $G$).

$$\sum_{g \in G} \sum_{i \in V, i \ne g} x_{igk} = \sum_{j \in V, j \ne start_k} x_{(start_k)jk} \quad \forall k \in K$$

*(L'équation dit : Nombre de retours vers un garage = Nombre de sorties du garage de départ)*

#### 3.1.4 Interdiction des Boucles (NEW) 🆕

Un camion ne peut pas faire de boucle sur lui-même (arc d'un nœud vers lui-même).

$$x_{iik} = 0 \quad \forall i \in V, \forall k \in K$$

*(Cette contrainte empêche le solveur de satisfaire artificiellement les contraintes avec des arcs de distance nulle)*

---

### 3.2 Contraintes Opérationnelles (Dépôts et Produits)

#### 3.2.1 Affectation à un seul dépôt

Un camion ne peut charger que dans, au maximum, un seul dépôt.

$$\sum_{d \in D} y_{kd} \le 1 \quad \forall k \in K$$

#### 3.2.2 Lien entre Routage et Choix du Dépôt

Si un camion $k$ visite le dépôt $d$ (s'il en sort pour aller vers un nœud $j$), alors la variable $y_{kd}$ doit être activée.

$$\sum_{j \in V} x_{djk} \le y_{kd} \quad \forall d \in D, \forall k \in K$$

*(Si $y_{kd} = 0$, le camion ne peut pas sortir du dépôt $d$)*

#### 3.2.3 Affectation à un seul produit

Un camion ne peut transporter qu'un type de produit par tournée.

$$\sum_{p \in P} z_{kp} \le 1 \quad \forall k \in K$$

#### 3.2.4 Cohérence Produit / Station (Compatibilité)

Un camion $k$ ne peut visiter une station $i$ que si le produit qu'il transporte ($z$) correspond au produit demandé par la station ($type_i$).

$$\sum_{j \in V} x_{ijk} \le z_{k, (type_i)} \quad \forall i \in S, \forall k \in K$$

*(Si la station $i$ veut du Gasoil, mais que $z_{k, Gasoil} = 0$, alors le camion ne peut pas entrer dans $i$)*

#### 3.2.5 Séquence Garage → Dépôt

Un camion ne peut pas aller directement du garage à une station (il doit charger d'abord).

$$x_{(start_k)jk} = 0 \quad \forall j \in S, \forall k \in K$$

#### 3.2.6 Lien Utilisation Dépôt et Sortie du Garage (NEW) 🆕

Si un camion utilise un dépôt, il doit obligatoirement sortir de son garage.

$$y_{kd} \le \sum_{j \in V, j \ne start_k} x_{(start_k)jk} \quad \forall k \in K, \forall d \in D$$

*(Cette contrainte empêche un camion d'utiliser un dépôt sans avoir quitté son garage)*

#### 3.2.7 Passage Obligatoire Garage → Dépôt (NEW) 🆕

Si un camion utilise un dépôt $d$, il doit y arriver directement depuis son garage de départ.

$$y_{kd} \le x_{(start_k)dk} \quad \forall k \in K, \forall d \in D$$

*(Cette contrainte force le camion à aller du garage au dépôt pour se charger avant de livrer)*

---

### 3.3 Contraintes de Demande et Capacité

#### 3.3.1 Satisfaction de la demande (Visite unique)

Chaque station (nœud client) doit être visitée exactement une fois par un seul camion.

$$\sum_{k \in K} \sum_{i \in V, i \ne j} x_{ijk} = 1 \quad \forall j \in S$$

*(Note : On exclut $i = j$ pour éviter les boucles)*

#### 3.3.2 Capacité du camion

La somme des demandes des stations visitées par un camion ne doit pas dépasser sa capacité maximale $Q_k$.

$$\sum_{i \in S} q_i \left( \sum_{j \in V, j \ne i} x_{ijk} \right) \le Q_k \quad \forall k \in K$$

*(Le terme entre parenthèses vaut 1 si le camion visite la station, 0 sinon. On exclut $j = i$ pour éviter les boucles)*

---

### 3.4 Contraintes d'Élimination des Sous-tours (MTZ)

#### 3.4.1 Gestion de l'ordre de passage

$$u_{ik} - u_{jk} + Q_k \cdot x_{ijk} \le Q_k - q_j \quad \forall\, i, j \in S, i \ne j, \forall\, k \in K$$

*(Cette contrainte empêche les circuits fermés qui ne passent pas par le dépôt/garage)*

#### 3.4.2 Bornes des variables $u$

$$q_i \le u_{ik} \le Q_k \quad \forall i \in S, \forall k \in K$$

---

### 3.5 Contraintes de Stock

#### 3.5.1 Contrainte de Stock Limité

Le stock total prélevé dans le dépôt $d$ pour le produit $p$ par tous les camions $k$ ne doit pas dépasser le stock initial.

$$\sum_{k \in K} L_{kdp} \le Stock_{dp} \quad \forall d \in D, \forall p \in P$$

#### 3.5.2 Contrainte de Conservation de Charge

La quantité chargée au dépôt $d$ pour le produit $p$ par le camion $k$ ($L_{kdp}$) doit être égale à la quantité totale livrée par ce même camion $k$ pour ce même produit $p$.

$$\sum_{d \in D} L_{kdp} = \sum_{i \in S, \text{type}_i=p} q_i \left( \sum_{j \in V, j \ne i} x_{ijk} \right) \quad \forall k \in K, \forall p \in P$$

*(Cette contrainte assure que la somme de ce que le camion charge (LHS) est égale à la somme de ce que le camion livre (RHS). On exclut $j = i$ pour éviter les boucles)*

---

## 4. Fonction Objectif

L'objectif du problème est de **minimiser la distance totale parcourue** par l'ensemble de la flotte de camions.

$$\text{Minimiser } Z = \sum_{k \in K} \sum_{i \in V} \sum_{j \in V} d_{ij} \cdot x_{ijk}$$

### Description des termes

| Terme | Description |
|-------|-------------|
| $\text{Minimiser } Z$ | L'objectif de l'optimisation |
| $k \in K$ | Somme sur tous les camions |
| $i \in V, j \in V$ | Somme sur toutes les paires de nœuds possibles |
| $d_{ij}$ | Le coût (distance) du trajet de $i$ à $j$ (Paramètre connu) |
| $x_{ijk}$ | Vaut 1 si le camion $k$ utilise le trajet $i \to j$, ce qui inclut $d_{ij}$ dans le total |

---

## Résumé du Modèle

Ce modèle d'optimisation représente un **Problème de Tournées de Véhicules (VRP)** avec plusieurs contraintes spécifiques :

- **Multi-dépôts** : Les camions peuvent charger dans différents dépôts
- **Multi-produits** : Gestion de plusieurs types de produits (Essence, Gasoil)
- **Capacité limitée** : Respect des capacités des camions
- **Stock limité** : Gestion des stocks disponibles dans les dépôts
- **Compatibilité produit-station** : Chaque station demande un type de produit spécifique

Le modèle utilise une formulation MTZ (Miller-Tucker-Zemlin) pour éliminer les sous-tours et garantir des tournées valides.
