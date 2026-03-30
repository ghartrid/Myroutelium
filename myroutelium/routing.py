"""Routing algorithms — Myroutelium (fungal + calcium) and traditional (Dijkstra)."""

from __future__ import annotations
import heapq
import math
import random
from dataclasses import dataclass
from typing import Optional

from .graph import MycelialGraph, Link


@dataclass
class RouteResult:
    """Result of a routing decision."""
    path: list[str]
    score: float
    latency: float      # total path latency (ms)
    bottleneck: float    # minimum available bandwidth on path
    hops: int
    calcium_boost: float = 0.0  # how much calcium signals influenced this choice


class MyrouteliumRouter:
    """Fungal-inspired router with calcium signaling (fast control plane).

    Two-tier routing:
    - Nutrient scores (slow, learned) — data plane awareness
    - Calcium signals (fast, propagated) — control plane awareness

    Calcium signals let the router know about congestion, failures, and
    optimal paths BEFORE nutrient scores have time to adapt, dramatically
    reducing the latency gap vs shortest-path algorithms.
    """

    def __init__(
        self,
        graph: MycelialGraph,
        temperature: float = 0.5,
        max_path_multiplier: float = 2.0,
        max_paths: int = 10,
        calcium_weight: float = 0.5,  # how much calcium influences vs nutrients
        shortest_path_bias: float = 0.3,  # bonus for shorter paths
    ):
        self.graph = graph
        self.temperature = temperature
        self.max_path_multiplier = max_path_multiplier
        self.max_paths = max_paths
        self.calcium_weight = calcium_weight
        self.shortest_path_bias = shortest_path_bias
        self._shortest_cache: dict[tuple[str, str], int] = {}

    def find_paths(self, src: str, dst: str) -> list[list[str]]:
        """Find multiple paths from src to dst using bounded DFS."""
        shortest = self._bfs_shortest(src, dst)
        if shortest is None:
            return []

        max_hops = int(shortest * self.max_path_multiplier)
        paths: list[list[str]] = []
        self._dfs(src, dst, [src], set([src]), max_hops, paths)
        return paths

    def _bfs_shortest(self, src: str, dst: str) -> Optional[int]:
        """BFS to find shortest path length."""
        cache_key = (src, dst)
        if cache_key in self._shortest_cache:
            return self._shortest_cache[cache_key]

        if src == dst:
            return 0
        visited = {src}
        queue = [(src, 0)]
        while queue:
            node, depth = queue.pop(0)
            for link in self.graph.get_active_neighbors(node):
                if link.dst == dst:
                    self._shortest_cache[cache_key] = depth + 1
                    return depth + 1
                if link.dst not in visited:
                    visited.add(link.dst)
                    queue.append((link.dst, depth + 1))
        return None

    def _dfs(self, current: str, dst: str, path: list[str],
             visited: set[str], max_hops: int, paths: list[list[str]]) -> None:
        """Bounded DFS to enumerate paths."""
        if len(paths) >= self.max_paths:
            return
        if current == dst:
            paths.append(list(path))
            return
        if len(path) - 1 >= max_hops:
            return

        for link in self.graph.get_active_neighbors(current):
            if link.dst not in visited:
                visited.add(link.dst)
                path.append(link.dst)
                self._dfs(link.dst, dst, path, visited, max_hops, paths)
                path.pop()
                visited.remove(link.dst)

    def score_path(self, path: list[str], src_node: str) -> tuple[float, float]:
        """Score a path using combined nutrient + calcium scoring.

        Returns (total_score, calcium_contribution).

        The two-tier scoring:
        1. Nutrient score (slow): ∏ N(e) × bottleneck / worst_latency
        2. Calcium score (fast): product of calcium modifiers from src's awareness
        3. Length penalty: shorter paths get a bonus

        Final = (1-w) × nutrient_score + w × calcium_adjusted_score
        """
        if len(path) < 2:
            return 0.0, 0.0

        nutrient_product = 1.0
        calcium_product = 1.0
        min_available = float("inf")
        max_latency = 0.0

        for i in range(len(path) - 1):
            link_key = (path[i], path[i + 1])
            link = self.graph.links.get(link_key)
            if link is None or link.dormant:
                return 0.0, 0.0

            nutrient_product *= link.nutrient
            min_available = min(min_available, link.available)
            max_latency = max(max_latency, link.latency)

            # Calcium signal modifier from source node's awareness
            ca_mod = self.graph.get_calcium_score(src_node, link_key)
            calcium_product *= ca_mod

        if max_latency <= 0:
            max_latency = 0.001
        if min_available <= 0:
            min_available = 0.001

        # Base nutrient score
        base_score = nutrient_product * min_available / max_latency

        # Calcium-adjusted score
        ca_score = base_score * calcium_product

        # Length penalty — prefer shorter paths
        shortest = self._bfs_shortest(path[0], path[-1])
        if shortest and shortest > 0:
            length_ratio = shortest / len(path)  # 1.0 for shortest, <1 for longer
            length_bonus = 1.0 + self.shortest_path_bias * (length_ratio - 0.5)
        else:
            length_bonus = 1.0

        # Blend nutrient and calcium scores
        w = self.calcium_weight
        final_score = ((1.0 - w) * base_score + w * ca_score) * length_bonus

        calcium_contribution = abs(ca_score - base_score) / max(base_score, 0.001)
        return final_score, calcium_contribution

    def path_latency(self, path: list[str]) -> float:
        """Total latency along a path."""
        total = 0.0
        for i in range(len(path) - 1):
            link = self.graph.links.get((path[i], path[i + 1]))
            if link:
                total += link.latency
        return total

    def path_bottleneck(self, path: list[str]) -> float:
        """Minimum available bandwidth along a path."""
        minimum = float("inf")
        for i in range(len(path) - 1):
            link = self.graph.links.get((path[i], path[i + 1]))
            if link:
                minimum = min(minimum, link.available)
        return minimum if minimum != float("inf") else 0.0

    def select_path(self, src: str, dst: str) -> Optional[RouteResult]:
        """Select a path using calcium-enhanced probabilistic multi-path selection."""
        paths = self.find_paths(src, dst)
        if not paths:
            return None

        scored = [(p, *self.score_path(p, src)) for p in paths]

        # Filter out zero-score paths
        valid = [(p, s, ca) for p, s, ca in scored if s > 0]
        if not valid:
            return None

        paths_v = [v[0] for v in valid]
        scores = [v[1] for v in valid]
        ca_boosts = [v[2] for v in valid]

        # Softmax with temperature
        probs = self._softmax(scores, self.temperature)

        # Sample from distribution
        idx = random.choices(range(len(paths_v)), weights=probs, k=1)[0]
        chosen = paths_v[idx]

        return RouteResult(
            path=chosen,
            score=scores[idx],
            latency=self.path_latency(chosen),
            bottleneck=self.path_bottleneck(chosen),
            hops=len(chosen) - 1,
            calcium_boost=ca_boosts[idx],
        )

    def route_and_reinforce(self, src: str, dst: str,
                            flow: float = 1.0) -> Optional[RouteResult]:
        """Route a packet/flow and reinforce the chosen path."""
        result = self.select_path(src, dst)
        if result is None:
            return None

        # Apply flow to links
        for i in range(len(result.path) - 1):
            link = self.graph.links.get((result.path[i], result.path[i + 1]))
            if link:
                link.flow += flow

        # Reinforce the path
        self.graph.reinforce_path(result.path)

        # Emit optimal calcium signal for successful high-quality paths
        if result.score > 0.5 and result.hops <= 3:
            for i in range(len(result.path) - 1):
                self.graph.emit_calcium(
                    origin=result.path[i],
                    signal_type="optimal",
                    target_link=(result.path[i], result.path[i + 1]),
                    strength=min(result.score, 1.0) * 0.5,
                )

        return result

    def clear_cache(self) -> None:
        """Clear shortest path cache (call after topology changes)."""
        self._shortest_cache.clear()

    @staticmethod
    def _softmax(scores: list[float], temperature: float) -> list[float]:
        """Compute softmax probabilities with temperature."""
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


