"""Visualization of Myroutelium network state and simulation results."""

from __future__ import annotations
import math
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.collections import LineCollection
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from .graph import MycelialGraph
from .simulation import SimMetrics


def _require_mpl():
    if not HAS_MPL:
        raise ImportError("matplotlib is required for visualization. "
                          "Install with: pip install matplotlib")


def plot_network(graph: MycelialGraph, title: str = "Myroutelium Network",
                 show_nutrients: bool = True, show_flow: bool = False,
                 highlight_path: Optional[list[str]] = None,
                 save_path: Optional[str] = None) -> None:
    """Plot the network graph with nutrient scores as link colors/widths."""
    _require_mpl()

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.set_title(title, fontsize=14, fontweight="bold")

    for (src, dst), link in graph.links.items():
        if src >= dst:
            continue
        n1, n2 = graph.nodes[src], graph.nodes[dst]
        if not n1.alive or not n2.alive:
            continue

        if show_nutrients:
            nutrient = link.nutrient
            rev_link = graph.links.get((dst, src))
            if rev_link:
                nutrient = max(nutrient, rev_link.nutrient)

            if link.dormant:
                color = "#cccccc"
                width = 0.5
                alpha = 0.3
            else:
                color = plt.cm.RdYlGn(nutrient)
                width = 0.5 + nutrient * 4
                alpha = 0.3 + nutrient * 0.7
        elif show_flow:
            util = link.utilization
            color = plt.cm.YlOrRd(util)
            width = 1 + util * 4
            alpha = 0.5 + util * 0.5
        else:
            color = "#888888"
            width = 1
            alpha = 0.5

        ax.plot([n1.x, n2.x], [n1.y, n2.y],
                color=color, linewidth=width, alpha=alpha, zorder=1)

    if highlight_path:
        for i in range(len(highlight_path) - 1):
            n1 = graph.nodes[highlight_path[i]]
            n2 = graph.nodes[highlight_path[i + 1]]
            ax.plot([n1.x, n2.x], [n1.y, n2.y],
                    color="#00aaff", linewidth=3, alpha=0.9, zorder=2)

    for node in graph.nodes.values():
        color = "#2196F3" if node.alive else "#ff4444"
        size = 80
        ax.scatter(node.x, node.y, s=size, c=color, zorder=3,
                   edgecolors="white", linewidth=1)
        ax.annotate(node.id, (node.x, node.y), fontsize=6,
                    ha="center", va="bottom", color="#333333",
                    xytext=(0, 6), textcoords="offset points")

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


def plot_comparison(myroutelium_metrics: list[SimMetrics],
                    dijkstra_metrics: list[SimMetrics],
                    title: str = "Myroutelium vs Dijkstra",
                    save_path: Optional[str] = None) -> None:
    """Plot side-by-side comparison of routing metrics over time."""
    _require_mpl()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    ticks = list(range(len(myroutelium_metrics)))

    def _plot(ax, myc_vals, dij_vals, ylabel, title):
        ax.plot(ticks, myc_vals, label="Myroutelium", color="#4CAF50", alpha=0.8, linewidth=1.5)
        ax.plot(ticks, dij_vals, label="Dijkstra", color="#F44336", alpha=0.8, linewidth=1.5)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Tick")

    _plot(axes[0][0],
          [m.avg_latency for m in myroutelium_metrics],
          [m.avg_latency for m in dijkstra_metrics],
          "Latency (ms)", "Average Latency")

    _plot(axes[0][1],
          [m.path_diversity for m in myroutelium_metrics],
          [m.path_diversity for m in dijkstra_metrics],
          "Diversity", "Path Diversity (unique paths / packets)")

    _plot(axes[0][2],
          [m.packets_dropped for m in myroutelium_metrics],
          [m.packets_dropped for m in dijkstra_metrics],
          "Dropped", "Packets Dropped per Tick")

    _plot(axes[1][0],
          [m.avg_hops for m in myroutelium_metrics],
          [m.avg_hops for m in dijkstra_metrics],
          "Hops", "Average Hop Count")

    # Calcium boost (Myroutelium only)
    axes[1][1].plot(ticks, [m.avg_calcium_boost for m in myroutelium_metrics],
                    color="#FF9800", alpha=0.8, linewidth=1.5)
    axes[1][1].fill_between(ticks, [m.avg_calcium_boost for m in myroutelium_metrics],
                            alpha=0.2, color="#FF9800")
    axes[1][1].set_ylabel("Ca2+ Influence")
    axes[1][1].set_title("Calcium Signal Influence (Myroutelium)")
    axes[1][1].set_xlabel("Tick")
    axes[1][1].grid(True, alpha=0.3)

    _plot(axes[1][2],
          [m.avg_utilization for m in myroutelium_metrics],
          [m.avg_utilization for m in dijkstra_metrics],
          "Utilization", "Average Link Utilization")

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close(fig)


def plot_nutrient_heatmap(graph: MycelialGraph,
                          title: str = "Nutrient Score Heatmap",
                          save_path: Optional[str] = None) -> None:
    """Plot a heatmap of nutrient scores across all links."""
    _require_mpl()

    nodes = sorted(graph.nodes.keys())
    n = len(nodes)
    idx = {name: i for i, name in enumerate(nodes)}

    matrix = [[0.0] * n for _ in range(n)]
    for (src, dst), link in graph.links.items():
        if src in idx and dst in idx:
            matrix[idx[src]][idx[dst]] = link.nutrient

    fig, ax = plt.subplots(figsize=(max(8, n * 0.5), max(6, n * 0.4)))
    im = ax.imshow(matrix, cmap="YlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(nodes, rotation=45, ha="right", fontsize=6)
    ax.set_yticklabels(nodes, fontsize=6)
    ax.set_xlabel("Destination")
    ax.set_ylabel("Source")
    ax.set_title(title, fontweight="bold")
    fig.colorbar(im, label="Nutrient Score")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    else:
        plt.show()
    plt.close(fig)
