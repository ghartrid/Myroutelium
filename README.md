# Myroutelium

**A three-layer biological routing system with living cryptography**

Myroutelium (mycelium + router) is a full-stack bio-inspired networking system that spans from network routing down to biological tissue. It uses two-tier fungal signaling — slow nutrient reinforcement (data plane) and fast calcium ion waves (control plane) — to produce emergent multi-path routing, adaptive load balancing, self-healing, and congestion-aware flow distribution from simple local rules.

The system transmits text and images through simulated living mycelial networks and encrypts data using the biological network itself as the encryption key.

## Quick Start

```bash
pip install -r requirements.txt

# Network layer benchmarks (Myroutelium vs Dijkstra)
python3 run_benchmark.py

# Physical layer benchmarks (adaptive radio vs static mesh)
python3 run_radio_benchmark.py

# Biological substrate benchmarks (living mycelial network)
python3 run_bio_benchmark.py

# Interactive visualization (open in browser)
xdg-open visualization.html
```

## Architecture

Myroutelium has three layers, each modeling a different level of biological organization, plus transmission and encryption protocols that operate across all layers.

```
myroutelium/
  Network Layer
  ├── graph.py              # Core network graph + nutrient dynamics + calcium signaling
  ├── routing.py            # Myroutelium router (fungal+Ca2+) + Dijkstra comparison
  ├── topologies.py         # Network topologies (grid, ring, fat-tree, random, internet-like)
  ├── simulation.py         # Discrete-event simulation framework
  └── visualize.py          # Network charts (matplotlib)

  Physical Layer (Adaptive Mesh Radio)
  ├── radio.py              # Radio node model — adaptive power, channels, 7 bio-optimizations
  ├── radio_routing.py      # Myroutelium radio router + static mesh (802.11s-like)
  ├── radio_topologies.py   # Radio topologies (grid, cluster, line, disaster, IoT)
  ├── radio_simulation.py   # Physical layer simulation
  └── radio_visualize.py    # Radio mesh charts

  Biological Substrate
  └── biosubstrate.py       # Living mycelial network — HH ion dynamics, growth, electrodes

Benchmarks
  ├── run_benchmark.py          # Network layer (5 benchmark suites)
  ├── run_radio_benchmark.py    # Physical layer (5 benchmark suites)
  └── run_bio_benchmark.py      # Biological substrate (5 benchmark suites)

Visualization & Demos
  └── visualization.html    # Interactive 7-tab visualization (see below)

Specifications
  ├── ALGORITHM.md           # Network layer + calcium signaling formal spec
  ├── PHYSICAL_LAYER.md      # Adaptive mesh radio protocol spec
  ├── BIOSUBSTRATE.md        # Biological substrate spec (Hodgkin-Huxley, growth, electrodes)
  ├── ENCRYPTION.md          # Mycelium encryption spec (4-layer living cryptography)
  ├── TRANSMISSION.md        # Text + image transmission protocol spec
  └── SECURITY.md            # Biological immune system spec (5 defense layers)

Paper
  └── paper/myroutelium.tex  # arXiv paper (IEEE two-column, cs.NI)
```

## The Three Layers

### Layer 3: Network Routing

Two-tier signaling inspired by real fungal biology:

**Tier 1 — Nutrient Transport (Data Plane)**
- Links have nutrient scores N in [0, 1] that strengthen with traffic and decay when idle
- Congested links weaken faster; dormant links get pruned
- Probabilistic multi-path selection via softmax sampling

**Tier 2 — Calcium Signaling (Control Plane)**
- Ca2+ waves propagate 3x faster than nutrient updates
- Signal types: CONGESTION, FAILURE, RECOVERY, OPTIMAL, PREEMPTIVE
- Each node maintains a calcium awareness map from received signals
- Router blends both tiers: `score = (1-w) * nutrient + w * calcium_adjusted`

This mirrors SDN (software-defined networking) control/data plane separation — but emerges from biology, not engineering.

See [ALGORITHM.md](ALGORITHM.md) for the full specification.

### Layer 2: Adaptive Mesh Radio

The physical medium self-organizes using seven biological optimizations:

