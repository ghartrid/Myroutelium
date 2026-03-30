"""Physical layer simulation — Myroutelium adaptive mesh vs static mesh."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional

from .radio import RadioMesh
from .radio_routing import MyrouteliumRadioRouter, StaticMeshRouter, RadioRouteResult


@dataclass
class RadioPacket:
    id: int
    src: str
    dst: str
    size_mbps: float = 1.0
    created_tick: int = 0
    delivered: bool = False
    dropped: bool = False
    path: list[str] = field(default_factory=list)
    router_type: str = ""


@dataclass
class RadioTrafficPattern:
    name: str
    src_nodes: list[str]
    dst_nodes: list[str]
    rate: float
    flow_size: float = 1.0
    burst_prob: float = 0.0
    burst_multiplier: float = 10.0


@dataclass
class RadioFailureEvent:
    tick: int
    event_type: str   # "kill_node", "revive_node"
    target: str


@dataclass
class RadioSimMetrics:
    tick: int
    packets_sent: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    avg_latency_ms: float = 0.0
    avg_hops: float = 0.0
    avg_throughput_mbps: float = 0.0
    path_diversity: float = 0.0
    total_power_dbm: float = 0.0
    power_efficiency: float = 0.0  # actual / max possible
    avg_snr: float = 0.0
    avg_nutrient: float = 0.0
    avg_calcium_boost: float = 0.0
    active_links: int = 0


class RadioSimulation:
    """Runs a physical-layer simulation comparing Myroutelium vs Static Mesh."""

    def __init__(self, mesh: RadioMesh, seed: int | None = None):
        self.mesh = mesh
        self.myroutelium = MyrouteliumRadioRouter(mesh)
        self.static_mesh = StaticMeshRouter(mesh)

        self.traffic_patterns: list[RadioTrafficPattern] = []
        self.failure_events: list[RadioFailureEvent] = []

        self.myroutelium_metrics: list[RadioSimMetrics] = []
        self.static_metrics: list[RadioSimMetrics] = []
        self._packet_counter = 0

        if seed is not None:
            random.seed(seed)

    def add_traffic(self, pattern: RadioTrafficPattern) -> None:
        self.traffic_patterns.append(pattern)

    def add_failure(self, event: RadioFailureEvent) -> None:
        self.failure_events.append(event)

    def add_uniform_traffic(self, rate: float = 0.5, flow_size: float = 1.0) -> None:
        nodes = self.mesh.get_all_node_ids()
        self.add_traffic(RadioTrafficPattern(
            name="uniform", src_nodes=nodes, dst_nodes=nodes,
            rate=rate, flow_size=flow_size,
        ))

    def add_hotspot_traffic(self, hotspot: str, rate: float = 2.0,
                            flow_size: float = 1.0) -> None:
        nodes = [n for n in self.mesh.get_all_node_ids() if n != hotspot]
        self.add_traffic(RadioTrafficPattern(
            name=f"hotspot_{hotspot}", src_nodes=nodes, dst_nodes=[hotspot],
            rate=rate, flow_size=flow_size,
        ))

    def add_random_failures(self, fail_prob: float = 0.02,
                            recovery_delay: int = 30,
                            start_tick: int = 50, end_tick: int = 200) -> None:
        nodes = self.mesh.get_all_node_ids()
        for tick in range(start_tick, end_tick, 15):
            for node_id in nodes:
                if random.random() < fail_prob:
                    self.add_failure(RadioFailureEvent(tick, "kill_node", node_id))
                    self.add_failure(RadioFailureEvent(tick + recovery_delay,
                                                       "revive_node", node_id))

    def _generate_packets(self, tick: int) -> list[RadioPacket]:
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
                src_node = self.mesh.nodes.get(src)
                dst_node = self.mesh.nodes.get(dst)
                if not src_node or not dst_node or not src_node.alive or not dst_node.alive:
                    continue

                self._packet_counter += 1
                packets.append(RadioPacket(
                    id=self._packet_counter, src=src, dst=dst,
                    size_mbps=pattern.flow_size, created_tick=tick,
                ))

        return packets

    def _apply_failures(self, tick: int) -> None:
        for event in self.failure_events:
            if event.tick != tick:
                continue
            if event.event_type == "kill_node":
                self.mesh.kill_node(event.target)
            elif event.event_type == "revive_node":
                self.mesh.revive_node(event.target)

    def _route_myroutelium(self, packets: list[RadioPacket]) -> RadioSimMetrics:
        metrics = RadioSimMetrics(tick=self.mesh.tick_count)
        latencies = []
        hops_list = []
        throughputs = []
        ca_boosts = []
        paths_used = set()

        for pkt in packets:
            metrics.packets_sent += 1
            result = self.myroutelium.route_and_reinforce(pkt.src, pkt.dst, pkt.size_mbps)

            if result is None:
                pkt.dropped = True
                metrics.packets_dropped += 1
            else:
                pkt.delivered = True
                pkt.path = result.path
                pkt.router_type = "myroutelium"
                metrics.packets_delivered += 1
                latencies.append(result.latency_ms)
                hops_list.append(result.hops)
                throughputs.append(result.bottleneck_mbps)
                ca_boosts.append(result.calcium_boost)
                paths_used.add(tuple(result.path))

        if latencies:
            metrics.avg_latency_ms = sum(latencies) / len(latencies)
            metrics.avg_hops = sum(hops_list) / len(hops_list)
            metrics.avg_throughput_mbps = sum(throughputs) / len(throughputs)
        if ca_boosts:
            metrics.avg_calcium_boost = sum(ca_boosts) / len(ca_boosts)
        if metrics.packets_delivered > 0:
            metrics.path_diversity = len(paths_used) / metrics.packets_delivered

        return metrics

    def _route_static(self, packets: list[RadioPacket]) -> RadioSimMetrics:
        metrics = RadioSimMetrics(tick=self.mesh.tick_count)
        latencies = []
        hops_list = []
        throughputs = []
        paths_used = set()

        for pkt in packets:
            metrics.packets_sent += 1
            result = self.static_mesh.route_with_flow(pkt.src, pkt.dst, pkt.size_mbps)

            if result is None:
                pkt.dropped = True
                metrics.packets_dropped += 1
            else:
                pkt.delivered = True
                pkt.path = result.path
                pkt.router_type = "static"
                metrics.packets_delivered += 1
                latencies.append(result.latency_ms)
                hops_list.append(result.hops)
                throughputs.append(result.bottleneck_mbps)
                paths_used.add(tuple(result.path))

        if latencies:
            metrics.avg_latency_ms = sum(latencies) / len(latencies)
            metrics.avg_hops = sum(hops_list) / len(hops_list)
            metrics.avg_throughput_mbps = sum(throughputs) / len(throughputs)
        if metrics.packets_delivered > 0:
            metrics.path_diversity = len(paths_used) / metrics.packets_delivered

        return metrics

    def _snapshot_metrics(self, metrics: RadioSimMetrics) -> None:
        all_links = []
        for node in self.mesh.nodes.values():
            all_links.extend(node.links.values())
        active = [l for l in all_links if l.active]

        metrics.active_links = len(active)
        if active:
            metrics.avg_snr = sum(l.snr for l in active) / len(active)
            metrics.avg_nutrient = sum(l.nutrient for l in active) / len(active)

        total_power = sum(n.total_tx_power for n in self.mesh.nodes.values() if n.alive)
        max_power = sum(
            n.max_power * max(n.n_active_links, 1)
            for n in self.mesh.nodes.values() if n.alive
        )
        metrics.total_power_dbm = total_power
        metrics.power_efficiency = total_power / max_power if max_power else 0

    def run(self, ticks: int = 300, verbose: bool = True) -> dict:
        if verbose:
            print(f"Running radio simulation: {ticks} ticks, "
                  f"{len(self.mesh.nodes)} nodes")

        for t in range(ticks):
            self._apply_failures(t)
            packets = self._generate_packets(t)

            # --- Myroutelium routing ---
            self.mesh.reset_flows()
            myc_packets = [RadioPacket(p.id, p.src, p.dst, p.size_mbps, p.created_tick)
                           for p in packets]
            myc_metrics = self._route_myroutelium(myc_packets)
            self._snapshot_metrics(myc_metrics)
            self.myroutelium_metrics.append(myc_metrics)

            # --- Static mesh routing ---
            self.mesh.reset_flows()
            stat_packets = [RadioPacket(p.id, p.src, p.dst, p.size_mbps, p.created_tick)
                            for p in packets]
            stat_metrics = self._route_static(stat_packets)
            self._snapshot_metrics(stat_metrics)
            self.static_metrics.append(stat_metrics)

            # Advance mesh (apply myroutelium flows for adaptation)
            self.mesh.reset_flows()
            for pkt in myc_packets:
                if pkt.path:
                    for i in range(len(pkt.path) - 1):
                        self.mesh.apply_flow(pkt.path[i], pkt.path[i + 1], pkt.size_mbps)
            self.mesh.tick()

            if verbose and (t + 1) % 50 == 0:
                m, s = myc_metrics, stat_metrics
                print(f"  Tick {t+1:4d} | "
                      f"Myroutelium: lat={m.avg_latency_ms:.2f}ms hops={m.avg_hops:.1f} "
                      f"drop={m.packets_dropped} pwr={m.power_efficiency:.2f} "
                      f"ca={m.avg_calcium_boost:.2f} | "
                      f"Static: lat={s.avg_latency_ms:.2f}ms hops={s.avg_hops:.1f} "
                      f"drop={s.packets_dropped}")

        return self.summary()

    def summary(self) -> dict:
        def _agg(metrics_list: list[RadioSimMetrics]) -> dict:
            if not metrics_list:
                return {}
            total_sent = sum(m.packets_sent for m in metrics_list)
            total_delivered = sum(m.packets_delivered for m in metrics_list)
            total_dropped = sum(m.packets_dropped for m in metrics_list)
            lats = [m.avg_latency_ms for m in metrics_list if m.avg_latency_ms > 0]
            divs = [m.path_diversity for m in metrics_list if m.path_diversity > 0]
            hops = [m.avg_hops for m in metrics_list if m.avg_hops > 0]
            thrps = [m.avg_throughput_mbps for m in metrics_list if m.avg_throughput_mbps > 0]
            pwrs = [m.power_efficiency for m in metrics_list if m.power_efficiency > 0]
            cas = [m.avg_calcium_boost for m in metrics_list if m.avg_calcium_boost > 0]

            return {
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_dropped": total_dropped,
                "delivery_rate": total_delivered / total_sent if total_sent else 0,
                "avg_latency_ms": sum(lats) / len(lats) if lats else 0,
                "avg_path_diversity": sum(divs) / len(divs) if divs else 0,
                "avg_hops": sum(hops) / len(hops) if hops else 0,
                "avg_throughput_mbps": sum(thrps) / len(thrps) if thrps else 0,
                "avg_power_efficiency": sum(pwrs) / len(pwrs) if pwrs else 0,
                "avg_calcium_boost": sum(cas) / len(cas) if cas else 0,
            }

        return {
            "myroutelium": _agg(self.myroutelium_metrics),
            "static_mesh": _agg(self.static_metrics),
        }
