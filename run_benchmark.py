#!/usr/bin/env python3
"""Myroutelium benchmark suite — compares fungal+calcium routing against Dijkstra
across multiple topologies, traffic patterns, and failure scenarios."""

import json
import os
import sys
import time

from myroutelium.graph import MycelialGraph
from myroutelium.routing import MyrouteliumRouter, DijkstraRouter
from myroutelium.simulation import Simulation, TrafficPattern, FailureEvent
from myroutelium.topologies import (
    grid_topology, ring_topology, fat_tree_topology,
    random_topology, internet_like_topology,
)

try:
    from myroutelium.visualize import plot_network, plot_comparison, plot_nutrient_heatmap
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


# ─── Benchmark 1: Topology comparison ────────────────────────

def bench_topologies():
    """Run Myroutelium vs Dijkstra across different network topologies."""
    banner("Benchmark 1: Topology Comparison")

    topologies = {
        "4x4 Grid": grid_topology(4, 4),
        "6x6 Grid": grid_topology(6, 6),
        "Ring (12 nodes)": ring_topology(12),
        "Random (20 nodes)": random_topology(20, edge_prob=0.2, seed=42),
        "Internet-like (35 nodes)": internet_like_topology(5, 10, 20),
    }

    results = {}
    for name, graph in topologies.items():
        print(f"\n--- {name} ---")
        sim = Simulation(graph, seed=42)
        sim.add_uniform_traffic(rate=1.0, flow_size=1.0)
        summary = sim.run(ticks=300, verbose=True)
        results[name] = summary

        if HAS_VIZ:
            safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")
            plot_network(graph, title=f"{name} — Final Nutrient State",
                         save_path=os.path.join(OUTPUT_DIR, f"topo_{safe_name}.png"))

    return results


# ─── Benchmark 2: Traffic patterns ───────────────────────────

def bench_traffic():
    """Test different traffic patterns on a grid topology."""
    banner("Benchmark 2: Traffic Pattern Comparison")

    patterns = {
        "Uniform": lambda sim: sim.add_uniform_traffic(rate=1.0),
        "Hotspot (center)": lambda sim: sim.add_hotspot_traffic("n2_2", rate=3.0),
        "Bursty": lambda sim: sim.add_traffic(TrafficPattern(
            name="bursty", src_nodes=list(sim.graph.nodes.keys()),
            dst_nodes=list(sim.graph.nodes.keys()),
            rate=0.5, burst_prob=0.1, burst_multiplier=15.0,
        )),
        "Heavy load": lambda sim: sim.add_uniform_traffic(rate=5.0, flow_size=5.0),
    }

    results = {}
    for name, setup_fn in patterns.items():
        print(f"\n--- {name} ---")
        graph = grid_topology(5, 5)
        sim = Simulation(graph, seed=42)
        setup_fn(sim)
        summary = sim.run(ticks=300, verbose=True)
        results[name] = summary

        if HAS_VIZ:
            safe_name = name.replace(" ", "_").replace("(", "").replace(")", "")
            plot_comparison(sim.myroutelium_metrics, sim.dijkstra_metrics,
                            title=f"Traffic: {name}",
                            save_path=os.path.join(OUTPUT_DIR, f"traffic_{safe_name}.png"))

    return results


# ─── Benchmark 3: Failure resilience ─────────────────────────

def bench_failures():
    """Test routing resilience under link/node failures."""
    banner("Benchmark 3: Failure Resilience")

    scenarios = {}

    # Scenario: Random link failures
    print("\n--- Random link failures ---")
    graph = grid_topology(5, 5)
    sim = Simulation(graph, seed=42)
    sim.add_uniform_traffic(rate=1.0)
    sim.add_random_failures(link_fail_prob=0.03, recovery_delay=30,
                            start_tick=50, end_tick=250)
    summary = sim.run(ticks=300, verbose=True)
    scenarios["Random link failures"] = summary

    if HAS_VIZ:
        plot_comparison(sim.myroutelium_metrics, sim.dijkstra_metrics,
                        title="Failure: Random Link Failures",
                        save_path=os.path.join(OUTPUT_DIR, "failure_random_links.png"))

    # Scenario: Critical node failure
    print("\n--- Critical node failure ---")
    graph = grid_topology(5, 5)
    sim = Simulation(graph, seed=42)
    sim.add_uniform_traffic(rate=1.0)
    sim.add_failure(FailureEvent(100, "kill_node", "n2_2"))
    sim.add_failure(FailureEvent(200, "revive_node", "n2_2"))
    summary = sim.run(ticks=300, verbose=True)
    scenarios["Critical node failure"] = summary

    if HAS_VIZ:
        plot_comparison(sim.myroutelium_metrics, sim.dijkstra_metrics,
                        title="Failure: Critical Node Down (tick 100-200)",
                        save_path=os.path.join(OUTPUT_DIR, "failure_critical_node.png"))

    # Scenario: Cascading failures
    print("\n--- Cascading failures ---")
    graph = grid_topology(5, 5)
    sim = Simulation(graph, seed=42)
    sim.add_uniform_traffic(rate=1.5)
    for i, node in enumerate(["n1_1", "n1_3", "n3_1", "n3_3"]):
        sim.add_failure(FailureEvent(80 + i * 20, "kill_node", node))
        sim.add_failure(FailureEvent(250 + i * 10, "revive_node", node))
    summary = sim.run(ticks=350, verbose=True)
    scenarios["Cascading failures"] = summary

    if HAS_VIZ:
        plot_comparison(sim.myroutelium_metrics, sim.dijkstra_metrics,
                        title="Failure: Cascading Node Failures",
                        save_path=os.path.join(OUTPUT_DIR, "failure_cascading.png"))

    return scenarios


