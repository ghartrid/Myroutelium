# Myroutelium

**Fungal-inspired network routing algorithm with calcium signaling for TCP/IP efficiency**

Myroutelium (mycelium + router) models network links as living hyphae with a two-tier biological signaling system:

1. **Nutrient transport** (slow data plane) — links strengthen with successful traffic and decay when unused
2. **Calcium signaling** (fast control plane) — Ca2+ waves propagate ahead of traffic to warn of congestion, failures, and optimal paths

This produces emergent multi-path routing, adaptive load balancing, self-healing after failures, and congestion-aware flow distribution — from simple local rules, not global computation.

## Quick Start

```bash
pip install -r requirements.txt
python3 run_benchmark.py
```

Results (charts + JSON) are written to `results/`.

## Architecture

```
myroutelium/
├── graph.py              # Core network graph with nutrient dynamics + calcium signaling
├── routing.py            # Myroutelium (fungal+Ca2+) + Dijkstra (traditional) routers
├── topologies.py         # Pre-built network topologies (grid, ring, fat-tree, etc.)
├── simulation.py         # Discrete-event simulation framework
├── visualize.py          # Network and comparison charts (matplotlib)
├── radio.py              # Radio node model — adaptive power, channels, signal propagation
├── radio_routing.py      # Myroutelium radio router + static mesh (802.11s-like)
├── radio_topologies.py   # Radio mesh topologies (grid, cluster, IoT, disaster, etc.)
├── radio_simulation.py   # Physical layer simulation framework
└── radio_visualize.py    # Radio mesh visualization and comparison charts

run_benchmark.py          # Network layer benchmark suite (5 scenarios)
run_radio_benchmark.py    # Physical layer benchmark suite (5 scenarios)
run_bio_benchmark.py      # Biological substrate benchmark suite (5 scenarios)
ALGORITHM.md              # Formal algorithm specification
PHYSICAL_LAYER.md         # Physical layer protocol specification
BIOSUBSTRATE.md           # Biological substrate specification
```

## Two-Tier Biological Routing

### Tier 1: Nutrient Transport (Data Plane)
Each network link has a **nutrient score** N in [0, 1]:
- **Reinforcement**: Successful packets strengthen the link
- **Decay**: Unused links weaken over time
- **Congestion penalty**: Overloaded links weaken faster
- **Pruning**: Links below threshold go dormant

### Tier 2: Calcium Signaling (Control Plane)
Ca2+ waves propagate 3x faster than nutrient updates:
- **Congestion signals**: Warn downstream nodes to avoid saturated links
- **Failure signals**: Instant notification of link/node failures
- **Recovery signals**: Announce restored connectivity
- **Optimal signals**: Boost paths that are performing well

The router blends both tiers: `score = (1-w) * nutrient_score + w * calcium_adjusted_score`

## Benchmarks

The benchmark suite tests 5 dimensions:

1. **Topology** — Grid, ring, random, internet-like
2. **Traffic** — Uniform, hotspot, bursty, heavy load
3. **Failures** — Random links, critical node, cascading
4. **Scalability** — 9 to 100 nodes
5. **Parameters** — Sensitivity to alpha, delta, tau, calcium_weight

Key finding: calcium signaling is most active under **heavy load** (ca=0.127) and **hotspot** (ca=0.120) traffic, where congestion awareness matters most.

## Key Biological Analogues

| Biology | Network |
|---|---|
| Hypha tube diameter | Link nutrient score |
| Nutrient flow | Packet traffic |
| Ca2+ ion waves | Fast control plane signals |
| Tube reinforcement | Path scoring + selection |
| Tube decay | Link deprioritization |
| Spore dispersal | Node/route discovery |
| Fruiting body | Topology optimization |

See [ALGORITHM.md](ALGORITHM.md) for the full formal specification.

## Physical Layer — Adaptive Mesh Radio

Myroutelium extends to the physical layer with an adaptive mesh radio protocol where radio parameters self-organize:

- **Transmit power = tube diameter** — nodes increase power to active neighbors, decrease to idle
- **Channel allocation = nutrient flow** — busy links get wider bandwidth
- **Calcium control channel** — dedicated low-power channel for fast state propagation
- **Power budget constraint** — nodes can't blast all directions, must prioritize (like real hyphae)

Run the physical layer benchmarks:
```bash
python3 run_radio_benchmark.py
```

Key findings:
- **Hotspot traffic**: 60.7% delivery, calcium active at 0.116
- **Very high traffic**: 81.4% delivery, highest calcium engagement (0.144), **power efficiency 0.461** vs static mesh's identical delivery at same power
- **Myroutelium uses more hops but maintains equal delivery** — the multi-path exploration trades latency for resilience

See [PHYSICAL_LAYER.md](PHYSICAL_LAYER.md) for the full physical layer specification.

## Biological Substrate — Living Network Computing

The ultimate layer: a simulation of actual living mycelium as a computing and routing medium.

```bash
python3 run_bio_benchmark.py
```

Models real fungal biology:
- **Hyphal growth** — tips extend, branch, and fuse (anastomosis) guided by calcium gradients
- **Ionic signaling** — Ca2+/K+ action potentials propagate at 0.5-5 mm/s along hyphae
- **Electrode interface** — digital controller reads spike patterns and injects stimulation
- **Environmental response** — moisture, temperature, pH affect growth and conductivity
- **Diameter adaptation** — high-traffic segments physically widen (Hagen-Poiseuille)
- **Self-healing** — damaged regions regrow through stimulated tip extension

Key benchmark results:
- **100% routing success** through living network after guided growth
- **4/4 target electrode connectivity** via stimulus-guided chemotropism
- Environmental sensitivity validated: dry conditions (20% moisture) reduce growth 20x
- Network grows to **541mm total length, 2000+ segments** from 8 initial tips

See [BIOSUBSTRATE.md](BIOSUBSTRATE.md) for the full biological specification.

## References

- Tero et al. (2010). "Rules for Biologically Inspired Adaptive Network Design." *Science*
- Nakagaki et al. (2000). "Maze-solving by an amoeboid organism." *Nature*
- Adamatzky, A. (2018). "On spiking behaviour of oyster fungi." *Scientific Reports*
