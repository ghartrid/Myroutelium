# Myroutelium Encryption — Living Cryptography Specification

## 1. Abstract

Myroutelium Encryption (ME) is a physical-layer cryptographic system where the encryption key is a living biological organism. Data is split across multiple parallel mycelial paths using secret sharing, with each share XOR-masked by a key derived from the physical properties of the biological path it traverses. The key changes continuously as the organism grows, creating a self-generating one-time pad. An attacker tapping any single hypha receives only a masked fragment. Physically destroying the network destroys the key with no digital copy remaining.

## 2. Security Model

### 2.1 Threat Model

| Threat | Protection |
|---|---|
| Passive eavesdropping (single path) | Secret sharing — any single share is random noise |
| Passive eavesdropping (multiple paths) | Biological key XOR — shares are masked with topology-derived keys |
| Replay attack | Temporal key rotation — key changes as organism grows |
| Key theft | Key is physical (biological tissue) — no digital copy exists |
| Brute force | Key space = product of all segment properties across all paths |
| Man-in-the-middle | Physical security — network is a contained biological specimen |
| Side channel | Biological noise provides natural signal masking |

### 2.2 Four Security Layers

**Layer 1: Secret Sharing (Information-Theoretic)**

Data is split across N biological paths such that no subset of N-1 paths reveals any information about the plaintext. This follows Shamir-like XOR secret sharing:

For each plaintext byte `P[i]`:
```
Share[0][i] = random() XOR PathKey[0][i]
Share[1][i] = random() XOR PathKey[1][i]
...
Share[N-2][i] = random() XOR PathKey[N-2][i]
Share[N-1][i] = P[i] XOR (Share[0..N-2] XOR'd) XOR PathKey[N-1][i]
```

Reconstruction:
```
P[i] = XOR(all shares with path keys reversed)
```

**Layer 2: Biological Path Signature (Physical Key)**

Each path's encryption key is derived from the physical properties of every segment along that path:

```
PathKey[p][i] = XOR over all segments s in path p:
    floor(s.diameter * 37 + s.length * 13 + s.ionSignature * 251 + i * 7 + s.index * 19) AND 0xFF
    XOR
    floor(node.ionState * 199 + i * 11 + node.index * 23) AND 0xFF
```

Key components:
- **Segment diameter** (μm) — physically determined by nutrient history
- **Segment length** (mm) — determined by growth pattern
- **Ion channel state** — current electrochemical state of each segment
- **Node ion state** — intracellular ion concentration at each junction

These properties are measurable only by the electrodes physically embedded in the network. They cannot be remotely observed.

**Layer 3: Temporal Key Rotation (Living One-Time Pad)**

The mycelium grows continuously:
- Hyphal tips extend at 1-4 mm/hr
- New branches form stochastically
- Anastomosis creates new connections
- Segment diameters change with traffic
- Ion channel states fluctuate

Every growth event changes the physical properties of at least one segment, changing the derived key. Over time, the key diverges completely from any previous state. The key rotation rate is:

```
Key change rate ≈ growth_events_per_hour × affected_segments × bits_per_segment
```

For a typical Physarum network: ~20 events/hr × ~5 segments × ~8 bits = ~800 key bits changed per hour.

**Layer 4: Physical Security**

- The encryption key exists only as physical biological tissue
- No digital representation of the key is stored anywhere
- Key derivation happens in real-time from electrode measurements
- Destroying the biological specimen destroys the key irrecoverably
- The specimen is a contained physical object — access requires physical proximity
- Biological noise (ion fluctuations, growth randomness) provides natural entropy

### 2.3 Key Space Analysis

For a network with N paths, each containing S segments with D-bit property resolution:

```
Key space = (2^D)^(S × N)
```

Typical values: N=5 paths, S=6 segments/path, D=8 bits/property, 3 properties/segment:
```
Key space = (2^8)^(6 × 5 × 3) = 256^90 ≈ 2^720
```

This exceeds AES-256 key space (2^256) by a factor of 2^464.

## 3. Transmission Protocol

### 3.1 Encoding

```
1. PLAINTEXT → byte array [P0, P1, ..., Pn]
2. Pad to multiple of N (path count)
3. For each byte position i:
   a. Generate N-1 random share bytes
   b. XOR each share with corresponding PathKey
   c. Compute final share: P[i] XOR all_other_shares XOR PathKey[N-1]
4. Assign shares to paths: Share[p] → Path[p]
```

