# Myroutelium Security — Biological Immune System Specification

## 1. Abstract

The Myroutelium Biological Immune System (MBIS) provides five layers of defense against malicious signals transmitted through the mycelial network. Unlike digital firewalls that inspect data content, MBIS authenticates signals based on their biological interaction with the living medium — the organism's electrochemical response to a signal is unique and unforgeable. Threats are neutralized through biological mechanisms: calcium immune bursts, segment quarantine, programmed cell death (apoptosis), and clean regrowth.

## 2. Threat Model

### 2.1 Attack Vectors

| Vector | Description | Biological Severity |
|---|---|---|
| Signal injection | Foreign electrode injects malicious spike trains | High |
| Signal replay | Captured signals re-injected at a later time | Medium |
| Path flooding | Overwhelming a path with noise to deny service | High |
| Signal manipulation | Altering spike patterns in transit | Medium |
| Electrode compromise | Attacker gains physical access to an electrode | Critical |
| Organism contamination | Foreign biological material introduced | Critical |

### 2.2 Trust Boundaries

```
TRUSTED:
  - Registered electrodes with known biological response profiles
  - Segments grown from the original organism (genetically compatible)
  - Calcium signals originating from verified junctions

UNTRUSTED:
  - New electrode connections (until validated)
  - Signals with anomalous biological response patterns
  - Segments exhibiting incompatible ion dynamics
  - External electromagnetic interference
```

## 3. Five Defense Layers

### 3.1 Layer 1: Spike Pattern Authentication

Every legitimate signal produces a specific biological response in the receiving segment. This response depends on the segment's current electrochemical state, which is unique and constantly changing.

**Authentication mechanism:**

```
For each incoming signal at junction J:
  1. Measure signal properties:
     - amplitude (mV)
     - duration (ms)
     - rise_time (ms)
     - inter_spike_interval (ms)
  2. Compare against expected biological response:
     - expected = f(J.membrane_potential, J.calcium, J.potassium, segment.ion_channels)
  3. Compute authentication score:
     - auth_score = 1.0 - |observed_response - expected_response| / tolerance
  4. If auth_score < AUTH_THRESHOLD (default: 0.6):
     - REJECT signal
     - Flag junction as under_attack
     - Emit IMMUNE calcium signal
```

**Why this works:** The "expected response" depends on the exact electrochemical state of the receiving junction at that instant. An attacker would need to know:
- The current membrane potential (changes every tick)
- The calcium concentration (changes with every signal)
- The potassium concentration
- The ion channel states of every connected segment

This state is only measurable from inside the organism.

### 3.2 Layer 2: Calcium Immune Response

When a threat is detected, a defensive calcium burst propagates through the network at maximum speed — faster than any data signal.

**Immune signal protocol:**

```
On threat detection at junction J:
  1. Emit IMMUNE calcium signal:
     - type: "IMMUNE"
     - strength: 1.0 (maximum)
     - propagation: 5x normal calcium speed
     - payload: {threat_type, source_junction, severity}
  2. Immune signal effects on receiving junctions:
     - Enter LOCKDOWN state for lockdown_duration ticks
     - Reject ALL incoming data signals (only accept IMMUNE signals)
     - Raise authentication threshold temporarily (0.6 → 0.9)
     - Increase calcium concentration (primes ion channels for defense)
  3. Lockdown cascade:
     - Each junction in lockdown re-emits IMMUNE signal (amplified)
     - Creates expanding defensive perimeter around threat source
```

### 3.3 Layer 3: Path Quarantine (Melanin Wall)

Segments carrying detected malicious signals are electrically isolated.

```
Quarantine protocol:
  1. Mark compromised segments as QUARANTINED
  2. Set segment conductivity to near-zero (simulates melanin encapsulation)
  3. All routing algorithms exclude quarantined segments
  4. Quarantined segments retain physical properties but carry no signals
  5. Traffic automatically reroutes through healthy paths
  6. Quarantine duration: QUARANTINE_TICKS (default: 100)
  7. After quarantine expires:
     - Re-test segment with authentication probe
     - If passes: restore to active duty
     - If fails: extend quarantine or trigger apoptosis
```

### 3.4 Layer 4: Segment Apoptosis (Programmed Death)

For severe or persistent contamination, compromised segments are killed.

```
Apoptosis protocol:
  1. Trigger conditions:
     - Segment fails authentication 3 consecutive times after quarantine
     - Segment shows anomalous ion dynamics for > APOPTOSIS_THRESHOLD ticks
     - IMMUNE signal received with severity = "critical"
  2. Apoptosis process:
     - Segment.alive = False (immediate)
     - All data in segment's ion states ceases to exist
     - Connected junctions update their segment lists
     - Calcium DEATH signal emitted to notify network
  3. Regrowth:
     - Nearby tips detect gap (reduced calcium from missing segment)
     - Chemotropism guides new growth toward the gap
     - New clean segment forms with fresh ion channel states
     - New segment inherits NO state from dead segment (clean slate)
```

### 3.5 Layer 5: Biological Validation (Vegetative Compatibility)

The deepest defense: the organism validates that all connected tissue belongs to the same genetic individual.

