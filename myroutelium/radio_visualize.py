"""Visualization for radio mesh physical layer simulation."""

from __future__ import annotations
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from .radio import RadioMesh
from .radio_simulation import RadioSimMetrics


def _require_mpl():
    if not HAS_MPL:
        raise ImportError("matplotlib required: pip install matplotlib")


def plot_radio_mesh(mesh: RadioMesh, title: str = "Myroutelium Radio Mesh",
                    show_power: bool = True, show_snr: bool = False,
                    save_path: Optional[str] = None) -> None:
    """Plot the radio mesh with adaptive power/SNR as link properties."""
    _require_mpl()

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.set_title(title, fontsize=14, fontweight="bold")

    # Draw links
    drawn = set()
    for node_id, node in mesh.nodes.items():
        if not node.alive:
            continue
        for neighbor_id, link in node.links.items():
            pair = tuple(sorted([node_id, neighbor_id]))
            if pair in drawn:
                continue
            drawn.add(pair)

            n2 = mesh.nodes[neighbor_id]
            if not n2.alive:
                continue

            if show_power:
                val = link.nutrient
                color = plt.cm.RdYlGn(val)
                width = 0.5 + val * 3
                alpha = 0.3 + val * 0.6
            elif show_snr:
                val = min(link.snr / 30.0, 1.0) if link.snr > 0 else 0
                color = plt.cm.viridis(val)
                width = 0.5 + val * 3
                alpha = 0.4 + val * 0.5
            else:
                color = "#888"
                width = 1
                alpha = 0.4

            if not link.active:
                color = "#cccccc"
                width = 0.3
                alpha = 0.2

            ax.plot([node.x, n2.x], [node.y, n2.y],
                    color=color, linewidth=width, alpha=alpha, zorder=1)

    # Draw nodes with size proportional to total power
    for node in mesh.nodes.values():
        if not node.alive:
            color = "#ff4444"
            size = 40
        else:
            power_frac = node.total_tx_power / (node.max_power * max(node.n_active_links, 1)) \
                if node.n_active_links > 0 else 0
            color = plt.cm.Blues(0.3 + power_frac * 0.7)
            size = 40 + power_frac * 80

        ax.scatter(node.x, node.y, s=size, c=[color], zorder=3,
                   edgecolors="white", linewidth=1)
        ax.annotate(node.id, (node.x, node.y), fontsize=5,
                    ha="center", va="bottom", color="#333",
                    xytext=(0, 5), textcoords="offset points")

    ax.set_xlabel("X (meters)")
    ax.set_ylabel("Y (meters)")
    ax.set_aspect("equal")
    ax.set_facecolor("#f8f8f8")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close(fig)


def plot_radio_comparison(myc_metrics: list[RadioSimMetrics],
                          static_metrics: list[RadioSimMetrics],
                          title: str = "Myroutelium vs Static Mesh",
                          save_path: Optional[str] = None) -> None:
    """Plot comparison of radio routing metrics."""
    _require_mpl()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    ticks = list(range(len(myc_metrics)))

    def _plot(ax, myc_vals, stat_vals, ylabel, title):
        ax.plot(ticks, myc_vals, label="Myroutelium", color="#4CAF50", alpha=0.8, linewidth=1.5)
        ax.plot(ticks, stat_vals, label="Static Mesh", color="#F44336", alpha=0.8, linewidth=1.5)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Tick")

    _plot(axes[0][0],
          [m.avg_latency_ms for m in myc_metrics],
          [m.avg_latency_ms for m in static_metrics],
          "Latency (ms)", "Average Latency")

    _plot(axes[0][1],
          [m.path_diversity for m in myc_metrics],
          [m.path_diversity for m in static_metrics],
          "Diversity", "Path Diversity")

    _plot(axes[0][2],
          [m.packets_dropped for m in myc_metrics],
          [m.packets_dropped for m in static_metrics],
          "Dropped", "Packets Dropped per Tick")

    # Power efficiency — key metric for physical layer
    _plot(axes[1][0],
          [m.power_efficiency for m in myc_metrics],
          [m.power_efficiency for m in static_metrics],
          "Power Ratio", "Power Efficiency (actual / max)")

    # Calcium influence
    axes[1][1].plot(ticks, [m.avg_calcium_boost for m in myc_metrics],
                    color="#FF9800", alpha=0.8, linewidth=1.5)
    axes[1][1].fill_between(ticks, [m.avg_calcium_boost for m in myc_metrics],
                            alpha=0.2, color="#FF9800")
    axes[1][1].set_ylabel("Ca2+ Influence")
    axes[1][1].set_title("Calcium Signal Influence")
    axes[1][1].set_xlabel("Tick")
    axes[1][1].grid(True, alpha=0.3)

    _plot(axes[1][2],
          [m.avg_hops for m in myc_metrics],
          [m.avg_hops for m in static_metrics],
          "Hops", "Average Hop Count")

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close(fig)
