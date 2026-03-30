"""Biological substrate model — living mycelial network with electrical signaling,
growth dynamics, and electrode interface for biological routing."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


# ─── Constants ────────────────────────────────────────────────

TICK_SECONDS = 300.0     # 1 simulation tick = 5 minutes biological time
MM_PER_UNIT = 1.0        # coordinate units are millimeters


# ─── Core Data Structures ────────────────────────────────────

@dataclass
class HyphalSegment:
    """A single hyphal tube between two junctions."""
    id: int
    junction_a: int
    junction_b: int
    length: float              # mm
    diameter: float = 5.0      # μm (2-10)
    alive: bool = True
    age: int = 0               # ticks

    # Electrical properties
    conductivity: float = 1.0  # mS/m — moisture dependent
    membrane_potential: float = -70.0  # mV (resting)
    in_refractory: bool = False
    refractory_timer: int = 0

    # Flow
    nutrient_flow: float = 0.0  # relative flow rate
    data_flow: float = 0.0      # signal flow (packets routed through)

    # Rhizomorph
    is_rhizomorph: bool = False
    sustained_flow_ticks: int = 0

    @property
    def resistance(self) -> float:
        """Electrical resistance (MΩ) — thicker = lower resistance."""
        area = math.pi * (self.diameter * 1e-3 / 2) ** 2  # mm²
        if area <= 0 or self.conductivity <= 0:
            return 1e9
        return self.length / (self.conductivity * area)

    @property
    def space_constant(self) -> float:
        """λ — how far a signal propagates (mm). Thicker hyphae = larger λ."""
        return 0.5 + (self.diameter / 10.0) * 1.5  # 0.5-2.0 mm

    @property
    def bandwidth(self) -> float:
        """Information carrying capacity — proportional to diameter² (Hagen-Poiseuille)."""
        return (self.diameter / 5.0) ** 2  # normalized, 1.0 at 5μm

    @property
    def propagation_time_ticks(self) -> int:
        """Time for a signal to traverse this segment (in ticks)."""
        speed_mm_per_s = 2.0  # mm/s propagation speed
        time_s = self.length / speed_mm_per_s
        return max(1, int(time_s / TICK_SECONDS))


@dataclass
class Junction:
    """Where hyphae meet, branch, or interface with electrodes."""
    id: int
    x: float                    # mm
    y: float                    # mm
    junction_type: str = "branch"  # "tip", "branch", "anastomosis", "electrode"
    segments: list[int] = field(default_factory=list)
    alive: bool = True

    # Electrical state
    potential: float = -70.0    # mV
    calcium: float = 0.05       # μM (resting ~50nM)
    potassium: float = 140.0    # μM (intracellular)

    # Growth state (tips only)
    growth_direction: float = 0.0  # radians
    growth_rate: float = 1.0       # mm/hr
    branch_cooldown: int = 0       # ticks until can branch again

    # Spike detection
    last_spike_tick: int = -100
    spike_count: int = 0


@dataclass
class Electrode:
    """Digital interface point — stimulate and record from the biological network."""
    id: int
    x: float                    # mm
    y: float                    # mm
    electrode_type: str = "bidirectional"  # "stimulate", "record", "bidirectional"
    junction_id: int | None = None  # connected junction

    # Stimulation state
    inject_current: float = 0.0     # μA
    active: bool = False

    # Recording state
    measured_potential: float = -70.0  # mV
    measured_calcium: float = 0.05     # μM
    spike_detected: bool = False
    spike_pattern: int = -1            # classified pattern (-1 = none)

    # Signal interpretation
    last_spike_tick: int = -100
    spike_history: list[int] = field(default_factory=list)  # recent spike ticks


@dataclass
class Environment:
    """Environmental conditions affecting the substrate."""
    moisture: float = 0.8       # 0-1 (optimal ~0.8)
    temperature: float = 25.0   # °C (optimal 20-30)
    ph: float = 6.0             # optimal 5-7
    base_nutrient: float = 1.0  # relative concentration

    @property
    def growth_factor(self) -> float:
        """Combined environmental growth modifier [0, 1]."""
        temp_f = max(0.05, 1.0 - ((self.temperature - 25) / 20) ** 2)
        moist_f = max(0.05, 1.0 - ((self.moisture - 0.8) / 0.6) ** 2)
        ph_f = max(0.05, 1.0 - ((self.ph - 6.0) / 3.0) ** 2)
        return temp_f * moist_f * ph_f

    @property
    def conductivity_factor(self) -> float:
        """Moisture-based conductivity modifier."""
        return 0.1 + 0.9 * self.moisture

    @property
    def signal_speed_factor(self) -> float:
        """Temperature-based signal speed modifier."""
        return max(0.3, 1.0 - abs(self.temperature - 25) / 20)


# ─── Spike Pattern Definitions ────────────────────────────────

SPIKE_PATTERNS = {
    0: "clear",         # path clear, low load
    1: "congested",     # congestion ahead
    2: "damage",        # segment damage detected
    3: "new_path",      # new connection available
    4: "nutrient_high", # high nutrient zone
    5: "nutrient_low",  # nutrient depleted zone
    6: "growth_signal", # tip growth active
    7: "fusion_signal", # anastomosis occurring
}


# ─── Biological Substrate ────────────────────────────────────

class BioSubstrate:
    """Living mycelial network substrate with electrical signaling and growth."""

    def __init__(
        self,
        environment: Environment | None = None,
        # Growth parameters
        base_growth_rate: float = 3.0,     # mm/hr (Physarum/Serpula-like)
        max_diameter: float = 10.0,        # μm
        min_diameter: float = 2.0,         # μm
        branch_prob: float = 0.02,         # per tip per tick
        fusion_prob: float = 0.3,          # on contact
        fusion_distance: float = 0.1,      # mm
        # Electrical parameters
        resting_potential: float = -70.0,   # mV
        threshold_potential: float = -40.0, # mV
        spike_amplitude: float = 80.0,     # mV
        refractory_ticks: int = 3,         # ~30s biological
        # Calcium parameters
        ca_resting: float = 0.05,          # μM
        ca_spike: float = 5.0,             # μM peak during spike
        ca_diffusion: float = 0.02,        # mm²/tick (scaled from 200 μm²/s)
        ca_decay: float = 0.1,             # per tick
        # Diameter adaptation
        diameter_growth_rate: float = 0.01,  # μm/tick when reinforced
        diameter_shrink_rate: float = 0.002, # μm/tick when idle
        # Rhizomorph
        rhizo_flow_threshold: float = 0.5,
        rhizo_ticks_required: int = 50,
    ):
        self.env = environment or Environment()
        self.base_growth_rate = base_growth_rate
        self.max_diameter = max_diameter
        self.min_diameter = min_diameter
        self.branch_prob = branch_prob
        self.fusion_prob = fusion_prob
        self.fusion_distance = fusion_distance
        self.resting_potential = resting_potential
        self.threshold_potential = threshold_potential
        self.spike_amplitude = spike_amplitude
        self.refractory_ticks = refractory_ticks
        self.ca_resting = ca_resting
        self.ca_spike = ca_spike
        self.ca_diffusion = ca_diffusion
        self.ca_decay = ca_decay
        self.diameter_growth_rate = diameter_growth_rate
        self.diameter_shrink_rate = diameter_shrink_rate
        self.rhizo_flow_threshold = rhizo_flow_threshold
        self.rhizo_ticks_required = rhizo_ticks_required

        self.junctions: dict[int, Junction] = {}
        self.segments: dict[int, HyphalSegment] = {}
        self.electrodes: dict[int, Electrode] = {}

        self._next_junction_id = 0
        self._next_segment_id = 0
        self._next_electrode_id = 0
        self.tick_count = 0

        # Pending spikes to propagate
        self._pending_spikes: deque[tuple[int, int, int]] = deque()  # (junction_id, from_segment, arrive_tick)

    # ─── Construction ─────────────────────────────────────────

    def add_junction(self, x: float, y: float,
                     junction_type: str = "branch") -> Junction:
        jid = self._next_junction_id
        self._next_junction_id += 1
        j = Junction(id=jid, x=x, y=y, junction_type=junction_type)
        self.junctions[jid] = j
        return j

    def add_segment(self, ja_id: int, jb_id: int,
                    diameter: float = 5.0) -> HyphalSegment:
        ja, jb = self.junctions[ja_id], self.junctions[jb_id]
        length = math.sqrt((ja.x - jb.x) ** 2 + (ja.y - jb.y) ** 2)
        length = max(length, 0.01)

        sid = self._next_segment_id
        self._next_segment_id += 1
        seg = HyphalSegment(
            id=sid, junction_a=ja_id, junction_b=jb_id,
            length=length, diameter=diameter,
            conductivity=1.0 * self.env.conductivity_factor,
        )
        self.segments[sid] = seg
        ja.segments.append(sid)
        jb.segments.append(sid)
        return seg

    def add_electrode(self, x: float, y: float,
                      electrode_type: str = "bidirectional") -> Electrode:
        eid = self._next_electrode_id
        self._next_electrode_id += 1
        e = Electrode(id=eid, x=x, y=y, electrode_type=electrode_type)

        # Find nearest junction
        min_dist = float("inf")
        for j in self.junctions.values():
            d = math.sqrt((j.x - x) ** 2 + (j.y - y) ** 2)
            if d < min_dist:
                min_dist = d
                e.junction_id = j.id

        # If no junction nearby, create one
        if e.junction_id is None or min_dist > 1.0:
            j = self.add_junction(x, y, junction_type="electrode")
            e.junction_id = j.id

        self.electrodes[eid] = e
        return e

    def seed_network(self, center_x: float, center_y: float,
                     n_tips: int = 8, radius: float = 2.0) -> None:
        """Seed an initial mycelial network — a center junction with radiating tips."""
        center = self.add_junction(center_x, center_y, "branch")

        for i in range(n_tips):
            angle = 2 * math.pi * i / n_tips + random.gauss(0, 0.2)
            tip_x = center_x + radius * math.cos(angle)
            tip_y = center_y + radius * math.sin(angle)
            tip = self.add_junction(tip_x, tip_y, "tip")
            tip.growth_direction = angle
            self.add_segment(center.id, tip.id, diameter=5.0)

    # ─── Electrical Signaling ─────────────────────────────────

    def stimulate(self, electrode_id: int, current_uA: float) -> bool:
        """Inject current at an electrode. Returns True if spike triggered."""
        e = self.electrodes.get(electrode_id)
        if e is None or e.junction_id is None:
            return False

        j = self.junctions.get(e.junction_id)
        if j is None or not j.alive:
            return False

        e.inject_current = current_uA
        e.active = True

        # Current injection raises membrane potential
        # dV = I * R_input, approximate R_input from connected segments
        connected = [self.segments[sid] for sid in j.segments if self.segments[sid].alive]
        if not connected:
            return False

        r_input = 1.0 / sum(1.0 / max(s.resistance, 0.001) for s in connected)
        dv = current_uA * r_input * 0.1  # scaled

        j.potential += dv

        # Check if spike triggered
        if j.potential >= self.threshold_potential and j.last_spike_tick + self.refractory_ticks < self.tick_count:
            self._trigger_spike(j.id)
            return True
        return False

    def _trigger_spike(self, junction_id: int) -> None:
        """Trigger an action potential at a junction."""
        j = self.junctions[junction_id]
        j.potential = self.resting_potential + self.spike_amplitude
        j.calcium = self.ca_spike
        j.last_spike_tick = self.tick_count
        j.spike_count += 1

        # Schedule propagation to neighboring junctions
        for sid in j.segments:
            seg = self.segments[sid]
            if not seg.alive or seg.in_refractory:
                continue

            # Determine the other end
            other_id = seg.junction_b if seg.junction_a == junction_id else seg.junction_a
            arrive_tick = self.tick_count + seg.propagation_time_ticks

            # Signal attenuates based on length vs space constant
            if seg.length > seg.space_constant * 3:
                continue  # too far, signal dies

            self._pending_spikes.append((other_id, sid, arrive_tick))

            # Mark segment as refractory
            seg.in_refractory = True
            seg.refractory_timer = self.refractory_ticks

    def _propagate_spikes(self) -> int:
        """Process arriving spikes. Returns number of spikes propagated."""
        propagated = 0
        still_pending = deque()

        while self._pending_spikes:
            junction_id, from_seg_id, arrive_tick = self._pending_spikes.popleft()

            if arrive_tick > self.tick_count:
                still_pending.append((junction_id, from_seg_id, arrive_tick))
                continue

            j = self.junctions.get(junction_id)
            if j is None or not j.alive:
                continue

            # Arriving signal depolarizes
            seg = self.segments.get(from_seg_id)
            if seg is None:
                continue

            # Attenuation: e^(-length/λ)
            attenuation = math.exp(-seg.length / seg.space_constant)
            dv = self.spike_amplitude * attenuation

            j.potential += dv
            propagated += 1

            # If above threshold and not in refractory, spike propagates
            if (j.potential >= self.threshold_potential and
                    j.last_spike_tick + self.refractory_ticks < self.tick_count):
                self._trigger_spike(junction_id)

        self._pending_spikes = still_pending
        return propagated

    def _update_electrical(self) -> None:
        """Update membrane potentials and refractory states."""
        for j in self.junctions.values():
            if not j.alive:
                continue
            # Membrane potential decays toward resting
            j.potential += 0.1 * (self.resting_potential - j.potential)
            # Calcium decays
            j.calcium += self.ca_decay * (self.ca_resting - j.calcium)
            j.calcium = max(0.0, j.calcium)

        for seg in self.segments.values():
            if seg.in_refractory:
                seg.refractory_timer -= 1
                if seg.refractory_timer <= 0:
                    seg.in_refractory = False
            # Membrane potential decay
            seg.membrane_potential += 0.1 * (self.resting_potential - seg.membrane_potential)

    def _diffuse_calcium(self) -> None:
        """Calcium diffusion between connected junctions."""
        deltas: dict[int, float] = {}

        for seg in self.segments.values():
            if not seg.alive:
                continue
            ja = self.junctions.get(seg.junction_a)
            jb = self.junctions.get(seg.junction_b)
            if ja is None or jb is None:
                continue

            # Fick's law: flux = -D * (dC/dx)
            gradient = (ja.calcium - jb.calcium) / max(seg.length, 0.01)
            flux = self.ca_diffusion * gradient * (seg.diameter / 5.0) ** 2

            deltas[ja.id] = deltas.get(ja.id, 0.0) - flux
            deltas[jb.id] = deltas.get(jb.id, 0.0) + flux

        for jid, delta in deltas.items():
            j = self.junctions.get(jid)
            if j:
                j.calcium = max(0.0, j.calcium + delta)

    # ─── Growth Dynamics ──────────────────────────────────────

    def _grow_tips(self) -> int:
        """Extend hyphal tips. Returns number of new segments created."""
        new_segments = 0
        tips = [j for j in self.junctions.values()
                if j.junction_type == "tip" and j.alive]

        for tip in tips:
            rate = self.base_growth_rate * self.env.growth_factor
            # Convert mm/hr to mm/tick
            growth_per_tick = rate * (TICK_SECONDS / 3600.0)

            if growth_per_tick < 0.001:
                continue

            # Chemotropism: turn toward nearby high-calcium junctions
            best_ca = 0.0
            best_angle = tip.growth_direction
            for other in self.junctions.values():
                if other.id == tip.id or not other.alive:
                    continue
                d = math.sqrt((other.x - tip.x) ** 2 + (other.y - tip.y) ** 2)
                if d > 5.0 or d < 0.01:
                    continue
                if other.calcium > best_ca:
                    best_ca = other.calcium
                    best_angle = math.atan2(other.y - tip.y, other.x - tip.x)

            if best_ca > self.ca_resting * 2:
                # Turn toward calcium source
                angle_diff = best_angle - tip.growth_direction
                angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
                tip.growth_direction += 0.3 * angle_diff

            # Random wandering
            tip.growth_direction += random.gauss(0, 0.1)

            # Extend
            new_x = tip.x + growth_per_tick * math.cos(tip.growth_direction)
            new_y = tip.y + growth_per_tick * math.sin(tip.growth_direction)

            # Create new tip junction and segment
            new_tip = self.add_junction(new_x, new_y, "tip")
            new_tip.growth_direction = tip.growth_direction
            new_tip.growth_rate = tip.growth_rate

            self.add_segment(tip.id, new_tip.id, diameter=self.min_diameter + 1)

            # Old tip becomes a branch point only if it has >1 segment
            if len(tip.segments) > 1:
                tip.junction_type = "branch"
            new_segments += 1

        return new_segments

    def _branch(self) -> int:
        """Stochastic branching from existing junctions. Returns new branches."""
        branches = 0
        for j in list(self.junctions.values()):
            if not j.alive or j.junction_type != "tip":
                continue
            if j.branch_cooldown > 0:
                j.branch_cooldown -= 1
                continue

            p = self.branch_prob * self.env.growth_factor
            # Electrical stimulation increases branching
            if j.calcium > self.ca_resting * 3:
                p *= 2.0

            if random.random() < p:
                # Create a new branch
                angle_offset = random.uniform(math.radians(30), math.radians(70))
                if random.random() < 0.5:
                    angle_offset = -angle_offset
                branch_angle = j.growth_direction + angle_offset

                d = 0.5  # initial branch length
                bx = j.x + d * math.cos(branch_angle)
                by = j.y + d * math.sin(branch_angle)

                new_tip = self.add_junction(bx, by, "tip")
                new_tip.growth_direction = branch_angle
                self.add_segment(j.id, new_tip.id, diameter=self.min_diameter)

                j.junction_type = "branch"
                j.branch_cooldown = 10  # prevent immediate re-branching
                branches += 1

        return branches

    def _anastomosis(self) -> int:
        """Check for hyphal fusions. Returns fusions performed."""
        fusions = 0
        tips = [j for j in self.junctions.values()
                if j.junction_type == "tip" and j.alive]

        for i, tip in enumerate(tips):
            for other in self.junctions.values():
                if other.id == tip.id or not other.alive:
                    continue
                if other.junction_type == "tip":
                    continue  # don't fuse two growing tips

                d = math.sqrt((tip.x - other.x) ** 2 + (tip.y - other.y) ** 2)
                if d > self.fusion_distance:
                    continue

                # Check not already connected
                connected = False
                for sid in tip.segments:
                    seg = self.segments[sid]
                    if seg.junction_a == other.id or seg.junction_b == other.id:
                        connected = True
                        break
                if connected:
                    continue

                if random.random() < self.fusion_prob:
                    # Fuse: create segment between tip and existing junction
                    self.add_segment(tip.id, other.id, diameter=self.min_diameter)
                    tip.junction_type = "anastomosis"
                    fusions += 1
                    break  # one fusion per tip per tick

        return fusions

    # ─── Diameter Adaptation ──────────────────────────────────

    def _adapt_diameters(self) -> None:
        """Segments carrying more flow widen, idle segments shrink."""
        for seg in self.segments.values():
            if not seg.alive:
                continue

            total_flow = seg.nutrient_flow + seg.data_flow

            if total_flow > 0:
                # Widen
                growth = self.diameter_growth_rate * total_flow
                seg.diameter += growth * (self.max_diameter - seg.diameter) / self.max_diameter
                seg.sustained_flow_ticks += 1
            else:
                # Shrink
                seg.diameter -= self.diameter_shrink_rate
                seg.sustained_flow_ticks = max(0, seg.sustained_flow_ticks - 1)

            seg.diameter = max(self.min_diameter, min(self.max_diameter, seg.diameter))

            # Rhizomorph promotion
            if seg.sustained_flow_ticks >= self.rhizo_ticks_required and total_flow >= self.rhizo_flow_threshold:
                seg.is_rhizomorph = True
            elif seg.sustained_flow_ticks < self.rhizo_ticks_required // 2:
                seg.is_rhizomorph = False

            # Segments that shrink below minimum die
            if seg.diameter <= self.min_diameter and seg.age > 100 and total_flow == 0:
                if random.random() < 0.01:
                    seg.alive = False

    # ─── Electrode Recording ──────────────────────────────────

    def _reconnect_electrodes(self) -> None:
        """Re-attach electrodes to nearest alive junction as network grows."""
        for e in self.electrodes.values():
            min_dist = float("inf")
            best_jid = e.junction_id
            for j in self.junctions.values():
                if not j.alive or len(j.segments) == 0:
                    continue
                # Only consider junctions with alive segments
                has_alive = any(self.segments[sid].alive for sid in j.segments)
                if not has_alive:
                    continue
                d = math.sqrt((j.x - e.x) ** 2 + (j.y - e.y) ** 2)
                if d < min_dist:
                    min_dist = d
                    best_jid = j.id
            if best_jid is not None:
                e.junction_id = best_jid

    def _update_electrodes(self) -> None:
        """Update electrode readings from the biological network."""
        for e in self.electrodes.values():
            if e.junction_id is None:
                continue
            j = self.junctions.get(e.junction_id)
            if j is None:
                continue

            e.measured_potential = j.potential
            e.measured_calcium = j.calcium

            # Spike detection
            e.spike_detected = (j.last_spike_tick == self.tick_count)
            if e.spike_detected:
                e.last_spike_tick = self.tick_count
                e.spike_history.append(self.tick_count)
                # Keep last 20 spikes
                if len(e.spike_history) > 20:
                    e.spike_history = e.spike_history[-20:]

            # Pattern classification based on calcium level and spike rate
            e.spike_pattern = self._classify_pattern(e)

    def _classify_pattern(self, electrode: Electrode) -> int:
        """Classify the biological signal into a routing-relevant pattern."""
        j = self.junctions.get(electrode.junction_id)
        if j is None:
            return -1

        # Count recent spikes (last 10 ticks)
        recent = sum(1 for t in electrode.spike_history
                     if t > self.tick_count - 10)

        if recent == 0 and j.calcium < self.ca_resting * 1.5:
            return 0  # clear
        elif recent >= 3:
            return 1  # congested (rapid firing)
        elif j.potential < self.resting_potential - 20:
            return 2  # damage (hyperpolarized)
        elif j.calcium > self.ca_spike * 0.5:
            return 4  # nutrient_high
        elif electrode.spike_detected and recent == 1:
            return 3  # new_path
        return 0

    # ─── Flow Management ──────────────────────────────────────

    def reset_flows(self) -> None:
        for seg in self.segments.values():
            seg.data_flow = 0.0

    def route_signal(self, src_electrode: int, dst_electrode: int) -> Optional[list[int]]:
        """Route a data signal between two electrodes through the biological network.

        Uses a Dijkstra-like search weighted by segment resistance (thinner/longer = worse).
        Returns the path as a list of junction IDs, or None if unreachable.
        """
        src_e = self.electrodes.get(src_electrode)
        dst_e = self.electrodes.get(dst_electrode)
        if src_e is None or dst_e is None:
            return None
        if src_e.junction_id is None or dst_e.junction_id is None:
            return None

        src_j = src_e.junction_id
        dst_j = dst_e.junction_id

        # Dijkstra by resistance (lower = better signal path)
        import heapq
        dist = {src_j: 0.0}
        prev: dict[int, int | None] = {src_j: None}
        heap = [(0.0, src_j)]
        visited = set()

        while heap:
            d, jid = heapq.heappop(heap)
            if jid in visited:
                continue
            visited.add(jid)
            if jid == dst_j:
                break

            j = self.junctions[jid]
            for sid in j.segments:
                seg = self.segments[sid]
                if not seg.alive:
                    continue
                other = seg.junction_b if seg.junction_a == jid else seg.junction_a
                if other in visited:
                    continue
                if not self.junctions[other].alive:
                    continue

                # Weight: resistance (favors thick, short segments)
                # Bonus for rhizomorphs
                weight = seg.resistance
                if seg.is_rhizomorph:
                    weight *= 0.3

                new_dist = d + weight
                if other not in dist or new_dist < dist[other]:
                    dist[other] = new_dist
                    prev[other] = jid
                    heapq.heappush(heap, (new_dist, other))

        if dst_j not in prev:
            return None

        # Reconstruct path
        path = []
        current: int | None = dst_j
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        # Apply data flow to segments along path
        for i in range(len(path) - 1):
            ja, jb = path[i], path[i + 1]
            for sid in self.junctions[ja].segments:
                seg = self.segments[sid]
                if (seg.junction_a == ja and seg.junction_b == jb) or \
                   (seg.junction_a == jb and seg.junction_b == ja):
                    seg.data_flow += 1.0
                    break

        return path

    # ─── Tick ─────────────────────────────────────────────────

    def tick(self) -> dict:
        """Advance one biological time step (~10 seconds)."""
        # Electrical signaling
        spikes_propagated = self._propagate_spikes()
        self._update_electrical()
        self._diffuse_calcium()

        # Growth (slower processes)
        new_segs = 0
        new_branches = 0
        fusions = 0
        new_segs = self._grow_tips()
        new_branches = self._branch()
        fusions = self._anastomosis()

        # Diameter adaptation
        if self.tick_count % 3 == 0:
            self._adapt_diameters()

        # Update conductivity based on environment
        for seg in self.segments.values():
            if seg.alive:
                seg.conductivity = 1.0 * self.env.conductivity_factor
                seg.age += 1

        # Update electrode-junction connections (network may have grown closer)
        self._reconnect_electrodes()

        # Electrode readings
        self._update_electrodes()

        self.tick_count += 1

        # Metrics
        alive_segs = [s for s in self.segments.values() if s.alive]
        alive_juncs = [j for j in self.junctions.values() if j.alive]
        tips = [j for j in alive_juncs if j.junction_type == "tip"]
        rhizomorphs = [s for s in alive_segs if s.is_rhizomorph]

        return {
            "tick": self.tick_count,
            "bio_time_s": self.tick_count * TICK_SECONDS,
            "junctions": len(alive_juncs),
            "segments": len(alive_segs),
            "tips": len(tips),
            "rhizomorphs": len(rhizomorphs),
            "fusions": fusions,
            "new_growth": new_segs + new_branches,
            "spikes_propagated": spikes_propagated,
            "avg_diameter": sum(s.diameter for s in alive_segs) / len(alive_segs) if alive_segs else 0,
            "avg_calcium": sum(j.calcium for j in alive_juncs) / len(alive_juncs) if alive_juncs else 0,
            "total_length_mm": sum(s.length for s in alive_segs),
            "avg_bandwidth": sum(s.bandwidth for s in alive_segs) / len(alive_segs) if alive_segs else 0,
        }

    # ─── Helpers ──────────────────────────────────────────────

    def get_electrode_states(self) -> list[dict]:
        """Get current state of all electrodes for the digital controller."""
        states = []
        for e in self.electrodes.values():
            states.append({
                "id": e.id,
                "potential_mV": e.measured_potential,
                "calcium_uM": e.measured_calcium,
                "spike": e.spike_detected,
                "pattern": e.spike_pattern,
                "pattern_name": SPIKE_PATTERNS.get(e.spike_pattern, "unknown"),
            })
        return states

    def get_network_topology(self) -> dict:
        """Get current network topology for visualization."""
        return {
            "junctions": {
                j.id: {"x": j.x, "y": j.y, "type": j.junction_type,
                        "calcium": j.calcium, "potential": j.potential}
                for j in self.junctions.values() if j.alive
            },
            "segments": {
                s.id: {"a": s.junction_a, "b": s.junction_b,
                        "diameter": s.diameter, "length": s.length,
                        "rhizomorph": s.is_rhizomorph, "bandwidth": s.bandwidth,
                        "flow": s.data_flow}
                for s in self.segments.values() if s.alive
            },
            "electrodes": {
                e.id: {"x": e.x, "y": e.y, "junction": e.junction_id,
                        "pattern": e.spike_pattern}
                for e in self.electrodes.values()
            },
        }
