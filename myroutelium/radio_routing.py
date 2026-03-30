"""Radio-layer routing — Myroutelium adaptive mesh with all optimizations and static mesh."""

from __future__ import annotations
import heapq
import math
import random
from dataclasses import dataclass
from typing import Optional

from .radio import RadioMesh, RadioLink


@dataclass
class RadioRouteResult:
    """Result of a radio routing decision."""
    path: list[str]
    score: float
    latency_ms: float
    bottleneck_mbps: float
    hops: int
    total_power: float
    calcium_boost: float = 0.0
    hops_saved: int = 0  # hops saved by cooperative relay


class MyrouteliumRadioRouter:
    """Myroutelium router with all physical layer optimizations.

    Scoring incorporates:
    - SNR-weighted hop penalty (each hop costs power/SNR)
    - Calcium signals (congestion/optimal/preemptive awareness)
    - Rhizomorph bonus (trunk links score higher)
    - Tropism gain (beamformed links have better SNR)
    - Cooperative relay skip (reduces hops post-selection)
    """

    def __init__(
        self,
        mesh: RadioMesh,
        temperature: float = 0.5,
        max_path_multiplier: float = 2.0,
        max_paths: int = 8,
        calcium_weight: float = 0.5,
        hop_penalty_weight: float = 0.4,  # how much hop cost matters
        rhizomorph_bonus: float = 2.0,    # score multiplier for rhizomorph paths
    ):
        self.mesh = mesh
        self.temperature = temperature
        self.max_path_multiplier = max_path_multiplier
        self.max_paths = max_paths
        self.calcium_weight = calcium_weight
        self.hop_penalty_weight = hop_penalty_weight
        self.rhizomorph_bonus = rhizomorph_bonus

    def _bfs_shortest(self, src: str, dst: str) -> Optional[int]:
        if src == dst:
            return 0
        visited = {src}
        queue = [(src, 0)]
        while queue:
            node, depth = queue.pop(0)
            for link in self.mesh.get_active_neighbors(node):
                if link.neighbor == dst:
                    return depth + 1
                if link.neighbor not in visited:
                    visited.add(link.neighbor)
                    queue.append((link.neighbor, depth + 1))
        return None

    def find_paths(self, src: str, dst: str) -> list[list[str]]:
        shortest = self._bfs_shortest(src, dst)
        if shortest is None:
            return []
        max_hops = int(shortest * self.max_path_multiplier)
        paths: list[list[str]] = []
        self._dfs(src, dst, [src], {src}, max_hops, paths)
        return paths

    def _dfs(self, current: str, dst: str, path: list[str],
             visited: set[str], max_hops: int, paths: list[list[str]]) -> None:
        if len(paths) >= self.max_paths:
            return
        if current == dst:
            paths.append(list(path))
            return
        if len(path) - 1 >= max_hops:
            return

        # Sort neighbors by SNR descending for better path discovery
        neighbors = self.mesh.get_active_neighbors(current)
        neighbors.sort(key=lambda l: l.effective_snr, reverse=True)

        for link in neighbors:
            if link.neighbor not in visited:
                visited.add(link.neighbor)
                path.append(link.neighbor)
                self._dfs(link.neighbor, dst, path, visited, max_hops, paths)
                path.pop()
                visited.remove(link.neighbor)

    def score_path(self, path: list[str], src: str) -> tuple[float, float]:
        """Score using SNR-weighted hop cost + nutrient + calcium + rhizomorph bonus.

        The key change: instead of just nutrient_product * throughput / latency,
        we penalize paths by their total hop cost (power/SNR per hop).
        """
        if len(path) < 2:
            return 0.0, 0.0

        nutrient_product = 1.0
        calcium_product = 1.0
        min_throughput = float("inf")
        total_latency = 0.0
        total_hop_cost = 0.0
        total_power = 0.0
        has_rhizomorph = False

        for i in range(len(path) - 1):
            node = self.mesh.nodes.get(path[i])
            if node is None:
                return 0.0, 0.0
            link = node.links.get(path[i + 1])
            if link is None or not link.active or link.sleeping:
                return 0.0, 0.0

            nutrient_product *= link.nutrient
            min_throughput = min(min_throughput, link.available)
            total_latency += link.distance / 300.0 + 0.1
            total_power += link.tx_power

            # SNR-weighted hop cost
            total_hop_cost += link.hop_cost

            # Rhizomorph detection
            if link.is_rhizomorph:
                has_rhizomorph = True

            # Calcium modifier
            ca_mod = self.mesh.get_calcium_modifier(src, path[i + 1])
            calcium_product *= ca_mod

        if min_throughput <= 0:
            min_throughput = 0.001
        if total_latency <= 0:
            total_latency = 0.001
        if total_hop_cost <= 0:
            total_hop_cost = 0.001

        # Base score: nutrient * throughput / (latency * hop_cost_penalty)
        hop_penalty = 1.0 / (1.0 + self.hop_penalty_weight * total_hop_cost)
        base_score = nutrient_product * min_throughput / total_latency * hop_penalty

        # Calcium-adjusted score
        ca_score = base_score * calcium_product

        # Rhizomorph bonus
        rhizo_multiplier = self.rhizomorph_bonus if has_rhizomorph else 1.0

        # Shortest path bias
        shortest = self._bfs_shortest(path[0], path[-1])
        if shortest and shortest > 0:
            length_ratio = shortest / (len(path) - 1)
            length_bonus = 1.0 + 0.4 * (length_ratio - 0.5)  # stronger bias
        else:
            length_bonus = 1.0

        w = self.calcium_weight
        final = ((1.0 - w) * base_score + w * ca_score) * length_bonus * rhizo_multiplier
        ca_contribution = abs(ca_score - base_score) / max(base_score, 0.001)

        return final, ca_contribution

    def _path_metrics(self, path: list[str]) -> tuple[float, float, float]:
        latency = 0.0
        bottleneck = float("inf")
        power = 0.0
        for i in range(len(path) - 1):
            node = self.mesh.nodes.get(path[i])
            if node is None:
                return 0.0, 0.0, 0.0
            link = node.links.get(path[i + 1])
            if link is None:
                return 0.0, 0.0, 0.0
            latency += link.distance / 300.0 + 0.1
            bottleneck = min(bottleneck, link.available)
            power += link.tx_power
        return latency, bottleneck if bottleneck != float("inf") else 0.0, power

    def select_path(self, src: str, dst: str) -> Optional[RadioRouteResult]:
        # Wake sleeping nodes along potential paths
        self.mesh.wake_node(src)
        self.mesh.wake_node(dst)

        paths = self.find_paths(src, dst)
        if not paths:
            return None

        scored = [(p, *self.score_path(p, src)) for p in paths]
        valid = [(p, s, ca) for p, s, ca in scored if s > 0]
        if not valid:
            return None

        paths_v = [v[0] for v in valid]
        scores = [v[1] for v in valid]
        ca_boosts = [v[2] for v in valid]

        probs = _softmax(scores, self.temperature)
        idx = random.choices(range(len(paths_v)), weights=probs, k=1)[0]
        chosen = paths_v[idx]

        # Cooperative relay: try to skip intermediate hops
        original_hops = len(chosen) - 1
        optimized = self.mesh.check_relay_skip(chosen)
        hops_saved = original_hops - (len(optimized) - 1)
        chosen = optimized

        lat, bw, pwr = self._path_metrics(chosen)
        return RadioRouteResult(
            path=chosen, score=scores[idx], latency_ms=lat,
            bottleneck_mbps=bw, hops=len(chosen) - 1,
            total_power=pwr, calcium_boost=ca_boosts[idx],
            hops_saved=hops_saved,
        )

    def route_and_reinforce(self, src: str, dst: str,
                            flow_mbps: float = 1.0) -> Optional[RadioRouteResult]:
        result = self.select_path(src, dst)
        if result is None:
            return None

        for i in range(len(result.path) - 1):
            self.mesh.apply_flow(result.path[i], result.path[i + 1], flow_mbps)

        self.mesh.reinforce_path(result.path)

        # Emit optimal signals for good paths
        if result.score > 0.3 and result.hops <= 4:
            for i in range(len(result.path) - 1):
                self.mesh.emit_calcium(
                    result.path[i], "OPT", result.path[i + 1],
                    strength=min(result.score, 1.0) * 0.5,
                )

        return result


