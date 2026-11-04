"""Explicit common environments for controlled SECON simulation scenarios.

The grid obstruction model is a synthetic multihop stress model, not a calibrated
RF deployment. No protocol receives the fault schedule or graph reachability.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import deque
from typing import Any, Mapping, Sequence

from lora_mesh_sim import Node

SCHEMA = "secon-common-environment-v1"
_FIELDS = {"model", "columns", "rows", "spacing_m", "position_jitter_fraction",
           "neighbor_loss_db", "nonneighbor_loss_db", "channel_bin_s",
           "endpoint_pairs", "faults"}


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve_environment(case: Any, seed: int, specification: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a fully replayable environment without consulting any outcome."""
    unknown = set(specification) - _FIELDS
    if unknown:
        raise ValueError(f"unknown common environment fields: {sorted(unknown)}")
    if specification.get("model") != "grid-obstructed-v1":
        raise ValueError("unknown common environment model")
    columns = specification.get("columns", 5)
    rows = specification.get("rows", 4)
    if type(columns) is not int or type(rows) is not int:
        raise ValueError("grid dimensions must be integers")
    if columns < 2 or rows < 2 or columns * rows != case.nodes:
        raise ValueError("grid dimensions must equal case.nodes")
    spacing = float(specification.get("spacing_m", 1000.0))
    jitter = float(specification.get("position_jitter_fraction", 0.025))
    bin_s = float(specification.get("channel_bin_s", 0.01))
    neighbor_loss = float(specification.get("neighbor_loss_db", 20.0))
    nonneighbor_loss = float(specification.get("nonneighbor_loss_db", 80.0))
    if (not all(math.isfinite(value) for value in (spacing, jitter, bin_s, neighbor_loss, nonneighbor_loss))
            or spacing <= 0 or not 0 <= jitter <= 0.1 or bin_s <= 0 or min(neighbor_loss, nonneighbor_loss) < 0):
        raise ValueError("invalid grid/channel parameters")
    rng = random.Random(f"secon-grid-positions-v1:{seed}")
    nodes = [dict(node_id=r * columns + c,
                  x=(c + rng.uniform(-jitter, jitter)) * spacing,
                  y=(r + rng.uniform(-jitter, jitter)) * spacing,
                  role="router") for r in range(rows) for c in range(columns)]
    default_pairs = [[columns, 2 * columns - 1], [2 * columns - 1, columns],
                     [(rows - 2) * columns, (rows - 1) * columns - 1],
                     [(rows - 1) * columns - 1, (rows - 2) * columns]]
    pairs = [list(map(int, pair)) for pair in specification.get("endpoint_pairs", default_pairs)]
    if len(pairs) != case.pair_count or len({tuple(p) for p in pairs}) != len(pairs):
        raise ValueError("endpoint pairs must be unique and equal case.pair_count")
    if any(len(p) != 2 or p[0] == p[1] or min(p) < 0 or max(p) >= case.nodes for p in pairs):
        raise ValueError("invalid endpoint pair")
    edges = [[i, j] for i in range(case.nodes) for j in range(i + 1, case.nodes)
             if abs(i // columns - j // columns) + abs(i % columns - j % columns) == 1]
    edge_set = {tuple(edge) for edge in edges}
    faults = []
    for fault in specification.get("faults", []):
        if set(fault) != {"start_s", "end_s", "edges", "attenuation_db"}:
            raise ValueError("fault requires start_s/end_s/edges/attenuation_db only")
        start, end, loss = float(fault["start_s"]), float(fault["end_s"]), float(fault["attenuation_db"])
        selected = sorted({tuple(sorted(map(int, edge))) for edge in fault["edges"]})
        if (not all(math.isfinite(value) for value in (start, end, loss))
                or not (0 <= start < end <= case.duration_s + 3600) or loss < 0 or not selected):
            raise ValueError("invalid fault timing or attenuation")
        if any(edge not in edge_set for edge in selected):
            raise ValueError("fault edge is not a grid neighbor")
        faults.append(dict(start_s=start, end_s=end, edges=[list(e) for e in selected], attenuation_db=loss))
    resolved = dict(schema=SCHEMA, model="grid-obstructed-v1", seed=seed,
                    columns=columns, rows=rows, spacing_m=spacing,
                    position_jitter_fraction=jitter, nodes=nodes, pairs=pairs,
                    neighbor_edges=edges, neighbor_loss_db=neighbor_loss,
                    nonneighbor_loss_db=nonneighbor_loss, channel_bin_s=bin_s,
                    channel_field="sha256-uniform-directed-link-time-bin-v1",
                    faults=faults)
    resolved["environment_sha256"] = canonical_digest(resolved)
    return resolved


def environment_nodes(environment: Mapping[str, Any]) -> list[Node]:
    return [Node(**row) for row in environment["nodes"]]


def attenuation_db(environment: Mapping[str, Any], sender: int, receiver: int, when: float) -> float:
    edge = sorted((sender, receiver))
    value = float(environment["neighbor_loss_db"] if edge in environment["neighbor_edges"]
                  else environment["nonneighbor_loss_db"])
    for fault in environment["faults"]:
        if fault["start_s"] <= when < fault["end_s"] and edge in fault["edges"]:
            value += float(fault["attenuation_db"])
    return value


def channel_uniform(environment: Mapping[str, Any], sender: int, receiver: int, when: float) -> float:
    """A common time/link field independent of protocol, TX id, and draw order."""
    time_bin = math.floor(max(0.0, when) / float(environment["channel_bin_s"]))
    key = f"secon-channel-v1:{environment['seed']}:{sender}:{receiver}:{time_bin}"
    bits = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") >> 11
    return bits / 2**53


def shortest_hops(environment: Mapping[str, Any], src: int, dst: int, when: float) -> int | None:
    """Offline structural description; never called by a routing protocol.

    Treat declared faults of at least 60 dB as absent structural edges; this
    is not an oracle for realized packet success under fading/interference.
    """
    removed = {tuple(edge) for fault in environment["faults"]
               if fault["start_s"] <= when < fault["end_s"] and fault["attenuation_db"] >= 60
               for edge in fault["edges"]}
    graph = {node["node_id"]: [] for node in environment["nodes"]}
    for a, b in environment["neighbor_edges"]:
        if (a, b) not in removed:
            graph[a].append(b)
            graph[b].append(a)
    queue = deque([(src, 0)])
    seen = {src}
    while queue:
        node, hops = queue.popleft()
        if node == dst:
            return hops
        for neighbor in graph[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, hops + 1))
    return None
