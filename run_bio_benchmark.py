#!/usr/bin/env python3
"""Myroutelium Biological Substrate benchmark — living mycelial network simulation."""

import json
import os
import time

from myroutelium.biosubstrate import BioSubstrate, Environment, SPIKE_PATTERNS

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results", "bio")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def plot_substrate(substrate: BioSubstrate, title: str, save_path: str) -> None:
    if not HAS_VIZ:
        return

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.set_title(title, fontsize=14, fontweight="bold")

    topo = substrate.get_network_topology()

    # Draw segments
    for sid, seg in topo["segments"].items():
        ja = topo["junctions"].get(seg["a"])
        jb = topo["junctions"].get(seg["b"])
        if ja is None or jb is None:
            continue

        diameter = seg["diameter"]
        width = 0.3 + (diameter / 10.0) * 3
        if seg["rhizomorph"]:
            color = "#FF9800"
            width *= 1.5
            alpha = 0.9
        elif seg["flow"] > 0:
            color = "#4CAF50"
            alpha = 0.8
        else:
            color = "#A5D6A7"
            alpha = 0.4

        ax.plot([ja["x"], jb["x"]], [ja["y"], jb["y"]],
                color=color, linewidth=width, alpha=alpha, zorder=1)

    # Draw junctions
    for jid, j in topo["junctions"].items():
        if j["type"] == "tip":
            color = "#E91E63"
            size = 30
        elif j["type"] == "anastomosis":
            color = "#9C27B0"
            size = 40
        elif j["type"] == "electrode":
            color = "#2196F3"
            size = 60
        else:
            # Color by calcium level
            ca_norm = min(j["calcium"] / 1.0, 1.0)
            color = plt.cm.YlOrRd(ca_norm)
            size = 15

        ax.scatter(j["x"], j["y"], s=size, c=[color], zorder=3,
                   edgecolors="white", linewidth=0.5)

    # Draw electrodes
    for eid, e in topo["electrodes"].items():
        ax.scatter(e["x"], e["y"], s=120, c=["#1565C0"], zorder=4,
                   marker="^", edgecolors="white", linewidth=1)
        pattern_name = SPIKE_PATTERNS.get(e["pattern"], "?")
        ax.annotate(f"E{eid}:{pattern_name}", (e["x"], e["y"]),
                    fontsize=6, ha="center", va="bottom",
                    xytext=(0, 8), textcoords="offset points", color="#1565C0")

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_aspect("equal")
    ax.set_facecolor("#f0f8f0")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    plt.close(fig)