class StaticMeshRouter:
    """Static mesh router (802.11s-like) for comparison."""

    def __init__(self, mesh: RadioMesh):
        self.mesh = mesh

    def find_path(self, src: str, dst: str) -> Optional[RadioRouteResult]:
        if src not in self.mesh.nodes or dst not in self.mesh.nodes:
            return None

        dist = {src: 0.0}
        prev: dict[str, Optional[str]] = {src: None}
        heap = [(0.0, src)]
        visited = set()

        while heap:
            d, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)
            if node == dst:
                break

            node_obj = self.mesh.nodes[node]
            for neighbor_id, link in node_obj.links.items():
                if not self.mesh.nodes[neighbor_id].alive:
                    continue
                if neighbor_id in visited:
                    continue
                if link.snr < self.mesh.snr_min:
                    continue

                weight = link.distance / 300.0 + 0.1
                new_dist = d + weight

                if neighbor_id not in dist or new_dist < dist[neighbor_id]:
                    dist[neighbor_id] = new_dist
                    prev[neighbor_id] = node
                    heapq.heappush(heap, (new_dist, neighbor_id))

        if dst not in prev:
            return None

        path = []
        current: Optional[str] = dst
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        latency = 0.0
        bottleneck = float("inf")
        total_power = 0.0
        for i in range(len(path) - 1):
            node_obj = self.mesh.nodes[path[i]]
            link = node_obj.links.get(path[i + 1])
            if link:
                latency += link.distance / 300.0 + 0.1
                bottleneck = min(bottleneck, link.max_throughput - link.flow)
                total_power += node_obj.max_power

        return RadioRouteResult(
            path=path, score=1.0 / latency if latency > 0 else 0.0,
            latency_ms=latency,
            bottleneck_mbps=max(bottleneck, 0.0) if bottleneck != float("inf") else 0.0,
            hops=len(path) - 1, total_power=total_power,
        )

    def route_with_flow(self, src: str, dst: str,
                        flow_mbps: float = 1.0) -> Optional[RadioRouteResult]:
        result = self.find_path(src, dst)
        if result is None:
            return None
        for i in range(len(result.path) - 1):
            self.mesh.apply_flow(result.path[i], result.path[i + 1], flow_mbps)
        return result


def _softmax(scores: list[float], temperature: float) -> list[float]:
    if not scores:
        return []
    if temperature <= 0:
        max_idx = scores.index(max(scores))
        return [1.0 if i == max_idx else 0.0 for i in range(len(scores))]
    max_s = max(scores)
    exps = [math.exp((s - max_s) / temperature) for s in scores]
    total = sum(exps)
    if total == 0:
        return [1.0 / len(scores)] * len(scores)
    return [e / total for e in exps]
