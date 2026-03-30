# Myroutelium Physical Layer — Adaptive Mesh Radio Protocol

## 1. Abstract

The Myroutelium Physical Layer (MPL) is a bio-inspired adaptive mesh radio protocol where the physical medium itself reorganizes based on traffic patterns. Unlike static mesh protocols (802.11s, Zigbee, LoRa mesh) where radio parameters are fixed or manually configured, MPL nodes dynamically adjust transmit power, channel width, and antenna directionality using fungal nutrient/calcium logic — making the radio topology a living, self-organizing system.

## 2. Biological Mapping

| Fungal Property | Radio Analogue |
|---|---|
| Hyphal tube diameter | Transmit power toward a neighbor |
| Nutrient concentration in tube | Channel width (bandwidth allocation) |
| Tube growth direction | Beam steering / antenna directionality |
| Ca2+ fast signaling | Out-of-band control channel (low-power, always-on) |
| Spore dispersal | Beacon / discovery broadcasts |
| Hyphal branching | Multi-path radio links to multiple neighbors |
| Tube decay / pruning | Power reduction / link deactivation |
| Fruiting body | Periodic topology optimization |

## 3. Radio Node Model

### 3.1 Node Properties

Each Myroutelium radio node has:

```
node = {
    id:             string
    position:       (x, y)              // geographic coordinates (meters)
    max_power:      P_max   ∈ ℝ⁺       // maximum transmit power (dBm)
    min_power:      P_min   ∈ ℝ⁺       // minimum transmit power (dBm)
    total_bandwidth: B_total ∈ ℝ⁺      // total available bandwidth (MHz)
    noise_floor:    N_f     ∈ ℝ        // receiver noise floor (dBm)
    frequency:      f       ∈ ℝ⁺       // center frequency (GHz)
    alive:          bool
}
```

### 3.2 Per-Neighbor Link State

Each node maintains per-neighbor state (one per visible neighbor):

```
radio_link = {
    neighbor:       node_id
    tx_power:       P_tx    ∈ [P_min, P_max]    // current transmit power to this neighbor
    channel_width:  B       ∈ [B_min, B_total]   // bandwidth allocated to this link
    nutrient:       N       ∈ [0, 1]             // mycelial reinforcement score
    snr:            SNR     ∈ ℝ                  // measured signal-to-noise ratio (dB)
    rssi:           RSSI    ∈ ℝ                  // received signal strength (dBm)
    ber:            BER     ∈ [0, 1]             // bit error rate
    active:         bool                          // whether this link is currently used
}
```

### 3.3 Signal Propagation Model

Free-space path loss with log-distance model:

```
PL(d) = PL_0 + 10 · n · log10(d / d_0) + X_σ
```

Where:
- **PL_0** = reference path loss at distance d_0 (typically 40 dB at 1m for 2.4 GHz)
- **n** = path loss exponent (2.0 free space, 2.5-4.0 urban/indoor)
- **d** = distance between nodes (meters)
- **d_0** = reference distance (1m)
- **X_σ** = shadow fading (log-normal, σ = 4-8 dB)

Received signal strength:

```
P_rx = P_tx - PL(d)
SNR = P_rx - N_f
```

### 3.4 Achievable Data Rate (Shannon)

```
R = B · log2(1 + SNR_linear)
```

Where `SNR_linear = 10^(SNR_dB / 10)`.

This gives the theoretical maximum throughput for each link.

## 4. Adaptive Power Control (Tube Diameter)

### 4.1 The Core Mechanism

Transmit power to each neighbor adapts based on nutrient score:

```
P_tx(neighbor) = P_min + N(neighbor) · (P_max - P_min)
```

High nutrient = high power = wider "tube" = better link quality.
Low nutrient = low power = narrower "tube" = saves energy, reduces interference.

### 4.2 Power Reinforcement

When data is successfully delivered through a neighbor:

```
N(neighbor) += α_phy · Q_phy · (1 - N(neighbor))
```

Where the physical quality signal incorporates radio metrics:

```
Q_phy = (1 - BER) · (SNR / SNR_max) · (1 - utilization)
```

### 4.3 Power Decay

Each tick, all neighbor power levels decay:

```
N(neighbor) *= (1 - δ_phy)
```

When N drops below `N_prune_phy`, the link is deactivated (radio goes silent to that neighbor).

### 4.4 Power Budget Constraint

Total transmit power across all neighbors is bounded:

```
Σ P_tx(neighbor_i) ≤ P_budget
```

Where `P_budget` is a fraction of `P_max × n_neighbors` (default: 70%). This forces the node to prioritize — it can't maintain full power to all neighbors simultaneously, just as a hypha can't grow in all directions at once.

## 5. Adaptive Channel Allocation (Nutrient Concentration)

### 5.1 Bandwidth Splitting

Total available bandwidth is split across active neighbors proportional to nutrient scores:

```
B(neighbor_i) = B_total × N(neighbor_i) / Σ_j N(neighbor_j)
```

With a minimum allocation `B_min` (default: 1 MHz) to keep the link discoverable.

### 5.2 Channel Reallocation

Bandwidth is reallocated every `T_realloc` ticks (default: 10). Changes are gradual to avoid oscillation:

```
B_new = B_old + β · (B_target - B_old)
```

Where β ∈ (0, 1) is the smoothing factor (default: 0.3).

## 6. Calcium Control Channel

### 6.1 Design

A dedicated low-power, narrow-band control channel runs in parallel with data channels:

```
calcium_channel = {
    bandwidth:      B_ca = 0.5 MHz    // narrow but always-on
    power:          P_ca = P_min      // low power, short range
    modulation:     robust (BPSK)     // reliability over speed
    data_rate:      ~100 kbps         // enough for control signals
}
```

### 6.2 Signal Types

The calcium channel carries the same signal types as the network layer, but at the physical level:

**CONGESTION_WARN**: Broadcast when a link's utilization > θ_phy (default: 0.7)
```
{ type: "CONG", link: neighbor_id, severity: float, util: float }
```

**LINK_DOWN**: Broadcast when SNR drops below minimum or node failure detected
```
{ type: "DOWN", link: neighbor_id, timestamp: tick }
```

**LINK_UP**: Broadcast when a new neighbor is discovered or link recovers
```
{ type: "UP", link: neighbor_id, snr: float, capacity: float }
```

**OPTIMAL_PATH**: Broadcast for high-quality links (high SNR, low utilization)
```
{ type: "OPT", link: neighbor_id, quality: float }
```

### 6.3 Propagation

Calcium signals propagate across the mesh at 3x the rate of data-plane updates. Each node that receives a calcium signal:
1. Updates its local awareness map
2. Rebroadcasts to all neighbors (with strength decay) if strength > threshold
3. Adjusts its own power/channel allocation in response

### 6.4 Interference Avoidance

The calcium channel uses a different frequency band or time slot than data channels to avoid self-interference. In simulation, we model this as a separate, parallel signaling path with no cross-interference.

## 7. Discovery Protocol (Spore Beacons)

### 7.1 Beacon Format

Every `T_beacon` ticks (default: 50), each node broadcasts a discovery beacon:

```
beacon = {
    node_id:        string
    position:       (x, y)
    capabilities:   { max_power, bandwidth, frequency }
    neighbor_count: int
    load:           float           // current overall utilization
    timestamp:      tick
}
```

### 7.2 Neighbor Table

On receiving a beacon, a node:
1. Calculates distance from position data
2. Estimates achievable SNR from distance + sender's max power
3. Adds to neighbor table if SNR > SNR_min (default: 5 dB)
4. Initializes nutrient score at N_init

### 7.3 Adaptive Beacon Rate

Nodes in dense areas (many neighbors) reduce beacon rate to avoid control overhead:

```
T_beacon_effective = T_beacon × (1 + n_neighbors / 10)
```

## 8. Static Mesh Comparison (802.11s-like)

For benchmarking, we implement a simplified static mesh protocol:

- **Fixed transmit power**: All nodes transmit at P_max
- **Equal channel allocation**: Bandwidth split equally among all neighbors
- **No calcium channel**: State changes propagate only through data plane
- **HWMP-like routing**: Proactive tree-based routing with periodic path refresh
- **No adaptation**: Radio parameters don't change based on traffic

## 9. Physical Layer Parameters

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Max transmit power | P_max | 20 dBm | Maximum radio output |
| Min transmit power | P_min | 0 dBm | Minimum radio output |
| Total bandwidth | B_total | 20 MHz | Available spectrum |
| Min channel width | B_min | 1 MHz | Minimum per-link allocation |
| Noise floor | N_f | -90 dBm | Receiver sensitivity |
| Center frequency | f | 2.4 GHz | Operating frequency |
| Path loss exponent | n | 3.0 | Signal decay with distance |
| Shadow fading std | σ | 4.0 dB | Random fading variation |
| Physical reinforcement | α_phy | 0.15 | Power reinforcement rate |
| Physical decay | δ_phy | 0.02 | Power decay rate |
| Power budget fraction | P_budget_frac | 0.7 | Max fraction of total power |
| Channel smoothing | β | 0.3 | Bandwidth reallocation rate |
| Reallocation interval | T_realloc | 10 ticks | How often bandwidth shifts |
| Beacon interval | T_beacon | 50 ticks | Discovery broadcast rate |
| Ca2+ channel bandwidth | B_ca | 0.5 MHz | Control channel width |
| Ca2+ channel power | P_ca | 0 dBm | Control channel power |
| Min SNR | SNR_min | 5 dB | Below this, link unusable |
| Physical congestion threshold | θ_phy | 0.7 | Triggers calcium warning |

## 10. Expected Advantages over Static Mesh

| Property | Static Mesh | Myroutelium MPL |
|---|---|---|
| Power consumption | Fixed (always max) | Adaptive (saves 30-60%) |
| Interference | High (all nodes at max) | Low (power only where needed) |
| Bandwidth efficiency | Equal split (wasted on idle links) | Proportional to demand |
| Failure response | Path recomputation | Instant calcium + power redirect |
| New node integration | Full mesh recomputation | Local spore discovery |
| Congestion handling | None (fixed allocation) | Dynamic power/bandwidth shift |
| Topology awareness | Periodic refresh | Continuous calcium sensing |