| Optimization | Biological Analogue | Effect |
|---|---|---|
| **SNR hop penalty** | Energy cost of transport | Fewer, higher-quality hops preferred |
| **Rhizomorphs** | Bundled trunk hyphae | 2.5x channel bonding on high-traffic links |
| **Anastomosis** | Hyphal fusion shortcuts | Bypasses multi-hop chains |
| **Tropism** | Directional growth | Up to 6dB beamforming gain toward active neighbors |
| **Sleep scheduling** | Segment dormancy | Idle nodes power down, wake on Ca2+ signal |
| **Preemptive Ca2+** | Early warning signals | Congestion warnings at 60% (not 70%) |
| **Cooperative relay** | Hyphal skip connections | Skip intermediate hops when direct SNR sufficient |

Result: Myroutelium **beats static mesh on latency** (0.77ms vs 0.87ms under very high traffic) while maintaining identical delivery rates.

See [PHYSICAL_LAYER.md](PHYSICAL_LAYER.md) for the full specification.

### Layer 1: Biological Substrate

A simulation of actual living mycelium as a computing and routing medium:

- **Hodgkin-Huxley ion dynamics** — Ca2+/K+ action potentials with voltage-dependent gating
- **Cable equation propagation** — signals attenuate with e^(-distance/lambda), thicker hyphae carry further
- **Hyphal growth** — tips extend at 1-4 mm/hr, branch stochastically, follow calcium chemotropism
- **Anastomosis** — hyphal fusion creates redundant loops
- **Diameter adaptation** — high-traffic segments physically widen (Hagen-Poiseuille)
- **Electrode interface** — stimulate (inject current), record (measure potential + calcium), classify spike patterns
- **Environmental response** — moisture, temperature, pH modulate all biological processes
- **Self-healing** — damaged regions regrow via stimulated tip extension

Key results: 100% routing success through grown biological networks, 4/4 target electrode connectivity via chemotropism, 2000+ segments grown from 8 initial tips.

See [BIOSUBSTRATE.md](BIOSUBSTRATE.md) for the full specification.

## Data Transmission

### Text Transmission Protocol (TTP)

Characters are encoded as 8-bit ASCII spike trains:
- Bit = 1: current injection triggers action potential
- Bit = 0: silence for one time slot
- Signals propagate through living hyphae at 0.5-5 mm/s
- Destination electrode detects spikes and reconstructs text

### Image Transmission Protocol (ITP)

16x16 grayscale images transmitted via multi-path parallel routing:
- Each pixel encoded as 8-bit grayscale spike train
- Different pixel rows route through different biological paths simultaneously
- 5 parallel paths = 5x throughput vs serial text
- Path failure triggers automatic rerouting through surviving hyphae

See [TRANSMISSION.md](TRANSMISSION.md) for the full specification.

## Mycelium Encryption

A physical-layer cryptographic system where the encryption key is alive:

**Four security layers:**

1. **Secret Sharing** — data split across N biological paths; no single path carries the complete message (Shamir-like XOR scheme)
2. **Biological Path Signature** — each share XOR-masked with a key derived from the path's physical properties (segment diameters, lengths, ion channel states). The network topology IS the encryption key
3. **Temporal Key Rotation** — the mycelium grows continuously, changing segment properties. The key is different every time — a living one-time pad
4. **Physical Security** — the key exists only as biological tissue. No digital copy. Destroying the specimen destroys the key irrecoverably

Key space: ~2^720 (exceeds AES-256 by a factor of 2^464).

An eavesdropper tapping a single hypha gets 1/N of the data, XOR-masked with a biological key they cannot access. Unreadable.

See [ENCRYPTION.md](ENCRYPTION.md) for the full specification.

## Biological Immune System

Five defense layers protect the network from malicious signals:

| Layer | Biological Analogue | Defense |
|---|---|---|
| **Spike Authentication** | Ion channel fingerprinting | Signals validated against biological response profile (amplitude, timing, Ca2+ response). Foreign signals produce wrong electrochemical cascade — detected in <5ms |
| **Calcium Immune Burst** | Immune signaling | Defensive Ca2+ wave propagates 5x faster than data, locks down surrounding junctions |
| **Path Quarantine** | Melanin encapsulation | Compromised segments electrically isolated (conductivity drops to ~0), traffic reroutes |
| **Apoptosis** | Programmed cell death | Persistent threats trigger segment death. Data physically ceases to exist. Network regrows clean |
| **ROS Purge** | Reactive oxygen species | Nuclear option: kill everything in a radius, regrow from scratch |

The fundamental advantage: in digital systems, malicious and legitimate data are both just bits. In a biological system, **the medium itself authenticates** — foreign signals interact differently with the living tissue than native ones.

See [SECURITY.md](SECURITY.md) for the full specification.

## Interactive Visualization

Open `visualization.html` in any browser. Seven tabs:

