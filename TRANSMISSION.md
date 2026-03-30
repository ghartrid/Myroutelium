# Myroutelium Transmission Protocols — Text and Image Over Living Networks

## 1. Abstract

Myroutelium implements two data transmission protocols that encode digital information as biological spike trains and route them through living mycelial networks. The Text Transmission Protocol (TTP) sends character data as 8-bit ASCII spike patterns. The Image Transmission Protocol (ITP) sends pixel data as grayscale values using multi-path parallel routing. Both protocols demonstrate that a biological network can function as a data link layer.

## 2. Text Transmission Protocol (TTP)

### 2.1 Overview

Text is transmitted character-by-character through the mycelial network as a serial spike train between source and destination electrodes.

### 2.2 Encoding

```
Character → ASCII code (0-127) → 8-bit binary → spike train

Example: 'H' = 72 = 01001000
  Bit 7: 0 → silence (no pulse)
  Bit 6: 1 → current injection → action potential
  Bit 5: 0 → silence
  Bit 4: 0 → silence
  Bit 3: 1 → current injection → action potential
  Bit 2: 0 → silence
  Bit 1: 0 → silence
  Bit 0: 0 → silence
```

### 2.3 Timing

| Parameter | Value | Biological Basis |
|---|---|---|
| Bit slot duration | 10 seconds | Refractory period of fungal action potential |
| Character duration | 80 seconds | 8 bits × 10s |
| Inter-character gap | 10 seconds | One silent slot |
| Effective bit rate | 0.1 bps | Limited by biological refractory period |
| "Hello World" duration | ~16.5 minutes | 11 chars × 90s |

### 2.4 Transmission

```
1. Source electrode injects current pulse (1-10 μA) for each '1' bit
2. Current triggers action potential at source junction
3. Action potential propagates along hyphae (0.5-5 mm/s)
4. Signal attenuates exponentially: amplitude × e^(-distance/λ)
5. Thicker segments (higher λ) carry signals further
6. Destination electrode detects arriving spike or silence
```

### 2.5 Reception and Decoding

```
1. Destination electrode monitors membrane potential
2. Spike detection: V > threshold → bit = 1, else bit = 0
3. Accumulate 8 bits → ASCII byte → character
4. Assemble characters → message string
```

### 2.6 Signal Quality

Signal quality depends on the biological path:

| Path Property | Effect on Signal |
|---|---|
| Segment diameter | Larger → higher space constant λ → less attenuation |
| Path length | Shorter → less attenuation |
| Rhizomorph trunk | Much thicker → signals travel much further |
| Moisture | Higher → better ionic conductivity |
| Temperature | Optimal range → faster propagation |
| Branching | Signal splits at branches → amplitude reduction |

### 2.7 Error Mitigation

- **Rhizomorph preference**: Route through thick trunk hyphae when available
- **Repeat coding**: Each bit transmitted 3× (majority vote at receiver)
- **Calcium pre-signaling**: Ca2+ wave sent before data to prime the path
- **Amplitude threshold tuning**: Adaptive threshold based on path SNR

## 3. Image Transmission Protocol (ITP)

### 3.1 Overview

Images are transmitted as pixel arrays using multi-path parallel routing. Different rows of the image route through different biological paths simultaneously, dramatically increasing throughput compared to serial text transmission.

### 3.2 Image Format

```
Resolution: 16×16 pixels (256 pixels total)
Color depth: 8-bit grayscale (0 = black, 255 = white)
Total data: 256 × 8 = 2,048 bits
```

### 3.3 Encoding

Each pixel is encoded as an 8-bit spike train, identical to TTP character encoding:

```
Pixel value 200 = 11001000 binary
  → spike, spike, silence, silence, spike, silence, silence, silence
```

### 3.4 Multi-Path Parallel Routing

The key advantage of ITP over TTP: parallel transmission across N biological paths.

```
Path assignment:
  Row 0 → Path 0
  Row 1 → Path 1
  Row 2 → Path 2
  ...
  Row N → Path (N % num_paths)

Each path carries IMG_WIDTH pixels per assigned row.
N paths transmit simultaneously → N× throughput.
```

### 3.5 Routing Strategy

```
1. Discover available paths between source and destination electrodes
2. Rank paths by quality (diameter, SNR, rhizomorph status)
3. Assign pixel rows to paths — best paths get more rows
4. Calcium pre-signal on all paths to prime them
5. Begin parallel transmission
6. Monitor path health — reroute on failure
```

### 3.6 Path Failure Recovery

If a biological path fails during transmission:

```
1. Calcium FAILURE signal propagates from failed segment
2. Affected packets marked as lost
3. Remaining pixels for that row rerouted to surviving paths
4. Lost pixels re-queued for retransmission
5. Destination requests missing pixel indices via return calcium signal
```

### 3.7 Reception and Reconstruction

```
1. Destination electrodes record incoming spikes from all paths
2. Each 8-bit sequence decoded to grayscale pixel value
3. Pixels placed in output image at their original (x, y) position
4. Image reconstructs progressively — visible as pixels fill in
5. CRC check per row — request retransmission on error
```

### 3.8 Performance

| Metric | Single Path (TTP) | Multi-Path 5× (ITP) |
|---|---|---|
| Throughput | ~0.1 bps | ~0.5 bps |
| 16×16 image time | ~5.7 hours | ~68 minutes |
| Latency per pixel | ~80 seconds | ~80 seconds |
| Path diversity | 1 | 5 (fault tolerant) |

### 3.9 Noise Injection Response

When environmental noise corrupts in-flight signals:

```
1. Noise flips random bits in spike trains
2. Received pixel values deviate from source
3. Visual artifact: "static" or brightness errors in received image
4. Mitigation: repeat coding, error correction, re-request
```

## 4. Network Topology for Transmission

### 4.1 Minimum Viable Network

```
Text (TTP):
  - 1 source electrode
  - 1 destination electrode
  - 1 connected mycelial path (any length)
  - Minimum: 2 junctions, 1 segment

Image (ITP):
  - 1 source electrode
  - 1 destination electrode
  - N parallel mycelial paths (N ≥ 3 recommended)
  - Paths should be independent (minimal shared segments)
```

### 4.2 Optimal Network

```
  - Dense mycelial network between source and destination
  - Multiple rhizomorph trunks for high-bandwidth channels
  - Anastomosis cross-connections for redundancy
  - Electrode array (not just single electrodes) for parallel I/O
```

## 5. Biological Modem Concept

The combination of TTP and ITP with the electrode interface constitutes a **biological modem** (modulator-demodulator):

```
Digital data
    ↓ [modulate]
Spike train (current injection)
    ↓ [biological channel]
Mycelial propagation (ion dynamics, attenuation, noise)
    ↓ [demodulate]
Spike detection → Digital data
```

### 5.1 Modulation: Digital → Biological

| Digital | Biological |
|---|---|
| Bit = 1 | Current injection → action potential |
| Bit = 0 | Silence (no injection) |
| Byte boundary | Extended silence (1.5× bit slot) |
| Message start | Preamble: 4 alternating spikes (10101010) |
| Message end | Postamble: 4 consecutive spikes (11111111) |

### 5.2 Demodulation: Biological → Digital

| Biological | Digital |
|---|---|
| Spike detected (V > threshold) | Bit = 1 |
| No spike in time slot | Bit = 0 |
| Preamble pattern matched | Start of message |
| Postamble pattern matched | End of message |

### 5.3 Achievable Data Rates

Limited by fungal action potential biology:

| Organism | Refractory Period | Max Bit Rate | "Hello World" Time |
|---|---|---|---|
| *Physarum polycephalum* | ~10s | 0.1 bps | 15 min |
| *Pleurotus ostreatus* | ~20s | 0.05 bps | 30 min |
| *Ganoderma lucidum* | ~30s | 0.03 bps | 45 min |
| Multi-path (5×) | ~10s | 0.5 bps | 3 min |

## 6. Visualization

The interactive visualization (visualization.html) demonstrates both protocols:

### Text Transmission Tab
- Type message → watch binary encoding at top
- Orange pulses = action potentials traversing hyphae
- Purple glow = calcium waves along active segments
- Binary stream reconstructs at destination → text appears character by character

### Image Transmission Tab
- Select image (smiley, heart, arrow, wave, grid, text, or draw custom)
- Pixels stream as colored dots through multi-path network
- Different rows take different biological paths (visible as distinct routes)
- Destination image reconstructs pixel by pixel
- Interactive: inject noise, break paths, watch rerouting

## 7. Implementation Status

| Component | Status |
|---|---|
| Text encoding/decoding | Implemented (visualization.html) |
| Image encoding/decoding | Implemented (visualization.html) |
| Multi-path routing | Implemented (visualization.html) |
| Noise injection | Implemented (visualization.html) |
| Path failure recovery | Implemented (visualization.html) |
| Biological modem spec | Specified (this document) |
| Physical implementation | Future (requires electrode hardware) |