```
Compatibility check:
  1. Periodic handshake between adjacent segments:
     - Segment A sends characteristic ion pulse pattern
     - Segment B responds with its characteristic pattern
     - Both compare responses against known-good profile
  2. Incompatibility detection:
     - Foreign tissue produces wrong ion cascade timing
     - Wrong calcium response amplitude
     - Wrong potassium channel behavior
  3. On incompatibility:
     - Contact zone segments undergo immediate apoptosis
     - Barrier of dead cells forms (melanin wall analogue)
     - IMMUNE alert propagated to entire network
     - Equivalent to biological vegetative incompatibility response
```

## 4. Biological Authentication Signatures

### 4.1 Signal Fingerprint

Each legitimate signal has a biological fingerprint determined by the organism's genetics and current state:

```
fingerprint = {
    spike_amplitude:    V_peak - V_rest     (mV, determined by ion channel density)
    spike_duration:     t_repolarize        (ms, determined by K+ channel kinetics)
    rise_time:          t_depolarize        (ms, determined by Ca2+ channel kinetics)
    refractory_period:  t_refractory        (ms, determined by channel inactivation)
    calcium_response:   [Ca2+]_peak         (μM, determined by internal Ca2+ stores)
    propagation_delay:  distance / v_prop   (ms, determined by segment properties)
}
```

### 4.2 Response Profile

When a signal arrives at a junction, the biological response follows a predictable pattern:

```
Legitimate signal:
  t=0ms:  Signal arrives, membrane depolarizes
  t=2ms:  Ca2+ channels open (organism-specific kinetics)
  t=5ms:  Ca2+ peaks at expected amplitude
  t=8ms:  K+ channels open (repolarization begins)
  t=15ms: Membrane returns toward resting potential
  t=30ms: Ca2+ pumped back to stores

Foreign/malicious signal:
  t=0ms:  Signal arrives, membrane depolarizes (may look normal)
  t=2ms:  Ca2+ response WRONG — amplitude or timing mismatch
  t=5ms:  Ion cascade diverges from expected profile
  → DETECTED as anomalous at t=5ms (before signal fully propagates)
```

The detection window (5ms biological, ~0.05 ticks simulation) is faster than the signal propagation time, meaning threats are detected before they can reach the next junction.

## 5. Reactive Oxygen Species (ROS) Purge

For area-wide contamination, the nuclear option:

```
ROS purge protocol:
  1. Trigger: Multiple IMMUNE signals converge on same region
  2. Effect: ALL segments within purge_radius are killed
     - Legitimate and compromised alike
     - Complete data destruction in the zone
  3. Recovery:
     - Surrounding healthy tissue grows inward
     - New clean network forms in the purged zone
     - Takes significant biological time (hours)
  4. Use case: Widespread coordinated attack that overwhelms
     targeted quarantine
```

## 6. Parameters

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Auth threshold | AUTH_THRESH | 0.6 | Below this, signal rejected |
| Lockdown auth threshold | AUTH_LOCK | 0.9 | Raised threshold during lockdown |
| Lockdown duration | T_LOCK | 20 ticks | How long junction stays locked |
| Immune propagation speed | V_IMMUNE | 5x | Multiplier vs normal calcium speed |
| Quarantine duration | T_QUAR | 100 ticks | How long segment stays isolated |
| Apoptosis failure count | N_APOPT | 3 | Auth failures before death |
| Apoptosis threshold | T_APOPT | 50 ticks | Anomalous ticks before death |
| ROS purge radius | R_PURGE | 5 mm | Area wiped on ROS trigger |
| Compatibility check interval | T_COMPAT | 200 ticks | How often segments handshake |
| Regrowth attraction | CA_REGROW | 2.0 μM | Calcium level to attract regrowth |

## 7. Security Properties

| Property | Mechanism |
|---|---|
| **Authentication** | Biological response fingerprinting (unforgeable) |
| **Detection speed** | Faster than signal propagation (pre-emptive) |
| **Containment** | Calcium immune burst + path quarantine |
| **Elimination** | Segment apoptosis (data ceases to exist physically) |
| **Recovery** | Clean biological regrowth (no state inheritance) |
| **Forward secrecy** | Dead segments carry no recoverable data |
| **Anti-replay** | Electrochemical state changes between signals |
| **Anti-flooding** | Lockdown rejects all signals during attack |
| **Physical security** | Vegetative incompatibility rejects foreign tissue |

## 8. Comparison with Digital Security

| Feature | Digital Firewall | Myroutelium MBIS |
|---|---|---|
| Inspection method | Content analysis (pattern matching) | Physical medium response |
| Authentication | Cryptographic (keys) | Biological (electrochemical state) |
| Key management | Manual rotation | Automatic (organism changes) |
| Containment | Network segmentation (config) | Biological quarantine (automatic) |
| Data destruction | Secure wipe (recoverable with effort) | Cell death (physically irreversible) |
| Recovery | Restore from backup | Biological regrowth (clean) |
| Zero-day defense | Vulnerable (unknown patterns) | Inherent (medium validates, not rules) |
| Forgery resistance | Computational (breakable in theory) | Physical (requires replicating organism) |

## 9. Implementation Status

| Component | Status |
|---|---|
| Spike authentication | Implementing |
| Calcium immune response | Implementing |
| Path quarantine | Implementing |
| Segment apoptosis | Implementing |
| Vegetative compatibility | Implementing |
| ROS purge | Implementing |
| Visualization | Implementing |
| Physical implementation | Future |
