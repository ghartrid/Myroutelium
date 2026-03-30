# Myroutelium Biological Substrate — Living Network Specification

## 1. Abstract

The Myroutelium Biological Substrate Layer (BSL) models a living mycelial network as a computing and routing medium. Unlike the radio and network layers which simulate biological *principles* on digital hardware, the BSL simulates the actual biological tissue — hyphal growth, ionic signaling, electrical conductivity, and environmental response — to serve as a development platform for controlling real fungal networks.

The goal: develop control algorithms that can be deployed on physical mycelium with electrode arrays, turning a living fungal network into a biological router.

## 2. Biological Properties Modeled

### 2.1 Hyphal Network

Real mycelial hyphae are tubular cells 2-10μm in diameter. Key properties:

| Property | Value | Source |
|---|---|---|
| Growth rate | 0.1-4.0 mm/hr | Species dependent |
| Tube diameter | 2-10 μm | Adapts to nutrient flow |
| Branching angle | 30-90° | Species and substrate dependent |
| Branching probability | 0.01-0.1 per μm per hr | Nutrient dependent |
| Anastomosis (fusion) rate | ~0.3 per encounter | Genetically compatible hyphae |
| Max network radius | 1-100+ meters | Largest organism on Earth |
| Lifespan of segment | Hours to years | Activity dependent |

### 2.2 Electrical Properties

Fungi generate and conduct bioelectrical signals:

| Property | Value | Source |
|---|---|---|
| Resting membrane potential | -50 to -200 mV | Species dependent |
| Action potential amplitude | 50-100 mV | Adamatzky 2018 |
| Propagation speed | 0.5-5.0 mm/s | Along hyphae |
| Spike duration | 1-20 seconds | Much slower than neurons |
| Spike patterns | Up to 50 distinct | Adamatzky 2018 (Pleurotus) |
| Refractory period | 10-60 seconds | Post-spike recovery |
| Ionic basis | Ca2+, K+, H+, Cl- | Multiple ion channels |
| Conductivity | 0.1-10 mS/m | Moisture dependent |

### 2.3 Environmental Factors

| Factor | Effect on Network |
|---|---|
| Moisture | Higher = better conductivity, faster growth |
| Temperature | Optimal 20-30°C, growth stops <5°C or >40°C |
| pH | Optimal 5-7, affects ion channel behavior |
| Nutrient concentration | Drives growth direction and tube diameter |
| Light | Some species exhibit negative phototropism |
| Mechanical stress | Triggers electrical signals, affects branching |

## 3. Substrate Model

### 3.1 Hyphal Segment

The basic unit is a hyphal segment between two junctions:

```
segment = {
    id:                 int
    start:              (x, y)           # position in mm
    end:                (x, y)
    length:             L ∈ ℝ⁺          # mm
    diameter:           D ∈ [2, 10]     # μm
    conductivity:       σ ∈ ℝ⁺          # mS/m — depends on diameter + moisture
    membrane_potential:  V_m ∈ [-200, 0] # mV
    nutrient_flow:      F ∈ ℝ⁺          # relative flow rate
    age:                ticks
    alive:              bool

    # Derived
    resistance:         R = L / (σ · π · (D/2)²)
    capacitance:        C_m = ε · π · D · L    # membrane capacitance
    bandwidth:          proportional to D² (Hagen-Poiseuille)
}
```

### 3.2 Junction (Node)

Where hyphae meet, branch, or fuse:

```
junction = {
    id:                 int
    position:           (x, y)          # mm
    type:               "tip" | "branch" | "anastomosis" | "electrode"
    segments:           [segment_ids]

    # Electrical state
    potential:          V ∈ ℝ           # mV
    calcium:            [Ca2+] ∈ ℝ⁺    # intracellular calcium concentration (μM)
    potassium:          [K+] ∈ ℝ⁺      # μM

    # Growth state (tips only)
    growth_direction:   θ ∈ [0, 2π)
    growth_rate:        r ∈ ℝ⁺         # mm/hr
    branch_probability: p ∈ [0, 1]
}
```

### 3.3 Electrode (Digital Interface)

Points where the digital control system interfaces with the biological network:

