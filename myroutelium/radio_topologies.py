"""Pre-built radio mesh topologies for physical layer simulation."""

from __future__ import annotations
import math
import random
from .radio import RadioMesh


def random_field(n: int = 20, area: float = 500.0,
                 seed: int | None = None, **kwargs) -> RadioMesh:
    """Random nodes scattered in a square field.

    Args:
        n: number of nodes
        area: side length of the field (meters)
    """
    if seed is not None:
        random.seed(seed)

    mesh = RadioMesh(**kwargs)
    for i in range(n):
        mesh.add_node(f"r{i}",
                      x=random.uniform(0, area),
                      y=random.uniform(0, area))
    mesh.discover_neighbors()
    return mesh


def grid_field(rows: int = 5, cols: int = 5, spacing: float = 80.0,
               **kwargs) -> RadioMesh:
    """Nodes arranged in a regular grid with fixed spacing.

    Good for testing — predictable distances and symmetry.
    """
    mesh = RadioMesh(**kwargs)
    for r in range(rows):
        for c in range(cols):
            mesh.add_node(f"r{r}_{c}", x=c * spacing, y=r * spacing)
    mesh.discover_neighbors()
    return mesh


def cluster_field(n_clusters: int = 4, nodes_per_cluster: int = 5,
                  cluster_radius: float = 50.0, field_size: float = 500.0,
                  seed: int | None = None, **kwargs) -> RadioMesh:
    """Clustered topology — dense groups separated by longer distances.

    Simulates neighborhoods/buildings with inter-cluster backbone links.
    """
    if seed is not None:
        random.seed(seed)

    mesh = RadioMesh(**kwargs)
    centers = []
    for i in range(n_clusters):
        cx = random.uniform(cluster_radius, field_size - cluster_radius)
        cy = random.uniform(cluster_radius, field_size - cluster_radius)
        centers.append((cx, cy))

        for j in range(nodes_per_cluster):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, cluster_radius)
            mesh.add_node(f"c{i}_n{j}", x=cx + r * math.cos(angle),
                          y=cy + r * math.sin(angle))

    mesh.discover_neighbors()
    return mesh


def line_field(n: int = 10, spacing: float = 100.0, **kwargs) -> RadioMesh:
    """Nodes in a line — worst case for multi-hop."""
    mesh = RadioMesh(**kwargs)
    for i in range(n):
        mesh.add_node(f"l{i}", x=i * spacing, y=0)
    mesh.discover_neighbors()
    return mesh


def disaster_field(n: int = 25, area: float = 800.0,
                   seed: int | None = None, **kwargs) -> RadioMesh:
    """Disaster recovery scenario — sparse, irregular, some nodes far apart.

    Models a post-disaster deployment with ad-hoc node placement.
    """
    if seed is not None:
        random.seed(seed)

    mesh = RadioMesh(**kwargs)
    for i in range(n):
        # Mix of clustered and scattered placement
        if random.random() < 0.3:
            # Scattered (far from others)
            mesh.add_node(f"d{i}",
                          x=random.uniform(0, area),
                          y=random.uniform(0, area))
        else:
            # Clustered around random centers
            cx = random.choice([area * 0.2, area * 0.5, area * 0.8])
            cy = random.choice([area * 0.2, area * 0.5, area * 0.8])
            mesh.add_node(f"d{i}",
                          x=cx + random.gauss(0, area * 0.08),
                          y=cy + random.gauss(0, area * 0.08))

    mesh.discover_neighbors()
    return mesh


def iot_field(n_gateways: int = 3, n_sensors: int = 30,
              area: float = 300.0, seed: int | None = None,
              **kwargs) -> RadioMesh:
    """IoT scenario — few powerful gateways + many low-power sensors."""
    if seed is not None:
        random.seed(seed)

    mesh = RadioMesh(**kwargs)

    # Gateways — high power, spread out
    for i in range(n_gateways):
        angle = 2 * math.pi * i / n_gateways
        mesh.add_node(f"gw{i}",
                      x=area / 2 + (area * 0.3) * math.cos(angle),
                      y=area / 2 + (area * 0.3) * math.sin(angle),
                      max_power=30.0, total_bandwidth=40.0)

    # Sensors — low power, scattered
    for i in range(n_sensors):
        mesh.add_node(f"s{i}",
                      x=random.uniform(0, area),
                      y=random.uniform(0, area),
                      max_power=10.0, total_bandwidth=5.0)

    mesh.discover_neighbors()
    return mesh