| Tab | Description |
|---|---|
| **Architecture** | Three-layer stack diagram with biological SDN explanation |
| **Network Layer** | Live nutrient reinforcement, calcium waves, packet routing |
| **Physical Layer** | Rhizomorphs forming, tropism beamforming, sleep scheduling, node failures |
| **Bio Substrate** | Growing mycelium with calcium diffusion, electrode stimulation, anastomosis |
| **Text Transmission** | Type a message, watch it encode to spikes, propagate through mycelium, decode |
| **Image Transmission** | Select/draw an image, watch pixels stream through multi-path network, reconstruct |
| **Mycelium Encryption** | Encrypt a message, see secret sharing across 5 paths, eavesdrop to see garbled data, regrow for new key |
| **Immune System** | Inject malicious signals, watch authentication reject them, see immune calcium bursts, quarantine, apoptosis, ROS purge |

All tabs are interactive with controls for triggering events (calcium waves, failures, traffic surges, noise injection, path breaking, network regrowth).

## Benchmark Results

### Network Layer (15 benchmark suites)

| Scenario | Myroutelium | Dijkstra |
|---|---|---|
| Delivery rate | 100% | 100% |
| Path diversity | 1.000 | 1.000 |
| Latency (hotspot) | 15.3ms | 12.6ms |
| Ca2+ most active | Heavy load (0.127) | N/A |

### Physical Layer (15 benchmark suites)

| Scenario | Myroutelium | Static Mesh |
|---|---|---|
| Latency (very high traffic) | **0.77ms** | 0.87ms |
| Hops (very high traffic) | **2.3** | 3.0 |
| Delivery rate | Equal | Equal |
| Ca2+ most active | Hotspot (0.076) | N/A |

### Biological Substrate (5 benchmark suites)

| Metric | Result |
|---|---|
| Growth | 8 tips -> 2000+ segments, 541mm total |
| Routing success | 100% (50/50 attempts) |
| Target connectivity | 4/4 electrodes reached via chemotropism |
| Environmental response | 20x growth difference (optimal vs dry) |
| Self-healing | Network regrows beyond pre-damage size |

## Biological Mapping

| Fungal Biology | Myroutelium Implementation |
|---|---|
| Hyphal tube | Network link / radio connection / biological segment |
| Tube diameter | Nutrient score / transmit power / physical diameter |
| Nutrient flow | Packet traffic / data flow |
| Ca2+ ion waves | Fast control plane signals |
| Rhizomorphs | Trunk links with channel bonding |
| Anastomosis | Shortcut discovery / hyphal fusion |
| Tropism | Beamforming toward active neighbors |
| Dormancy | Sleep scheduling for idle nodes |
| Spore dispersal | Node/route discovery beacons |
| Action potentials | Encoded data bits (spike = 1, silence = 0) |
| Network topology | Encryption key (physical, non-copiable) |

## Paper

IEEE two-column format paper for arXiv cs.NI:

```
paper/myroutelium.tex
```

"Myroutelium: A Three-Layer Bio-Inspired Routing Architecture with Fungal Calcium Signaling as a Separated Control Plane"

Compile with `pdflatex myroutelium.tex` or upload to Overleaf.

## Species Candidates for Physical Implementation

| Species | Growth Rate | Spike Patterns | Best For |
|---|---|---|---|
| *Physarum polycephalum* | Fast (4 mm/hr) | Well-studied | Development + prototyping |
| *Pleurotus ostreatus* | Medium | 50+ patterns | Signal diversity |
| *Ganoderma lucidum* | Slow, stable | Strong signals | Production stability |
| *Armillaria ostoyae* | Variable | Unknown | Extreme scale (largest organism) |

## References

- Tero, A. et al. (2010). "Rules for Biologically Inspired Adaptive Network Design." *Science*, 327(5964), 439-442.
- Nakagaki, T. et al. (2000). "Intelligence: Maze-solving by an amoeboid organism." *Nature*, 407, 470.
- Adamatzky, A. (2018). "On spiking behaviour of oyster fungi." *Scientific Reports*, 8, 7873.
- Adamatzky, A. (2022). "Language of fungi derived from their electrical spiking activity." *R. Soc. Open Sci.*, 9(4), 211926.
- Dorigo, M. & Stutzle, T. (2004). *Ant Colony Optimization.* MIT Press.
- McKeown, N. et al. (2008). "OpenFlow: Enabling innovation in campus networks." *ACM SIGCOMM CCR*, 38(2), 69-74.

## License

All rights reserved. See repository for details.