```
electrode = {
    id:                 int
    position:           (x, y)          # mm
    type:               "stimulate" | "record" | "bidirectional"
    junction_id:        int | None      # nearest junction

    # Stimulation
    inject_current:     I ∈ ℝ           # μA — positive or negative
    inject_voltage:     V ∈ ℝ           # mV — clamp voltage

    # Recording
    measured_potential:  V_rec ∈ ℝ       # mV
    measured_calcium:   [Ca2+]_rec ∈ ℝ⁺ # μM (fluorescence proxy)
    spike_detected:     bool
    spike_pattern:      int             # classified pattern ID
}
```

## 4. Electrical Signaling Model

### 4.1 Hodgkin-Huxley Adapted for Fungi

Membrane potential dynamics (simplified from full HH):

```
C_m · dV/dt = -g_K · n⁴ · (V - E_K) - g_Ca · m² · (V - E_Ca) - g_leak · (V - E_leak) + I_ext
```

Where:
- **g_K** = potassium conductance (~5 mS/cm²)
- **g_Ca** = calcium conductance (~2 mS/cm²)
- **g_leak** = leak conductance (~0.3 mS/cm²)
- **E_K** = potassium reversal potential (~-80 mV)
- **E_Ca** = calcium reversal potential (~+60 mV)
- **E_leak** = leak reversal potential (~-60 mV)
- **I_ext** = externally injected current (from electrodes or neighbors)
- **n, m** = gating variables (0-1) with voltage-dependent kinetics

### 4.2 Calcium Wave Propagation

Calcium signals propagate through IP3-mediated release from internal stores:

```
d[Ca2+]/dt = J_release - J_pump + J_influx + D_Ca · ∇²[Ca2+]
```

Where:
- **J_release** = IP3-triggered release from ER (endoplasmic reticulum)
- **J_pump** = SERCA pump reuptake
- **J_influx** = external calcium entry through ion channels
- **D_Ca** = calcium diffusion coefficient (~200 μm²/s in cytoplasm)

### 4.3 Signal Propagation Along Hyphae

Electrical signals propagate as cable equation:

```
λ² · ∂²V/∂x² = τ · ∂V/∂t + V
```

Where:
- **λ** = space constant = √(r_m / r_i) — how far signal travels (~0.5-2 mm)
- **τ** = time constant = r_m · c_m (~10-100 ms)
- **r_m** = membrane resistance per length
- **r_i** = internal resistance per length

Thicker hyphae have larger λ (signal travels further) — this is the physical basis for rhizomorphs.

## 5. Growth Dynamics

### 5.1 Tip Extension

Hyphal tips extend in their growth direction:

```
dx/dt = growth_rate · cos(θ)
dy/dt = growth_rate · sin(θ)
```

Growth rate depends on:
```
growth_rate = r_base · nutrient_factor · moisture_factor · temperature_factor
```

### 5.2 Chemotropism (Direction Change)

Tips turn toward nutrient/signal gradients:

```
dθ/dt = κ · sin(θ_gradient - θ)
```

Where κ is the turning rate and θ_gradient points toward the nutrient source.

### 5.3 Branching

New branches form stochastically:

```
P(branch) = p_base · nutrient_factor · (1 + electrical_stimulus)
```

Branch angle: θ_branch = θ_parent ± Uniform(30°, 70°)

### 5.4 Anastomosis (Fusion)

When two tips from the same organism come within fusion distance:

```
P(fuse) = 0.3 · compatibility · proximity_factor
```

Creates a loop in the network, adding redundant paths.

### 5.5 Tube Diameter Adaptation

Segments carrying more flow physically widen (Hagen-Poiseuille analog):

```
dD/dt = α_grow · (flow / flow_ref) · (D_max - D) - δ_shrink · (D - D_min)
```

## 6. Electrode Control Interface

### 6.1 Stimulation Strategies

The digital controller can influence the biological network through electrodes:

**Current injection**: Trigger or suppress action potentials
```
I_stim → depolarize nearby junction → trigger spike → propagates through network
```

**Voltage clamping**: Force a junction to a specific potential
```
V_clamp → attract or repel calcium ions → modulate local signaling
```

**Nutrient electrode**: Release nutrients at a point (chemical stimulation)
```
nutrient_pulse → attract hyphal growth → grow network toward electrode
```

### 6.2 Recording and Classification

Electrodes record membrane potential and classify spike patterns:

```
recorded_signal → bandpass_filter → spike_detection → pattern_matching
```

