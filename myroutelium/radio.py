"""Radio node model — adaptive mesh radio with variable power, channels, signal propagation,
rhizomorphs, anastomosis, sleep scheduling, tropism, and cooperative relay."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from collections import deque
from typing import Optional


@dataclass
class RadioLink:
    """Physical radio link state to a neighbor."""
    neighbor: str
    tx_power: float = 0.0       # current transmit power (dBm)
    channel_width: float = 1.0  # allocated bandwidth (MHz)
    nutrient: float = 0.3       # mycelial reinforcement score [0, 1]
    snr: float = 0.0            # measured signal-to-noise ratio (dB)
    rssi: float = -100.0        # received signal strength (dBm)
    distance: float = 0.0       # distance to neighbor (meters)
    throughput: float = 0.0     # current data rate (Mbps)
    max_throughput: float = 0.0 # Shannon capacity (Mbps)
    utilization: float = 0.0    # current load / capacity
    flow: float = 0.0           # current traffic (Mbps)
    active: bool = True
    age: int = 0
    _prune_counter: int = 0

    # Rhizomorph state
    is_rhizomorph: bool = False  # whether this link is a trunk cable
    rhizomorph_ticks: int = 0    # how long nutrient has been > threshold
    channel_bond_factor: float = 1.0  # bandwidth multiplier (1.0 = normal, up to 3.0)

    # Tropism state
    directional_gain: float = 0.0  # dB gain from beamforming toward this neighbor

    # Sleep state
    sleeping: bool = False

    @property
    def available(self) -> float:
        return max(self.max_throughput - self.flow, 0.0)

    @property
    def ber(self) -> float:
        if self.snr <= 0:
            return 0.5
        snr_lin = 10 ** (self.snr / 10)
        return 0.5 * math.erfc(math.sqrt(snr_lin))

    @property
    def effective_snr(self) -> float:
        """SNR including directional gain."""
        return self.snr + self.directional_gain

    @property
    def hop_cost(self) -> float:
        """Power cost per hop — used for SNR-weighted hop penalty."""
        esnr = self.effective_snr
        if esnr <= 0:
            return 100.0
        snr_lin = 10 ** (esnr / 10)
        return self.tx_power / snr_lin


@dataclass
class CalciumRadioSignal:
    """Physical-layer calcium control signal."""
    origin: str
    signal_type: str         # "CONG", "DOWN", "UP", "OPT", "PRECONG"
    target_neighbor: str
    strength: float
    hops: int = 0
    data: dict = field(default_factory=dict)


@dataclass
class RadioNode:
    """A Myroutelium adaptive mesh radio node."""
    id: str
    x: float
    y: float
    max_power: float = 20.0
    min_power: float = 0.0
    total_bandwidth: float = 20.0
    noise_floor: float = -90.0
    frequency: float = 2.4
    alive: bool = True

    links: dict[str, RadioLink] = field(default_factory=dict)
    calcium_map: dict[str, CalciumRadioSignal] = field(default_factory=dict)

    # Sleep scheduling
    sleeping: bool = False
    idle_ticks: int = 0  # consecutive ticks with no traffic

    @property
    def total_tx_power(self) -> float:
        return sum(l.tx_power for l in self.links.values() if l.active and not l.sleeping)

    @property
    def n_active_links(self) -> int:
        return sum(1 for l in self.links.values() if l.active and not l.sleeping)

    @property
    def avg_utilization(self) -> float:
        active = [l for l in self.links.values() if l.active and not l.sleeping]
        if not active:
            return 0.0
        return sum(l.utilization for l in active) / len(active)


class RadioMesh:
    """Adaptive mesh radio network with full Myroutelium physical layer optimizations."""

    def __init__(
        self,
        # Radio parameters
        path_loss_exponent: float = 3.0,
        shadow_fading_std: float = 4.0,
        ref_path_loss: float = 40.0,
        snr_min: float = 5.0,
        # Adaptation parameters
        alpha_phy: float = 0.15,
        delta_phy: float = 0.02,
        theta_phy: float = 0.7,
        gamma_phy: float = 0.3,
        n_min_phy: float = 0.05,
        n_prune_phy: float = 0.02,
        t_prune_phy: int = 30,
        n_init: float = 0.6,
        power_budget_frac: float = 0.7,
        channel_smoothing: float = 0.3,
        t_realloc: int = 10,
        min_channel_width: float = 1.0,
        # Calcium control channel
        ca_bandwidth: float = 0.5,
        ca_power: float = 0.0,
        ca_speed: int = 3,
        ca_decay_per_hop: float = 0.15,
        ca_threshold: float = 0.1,
        ca_congestion_boost: float = 0.3,
        ca_optimal_boost: float = 0.4,
        ca_preemptive_threshold: float = 0.6,  # earlier warning threshold
        # Discovery
        t_beacon: int = 50,
        # Rhizomorph parameters
        rhizo_nutrient_threshold: float = 0.7,
        rhizo_ticks_required: int = 30,
        rhizo_channel_bond: float = 2.5,
        rhizo_power_boost: float = 1.3,
        # Anastomosis parameters
        t_anastomosis: int = 40,           # ticks between shortcut probes
        anastomosis_min_hop_savings: int = 2,  # minimum hops saved to create shortcut
        # Sleep scheduling
        t_sleep_threshold: int = 25,  # idle ticks before sleeping
        sleep_beacon_power: float = -5.0,  # minimal beacon power when sleeping (dBm)
        # Tropism / beamforming
        tropism_max_gain: float = 6.0,  # max directional gain (dB)
        tropism_rate: float = 0.1,       # how fast gain builds
        tropism_decay: float = 0.03,     # how fast gain fades
        # Cooperative relay
        relay_skip_snr_threshold: float = 12.0,  # min SNR for direct skip
    ):
        self.nodes: dict[str, RadioNode] = {}
        self.path_loss_exponent = path_loss_exponent
        self.shadow_fading_std = shadow_fading_std
        self.ref_path_loss = ref_path_loss
        self.snr_min = snr_min
        self.alpha_phy = alpha_phy
        self.delta_phy = delta_phy
        self.theta_phy = theta_phy
        self.gamma_phy = gamma_phy
        self.n_min_phy = n_min_phy
        self.n_prune_phy = n_prune_phy
        self.t_prune_phy = t_prune_phy
        self.n_init = n_init
        self.power_budget_frac = power_budget_frac
        self.channel_smoothing = channel_smoothing
        self.t_realloc = t_realloc
        self.min_channel_width = min_channel_width
        self.ca_bandwidth = ca_bandwidth
        self.ca_power = ca_power
        self.ca_speed = ca_speed
        self.ca_decay_per_hop = ca_decay_per_hop
        self.ca_threshold = ca_threshold
        self.ca_congestion_boost = ca_congestion_boost
        self.ca_optimal_boost = ca_optimal_boost
        self.ca_preemptive_threshold = ca_preemptive_threshold
        self.t_beacon = t_beacon
        self.rhizo_nutrient_threshold = rhizo_nutrient_threshold
        self.rhizo_ticks_required = rhizo_ticks_required
        self.rhizo_channel_bond = rhizo_channel_bond
        self.rhizo_power_boost = rhizo_power_boost
        self.t_anastomosis = t_anastomosis
        self.anastomosis_min_hop_savings = anastomosis_min_hop_savings
        self.t_sleep_threshold = t_sleep_threshold
        self.sleep_beacon_power = sleep_beacon_power
        self.tropism_max_gain = tropism_max_gain
        self.tropism_rate = tropism_rate
        self.tropism_decay = tropism_decay
        self.relay_skip_snr_threshold = relay_skip_snr_threshold
        self.tick_count = 0

        self._fading_cache: dict[tuple[str, str], float] = {}
        self._ca_pending: deque[tuple[str, CalciumRadioSignal]] = deque()
        # Track rhizomorph count and sleep count for metrics
        self._rhizomorph_count = 0
        self._sleeping_count = 0
        self._anastomosis_shortcuts = 0

    def add_node(self, node_id: str, x: float, y: float, **kwargs) -> RadioNode:
        node = RadioNode(id=node_id, x=x, y=y, **kwargs)
        self.nodes[node_id] = node
        return node

    def distance(self, n1: str, n2: str) -> float:
        a, b = self.nodes[n1], self.nodes[n2]
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def path_loss(self, n1: str, n2: str) -> float:
        d = self.distance(n1, n2)
        if d < 1.0:
            d = 1.0
        pl = self.ref_path_loss + 10 * self.path_loss_exponent * math.log10(d)
        key = (min(n1, n2), max(n1, n2))
        if key not in self._fading_cache:
            self._fading_cache[key] = random.gauss(0, self.shadow_fading_std)
        pl += self._fading_cache[key]
        return pl

    def compute_snr(self, src: str, dst: str, tx_power: float,
                    directional_gain: float = 0.0) -> float:
        pl = self.path_loss(src, dst)
        rx_power = tx_power + directional_gain - pl
        return rx_power - self.nodes[dst].noise_floor

    def shannon_capacity(self, bandwidth_mhz: float, snr_db: float) -> float:
        if snr_db <= 0:
            return 0.0
        snr_linear = 10 ** (snr_db / 10)
        return bandwidth_mhz * math.log2(1 + snr_linear)

    # ─── Discovery & Anastomosis ──────────────────────────────

    def discover_neighbors(self) -> int:
        new_links = 0
        node_ids = list(self.nodes.keys())
        for i, n1_id in enumerate(node_ids):
            n1 = self.nodes[n1_id]
            if not n1.alive:
                continue
            for n2_id in node_ids[i + 1:]:
                n2 = self.nodes[n2_id]
                if not n2.alive:
                    continue
                snr = self.compute_snr(n1_id, n2_id, n1.max_power)
                if snr < self.snr_min:
                    continue
                d = self.distance(n1_id, n2_id)
                for src, dst in [(n1_id, n2_id), (n2_id, n1_id)]:
                    if dst not in self.nodes[src].links:
                        src_node = self.nodes[src]
                        link = RadioLink(
                            neighbor=dst,
                            tx_power=src_node.min_power + self.n_init * (src_node.max_power - src_node.min_power),
                            channel_width=self.min_channel_width,
                            nutrient=self.n_init,
                            distance=d,
                        )
                        src_node.links[dst] = link
                        new_links += 1
        self._update_all_link_metrics()
        self._reallocate_channels()
        return new_links

    def _anastomosis_probe(self) -> int:
        """Periodic shortcut discovery — check if multi-hop paths can be replaced
        by direct links at boosted power. Returns shortcuts created."""
        shortcuts = 0
        node_ids = [n.id for n in self.nodes.values() if n.alive and not n.sleeping]

        for n1_id in node_ids:
            n1 = self.nodes[n1_id]
            # For each 2-hop neighbor, check if direct link is viable
            for link1 in list(n1.links.values()):
                if not link1.active or link1.sleeping:
                    continue
                mid = link1.neighbor
                mid_node = self.nodes.get(mid)
                if mid_node is None or not mid_node.alive:
                    continue

                for link2 in list(mid_node.links.values()):
                    if not link2.active or link2.sleeping:
                        continue
                    far = link2.neighbor
                    if far == n1_id or far in n1.links:
                        continue

                    # Check if direct link at max power + tropism gain would work
                    snr_direct = self.compute_snr(
                        n1_id, far, n1.max_power,
                        directional_gain=self.tropism_max_gain * 0.5
                    )
                    if snr_direct >= self.snr_min + 3:  # need margin
                        d = self.distance(n1_id, far)
                        # Create new shortcut link
                        for src, dst in [(n1_id, far), (far, n1_id)]:
                            if dst not in self.nodes[src].links:
                                src_node = self.nodes[src]
                                link = RadioLink(
                                    neighbor=dst,
                                    tx_power=src_node.max_power * 0.8,
                                    channel_width=self.min_channel_width,
                                    nutrient=self.n_init * 0.8,
                                    distance=d,
                                )
                                src_node.links[dst] = link
                        shortcuts += 1

        self._anastomosis_shortcuts += shortcuts
        return shortcuts

    def _update_all_link_metrics(self) -> None:
        for node_id, node in self.nodes.items():
            if not node.alive:
                continue
            for neighbor_id, link in node.links.items():
                if not self.nodes[neighbor_id].alive:
                    link.active = False
                    continue
                if link.sleeping:
                    continue

                link.snr = self.compute_snr(
                    node_id, neighbor_id, link.tx_power,
                    directional_gain=link.directional_gain
                )
                link.rssi = link.tx_power + link.directional_gain - self.path_loss(node_id, neighbor_id)
                # Apply rhizomorph channel bonding
                effective_bw = link.channel_width * link.channel_bond_factor
                link.max_throughput = self.shannon_capacity(effective_bw, link.effective_snr)

                if link.snr < self.snr_min:
                    link.active = False
                elif link.nutrient >= self.n_min_phy:
                    link.active = True

    # ─── Rhizomorph Formation ─────────────────────────────────

    def _update_rhizomorphs(self) -> None:
        """Promote high-traffic links to rhizomorphs (trunk cables).

        Rhizomorphs get channel bonding and power boost.
        """
        rhizo_count = 0
        for node in self.nodes.values():
            if not node.alive:
                continue
            for link in node.links.values():
                if not link.active or link.sleeping:
                    continue

                if link.nutrient >= self.rhizo_nutrient_threshold:
                    link.rhizomorph_ticks += 1
                else:
                    link.rhizomorph_ticks = max(0, link.rhizomorph_ticks - 2)

                if link.rhizomorph_ticks >= self.rhizo_ticks_required:
                    if not link.is_rhizomorph:
                        link.is_rhizomorph = True
                    link.channel_bond_factor = self.rhizo_channel_bond
                    rhizo_count += 1
                else:
                    if link.is_rhizomorph and link.rhizomorph_ticks < self.rhizo_ticks_required // 2:
                        link.is_rhizomorph = False
                    link.channel_bond_factor = 1.0

        self._rhizomorph_count = rhizo_count

    # ─── Sleep Scheduling ─────────────────────────────────────

    def _update_sleep(self) -> None:
        """Put idle nodes and links to sleep, wake them on demand."""
        sleeping = 0
        for node in self.nodes.values():
            if not node.alive:
                continue

            # Check if node had any traffic
            had_traffic = any(l.flow > 0 for l in node.links.values())

            if had_traffic:
                node.idle_ticks = 0
                if node.sleeping:
                    node.sleeping = False
                    for link in node.links.values():
                        link.sleeping = False
            else:
                node.idle_ticks += 1

                if node.idle_ticks >= self.t_sleep_threshold:
                    node.sleeping = True
                    sleeping += 1
                    for link in node.links.values():
                        link.sleeping = True
                        link.tx_power = self.sleep_beacon_power

        self._sleeping_count = sleeping

    def wake_node(self, node_id: str) -> None:
        """Wake a sleeping node (called when traffic needs to route through it)."""
        node = self.nodes.get(node_id)
        if node and node.sleeping:
            node.sleeping = False
            node.idle_ticks = 0
            for link in node.links.values():
                link.sleeping = False
                link.tx_power = node.min_power + link.nutrient * (node.max_power - node.min_power)

    # ─── Tropism / Beamforming ────────────────────────────────

    def _update_tropism(self) -> None:
        """Adjust directional gain based on traffic patterns.

        Links with high traffic get antenna gain (beamforming toward neighbor).
        Links with no traffic lose gain.
        """
        for node in self.nodes.values():
            if not node.alive or node.sleeping:
                continue

            # Total gain budget per node (can't focus everywhere)
            total_gain = 0.0
            max_total_gain = self.tropism_max_gain * 2  # can share across 2 directions

            for link in node.links.values():
                if not link.active or link.sleeping:
                    link.directional_gain *= (1.0 - self.tropism_decay)
                    continue

                if link.flow > 0 or link.is_rhizomorph:
                    # Build gain toward active neighbors
                    target_gain = min(
                        self.tropism_max_gain,
                        self.tropism_max_gain * link.nutrient
                    )
                    link.directional_gain += self.tropism_rate * (target_gain - link.directional_gain)
                else:
                    # Decay gain from idle links
                    link.directional_gain *= (1.0 - self.tropism_decay)

                link.directional_gain = max(0.0, min(link.directional_gain, self.tropism_max_gain))
                total_gain += link.directional_gain

            # Enforce gain budget
            if total_gain > max_total_gain and total_gain > 0:
                scale = max_total_gain / total_gain
                for link in node.links.values():
                    link.directional_gain *= scale

    # ─── Cooperative Relay ────────────────────────────────────

    def check_relay_skip(self, path: list[str]) -> list[str]:
        """Check if any intermediate nodes can be skipped.

        If A->B->C exists but A->C has good enough SNR at boosted power,
        skip B and save a hop.
        """
        if len(path) <= 2:
            return path

        optimized = [path[0]]
        i = 0

        while i < len(path) - 1:
            # Try to skip ahead
            best_skip = i + 1  # default: next hop

            for j in range(min(i + 3, len(path) - 1), i + 1, -1):
                # Can we reach path[j] directly from path[i]?
                src = path[i]
                dst = path[j]
                src_node = self.nodes.get(src)
                if src_node is None:
                    break

                # Check if direct link exists or could work at max power
                if dst in src_node.links and src_node.links[dst].active:
                    link = src_node.links[dst]
                    if link.effective_snr >= self.relay_skip_snr_threshold:
                        best_skip = j
                        break
                else:
                    # Check if hop could work with max power + gain
                    snr = self.compute_snr(
                        src, dst, src_node.max_power,
                        directional_gain=self.tropism_max_gain * 0.3
                    )
                    if snr >= self.relay_skip_snr_threshold:
                        best_skip = j
                        break

            optimized.append(path[best_skip])
            i = best_skip

        return optimized

    # ─── Adaptive Power Control ───────────────────────────────

    def _update_power(self) -> None:
        for node in self.nodes.values():
            if not node.alive or node.sleeping:
                continue

            budget = self.power_budget_frac * node.max_power * max(node.n_active_links, 1)

            for link in node.links.values():
                if not link.active or link.sleeping:
                    continue

                target_power = node.min_power + link.nutrient * (node.max_power - node.min_power)

                # Rhizomorph power boost
                if link.is_rhizomorph:
                    target_power *= self.rhizo_power_boost
                    target_power = min(target_power, node.max_power)

                link.tx_power = target_power

            total = sum(l.tx_power for l in node.links.values() if l.active and not l.sleeping)
            if total > budget and total > 0:
                scale = budget / total
                for link in node.links.values():
                    if link.active and not link.sleeping:
                        link.tx_power *= scale
                        link.tx_power = max(link.tx_power, node.min_power)

    # ─── Adaptive Channel Allocation ──────────────────────────

    def _reallocate_channels(self) -> None:
        for node in self.nodes.values():
            if not node.alive or node.sleeping:
                continue

            active_links = [l for l in node.links.values() if l.active and not l.sleeping]
            if not active_links:
                continue

            available_bw = node.total_bandwidth - self.ca_bandwidth
            total_nutrient = sum(l.nutrient for l in active_links)

            if total_nutrient <= 0:
                per_link = max(available_bw / len(active_links), self.min_channel_width)
                for link in active_links:
                    link.channel_width = per_link
            else:
                for link in active_links:
                    target = available_bw * (link.nutrient / total_nutrient)
                    target = max(target, self.min_channel_width)
                    link.channel_width += self.channel_smoothing * (target - link.channel_width)
                    link.channel_width = max(link.channel_width, self.min_channel_width)

    # ─── Nutrient Dynamics ────────────────────────────────────

    def reinforce_link(self, src: str, dst: str) -> None:
        node = self.nodes.get(src)
        if node is None:
            return
        link = node.links.get(dst)
        if link is None:
            return

        snr_max = 40.0
        q = (1.0 - link.ber) * min(link.effective_snr / snr_max, 1.0) * (1.0 - link.utilization)
        q = max(q, 0.0)

        link.nutrient += self.alpha_phy * q * (1.0 - link.nutrient)
        link.nutrient = min(link.nutrient, 1.0)
        link.age = 0
        link._prune_counter = 0

    def reinforce_path(self, path: list[str]) -> None:
        for i in range(len(path) - 1):
            self.reinforce_link(path[i], path[i + 1])

    def _decay_all(self) -> None:
        for node in self.nodes.values():
            for link in node.links.values():
                if not link.active or link.sleeping:
                    continue
                link.nutrient *= (1.0 - self.delta_phy)
                if link.snr > self.snr_min:
                    snr_floor = min(0.15 * link.snr / 20.0, 0.2)
                    link.nutrient = max(link.nutrient, snr_floor)
                link.age += 1

    def _apply_congestion(self) -> None:
        for node in self.nodes.values():
            for link in node.links.values():
                if not link.active or link.sleeping:
                    continue
                if link.utilization > self.theta_phy:
                    penalty = self.gamma_phy * (link.utilization - self.theta_phy) / (1.0 - self.theta_phy)
                    link.nutrient *= (1.0 - penalty)

    def _prune_check(self) -> int:
        pruned = 0
        for node_id, node in self.nodes.items():
            for neighbor_id, link in node.links.items():
                if not link.active:
                    if link.snr >= self.snr_min and self.nodes[neighbor_id].alive:
                        link.active = True
                        link.nutrient = max(link.nutrient, self.n_init * 0.5)
                    continue
                if link.snr < self.snr_min:
                    link.active = False
                    pruned += 1
        return pruned

    # ─── Calcium Control Channel ──────────────────────────────

    def emit_calcium(self, origin: str, signal_type: str,
                     target_neighbor: str, strength: float = 1.0,
                     data: dict | None = None) -> None:
        signal = CalciumRadioSignal(
            origin=origin, signal_type=signal_type,
            target_neighbor=target_neighbor, strength=strength,
            data=data or {},
        )
        self._ca_pending.append((origin, signal))

    def _emit_automatic_calcium(self) -> None:
        for node_id, node in self.nodes.items():
            if not node.alive or node.sleeping:
                continue
            for neighbor_id, link in node.links.items():
                if not link.active or link.sleeping:
                    continue

                # Preemptive congestion warning (earlier than before)
                if link.utilization > self.ca_preemptive_threshold:
                    severity = (link.utilization - self.ca_preemptive_threshold) / (1.0 - self.ca_preemptive_threshold)
                    sig_type = "PRECONG" if link.utilization < self.theta_phy else "CONG"
                    self.emit_calcium(node_id, sig_type, neighbor_id,
                                      strength=min(severity, 1.0),
                                      data={"util": link.utilization})

                # Optimal link signal — also promote rhizomorphs
                if (link.nutrient > 0.7 and link.utilization < 0.3 and link.snr > 15) or link.is_rhizomorph:
                    strength = link.nutrient * (1.0 - link.utilization)
                    if link.is_rhizomorph:
                        strength = min(strength * 1.5, 1.0)
                    self.emit_calcium(node_id, "OPT", neighbor_id,
                                      strength=strength,
                                      data={"snr": link.snr, "nutrient": link.nutrient,
                                            "rhizo": link.is_rhizomorph})

    def propagate_calcium(self) -> int:
        total = 0
        for _ in range(self.ca_speed):
            if not self._ca_pending:
                break

            next_round: deque[tuple[str, CalciumRadioSignal]] = deque()
            seen: set[tuple[str, str, str]] = set()

            while self._ca_pending:
                current_node, signal = self._ca_pending.popleft()
                total += 1

                node = self.nodes.get(current_node)
                if node:
                    existing = node.calcium_map.get(signal.target_neighbor)
                    if existing is None or signal.strength > existing.strength:
                        node.calcium_map[signal.target_neighbor] = signal

                    # Calcium wakes sleeping nodes on CONG/DOWN signals
                    if signal.signal_type in ("CONG", "DOWN") and node.sleeping:
                        self.wake_node(current_node)

                new_strength = signal.strength - self.ca_decay_per_hop
                if new_strength < self.ca_threshold:
                    continue

                if node:
                    for neighbor_id, link in node.links.items():
                        if not self.nodes[neighbor_id].alive:
                            continue
                        if not link.active and not link.sleeping:
                            continue

                        sig_key = (neighbor_id, signal.signal_type, signal.target_neighbor)
                        if sig_key in seen:
                            continue
                        seen.add(sig_key)

                        new_signal = CalciumRadioSignal(
                            origin=signal.origin,
                            signal_type=signal.signal_type,
                            target_neighbor=signal.target_neighbor,
                            strength=new_strength,
                            hops=signal.hops + 1,
                            data=signal.data,
                        )
                        next_round.append((neighbor_id, new_signal))

            self._ca_pending = next_round
        return total

    def _decay_calcium(self) -> None:
        for node in self.nodes.values():
            expired = []
            for key, signal in node.calcium_map.items():
                signal.strength *= 0.7
                if signal.strength < 0.05:
                    expired.append(key)
            for key in expired:
                del node.calcium_map[key]

    def get_calcium_modifier(self, node_id: str, neighbor_id: str) -> float:
        node = self.nodes.get(node_id)
        if node is None:
            return 1.0
        signal = node.calcium_map.get(neighbor_id)
        if signal is None:
            return 1.0

        if signal.signal_type == "CONG":
            return max(0.1, 1.0 - self.ca_congestion_boost * signal.strength)
        elif signal.signal_type == "PRECONG":
            return max(0.3, 1.0 - self.ca_congestion_boost * 0.5 * signal.strength)
        elif signal.signal_type == "DOWN":
            return max(0.01, 1.0 - 0.9 * signal.strength)
        elif signal.signal_type == "UP":
            return 1.0 + 0.2 * signal.strength
        elif signal.signal_type == "OPT":
            boost = self.ca_optimal_boost * signal.strength
            if signal.data.get("rhizo"):
                boost *= 1.5
            return 1.0 + boost
        return 1.0

    # ─── Node Failure / Recovery ──────────────────────────────

    def kill_node(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if node:
            node.alive = False
            for other_id, other_node in self.nodes.items():
                if other_id == node_id or not other_node.alive:
                    continue
                if node_id in other_node.links:
                    other_node.links[node_id].active = False
                    self.emit_calcium(other_id, "DOWN", node_id, strength=1.0)

    def revive_node(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if node:
            node.alive = True
            node.sleeping = False
            node.idle_ticks = 0
            for link in node.links.values():
                link.nutrient = self.n_init
                link.active = True
                link.sleeping = False
                link._prune_counter = 0
            self.emit_calcium(node_id, "UP", node_id, strength=1.0)

    # ─── Flow Management ──────────────────────────────────────

    def reset_flows(self) -> None:
        for node in self.nodes.values():
            for link in node.links.values():
                link.flow = 0.0
                link.utilization = 0.0

    def apply_flow(self, src: str, dst: str, flow_mbps: float) -> bool:
        node = self.nodes.get(src)
        if node is None:
            return False
        link = node.links.get(dst)
        if link is None or not link.active:
            return False

        # Wake sleeping nodes on traffic
        if node.sleeping:
            self.wake_node(src)
        dst_node = self.nodes.get(dst)
        if dst_node and dst_node.sleeping:
            self.wake_node(dst)

        link.flow += flow_mbps
        if link.max_throughput > 0:
            link.utilization = link.flow / link.max_throughput
        return True

    # ─── Tick ─────────────────────────────────────────────────

    def tick(self) -> dict:
        # Nutrient dynamics
        self._decay_all()
        self._apply_congestion()
        pruned = self._prune_check()

        # Biological optimizations
        self._update_rhizomorphs()
        self._update_tropism()
        self._update_sleep()

        # Anastomosis (periodic shortcut discovery)
        anastomosis = 0
        if self.tick_count > 0 and self.tick_count % self.t_anastomosis == 0:
            anastomosis = self._anastomosis_probe()

        # Power and channel adaptation
        self._update_power()
        if self.tick_count % self.t_realloc == 0:
            self._reallocate_channels()

        self._update_all_link_metrics()

        # Calcium signaling
        self._emit_automatic_calcium()
        ca_propagated = self.propagate_calcium()
        self._decay_calcium()

        self.tick_count += 1

        # Metrics
        all_links = []
        for node in self.nodes.values():
            all_links.extend(node.links.values())
        active = [l for l in all_links if l.active and not l.sleeping]
        total_power = sum(n.total_tx_power for n in self.nodes.values() if n.alive)
        max_possible_power = sum(
            n.max_power * max(n.n_active_links, 1)
            for n in self.nodes.values() if n.alive
        )

        return {
            "tick": self.tick_count,
            "active_links": len(active),
            "pruned": pruned,
            "avg_nutrient": sum(l.nutrient for l in active) / len(active) if active else 0,
            "avg_snr": sum(l.snr for l in active) / len(active) if active else 0,
            "avg_throughput": sum(l.max_throughput for l in active) / len(active) if active else 0,
            "total_power_dbm": total_power,
            "power_efficiency": total_power / max_possible_power if max_possible_power else 0,
            "calcium_propagated": ca_propagated,
            "rhizomorphs": self._rhizomorph_count,
            "sleeping_nodes": self._sleeping_count,
            "anastomosis_shortcuts": anastomosis,
            "avg_directional_gain": (sum(l.directional_gain for l in active) /
                                      len(active)) if active else 0,
        }

    # ─── Helpers ──────────────────────────────────────────────

    def get_active_neighbors(self, node_id: str) -> list[RadioLink]:
        node = self.nodes.get(node_id)
        if node is None or not node.alive:
            return []
        return [l for l in node.links.values()
                if l.active and not l.sleeping
                and l.snr >= self.snr_min
                and self.nodes[l.neighbor].alive]

    def get_all_node_ids(self) -> list[str]:
        return [n.id for n in self.nodes.values() if n.alive]
