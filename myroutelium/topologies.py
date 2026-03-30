"""Pre-built network topologies for simulation."""

from __future__ import annotations
import math
import random
from .graph import MycelialGraph


def grid_topology(rows: int = 4, cols: int = 4,
                  capacity: float = 100.0, latency: float = 5.0) -> MycelialGraph:
    """Create a grid/mesh network topology.

    Nodes arranged in a grid with connections to immediate neighbors.
    Good for testing multi-path routing since there are many parallel paths.
    """
    g = MycelialGraph()
    for r in range(rows):
        for c in range(cols):
            node_id = f"n{r}_{c}"
            g.add_node(node_id, x=c * 100, y=r * 100)

    for r in range(rows):
        for c in range(cols):
            node_id = f"n{r}_{c}"
            # Right neighbor
            if c + 1 < cols:
                g.add_link(node_id, f"n{r}_{c+1}", capacity=capacity, latency=latency)
            # Down neighbor
            if r + 1 < rows:
                g.add_link(node_id, f"n{r+1}_{c}", capacity=capacity, latency=latency)

    return g


def ring_topology(n: int = 8, capacity: float = 100.0,
                  latency: float = 5.0) -> MycelialGraph:
    """Create a ring network with n nodes."""
    g = MycelialGraph()
    for i in range(n):
        angle = 2 * math.pi * i / n
        g.add_node(f"n{i}", x=200 + 150 * math.cos(angle),
                   y=200 + 150 * math.sin(angle))

    for i in range(n):
        g.add_link(f"n{i}", f"n{(i+1) % n}", capacity=capacity, latency=latency)

    return g


def fat_tree_topology(k: int = 4, core_cap: float = 1000.0,
                      agg_cap: float = 100.0, edge_cap: float = 10.0) -> MycelialGraph:
    """Create a simplified fat-tree (datacenter-like) topology.

    k = number of pods. Each pod has 2 aggregation + 2 edge switches.
    Core layer connects all pods.
    """
    g = MycelialGraph()

    # Core switches
    n_core = (k // 2) ** 2
    for i in range(n_core):
        g.add_node(f"core{i}", x=100 + i * 80, y=0)

    # Per-pod switches
    for p in range(k):
        for a in range(k // 2):
            agg_id = f"agg{p}_{a}"
            g.add_node(agg_id, x=p * 200 + a * 80, y=100)
            # Connect to core
            for c in range(k // 2):
                core_idx = a * (k // 2) + c
                if core_idx < n_core:
                    g.add_link(agg_id, f"core{core_idx}",
                               capacity=core_cap, latency=1.0)

        for e in range(k // 2):
            edge_id = f"edge{p}_{e}"
            g.add_node(edge_id, x=p * 200 + e * 80, y=200)
            # Connect to all aggregation in same pod
            for a in range(k // 2):
                g.add_link(edge_id, f"agg{p}_{a}",
                           capacity=agg_cap, latency=2.0)

            # Host nodes
            for h in range(k // 2):
                host_id = f"host{p}_{e}_{h}"
                g.add_node(host_id, x=p * 200 + e * 80 + h * 30, y=300)
                g.add_link(host_id, edge_id,
                           capacity=edge_cap, latency=0.5)

    return g


def random_topology(n: int = 20, edge_prob: float = 0.2,
                    capacity_range: tuple[float, float] = (10.0, 200.0),
                    latency_range: tuple[float, float] = (1.0, 20.0),
                    seed: int | None = None) -> MycelialGraph:
    """Create a random Erdos-Renyi topology.

    Guarantees connectivity by adding a spanning tree first.
    """
    if seed is not None:
        random.seed(seed)

    g = MycelialGraph()
    for i in range(n):
        g.add_node(f"n{i}",
                   x=random.uniform(0, 400),
                   y=random.uniform(0, 400))

    # Spanning tree for connectivity
    nodes = list(range(n))
    random.shuffle(nodes)
    for i in range(1, n):
        parent = random.choice(nodes[:i])
        cap = random.uniform(*capacity_range)
        lat = random.uniform(*latency_range)
        g.add_link(f"n{nodes[i]}", f"n{parent}", capacity=cap, latency=lat)

    # Additional random edges
    for i in range(n):
        for j in range(i + 1, n):
            if (f"n{i}", f"n{j}") not in g.links and random.random() < edge_prob:
                cap = random.uniform(*capacity_range)
                lat = random.uniform(*latency_range)
                g.add_link(f"n{i}", f"n{j}", capacity=cap, latency=lat)

    return g


def internet_like_topology(n_backbone: int = 5, n_regional: int = 10,
                           n_edge: int = 20) -> MycelialGraph:
    """Create a hierarchical internet-like topology.

    Three tiers: backbone (high capacity), regional, edge (low capacity).
    """
    g = MycelialGraph()

    # Backbone nodes — fully meshed
    for i in range(n_backbone):
        angle = 2 * math.pi * i / n_backbone
        g.add_node(f"bb{i}", x=200 + 80 * math.cos(angle),
                   y=200 + 80 * math.sin(angle))
    for i in range(n_backbone):
        for j in range(i + 1, n_backbone):
            g.add_link(f"bb{i}", f"bb{j}", capacity=10000.0, latency=2.0)

    # Regional nodes — each connects to 2 backbone nodes
    for i in range(n_regional):
        angle = 2 * math.pi * i / n_regional
        g.add_node(f"reg{i}", x=200 + 160 * math.cos(angle),
                   y=200 + 160 * math.sin(angle))
        bb1 = i % n_backbone
        bb2 = (i + 1) % n_backbone
        g.add_link(f"reg{i}", f"bb{bb1}", capacity=1000.0, latency=5.0)
        g.add_link(f"reg{i}", f"bb{bb2}", capacity=1000.0, latency=5.0)

    # Edge nodes — each connects to 1-2 regional nodes
    for i in range(n_edge):
        angle = 2 * math.pi * i / n_edge
        g.add_node(f"edge{i}", x=200 + 250 * math.cos(angle),
                   y=200 + 250 * math.sin(angle))
        reg1 = i % n_regional
        g.add_link(f"edge{i}", f"reg{reg1}", capacity=100.0, latency=10.0)
        if random.random() < 0.5:
            reg2 = (i + 1) % n_regional
            g.add_link(f"edge{i}", f"reg{reg2}", capacity=100.0, latency=10.0)

    return g
