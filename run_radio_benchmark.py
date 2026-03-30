#!/usr/bin/env python3
"""Myroutelium Physical Layer benchmark — adaptive mesh radio vs static mesh."""

import json
import os
import time

from myroutelium.radio import RadioMesh
from myroutelium.radio_simulation import RadioSimulation, RadioTrafficPattern, RadioFailureEvent
from myroutelium.radio_topologies import (
    random_field, grid_field, cluster_field, line_field,
    disaster_field, iot_field,
)

try:
    from myroutelium.radio_visualize import plot_radio_mesh, plot_radio_comparison
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results", "radio")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


# ─── Benchmark 1: Topology comparison ────────────────────────

def bench_radio_topologies():
    banner("Radio Bench 1: Topology Comparison")

    topologies = {
        "Grid 5x5 (25 nodes)": grid_field(5, 5, spacing=50.0),
        "Random (20 nodes)": random_field(20, area=300.0, seed=42),
        "Clustered (4x5=20 nodes)": cluster_field(4, 5, cluster_radius=40.0, field_size=300.0, seed=42),
        "Line (8 nodes)": line_field(8, spacing=60.0),
        "Disaster (20 nodes)": disaster_field(20, area=400.0, seed=42),
    }

    results = {}
    for name, mesh in topologies.items():
        print(f"\n--- {name} ---")
        print(f"    Nodes: {len(mesh.nodes)}, "
              f"Links: {sum(len(n.links) for n in mesh.nodes.values())}")
        sim = RadioSimulation(mesh, seed=42)
        sim.add_uniform_traffic(rate=1.0, flow_size=1.0)
        summary = sim.run(ticks=250, verbose=True)
        results[name] = summary

        if HAS_VIZ:
            safe = name.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "")
            plot_radio_mesh(mesh, title=f"{name} — Final State",
                            save_path=os.path.join(OUTPUT_DIR, f"radio_topo_{safe}.png"))

    return results


# ─── Benchmark 2: Traffic patterns ───────────────────────────