class DijkstraRouter:
    """Traditional shortest-path router for comparison."""

    def __init__(self, graph: MycelialGraph, metric: str = "latency"):
        self.graph = graph
        self.metric = metric

    def find_path(self, src: str, dst: str) -> Optional[RouteResult]:
        """Find shortest path using Dijkstra's algorithm."""
        if src not in self.graph.nodes or dst not in self.graph.nodes:
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

            for link in self.graph.get_neighbors(node, include_dormant=False):
                if not self.graph.nodes[link.dst].alive:
                    continue
                if link.dst in visited:
                    continue

                weight = link.latency if self.metric == "latency" else 1.0
                new_dist = d + weight

                if link.dst not in dist or new_dist < dist[link.dst]:
                    dist[link.dst] = new_dist
                    prev[link.dst] = node
                    heapq.heappush(heap, (new_dist, link.dst))

        if dst not in prev:
            return None

        path = []
        current: Optional[str] = dst
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        total_latency = 0.0
        bottleneck = float("inf")
        for i in range(len(path) - 1):
            link = self.graph.links.get((path[i], path[i + 1]))
            if link:
                total_latency += link.latency
                bottleneck = min(bottleneck, link.available)

        return RouteResult(
            path=path,
            score=1.0 / total_latency if total_latency > 0 else 0.0,
            latency=total_latency,
            bottleneck=bottleneck if bottleneck != float("inf") else 0.0,
            hops=len(path) - 1,
        )

    def route_with_flow(self, src: str, dst: str,
                        flow: float = 1.0) -> Optional[RouteResult]:
        """Route and apply flow to links."""
        result = self.find_path(src, dst)
        if result is None:
            return None

        for i in range(len(result.path) - 1):
            link = self.graph.links.get((result.path[i], result.path[i + 1]))
            if link:
                link.flow += flow

        return result
