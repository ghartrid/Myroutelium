"""Core mycelial network graph — nodes, links (hyphae), nutrient dynamics, and calcium signaling."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


@dataclass
class Link:
    """A network link (hypha) between two nodes."""
    src: str
    dst: str
    capacity: float          # max bandwidth (Mbps)
    latency: float           # base propagation delay (ms)
    flow: float = 0.0        # current traffic load (Mbps)
    nutrient: float = 0.3    # mycelial reinforcement score [0, 1]
    age: int = 0             # ticks since last successful packet
    dormant: bool = False    # pruned from routing
    _prune_counter: int = 0  # consecutive ticks below prune threshold

    @property
    def utilization(self) -> float:
        if self.capacity <= 0:
            return 1.0
        return min(self.flow / self.capacity, 1.0)

    @property
    def available(self) -> float:
        return max(self.capacity - self.flow, 0.0)

    def quality(self, l_ref: float) -> float:
        """Quality signal Q(u,v) — combines available capacity and latency."""
        cap_factor = 1.0 - self.utilization
        lat_factor = 1.0 / (1.0 + self.latency / max(l_ref, 0.001))
        return cap_factor * lat_factor


@dataclass
class CalciumSignal:
    """A fast-propagating calcium signal (Ca2+ wave).

    Calcium signals form the fast control plane — they propagate ahead of
    nutrient transport to give the router instant awareness of network state
    changes (congestion, failures, recoveries, good paths).
    """
    origin: str              # node that originated the signal
    signal_type: str         # "congestion", "failure", "recovery", "optimal"
    target_link: tuple[str, str] | None  # specific link this is about
    strength: float          # signal intensity [0, 1], decays with hops
    hops: int = 0            # how many hops this has traveled
    data: dict = field(default_factory=dict)  # extra info (utilization, latency, etc.)


@dataclass
class Node:
    """A network node (router)."""
    id: str
    x: float = 0.0   # position for visualization
    y: float = 0.0
    alive: bool = True


class MycelialGraph:
    """Network graph with fungal nutrient dynamics and calcium signaling on links."""

    def __init__(
        self,
        alpha: float = 0.1,    # reinforcement rate
        delta: float = 0.01,   # decay rate
        theta: float = 0.8,    # congestion threshold
        gamma: float = 0.3,    # congestion penalty
        n_min: float = 0.05,   # dead hypha threshold
        n_prune: float = 0.02, # prune threshold
        t_prune: int = 50,     # ticks before dormancy
        n_init: float = 0.3,   # initial nutrient score
        # Calcium signaling parameters
        ca_propagation_speed: int = 3,   # hops per tick (vs 1 for nutrients)
        ca_decay_per_hop: float = 0.15,  # signal strength lost per hop
        ca_threshold: float = 0.1,       # minimum strength to keep propagating
        ca_congestion_boost: float = 0.3, # how much congestion signals penalize paths
        ca_optimal_boost: float = 0.4,   # how much optimal signals boost paths
    ):
        self.nodes: dict[str, Node] = {}
        self.links: dict[tuple[str, str], Link] = {}  # (src, dst) -> Link
        self.alpha = alpha
        self.delta = delta
        self.theta = theta
        self.gamma = gamma
        self.n_min = n_min
        self.n_prune = n_prune
        self.t_prune = t_prune
        self.n_init = n_init
        self.tick_count = 0

        # Calcium signaling state
        self.ca_propagation_speed = ca_propagation_speed
        self.ca_decay_per_hop = ca_decay_per_hop
        self.ca_threshold = ca_threshold
        self.ca_congestion_boost = ca_congestion_boost
        self.ca_optimal_boost = ca_optimal_boost

        # Per-node calcium awareness map: node_id -> {link_key -> CalciumSignal}
        # This is the "fast memory" — what each node knows from calcium waves
        self.calcium_map: dict[str, dict[tuple[str, str], CalciumSignal]] = {}

        # Pending calcium signals to propagate
        self._ca_pending: deque[CalciumSignal] = deque()

    def add_node(self, node_id: str, x: float = 0.0, y: float = 0.0) -> Node:
        node = Node(id=node_id, x=x, y=y)
        self.nodes[node_id] = node
        self.calcium_map[node_id] = {}
        return node

    def add_link(self, src: str, dst: str, capacity: float = 100.0,
                 latency: float = 5.0, bidirectional: bool = True) -> list[Link]:
        """Add a link (hypha). Bidirectional by default."""
        links = []
        for s, d in [(src, dst)] + ([(dst, src)] if bidirectional else []):
            link = Link(src=s, dst=d, capacity=capacity, latency=latency,
                        nutrient=self.n_init)
            self.links[(s, d)] = link
            links.append(link)
        return links

    def get_neighbors(self, node_id: str, include_dormant: bool = False) -> list[Link]:
        """Get all outgoing links from a node."""
        result = []
        for (src, dst), link in self.links.items():
            if src == node_id and self.nodes[dst].alive:
                if include_dormant or not link.dormant:
                    result.append(link)
        return result

    def get_active_neighbors(self, node_id: str) -> list[Link]:
        """Get outgoing links above the dead threshold."""
        return [l for l in self.get_neighbors(node_id)
                if l.nutrient >= self.n_min]

    @property
    def median_latency(self) -> float:
        latencies = [l.latency for l in self.links.values() if not l.dormant]
        if not latencies:
            return 1.0
        latencies.sort()
        mid = len(latencies) // 2
        return latencies[mid]

    # ─── Calcium Signaling System ─────────────────────────────

    def emit_calcium(self, origin: str, signal_type: str,
                     target_link: tuple[str, str] | None = None,
                     strength: float = 1.0, data: dict | None = None) -> None:
        """Emit a calcium signal from a node. Propagates rapidly through the network."""
        signal = CalciumSignal(
            origin=origin,
            signal_type=signal_type,
            target_link=target_link,
            strength=strength,
            hops=0,
            data=data or {},
        )
        self._ca_pending.append(signal)

    def propagate_calcium(self) -> int:
        """Propagate all pending calcium signals up to ca_propagation_speed hops.

        Returns number of signals propagated.
        """
        total_propagated = 0

        for _ in range(self.ca_propagation_speed):
            if not self._ca_pending:
                break

            next_round: deque[CalciumSignal] = deque()
            seen_this_round: set[tuple[str, str, str]] = set()

            while self._ca_pending:
                signal = self._ca_pending.popleft()
                total_propagated += 1

                # Update calcium map at origin node
                if signal.origin in self.calcium_map:
                    link_key = signal.target_link
                    if link_key:
                        self.calcium_map[signal.origin][link_key] = signal

                # Propagate to neighbors
                new_strength = signal.strength - self.ca_decay_per_hop
                if new_strength < self.ca_threshold:
                    continue

                for link in self.get_neighbors(signal.origin, include_dormant=True):
                    neighbor = link.dst
                    if not self.nodes[neighbor].alive:
                        continue

                    sig_key = (neighbor, signal.signal_type,
                               str(signal.target_link))
                    if sig_key in seen_this_round:
                        continue
                    seen_this_round.add(sig_key)

                    new_signal = CalciumSignal(
                        origin=neighbor,
                        signal_type=signal.signal_type,
                        target_link=signal.target_link,
                        strength=new_strength,
                        hops=signal.hops + 1,
                        data=signal.data,
                    )

                    # Update neighbor's calcium map
                    if neighbor in self.calcium_map and signal.target_link:
                        existing = self.calcium_map[neighbor].get(signal.target_link)
                        if existing is None or new_signal.strength > existing.strength:
                            self.calcium_map[neighbor][signal.target_link] = new_signal

                    next_round.append(new_signal)

            self._ca_pending = next_round

        return total_propagated

    def get_calcium_score(self, node_id: str, link_key: tuple[str, str]) -> float:
        """Get the calcium-adjusted score modifier for a link from a node's perspective.

        Returns a multiplier: >1 means calcium signals say this link is good,
        <1 means signals indicate congestion/failure.
        """
        ca_map = self.calcium_map.get(node_id, {})
        signal = ca_map.get(link_key)
        if signal is None:
            return 1.0  # no calcium info — neutral

        if signal.signal_type == "congestion":
            return max(0.1, 1.0 - self.ca_congestion_boost * signal.strength)
        elif signal.signal_type == "failure":
            return max(0.01, 1.0 - 0.9 * signal.strength)
        elif signal.signal_type == "recovery":
            return 1.0 + 0.2 * signal.strength
        elif signal.signal_type == "optimal":
            return 1.0 + self.ca_optimal_boost * signal.strength
        return 1.0

    def _emit_automatic_signals(self) -> None:
        """Automatically emit calcium signals based on current network state.

        This is the "sensory" layer — the network feels its own state
        and converts it to fast calcium signals.
        """
        for (src, dst), link in self.links.items():
            if link.dormant:
                continue

            # Congestion signal — link utilization above threshold
            if link.utilization > self.theta:
                severity = (link.utilization - self.theta) / (1.0 - self.theta)
                self.emit_calcium(
                    origin=src,
                    signal_type="congestion",
                    target_link=(src, dst),
                    strength=min(severity, 1.0),
                    data={"utilization": link.utilization},
                )

            # Optimal path signal — high nutrient, low utilization
            if link.nutrient > 0.7 and link.utilization < 0.3:
                self.emit_calcium(
                    origin=src,
                    signal_type="optimal",
                    target_link=(src, dst),
                    strength=link.nutrient * (1.0 - link.utilization),
                    data={"nutrient": link.nutrient, "utilization": link.utilization},
                )

    def decay_calcium(self) -> None:
        """Decay calcium map entries — signals fade over time."""
        for node_id in self.calcium_map:
            expired = []
            for link_key, signal in self.calcium_map[node_id].items():
                signal.strength *= 0.7  # calcium decays faster than nutrients
                if signal.strength < 0.05:
                    expired.append(link_key)
            for key in expired:
                del self.calcium_map[node_id][key]

    # ─── Nutrient Dynamics ────────────────────────────────────

    def reinforce(self, src: str, dst: str) -> None:
        """Reinforce a link after successful packet traversal."""
        link = self.links.get((src, dst))
        if link is None:
            return
        q = link.quality(self.median_latency)
        link.nutrient += self.alpha * q * (1.0 - link.nutrient)
        link.nutrient = min(link.nutrient, 1.0)
        link.age = 0
        link._prune_counter = 0
        if link.dormant:
            link.dormant = False

    def reinforce_path(self, path: list[str]) -> None:
        """Reinforce all links along a path."""
        for i in range(len(path) - 1):
            self.reinforce(path[i], path[i + 1])

    def decay_all(self) -> None:
        """Apply decay to all nutrient scores (called each tick)."""
        for link in self.links.values():
            if link.dormant:
                continue
            link.nutrient *= (1.0 - self.delta)
            link.age += 1

    def apply_congestion_penalties(self) -> None:
        """Penalize congested links."""
        for link in self.links.values():
            if link.dormant:
                continue
            u = link.utilization
            if u > self.theta:
                penalty = self.gamma * (u - self.theta) / (1.0 - self.theta)
                link.nutrient *= (1.0 - penalty)

    def prune_check(self) -> list[Link]:
        """Check for links that should become dormant. Returns newly pruned links."""
        pruned = []
        for link in self.links.values():
            if link.dormant:
                continue
            if link.nutrient < self.n_prune:
                link._prune_counter += 1
                if link._prune_counter >= self.t_prune:
                    link.dormant = True
                    pruned.append(link)
            else:
                link._prune_counter = 0
        return pruned

    def tick(self) -> dict:
        """Advance one simulation tick. Returns tick metrics."""
        # Nutrient dynamics (slow data plane)
        self.decay_all()
        self.apply_congestion_penalties()
        pruned = self.prune_check()

        # Calcium signaling (fast control plane)
        self._emit_automatic_signals()
        ca_propagated = self.propagate_calcium()
        self.decay_calcium()

        self.tick_count += 1

        active_links = [l for l in self.links.values() if not l.dormant]
        total_ca_entries = sum(len(m) for m in self.calcium_map.values())

        return {
            "tick": self.tick_count,
            "active_links": len(active_links),
            "dormant_links": len(self.links) - len(active_links),
            "newly_pruned": len(pruned),
            "avg_nutrient": (sum(l.nutrient for l in active_links) /
                            len(active_links)) if active_links else 0,
            "avg_utilization": (sum(l.utilization for l in active_links) /
                                len(active_links)) if active_links else 0,
            "calcium_signals_propagated": ca_propagated,
            "calcium_map_entries": total_ca_entries,
        }

    def kill_node(self, node_id: str) -> None:
        """Simulate node failure."""
        if node_id in self.nodes:
            self.nodes[node_id].alive = False
            # Emit failure calcium signals for all affected links
            for (src, dst), link in self.links.items():
                if src == node_id or dst == node_id:
                    alive_end = dst if src == node_id else src
                    if self.nodes[alive_end].alive:
                        self.emit_calcium(
                            origin=alive_end,
                            signal_type="failure",
                            target_link=(src, dst),
                            strength=1.0,
                        )

    def revive_node(self, node_id: str) -> None:
        """Bring a node back online."""
        if node_id in self.nodes:
            self.nodes[node_id].alive = True
            for (src, dst), link in self.links.items():
                if src == node_id or dst == node_id:
                    link.nutrient = self.n_init
                    link.dormant = False
                    link._prune_counter = 0
            # Emit recovery calcium signals
            self.emit_calcium(
                origin=node_id,
                signal_type="recovery",
                target_link=None,
                strength=1.0,
            )

    def kill_link(self, src: str, dst: str) -> None:
        """Simulate link failure."""
        link = self.links.get((src, dst))
        if link:
            link.nutrient = 0.0
            link.dormant = True
            # Emit failure signal
            if self.nodes[src].alive:
                self.emit_calcium(
                    origin=src,
                    signal_type="failure",
                    target_link=(src, dst),
                    strength=1.0,
                )

    def revive_link(self, src: str, dst: str) -> None:
        """Bring a link back online."""
        link = self.links.get((src, dst))
        if link:
            link.nutrient = self.n_init
            link.dormant = False
            link._prune_counter = 0
            # Emit recovery signal
            if self.nodes[src].alive:
                self.emit_calcium(
                    origin=src,
                    signal_type="recovery",
                    target_link=(src, dst),
                    strength=0.8,
                )

    def reset_flows(self) -> None:
        """Reset all link flows to zero (call at start of each tick before routing)."""
        for link in self.links.values():
            link.flow = 0.0