def bench_radio_traffic():
    banner("Radio Bench 2: Traffic Patterns")

    patterns = {
        "Uniform": lambda sim: sim.add_uniform_traffic(rate=1.0),
        "Hotspot": lambda sim: sim.add_hotspot_traffic(
            list(sim.mesh.nodes.keys())[len(sim.mesh.nodes) // 2], rate=3.0),
        "Bursty": lambda sim: sim.add_traffic(RadioTrafficPattern(
            name="bursty", src_nodes=sim.mesh.get_all_node_ids(),
            dst_nodes=sim.mesh.get_all_node_ids(),
            rate=0.5, burst_prob=0.1, burst_multiplier=12.0,
        )),
        "Heavy load": lambda sim: sim.add_uniform_traffic(rate=4.0, flow_size=3.0),
    }

    results = {}
    for name, setup_fn in patterns.items():
        print(f"\n--- {name} ---")
        mesh = grid_field(5, 5, spacing=50.0)
        sim = RadioSimulation(mesh, seed=42)
        setup_fn(sim)
        summary = sim.run(ticks=250, verbose=True)
        results[name] = summary

        if HAS_VIZ:
            safe = name.replace(" ", "_")
            plot_radio_comparison(sim.myroutelium_metrics, sim.static_metrics,
                                  title=f"Radio Traffic: {name}",
                                  save_path=os.path.join(OUTPUT_DIR, f"radio_traffic_{safe}.png"))

    return results


# ─── Benchmark 3: Failure resilience ─────────────────────────

def bench_radio_failures():
    banner("Radio Bench 3: Failure Resilience")

    scenarios = {}

    # Random node failures
    print("\n--- Random node failures ---")
    mesh = grid_field(5, 5, spacing=50.0)
    sim = RadioSimulation(mesh, seed=42)
    sim.add_uniform_traffic(rate=1.0)
    sim.add_random_failures(fail_prob=0.04, recovery_delay=25,
                            start_tick=40, end_tick=180)
    summary = sim.run(ticks=250, verbose=True)
    scenarios["Random node failures"] = summary

    if HAS_VIZ:
        plot_radio_comparison(sim.myroutelium_metrics, sim.static_metrics,
                              title="Radio: Random Node Failures",
                              save_path=os.path.join(OUTPUT_DIR, "radio_failure_random.png"))

    # Critical gateway failure
    print("\n--- Critical gateway failure ---")
    mesh = grid_field(5, 5, spacing=50.0)
    sim = RadioSimulation(mesh, seed=42)
    sim.add_uniform_traffic(rate=1.0)
    sim.add_failure(RadioFailureEvent(80, "kill_node", "r2_2"))
    sim.add_failure(RadioFailureEvent(180, "revive_node", "r2_2"))
    summary = sim.run(ticks=250, verbose=True)
    scenarios["Critical gateway failure"] = summary

    if HAS_VIZ:
        plot_radio_comparison(sim.myroutelium_metrics, sim.static_metrics,
                              title="Radio: Central Node Down (tick 80-180)",
                              save_path=os.path.join(OUTPUT_DIR, "radio_failure_gateway.png"))

    return scenarios


# ─── Benchmark 4: Power efficiency ───────────────────────────

def bench_radio_power():
    banner("Radio Bench 4: Power Efficiency")

    scenarios = {
        "Low traffic": 0.3,
        "Medium traffic": 1.0,
        "High traffic": 3.0,
        "Very high traffic": 6.0,
    }

    results = {}
    for name, rate in scenarios.items():
        print(f"\n--- {name} (rate={rate}) ---")
        mesh = grid_field(5, 5, spacing=50.0)
        sim = RadioSimulation(mesh, seed=42)
        sim.add_uniform_traffic(rate=rate, flow_size=1.0)
        summary = sim.run(ticks=200, verbose=True)
        results[name] = summary

    return results


# ─── Benchmark 5: IoT scenario ───────────────────────────────

def bench_radio_iot():
    banner("Radio Bench 5: IoT Scenario")

    print("\n--- 3 gateways + 25 sensors ---")
    mesh = iot_field(n_gateways=3, n_sensors=25, area=250.0, seed=42)
    sim = RadioSimulation(mesh, seed=42)

    # Sensors report to random gateway
    gateways = [n for n in mesh.get_all_node_ids() if n.startswith("gw")]
    sensors = [n for n in mesh.get_all_node_ids() if n.startswith("s")]
    sim.add_traffic(RadioTrafficPattern(
        name="sensor_report", src_nodes=sensors, dst_nodes=gateways,
        rate=2.0, flow_size=0.5,
    ))
    # Add some sensor failures
    sim.add_random_failures(fail_prob=0.03, recovery_delay=40,
                            start_tick=30, end_tick=150)

    summary = sim.run(ticks=200, verbose=True)

    if HAS_VIZ:
        plot_radio_mesh(mesh, title="IoT Mesh — Final State",
                        save_path=os.path.join(OUTPUT_DIR, "radio_iot_mesh.png"))
        plot_radio_comparison(sim.myroutelium_metrics, sim.static_metrics,
                              title="IoT: 3 Gateways + 25 Sensors",
                              save_path=os.path.join(OUTPUT_DIR, "radio_iot_comparison.png"))

    return {"IoT (3gw + 25 sensors)": summary}


# ─── Main ─────────────────────────────────────────────────────

def print_summary_table(all_results: dict):
    banner("RADIO LAYER SUMMARY")

    print(f"{'Scenario':<35} {'Router':<14} {'Deliver%':>9} {'Lat(ms)':>9} "
          f"{'Hops':>6} {'Pwr Eff':>8} {'Thr(Mbps)':>10} {'Ca2+':>6}")
    print("-" * 102)

    for bench_name, scenarios in all_results.items():
        for scenario_name, data in scenarios.items():
            for router in ["myroutelium", "static_mesh"]:
                if router not in data:
                    continue
                r = data[router]
                ca = r.get("avg_calcium_boost", 0)
                ca_str = f"{ca:.3f}" if ca else "  -"
                pwr = r.get("avg_power_efficiency", 0)
                pwr_str = f"{pwr:.3f}" if pwr else "  -"
                print(f"{scenario_name[:35]:<35} {router:<14} "
                      f"{r.get('delivery_rate', 0)*100:>8.1f}% "
                      f"{r.get('avg_latency_ms', 0):>8.2f}ms "
                      f"{r.get('avg_hops', 0):>6.1f} "
                      f"{pwr_str:>8} "
                      f"{r.get('avg_throughput_mbps', 0):>9.1f}M "
                      f"{ca_str:>6}")
            print()


def main():
    ensure_output_dir()
    all_results = {}

    all_results["Topologies"] = bench_radio_topologies()
    all_results["Traffic"] = bench_radio_traffic()
    all_results["Failures"] = bench_radio_failures()
    all_results["Power"] = bench_radio_power()
    all_results["IoT"] = bench_radio_iot()

    print_summary_table(all_results)

    results_path = os.path.join(OUTPUT_DIR, "radio_benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRaw results: {results_path}")

    if HAS_VIZ:
        print(f"Charts: {OUTPUT_DIR}/")

    print("\nDone.")


if __name__ == "__main__":
    main()
