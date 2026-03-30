# Myroutelium Routing Algorithm — Formal Specification

## 1. Abstract

Myroutelium is a bio-inspired network routing algorithm modeled on fungal mycelial networks with a two-tier signaling system. Unlike traditional shortest-path routing (Dijkstra/OSPF/BGP), Myroutelium treats network links as living hyphae with:

1. **Nutrient transport** (slow data plane) — links strengthen with successful traffic and decay when underperforming
2. **Calcium signaling** (fast control plane) — Ca2+ waves propagate rapidly through the network to signal congestion, failures, recoveries, and optimal paths

This two-tier approach mirrors real fungal biology where calcium ion waves travel orders of magnitude faster than nutrient transport, giving the network rapid awareness of state changes before the slower reinforcement learning has time to adapt.

## 2. Biological Basis

### 2.1 Mycelial Network Properties

Real fungal networks (particularly *Physarum polycephalum*) exhibit:

- **Adaptive tube reinforcement**: Channels carrying more nutrients grow wider; unused channels shrink
- **Multi-path transport**: Resources flow through multiple parallel paths simultaneously
- **Fault tolerance**: Severed connections trigger rapid rerouting through existing redundant paths
- **Exploration/exploitation balance**: Growing tips explore while established paths exploit
- **Near-optimal topology**: Networks converge to solutions competitive with Steiner trees

### 2.2 Mapping to Network Routing

| Biological Concept | Network Analogue |
|---|---|
| Mycelium node | Router / switch |
| Hypha (tube) | Network link |
| Nutrient flow | Packet traffic |
| Tube diameter | Link score / preference weight |
| Nutrient concentration | Bandwidth utilization |
| Hyphal tip growth | Route discovery |
| Tube decay | Link deprioritization |
| Spore dispersal | New node announcement |
| Fruiting body | Topology optimization event |

## 3. Formal Model

### 3.1 Network Graph

The network is modeled as a weighted directed graph G = (V, E) where:

- **V** = set of nodes (routers)
- **E** = set of edges (links)

Each edge e(u,v) ∈ E has the following properties:

```
e(u,v) = {
    capacity:    C(u,v)    ∈ ℝ⁺     // maximum bandwidth (bits/sec)
    latency:     L(u,v)    ∈ ℝ⁺     // base propagation delay (ms)
    flow:        F(u,v)    ∈ [0, C]  // current traffic load
    nutrient:    N(u,v)    ∈ [0, 1]  // mycelial reinforcement score
    age:         A(u,v)    ∈ ℕ       // ticks since last successful packet
}
```

### 3.2 Nutrient Score Dynamics

The nutrient score N(u,v) is the core of the algorithm. It represents how "healthy" a link is, analogous to hyphal tube diameter.

#### 3.2.1 Reinforcement (on successful packet delivery)

When a packet successfully traverses edge e(u,v), the nutrient score is reinforced:

```
N(u,v) ← N(u,v) + α · Q(u,v) · (1 - N(u,v))
```

Where:
- **α** ∈ (0, 1] is the reinforcement rate (default: 0.1)
- **Q(u,v)** is the quality signal:

```
Q(u,v) = (1 - F(u,v)/C(u,v)) · (1 / (1 + L(u,v)/L_ref))
```

Q captures both available capacity and latency performance. L_ref is a reference latency (e.g., median network latency).

The term (1 - N) ensures diminishing returns — already strong links grow slower, preventing monopolization.

#### 3.2.2 Decay (continuous)

Every simulation tick, all nutrient scores decay:

```
N(u,v) ← N(u,v) · (1 - δ)
```

Where:
- **δ** ∈ (0, 1) is the decay rate (default: 0.01)

This ensures unused links gradually lose priority, mimicking hyphal tube shrinkage.

#### 3.2.3 Congestion Penalty

When a link's utilization exceeds a threshold θ (default: 0.8):

```
if F(u,v)/C(u,v) > θ:
    N(u,v) ← N(u,v) · (1 - γ · (F(u,v)/C(u,v) - θ)/(1 - θ))
```

Where γ ∈ (0, 1) is the congestion penalty rate (default: 0.3).

### 3.3 Route Selection — Probabilistic Multi-Path

Unlike traditional routing which selects a single best path, Mycelium distributes traffic across multiple paths probabilistically.

#### 3.3.1 Path Discovery

For a packet from source s to destination d, compute all simple paths P = {p₁, p₂, ..., pₖ} up to a maximum hop count H (default: 2× shortest path length).

In practice, use a modified BFS/DFS that prunes paths with any edge where N(u,v) < N_min (default: 0.05) — the "dead hypha" threshold.

#### 3.3.2 Path Scoring

Each path pᵢ receives a composite score:

```
S(pᵢ) = ∏(e ∈ pᵢ) N(e) · min(e ∈ pᵢ) (C(e) - F(e)) / max(e ∈ pᵢ) L(e)
```

