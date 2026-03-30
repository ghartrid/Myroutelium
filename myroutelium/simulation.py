"""Discrete-event network simulation framework for Myroutelium."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, Callable

from .graph import MycelialGraph
from .routing import MyrouteliumRouter, DijkstraRouter, RouteResult


@dataclass
class Packet:
    """A network packet."""
    id: int
    src: str
    dst: str
    size: float = 1.0   # Mbps of flow
    created_tick: int = 0
    delivered_tick: int = -1
    path: list[str] = field(default_factory=list)
    dropped: bool = False
    router_type: str = ""  # "myroutelium" or "dijkstra"


@dataclass
class TrafficPattern:
    """Defines how traffic is generated."""
    name: str
    src_nodes: list[str]
    dst_nodes: list[str]
    rate: float              # packets per tick
    flow_size: float = 1.0   # Mbps per packet
    burst_prob: float = 0.0  # probability of a burst (10x rate) each tick
    burst_multiplier: float = 10.0


@dataclass
class FailureEvent:
    """Scheduled failure/recovery event."""
    tick: int
    event_type: str   # "kill_node", "revive_node", "kill_link", "revive_link"
    target: str | tuple[str, str]  # node_id or (src, dst)


@dataclass
class SimMetrics:
    """Collected metrics for a single tick."""
    tick: int
    packets_sent: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    avg_latency: float = 0.0
    avg_hops: float = 0.0
    path_diversity: float = 0.0
    avg_nutrient: float = 0.0
    avg_utilization: float = 0.0
    active_links: int = 0
    dormant_links: int = 0
    avg_calcium_boost: float = 0.0  # how much calcium influenced routing


class Simulation:
    """Runs a network simulation comparing Myroutelium vs Dijkstra routing."""

    def __init__(self, graph: MycelialGraph, seed: int | None = None):
        self.graph = graph
        self.myroutelium = MyrouteliumRouter(graph)
        self.dijkstra = DijkstraRouter(graph)

        self.traffic_patterns: list[TrafficPattern] = []
        self.failure_events: list[FailureEvent] = []

        self.myroutelium_metrics: list[SimMetrics] = []
        self.dijkstra_metrics: list[SimMetrics] = []
        self.all_packets: list[Packet] = []
        self._packet_counter = 0

        if seed is not None:
            random.seed(seed)

    def add_traffic(self, pattern: TrafficPattern) -> None:
        self.traffic_patterns.append(pattern)

    def add_failure(self, event: FailureEvent) -> None:
        self.failure_events.append(event)

    def add_uniform_traffic(self, rate: float = 0.5, flow_size: float = 1.0) -> None:
        nodes = list(self.graph.nodes.keys())
        self.add_traffic(TrafficPattern(
            name="uniform", src_nodes=nodes, dst_nodes=nodes,
            rate=rate, flow_size=flow_size,
        ))

    def add_hotspot_traffic(self, hotspot: str, rate: float = 2.0,
                            flow_size: float = 1.0) -> None:
        nodes = [n for n in self.graph.nodes if n != hotspot]
        self.add_traffic(TrafficPattern(
            name=f"hotspot_{hotspot}", src_nodes=nodes, dst_nodes=[hotspot],
            rate=rate, flow_size=flow_size,
        ))

    def add_random_failures(self, link_fail_prob: float = 0.01,
                            recovery_delay: int = 20,
                            start_tick: int = 100, end_tick: int = 400) -> None:
        links = list(self.graph.links.keys())
        for tick in range(start_tick, end_tick, 10):
            for src, dst in links:
                if random.random() < link_fail_prob:
                    self.add_failure(FailureEvent(tick, "kill_link", (src, dst)))
                    self.add_failure(FailureEvent(tick + recovery_delay,
                                                  "revive_link", (src, dst)))

    def _generate_packets(self, tick: int) -> list[Packet]:
        packets = []
        for pattern in self.traffic_patterns:
            rate = pattern.rate
            if pattern.burst_prob > 0 and random.random() < pattern.burst_prob:
                rate *= pattern.burst_multiplier

            n_packets = int(rate)
            if random.random() < (rate - n_packets):
                n_packets += 1

            for _ in range(n_packets):
                src = random.choice(pattern.src_nodes)
                dst = random.choice(pattern.dst_nodes)
                if src == dst:
                    continue
                if not self.graph.nodes[src].alive or not self.graph.nodes[dst].alive:
                    continue

                self._packet_counter += 1
                packets.append(Packet(
                    id=self._packet_counter, src=src, dst=dst,
                    size=pattern.flow_size, created_tick=tick,
                ))

        return packets

    def _apply_failures(self, tick: int) -> None:
        for event in self.failure_events:
            if event.tick != tick:
                continue
            if event.event_type == "kill_node":
                self.graph.kill_node(event.target)
                self.myroutelium.clear_cache()
            elif event.event_type == "revive_node":
                self.graph.revive_node(event.target)
                self.myroutelium.clear_cache()
            elif event.event_type == "kill_link":
                src, dst = event.target
                self.graph.kill_link(src, dst)
                self.myroutelium.clear_cache()
            elif event.event_type == "revive_link":
                src, dst = event.target
                self.graph.revive_link(src, dst)
                self.myroutelium.clear_cache()

    def _route_packets_myroutelium(self, packets: list[Packet]) -> SimMetrics:
        metrics = SimMetrics(tick=self.graph.tick_count)
        delivered_latencies = []
        delivered_hops = []
        calcium_boosts = []
        paths_used = set()

        for pkt in packets:
            metrics.packets_sent += 1
            result = self.myroutelium.route_and_reinforce(pkt.src, pkt.dst, pkt.size)

            if result is None:
                pkt.dropped = True
                metrics.packets_dropped += 1
            else:
                pkt.path = result.path
                pkt.delivered_tick = self.graph.tick_count
                pkt.router_type = "myroutelium"
                metrics.packets_delivered += 1
                delivered_latencies.append(result.latency)
                delivered_hops.append(result.hops)
                calcium_boosts.append(result.calcium_boost)
                paths_used.add(tuple(result.path))

        if delivered_latencies:
            metrics.avg_latency = sum(delivered_latencies) / len(delivered_latencies)
            metrics.avg_hops = sum(delivered_hops) / len(delivered_hops)
        if calcium_boosts:
            metrics.avg_calcium_boost = sum(calcium_boosts) / len(calcium_boosts)
        if metrics.packets_delivered > 0:
            metrics.path_diversity = len(paths_used) / metrics.packets_delivered

        return metrics

    def _route_packets_dijkstra(self, packets: list[Packet]) -> SimMetrics:
        metrics = SimMetrics(tick=self.graph.tick_count)
        delivered_latencies = []
        delivered_hops = []
        paths_used = set()

        for pkt in packets:
            metrics.packets_sent += 1
            result = self.dijkstra.route_with_flow(pkt.src, pkt.dst, pkt.size)

            if result is None:
                pkt.dropped = True
                metrics.packets_dropped += 1
            else:
                pkt.path = result.path
                pkt.delivered_tick = self.graph.tick_count
                pkt.router_type = "dijkstra"
                metrics.packets_delivered += 1
                delivered_latencies.append(result.latency)
                delivered_hops.append(result.hops)
                paths_used.add(tuple(result.path))

        if delivered_latencies:
            metrics.avg_latency = sum(delivered_latencies) / len(delivered_latencies)
            metrics.avg_hops = sum(delivered_hops) / len(delivered_hops)
        if metrics.packets_delivered > 0:
            metrics.path_diversity = len(paths_used) / metrics.packets_delivered

        return metrics

    def _snapshot_graph_metrics(self, metrics: SimMetrics) -> None:
        active = [l for l in self.graph.links.values() if not l.dormant]
        metrics.active_links = len(active)
        metrics.dormant_links = len(self.graph.links) - len(active)
        if active:
            metrics.avg_nutrient = sum(l.nutrient for l in active) / len(active)
            metrics.avg_utilization = sum(l.utilization for l in active) / len(active)

    def run(self, ticks: int = 500, verbose: bool = True) -> dict:
        """Run the full simulation comparing Myroutelium vs Dijkstra."""
        if verbose:
            print(f"Running simulation: {ticks} ticks, "
                  f"{len(self.graph.nodes)} nodes, "
                  f"{len(self.graph.links)} links")

        for t in range(ticks):
            self._apply_failures(t)
            packets = self._generate_packets(t)

            # --- Myroutelium routing ---
            self.graph.reset_flows()
            myc_packets = [Packet(p.id, p.src, p.dst, p.size, p.created_tick)
                           for p in packets]
            myc_metrics = self._route_packets_myroutelium(myc_packets)
            self._snapshot_graph_metrics(myc_metrics)
            self.myroutelium_metrics.append(myc_metrics)

            # --- Dijkstra routing (same packets, fresh state) ---
            self.graph.reset_flows()
            dij_packets = [Packet(p.id, p.src, p.dst, p.size, p.created_tick)
                           for p in packets]
            dij_metrics = self._route_packets_dijkstra(dij_packets)
            self._snapshot_graph_metrics(dij_metrics)
            self.dijkstra_metrics.append(dij_metrics)

            # Advance the graph (decay, prune, calcium propagation)
            self.graph.reset_flows()
            for pkt in myc_packets:
                if pkt.path:
                    for i in range(len(pkt.path) - 1):
                        link = self.graph.links.get((pkt.path[i], pkt.path[i+1]))
                        if link:
                            link.flow += pkt.size
            self.graph.tick()

            if verbose and (t + 1) % 50 == 0:
                m, d = myc_metrics, dij_metrics
                print(f"  Tick {t+1:4d} | "
                      f"Myroutelium: lat={m.avg_latency:.1f}ms div={m.path_diversity:.2f} "
                      f"drop={m.packets_dropped} ca={m.avg_calcium_boost:.2f} | "
                      f"Dijkstra: lat={d.avg_latency:.1f}ms div={d.path_diversity:.2f} "
                      f"drop={d.packets_dropped}")

        return self.summary()

    def summary(self) -> dict:
        def _agg(metrics_list: list[SimMetrics], name: str) -> dict:
            if not metrics_list:
                return {}
            total_sent = sum(m.packets_sent for m in metrics_list)
            total_delivered = sum(m.packets_delivered for m in metrics_list)
            total_dropped = sum(m.packets_dropped for m in metrics_list)
            latencies = [m.avg_latency for m in metrics_list if m.avg_latency > 0]
            diversities = [m.path_diversity for m in metrics_list if m.path_diversity > 0]
            hops = [m.avg_hops for m in metrics_list if m.avg_hops > 0]
            ca_boosts = [m.avg_calcium_boost for m in metrics_list if m.avg_calcium_boost > 0]

            result = {
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_dropped": total_dropped,
                "delivery_rate": total_delivered / total_sent if total_sent else 0,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "avg_path_diversity": sum(diversities) / len(diversities) if diversities else 0,
                "avg_hops": sum(hops) / len(hops) if hops else 0,
            }
            if ca_boosts:
                result["avg_calcium_boost"] = sum(ca_boosts) / len(ca_boosts)
            return result

        return {
            "myroutelium": _agg(self.myroutelium_metrics, "myroutelium"),
            "dijkstra": _agg(self.dijkstra_metrics, "dijkstra"),
        }