Pattern classification maps biological signals to digital routing information:
- Pattern A = "path clear, low load"
- Pattern B = "congestion ahead"
- Pattern C = "damage detected"
- Pattern D = "new path available"

### 6.3 Control Loop

The Myroutelium control algorithm runs a continuous loop:

```
1. READ: Sample all recording electrodes
2. CLASSIFY: Map spike patterns to network state
3. DECIDE: Run Myroutelium routing algorithm
4. STIMULATE: Inject signals to guide the network
5. GROW: Guide growth toward desired topology via nutrient electrodes
6. WAIT: Biological timescale (seconds to minutes per cycle)
```

## 7. Mapping: Digital Myroutelium → Biological Substrate

| Digital Concept | Biological Implementation |
|---|---|
| Node (router) | Junction + electrode |
| Link (connection) | Hyphal segment |
| Link capacity | Segment diameter² (Hagen-Poiseuille) |
| Nutrient score | Actual nutrient flow through segment |
| Calcium signal | Real Ca2+ wave propagation |
| Packet | Encoded electrical pulse pattern |
| Reinforcement | Increased nutrient flow → tube widening |
| Decay | Reduced flow → tube shrinkage |
| Pruning | Segment death from starvation |
| Rhizomorph | Naturally thick trunk hypha |
| Tropism | Hyphal tip turning toward stimulus |
| Sleep | Segment dormancy (reduced metabolism) |
| Anastomosis | Natural hyphal fusion |

## 8. Substrate Parameters

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Base growth rate | r_base | 1.0 mm/hr | Tip extension speed |
| Max diameter | D_max | 10 μm | Thickest a segment can get |
| Min diameter | D_min | 2 μm | Thinnest viable segment |
| Branch probability | p_base | 0.02 /hr | Spontaneous branching rate |
| Fusion probability | p_fuse | 0.3 | Anastomosis success rate |
| Fusion distance | d_fuse | 0.1 mm | Max gap for fusion |
| Membrane capacitance | C_m | 1.0 μF/cm² | Standard biological membrane |
| Resting potential | V_rest | -70 mV | Resting membrane potential |
| AP threshold | V_thresh | -40 mV | Spike initiation threshold |
| AP amplitude | V_spike | 80 mV | Peak-to-trough amplitude |
| Propagation speed | v_prop | 2.0 mm/s | Along hyphae |
| Refractory period | t_refrac | 30 s | Post-spike recovery |
| Ca2+ diffusion | D_Ca | 200 μm²/s | Cytoplasmic diffusion |
| Space constant | λ | 1.0 mm | Signal decay length |
| Time constant | τ | 50 ms | Membrane time constant |
| Optimal temperature | T_opt | 25°C | Peak growth/signaling |
| Optimal moisture | M_opt | 0.8 | Relative (0-1) |
| Optimal pH | pH_opt | 6.0 | Slightly acidic |
| Electrode spacing | d_electrode | 5 mm | Distance between electrodes |
| Stimulus current | I_stim | 1-10 μA | Electrode injection range |

## 9. Timescale Mapping

A critical challenge: biological timescales are orders of magnitude slower than digital:

| Process | Biological | Digital Equivalent |
|---|---|---|
| Action potential | 1-20 seconds | 1 simulation tick |
| Calcium wave | 10-60 seconds | 3-5 ticks |
| Growth (1mm) | 15-60 minutes | 50-200 ticks |
| Diameter change | Hours | 500-2000 ticks |
| Branching event | Hours | Stochastic per tick |
| Anastomosis | Minutes | 10-30 ticks on contact |
| Full topology change | Days | Full simulation run |

The simulation runs at ~1 tick = 10 seconds of biological time.

## 10. Species Candidates

| Species | Why | Notes |
|---|---|---|
| *Physarum polycephalum* | Best studied, proven maze solver | Slime mold (not true fungus), fastest growth |
| *Pleurotus ostreatus* | 50 spike patterns measured | Oyster mushroom, robust, edible |
| *Ganoderma lucidum* | Strong electrical signals | Reishi, slow but very resilient |
| *Serpula lacrymans* | Fastest hyphal growth (4mm/hr) | Dry rot fungus, aggressive grower |
| *Armillaria ostoyae* | Largest organism on Earth (2.4 mi²) | Honey fungus, extreme scalability proven |

**Recommended starting species**: *Physarum polycephalum* — fastest iteration cycle, most existing research, simplest growth requirements, proven computational capabilities.