# ─── Benchmark 4: Scalability ────────────────────────────────

def bench_scalability():
    """Test how routing performance scales with network size."""
    banner("Benchmark 4: Scalability")

    sizes = [
        ("3x3 (9 nodes)", 3, 3),
        ("5x5 (25 nodes)", 5, 5),
        ("7x7 (49 nodes)", 7, 7),
        ("10x10 (100 nodes)", 10, 10),
    ]

    results = {}
    for name, rows, cols in sizes:
        print(f"\n--- {name} ---")
        graph = grid_topology(rows, cols)
        sim = Simulation(graph, seed=42)
        sim.add_uniform_traffic(rate=0.5)

        t0 = time.time()
        summary = sim.run(ticks=200, verbose=True)
        elapsed = time.time() - t0

        summary["wall_time_sec"] = round(elapsed, 2)
        results[name] = summary
        print(f"  Wall time: {elapsed:.2f}s")

    return results


# ─── Benchmark 5: Parameter sensitivity ──────────────────────

def bench_parameters():
    """Test sensitivity to key algorithm parameters."""
    banner("Benchmark 5: Parameter Sensitivity")

    param_sets = {
        "Default (α=0.1, δ=0.01, τ=0.5)": {"alpha": 0.1, "delta": 0.01, "temp": 0.5, "ca_w": 0.5},
        "Fast learning (α=0.3)": {"alpha": 0.3, "delta": 0.01, "temp": 0.5, "ca_w": 0.5},
        "Fast decay (δ=0.05)": {"alpha": 0.1, "delta": 0.05, "temp": 0.5, "ca_w": 0.5},
        "High exploration (τ=2.0)": {"alpha": 0.1, "delta": 0.01, "temp": 2.0, "ca_w": 0.5},
        "Low exploration (τ=0.1)": {"alpha": 0.1, "delta": 0.01, "temp": 0.1, "ca_w": 0.5},
        "Heavy calcium (ca=0.8)": {"alpha": 0.1, "delta": 0.01, "temp": 0.5, "ca_w": 0.8},
        "No calcium (ca=0.0)": {"alpha": 0.1, "delta": 0.01, "temp": 0.5, "ca_w": 0.0},
        "Aggressive (α=0.3, δ=0.05, τ=0.1)": {"alpha": 0.3, "delta": 0.05, "temp": 0.1, "ca_w": 0.5},
    }

    results = {}
    for name, params in param_sets.items():
        print(f"\n--- {name} ---")
        graph = grid_topology(5, 5, capacity=100.0, latency=5.0)
        graph.alpha = params["alpha"]
        graph.delta = params["delta"]

        sim = Simulation(graph, seed=42)
        sim.myroutelium.temperature = params["temp"]
        sim.myroutelium.calcium_weight = params["ca_w"]
        sim.add_uniform_traffic(rate=1.0)
        sim.add_random_failures(link_fail_prob=0.02, start_tick=80, end_tick=200)

        summary = sim.run(ticks=300, verbose=True)
        results[name] = summary

    return results


# ─── Main ─────────────────────────────────────────────────────

def print_summary_table(all_results: dict):
    """Print a formatted summary comparison table."""
    banner("SUMMARY")

    print(f"{'Benchmark':<35} {'Router':<14} {'Delivery%':>10} {'Avg Lat':>10} "
          f"{'Path Div':>10} {'Avg Hops':>10} {'Ca2+':>8}")
    print("-" * 100)

    for bench_name, scenarios in all_results.items():
        for scenario_name, data in scenarios.items():
            for router in ["myroutelium", "dijkstra"]:
                if router not in data:
                    continue
                r = data[router]
                ca = r.get('avg_calcium_boost', 0)
                ca_str = f"{ca:.3f}" if ca else "   -"
                print(f"{scenario_name[:35]:<35} {router:<14} "
                      f"{r.get('delivery_rate', 0)*100:>9.1f}% "
                      f"{r.get('avg_latency', 0):>9.1f}ms "
                      f"{r.get('avg_path_diversity', 0):>10.3f} "
                      f"{r.get('avg_hops', 0):>10.2f} "
                      f"{ca_str:>8}")
            print()


def main():
    ensure_output_dir()

    all_results = {}

    all_results["Topologies"] = bench_topologies()
    all_results["Traffic"] = bench_traffic()
    all_results["Failures"] = bench_failures()
    all_results["Scalability"] = bench_scalability()
    all_results["Parameters"] = bench_parameters()

    print_summary_table(all_results)

    # Save raw results
    results_path = os.path.join(OUTPUT_DIR, "benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRaw results saved to: {results_path}")

    if HAS_VIZ:
        print(f"Charts saved to: {OUTPUT_DIR}/")
    else:
        print("\nNote: Install matplotlib for charts: pip install matplotlib")

    print("\nDone.")


if __name__ == "__main__":
    main()