This is:
- Product of nutrient scores along the path (multiplicative — one weak link kills the score)
- Times the bottleneck available bandwidth
- Divided by the worst-case latency

#### 3.3.3 Probabilistic Selection

Convert scores to probabilities using a softmax with temperature τ (default: 0.5):

```
P(pᵢ) = exp(S(pᵢ)/τ) / Σⱼ exp(S(pⱼ)/τ)
```

Lower temperature → more deterministic (exploit). Higher temperature → more random (explore).

Select path by sampling from this distribution.

#### 3.3.4 Flow Splitting (for bulk transfers)

For large flows, split traffic across the top-k paths proportional to their probabilities:

```
flow_fraction(pᵢ) = P(pᵢ) / Σ(top-k) P(pⱼ)
```

### 3.4 Calcium Signaling System (Fast Control Plane)

#### 3.4.1 Biological Basis

Real fungi use Ca2+ ion waves as a rapid signaling mechanism that travels far faster than nutrient transport through hyphae. This serves as a "nervous system" for the network — detecting and responding to environmental changes (damage, food sources, threats) before the slower structural adaptation occurs.

In Myroutelium, calcium signals form the fast control plane:

```
ca_signal = {
    origin:       node_id          // where this signal currently is
    signal_type:  string           // "congestion" | "failure" | "recovery" | "optimal"
    target_link:  (src, dst)       // the specific link this signal is about
    strength:     s ∈ [0, 1]       // signal intensity, decays per hop
    hops:         h ∈ ℕ            // how far this has traveled
}
```

#### 3.4.2 Signal Propagation

Calcium signals propagate at `ca_propagation_speed` hops per tick (default: 3), compared to nutrient updates which effectively propagate at 1 hop per tick.

Per hop, signal strength decays:

```
s_new = s - ca_decay_per_hop     (default decay: 0.15 per hop)
```

Propagation stops when `s < ca_threshold` (default: 0.1).

#### 3.4.3 Signal Types

**Congestion** — emitted automatically when link utilization exceeds θ:
```
strength = min((utilization - θ) / (1 - θ), 1.0)
effect: path_score *= max(0.1, 1.0 - ca_congestion_boost × strength)
```

**Failure** — emitted when a link or node goes down:
```
strength = 1.0
effect: path_score *= max(0.01, 1.0 - 0.9 × strength)
```

**Recovery** — emitted when a link or node comes back online:
```
strength = 0.8
effect: path_score *= 1.0 + 0.2 × strength
```

**Optimal** — emitted for high-nutrient, low-utilization links (N > 0.7, U < 0.3):
```
strength = nutrient × (1.0 - utilization)
effect: path_score *= 1.0 + ca_optimal_boost × strength
```

#### 3.4.4 Calcium Map

Each node maintains a **calcium map** — a local cache of received calcium signals indexed by link:

```
calcium_map[node_id] = { (src, dst) → CalciumSignal }
```

When a new signal arrives for a link already in the map, the stronger signal wins. Calcium map entries decay by 30% per tick (much faster than nutrient decay), ensuring stale information is quickly forgotten.

#### 3.4.5 Two-Tier Path Scoring

The router blends nutrient scores and calcium awareness:

```
base_score = ∏ N(e) × min(available) / max(latency)          // nutrient only
ca_score = base_score × ∏ calcium_modifier(src, e)            // calcium adjusted
final_score = (1 - w) × base_score + w × ca_score             // blended
```

Where `w` is the `calcium_weight` parameter (default: 0.5).

An additional **shortest path bias** favors shorter routes:

```
length_bonus = 1.0 + shortest_path_bias × (shortest_hops / actual_hops - 0.5)
final_score *= length_bonus
```

### 3.5 Spore Discovery Protocol

New nodes or recovered links are announced via "spores" — lightweight probe packets:

```
spore = {
    origin:     node_id
    ttl:        max_hops (default: 8)
    timestamp:  creation_time
}
```

When a node receives a spore:
1. Record/update the origin node in its neighbor table
2. Initialize nutrient score for the new link: N = N_init (default: 0.3)
3. Decrement TTL and forward to all neighbors (if TTL > 0)

Spores are sent:
- On node boot
- When a previously dead link comes back up
- Periodically at low frequency (every T_spore ticks, default: 100)

### 3.5 Pruning Protocol

Links with nutrient scores below N_prune (default: 0.02) for more than T_prune consecutive ticks (default: 50) are marked as "dormant":

- Dormant links are excluded from path discovery
- They retain their physical properties (capacity, latency) for potential reactivation
- A spore or explicit probe can reactivate a dormant link, resetting N to N_init

### 3.6 Fruiting Events (Topology Optimization)

Every T_fruit ticks (default: 500), a global optimization pass runs:

1. **Identify critical paths**: Links where N > 0.8 on paths serving >10% of total traffic
2. **Identify redundant paths**: Multiple high-N paths between the same source-destination pairs
3. **Rebalance**: Slightly boost N on underutilized alternate paths to maintain redundancy
4. **Report**: Generate topology health metrics

This mimics the biological fruiting event where the network consolidates resources and produces emergent structure.

## 4. Algorithm Parameters

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Reinforcement rate | α | 0.1 | How fast successful links strengthen |
| Decay rate | δ | 0.01 | How fast unused links weaken |
| Congestion threshold | θ | 0.8 | Utilization level triggering penalty |
| Congestion penalty | γ | 0.3 | Strength of congestion penalty |
| Temperature | τ | 0.5 | Exploration vs exploitation balance |
| Dead threshold | N_min | 0.05 | Below this, links excluded from routing |
| Prune threshold | N_prune | 0.02 | Below this for T_prune ticks → dormant |
| Prune timer | T_prune | 50 | Ticks before dormancy |
| Initial nutrient | N_init | 0.3 | Starting score for new/reactivated links |
| Spore interval | T_spore | 100 | Ticks between periodic spore broadcasts |
| Fruiting interval | T_fruit | 500 | Ticks between optimization passes |
| Max path multiplier | H | 2× | Max hops as multiple of shortest path |
| Reference latency | L_ref | median | Baseline for quality signal |
| Ca2+ propagation speed | ca_speed | 3 hops/tick | How fast calcium signals travel |
| Ca2+ decay per hop | ca_decay | 0.15 | Signal strength lost per hop |
| Ca2+ threshold | ca_thresh | 0.1 | Minimum strength to keep propagating |
| Ca2+ congestion boost | ca_cong | 0.3 | How much congestion signals penalize |
| Ca2+ optimal boost | ca_opt | 0.4 | How much optimal signals boost |
| Calcium weight | w | 0.5 | Blend of nutrient vs calcium scoring |
| Shortest path bias | sp_bias | 0.3 | Bonus for shorter paths |

## 5. Convergence Properties

### 5.1 Steady State

Under constant traffic patterns, the algorithm converges to a stable nutrient distribution where:

```
∀ e ∈ E: dN(e)/dt ≈ 0
```

This occurs when reinforcement from traffic balances decay, producing a fixed-point nutrient map.

### 5.2 Adaptation Time

After a topology change (link failure, new node), the algorithm adapts in O(diameter × 1/α) ticks through:
1. Immediate: failed link's nutrient drops to 0
2. Fast (1-10 ticks): alternate paths absorb rerouted traffic, nutrient scores rise
3. Medium (10-50 ticks): new steady state forms
4. Slow (50-500 ticks): fruiting event optimizes the new topology

### 5.3 Comparison with Traditional Algorithms

| Property | Dijkstra/OSPF | BGP | Myroutelium |
|---|---|---|---|
| Path selection | Single shortest | Single best (policy) | Multi-path probabilistic |
| Load balancing | Equal-cost only (ECMP) | Manual | Automatic, proportional |
| Convergence after failure | O(n²) recomputation | Minutes (BGP reconvergence) | Gradual, immediate partial |
| Congestion response | None (static) | None (static) | Automatic rerouting |
| Exploration of new paths | Only on topology change | Only on policy change | Continuous (temperature) |
| Computational complexity | O(V² or V·log(V)) per update | O(V·E) per update | O(k·paths) per packet |

## 6. Implementation Notes

### 6.1 Simulation Architecture

The prototype simulation implements:
1. A discrete-event network simulator with configurable topologies
2. The full Mycelium routing algorithm
3. Traditional Dijkstra shortest-path routing for comparison
4. Traffic generators (uniform, hotspot, bursty)
5. Failure injection (random link/node failures)
6. Metrics collection (latency, throughput, packet loss, path diversity)
7. Visualization of nutrient scores and traffic flow

### 6.2 Scaling Considerations

For production deployment (future work):
- Path discovery should use bounded DFS, not enumerate all paths
- Nutrient updates can be batched and applied asynchronously
- Fruiting events should be distributed, not global
- SDN controller integration via OpenFlow or P4

## 7. References

- Tero, A. et al. (2010). "Rules for Biologically Inspired Adaptive Network Design." *Science*, 327(5964), 439-442.
- Nakagaki, T. et al. (2000). "Intelligence: Maze-solving by an amoeboid organism." *Nature*, 407, 470.
- Adamatzky, A. (2010). *Physarum Machines: Computers from Slime Mould.* World Scientific.
- Dorigo, M. & Stützle, T. (2004). *Ant Colony Optimization.* MIT Press.
- Bonabeau, E. et al. (1999). *Swarm Intelligence: From Natural to Artificial Systems.* Oxford University Press.