### 3.2 Transmission

Each share byte is transmitted as a spike train through its assigned biological path:

```
For each bit in share byte (MSB first):
    bit = 1 → inject current pulse at source electrode → action potential propagates
    bit = 0 → silence (no pulse) for one time slot
```

All N paths transmit simultaneously — parallel biological data links.

### 3.3 Reception

The destination electrode array records arriving spikes from all paths:

```
1. For each path, reconstruct share bytes from spike patterns
2. For each byte position i:
   a. Collect Share[0][i] through Share[N-1][i]
   b. Reverse path key masking: Share[p][i] XOR PathKey[p][i]
   c. XOR all unmasked shares → P[i] (plaintext byte)
3. Reassemble plaintext byte array → text
```

### 3.4 Error Handling

Biological transmission is inherently noisy. Error handling:

- **Redundancy**: Each share byte transmitted 3 times (majority vote)
- **Checksum**: CRC-8 appended to each share block
- **Retransmission**: On CRC failure, re-request specific share bytes via calcium signal
- **Path health monitoring**: Continuous SNR measurement per path; degraded paths trigger rerouting

## 4. Key Management

### 4.1 Key Derivation

Keys are derived fresh for each transmission by sampling electrode measurements:

```
1. Source electrode array measures:
   - Membrane potential at each junction
   - Calcium concentration at each junction
   - Segment conductivity (impedance measurement)
2. Destination electrode array measures the same
3. Both derive identical keys from shared physical reality
4. No key exchange protocol needed — the biology IS the shared secret
```

### 4.2 Key Agreement

Source and destination must be connected to the same biological network. Key agreement is implicit:

- Both endpoints measure the same physical segments
- Identical measurement protocol yields identical keys
- Key synchronization verified by transmitting a known test pattern

### 4.3 Key Rotation

Automatic — the organism grows. Explicit rotation by:

```
1. Stimulate growth at specific points (nutrient electrodes)
2. Wait for growth to change segment properties
3. Re-derive keys from updated measurements
4. Old key is permanently lost (segments have physically changed)
```

### 4.4 Key Destruction

- Remove the biological specimen from the electrode array
- Or: allow the specimen to die (desiccation, temperature)
- Or: physically destroy the specimen
- In all cases: key is irrecoverably lost with no digital residue

## 5. Comparison with Digital Encryption

| Property | AES-256 | RSA-4096 | Myroutelium |
|---|---|---|---|
| Key storage | Digital (copiable) | Digital (copiable) | Physical (non-copiable) |
| Key rotation | Manual | Manual | Automatic (biological) |
| Key destruction | Requires secure wipe | Requires secure wipe | Physical destruction |
| Key space | 2^256 | ~2^256 | ~2^720 |
| Side channel risk | High (timing, power) | High | Low (biological noise) |
| Quantum resistant | No (Grover) | No (Shor) | Yes (physical, not mathematical) |
| Forward secrecy | With protocol support | With protocol support | Inherent (key changes biologically) |
| Requires hardware | Standard CPU | Standard CPU | Biological specimen + electrodes |
| Scalability | Unlimited | Unlimited | Limited by specimen size |

## 6. Limitations

- **Physical proximity required**: Both endpoints must connect to the same biological network
- **Bandwidth**: Biological signaling is slow (bits/second, not gigabits/second)
- **Environmental sensitivity**: Temperature, moisture, pH affect the organism and thus the key
- **Specimen maintenance**: The organism must be kept alive
- **Not suitable for**: High-bandwidth, long-distance, or general internet communication
- **Suitable for**: Ultra-high-security local communication, air-gapped secure channels, diplomatic/military secure rooms, secure key storage

## 7. Candidate Organisms

| Organism | Key Change Rate | Bandwidth | Maintenance |
|---|---|---|---|
| *Physarum polycephalum* | High (fast growth) | ~10 bps | Easy (oat flakes + moisture) |
| *Pleurotus ostreatus* | Medium | ~5 bps | Medium (wood substrate) |
| *Ganoderma lucidum* | Low (slow, stable) | ~2 bps | Easy (resilient) |

Recommended: *Physarum polycephalum* for development, *Ganoderma lucidum* for production (stability over speed).

## 8. Implementation Status

- **Simulated**: Full 4-layer encryption implemented in visualization.html
- **Validated**: Secret sharing, biological key derivation, eavesdropper demonstration
- **Future**: Physical implementation with real organism + Arduino/Raspberry Pi electrode array