def plot_bio_metrics(metrics_history: list[dict], title: str, save_path: str) -> None:
    if not HAS_VIZ:
        return

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    ticks = [m["tick"] for m in metrics_history]

    axes[0][0].plot(ticks, [m["segments"] for m in metrics_history], color="#4CAF50")
    axes[0][0].set_title("Segments (alive)")
    axes[0][0].set_xlabel("Tick")
    axes[0][0].grid(True, alpha=0.3)

    axes[0][1].plot(ticks, [m["avg_diameter"] for m in metrics_history], color="#FF9800")
    axes[0][1].set_title("Avg Diameter (μm)")
    axes[0][1].set_xlabel("Tick")
    axes[0][1].grid(True, alpha=0.3)

    axes[0][2].plot(ticks, [m["tips"] for m in metrics_history], color="#E91E63", label="Tips")
    axes[0][2].plot(ticks, [m["rhizomorphs"] for m in metrics_history], color="#FF9800", label="Rhizomorphs")
    axes[0][2].set_title("Tips & Rhizomorphs")
    axes[0][2].legend(fontsize=8)
    axes[0][2].set_xlabel("Tick")
    axes[0][2].grid(True, alpha=0.3)

    axes[1][0].plot(ticks, [m["avg_calcium"] for m in metrics_history], color="#9C27B0")
    axes[1][0].set_title("Avg Calcium (μM)")
    axes[1][0].set_xlabel("Tick")
    axes[1][0].grid(True, alpha=0.3)

    axes[1][1].plot(ticks, [m["spikes_propagated"] for m in metrics_history], color="#F44336")
    axes[1][1].set_title("Spikes Propagated / Tick")
    axes[1][1].set_xlabel("Tick")
    axes[1][1].grid(True, alpha=0.3)

    axes[1][2].plot(ticks, [m["total_length_mm"] for m in metrics_history], color="#2196F3")
    axes[1][2].set_title("Total Network Length (mm)")
    axes[1][2].set_xlabel("Tick")
    axes[1][2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {save_path}")
    plt.close(fig)


# ─── Benchmark 1: Natural Growth ─────────────────────────────

def bench_natural_growth():
    banner("Bio Bench 1: Natural Growth & Self-Organization")

    sub = BioSubstrate()
    sub.seed_network(center_x=0, center_y=0, n_tips=8, radius=2.0)

    # Place electrodes around the periphery
    for i in range(6):
        import math
        angle = 2 * math.pi * i / 6
        sub.add_electrode(15 * math.cos(angle), 15 * math.sin(angle))

    print(f"Initial: {len(sub.junctions)} junctions, {len(sub.segments)} segments")

    metrics_history = []
    for t in range(300):
        m = sub.tick()
        metrics_history.append(m)

        if (t + 1) % 50 == 0:
            print(f"  Tick {t+1:4d} (bio: {m['bio_time_s']:.0f}s) | "
                  f"segs={m['segments']} tips={m['tips']} rhizo={m['rhizomorphs']} "
                  f"fusions={m['fusions']} len={m['total_length_mm']:.1f}mm "
                  f"dia={m['avg_diameter']:.1f}μm")

    if HAS_VIZ:
        plot_substrate(sub, "Natural Growth — Final State",
                       os.path.join(OUTPUT_DIR, "bio_natural_growth.png"))
        plot_bio_metrics(metrics_history, "Natural Growth Metrics",
                         os.path.join(OUTPUT_DIR, "bio_natural_metrics.png"))

    return metrics_history[-1]


# ─── Benchmark 2: Electrode-Guided Routing ───────────────────

def bench_electrode_routing():
    banner("Bio Bench 2: Electrode-Guided Signal Routing")

    sub = BioSubstrate()
    sub.seed_network(center_x=0, center_y=0, n_tips=12, radius=3.0)

    # Source and destination electrodes — within reachable distance
    e_src = sub.add_electrode(-6, 0)
    e_dst = sub.add_electrode(6, 0)
    # Intermediate electrodes
    e_mid1 = sub.add_electrode(0, 4)
    e_mid2 = sub.add_electrode(0, -4)

    # Grow the network with periodic stimulation to guide growth
    print("Growing network (200 ticks with electrode stimulation)...")
    for t in range(200):
        # Stimulate electrodes to attract growth
        if t % 3 == 0:
            for e in [e_src, e_dst, e_mid1, e_mid2]:
                sub.stimulate(e.id, current_uA=5.0)
        sub.tick()

    print(f"Network grown: {len([s for s in sub.segments.values() if s.alive])} segments, "
          f"{sum(s.length for s in sub.segments.values() if s.alive):.1f}mm total")

    # Now route signals
    print("\nRouting signals through biological network...")
    successful_routes = 0
    total_attempts = 50
    path_lengths = []

    for i in range(total_attempts):
        sub.reset_flows()
        # Stimulate source
        sub.stimulate(e_src.id, current_uA=5.0)
        sub.tick()

        # Try to route
        path = sub.route_signal(e_src.id, e_dst.id)
        if path is not None:
            successful_routes += 1
            path_lengths.append(len(path))
            # Reinforce by stimulating along path
            for jid in path:
                for e in sub.electrodes.values():
                    if e.junction_id == jid:
                        sub.stimulate(e.id, current_uA=2.0)
        sub.tick()

    print(f"\nRouting results:")
    print(f"  Successful: {successful_routes}/{total_attempts} ({100*successful_routes/total_attempts:.0f}%)")
    if path_lengths:
        print(f"  Avg path length: {sum(path_lengths)/len(path_lengths):.1f} junctions")

    # Check electrode readings
    states = sub.get_electrode_states()
    print(f"\nElectrode states:")
    for s in states:
        print(f"  E{s['id']}: {s['potential_mV']:.1f}mV, Ca={s['calcium_uM']:.3f}μM, "
              f"pattern={s['pattern_name']}")

    if HAS_VIZ:
        plot_substrate(sub, "Electrode-Guided Routing — Final State",
                       os.path.join(OUTPUT_DIR, "bio_electrode_routing.png"))

    return {
        "success_rate": successful_routes / total_attempts,
        "avg_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0,
    }


# ─── Benchmark 3: Stimulus-Guided Growth ─────────────────────

def bench_guided_growth():
    banner("Bio Bench 3: Stimulus-Guided Network Growth")

    sub = BioSubstrate()
    sub.seed_network(center_x=0, center_y=0, n_tips=6, radius=1.5)

    # Place electrodes as growth targets
    targets = [(8, 8), (-8, 8), (8, -8), (-8, -8)]
    target_electrodes = []
    for tx, ty in targets:
        e = sub.add_electrode(tx, ty)
        target_electrodes.append(e)

    # Stimulate targets with calcium-attracting signals to guide growth
    print("Guiding growth toward target electrodes...")
    metrics_history = []

    for t in range(400):
        # Periodically stimulate targets to create calcium gradients
        if t % 5 == 0:
            for e in target_electrodes:
                sub.stimulate(e.id, current_uA=8.0)

        m = sub.tick()
        metrics_history.append(m)

        if (t + 1) % 100 == 0:
            # Check connectivity to targets
            connected = 0
            center_e = sub.electrodes.get(0)
            for te in target_electrodes:
                path = sub.route_signal(0, te.id)
                if path is not None:
                    connected += 1

            print(f"  Tick {t+1:4d} | segs={m['segments']} tips={m['tips']} "
                  f"len={m['total_length_mm']:.1f}mm | "
                  f"targets connected: {connected}/{len(targets)}")

    if HAS_VIZ:
        plot_substrate(sub, "Stimulus-Guided Growth — Final State",
                       os.path.join(OUTPUT_DIR, "bio_guided_growth.png"))
        plot_bio_metrics(metrics_history, "Guided Growth Metrics",
                         os.path.join(OUTPUT_DIR, "bio_guided_metrics.png"))

    return metrics_history[-1]


# ─── Benchmark 4: Environmental Response ─────────────────────

def bench_environment():
    banner("Bio Bench 4: Environmental Response")

    envs = {
        "Optimal (25°C, 80% moist)": Environment(temperature=25, moisture=0.8, ph=6.0),
        "Cold (10°C)": Environment(temperature=10, moisture=0.8, ph=6.0),
        "Hot (38°C)": Environment(temperature=38, moisture=0.8, ph=6.0),
        "Dry (20% moist)": Environment(temperature=25, moisture=0.2, ph=6.0),
        "Acidic (pH 4)": Environment(temperature=25, moisture=0.8, ph=4.0),
    }

    results = {}
    for name, env in envs.items():
        print(f"\n--- {name} ---")
        print(f"  Growth factor: {env.growth_factor:.2f}, "
              f"Conductivity: {env.conductivity_factor:.2f}")

        sub = BioSubstrate(environment=env)
        sub.seed_network(0, 0, n_tips=8, radius=2.0)

        final = None
        for t in range(200):
            final = sub.tick()

        print(f"  Final: segs={final['segments']} tips={final['tips']} "
              f"len={final['total_length_mm']:.1f}mm dia={final['avg_diameter']:.1f}μm")
        results[name] = final

    return results


# ─── Benchmark 5: Damage and Recovery ────────────────────────

def bench_damage_recovery():
    banner("Bio Bench 5: Damage and Self-Healing")

    sub = BioSubstrate()
    sub.seed_network(0, 0, n_tips=10, radius=2.5)

    # Grow first
    print("Growing (150 ticks)...")
    for t in range(150):
        sub.tick()

    pre_damage = len([s for s in sub.segments.values() if s.alive])
    print(f"Pre-damage: {pre_damage} segments")

    # Damage: kill segments in a region
    killed = 0
    for seg in sub.segments.values():
        ja = sub.junctions[seg.junction_a]
        jb = sub.junctions[seg.junction_b]
        mid_x = (ja.x + jb.x) / 2
        mid_y = (ja.y + jb.y) / 2
        if -2 < mid_x < 2 and -1 < mid_y < 1:
            seg.alive = False
            killed += 1

    print(f"Damaged: killed {killed} segments in center region")

    # Stimulate edges to trigger repair growth
    for e in sub.electrodes.values():
        sub.stimulate(e.id, current_uA=10.0)

    # Recovery period
    print("Recovery (200 ticks)...")
    metrics_history = []
    for t in range(200):
        m = sub.tick()
        metrics_history.append(m)

        if (t + 1) % 50 == 0:
            alive = len([s for s in sub.segments.values() if s.alive])
            print(f"  Tick {t+1:4d} | segs={alive} (was {pre_damage}, killed {killed}) "
                  f"tips={m['tips']} fusions={m['fusions']}")

    post_recovery = len([s for s in sub.segments.values() if s.alive])
    recovery_pct = (post_recovery - (pre_damage - killed)) / killed * 100 if killed else 0

    print(f"\nRecovery: {pre_damage} → {pre_damage - killed} (damage) → {post_recovery}")
    print(f"  Regrowth: {recovery_pct:.0f}% of lost segments replaced")

    if HAS_VIZ:
        plot_substrate(sub, "Damage Recovery — Final State",
                       os.path.join(OUTPUT_DIR, "bio_damage_recovery.png"))

    return {
        "pre_damage": pre_damage,
        "killed": killed,
        "post_recovery": post_recovery,
        "recovery_pct": recovery_pct,
    }


# ─── Main ─────────────────────────────────────────────────────

def main():
    ensure_output_dir()

    results = {}
    results["natural_growth"] = bench_natural_growth()
    results["electrode_routing"] = bench_electrode_routing()
    results["guided_growth"] = bench_guided_growth()
    results["environment"] = bench_environment()
    results["damage_recovery"] = bench_damage_recovery()

    # Save results
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(i) for i in obj]
        elif isinstance(obj, float):
            if obj != obj:  # NaN
                return 0.0
            return obj
        return obj

    results_path = os.path.join(OUTPUT_DIR, "bio_benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(make_serializable(results), f, indent=2)
    print(f"\nResults: {results_path}")
    if HAS_VIZ:
        print(f"Charts: {OUTPUT_DIR}/")
    print("\nDone.")


if __name__ == "__main__":
    main()
