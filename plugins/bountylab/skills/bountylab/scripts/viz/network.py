"""
Network graph visualization (influence rings, OSS ecosystem maps).

Reads a JSON document from stdin describing nodes, edges, and layout preferences,
then renders a network graph to a PNG file.

Usage:
    echo '{"title":"...","nodes":[...],"edges":[...]}' | python network.py -o output.png
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import PALETTE, BG_COLOR, TEXT_COLOR, MUTED_COLOR, save, get_color, truncate_label

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIGURE_SIZE = (14, 14)
DEFAULT_DPI = 150
DEFAULT_LAYOUT = "spring"
SUPPORTED_LAYOUTS = {"spring", "circular", "kamada_kawai", "shell"}

# Node sizing bounds (in scatter-point units)
NODE_SIZE_MIN = 100
NODE_SIZE_MAX = 3000
NODE_SIZE_DEFAULT = 400

# Edge styling
EDGE_ALPHA = 0.3
EDGE_WIDTH_MIN = 0.5
EDGE_WIDTH_MAX = 6.0
EDGE_COLOR = MUTED_COLOR

# Label thresholds
LARGE_GRAPH_THRESHOLD = 50
LARGE_GRAPH_LABEL_COUNT = 20

# Font sizing (auto-scaled by node count)
FONT_SIZE_MAX = 11
FONT_SIZE_MIN = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a network graph from JSON on stdin.")
    parser.add_argument("-o", "--output", required=True, help="Output PNG path")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"Output DPI (default {DEFAULT_DPI})")
    return parser.parse_args()


def read_input() -> dict[str, Any]:
    """Read and validate JSON from stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def build_group_color_map(nodes: list[dict[str, Any]]) -> dict[str, str]:
    """Assign a palette color to each unique group."""
    groups: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        group = node.get("group", "default")
        if group not in seen:
            groups.append(group)
            seen.add(group)
    return {group: get_color(i) for i, group in enumerate(groups)}


def scale_node_sizes(nodes: list[dict[str, Any]]) -> list[float]:
    """Map raw `size` values to scatter-point sizes within [NODE_SIZE_MIN, NODE_SIZE_MAX]."""
    raw_sizes = [float(n.get("size", 10)) for n in nodes]
    if not raw_sizes:
        return []

    lo, hi = min(raw_sizes), max(raw_sizes)
    if lo == hi:
        # All nodes the same size -- use a sensible middle value
        return [NODE_SIZE_DEFAULT] * len(raw_sizes)

    return [
        NODE_SIZE_MIN + (NODE_SIZE_MAX - NODE_SIZE_MIN) * ((s - lo) / (hi - lo))
        for s in raw_sizes
    ]


def scale_edge_widths(edges: list[dict[str, Any]]) -> list[float]:
    """Map raw `weight` values to line widths within [EDGE_WIDTH_MIN, EDGE_WIDTH_MAX]."""
    raw_weights = [float(e.get("weight", 1)) for e in edges]
    if not raw_weights:
        return []

    lo, hi = min(raw_weights), max(raw_weights)
    if lo == hi:
        return [1.5] * len(raw_weights)

    return [
        EDGE_WIDTH_MIN + (EDGE_WIDTH_MAX - EDGE_WIDTH_MIN) * ((w - lo) / (hi - lo))
        for w in raw_weights
    ]


def compute_layout(
    G: nx.Graph,
    layout: str,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """Compute node positions using the requested layout algorithm."""
    if layout == "circular":
        return nx.circular_layout(G)
    if layout == "kamada_kawai":
        return nx.kamada_kawai_layout(G)
    if layout == "shell":
        return nx.shell_layout(G)
    # Default: spring (Fruchterman-Reingold)
    k = 1.5 / max(np.sqrt(G.number_of_nodes()), 1)
    return nx.spring_layout(G, k=k, iterations=80, seed=seed)


def auto_font_size(node_count: int) -> float:
    """Pick a font size that scales down as the graph gets larger."""
    if node_count <= 10:
        return FONT_SIZE_MAX
    if node_count >= 100:
        return FONT_SIZE_MIN
    # Linear interpolation between 10 and 100 nodes
    t = (node_count - 10) / 90.0
    return FONT_SIZE_MAX - t * (FONT_SIZE_MAX - FONT_SIZE_MIN)


def select_labeled_nodes(
    nodes: list[dict[str, Any]],
    node_ids: list[str],
) -> set[str]:
    """For large graphs, only label the top N nodes by size."""
    if len(nodes) <= LARGE_GRAPH_THRESHOLD:
        return set(node_ids)

    indexed = sorted(
        enumerate(nodes),
        key=lambda pair: float(pair[1].get("size", 0)),
        reverse=True,
    )
    top_indices = {node_ids[i] for i, _ in indexed[:LARGE_GRAPH_LABEL_COUNT]}
    return top_indices


# ---------------------------------------------------------------------------
# Main rendering
# ---------------------------------------------------------------------------


def render(data: dict[str, Any], output: str, dpi: int) -> None:
    """Build the networkx graph and render it to a PNG."""
    title = data.get("title", "")
    subtitle = data.get("subtitle", "")
    nodes: list[dict[str, Any]] = data.get("nodes", [])
    edges: list[dict[str, Any]] = data.get("edges", [])
    layout_name = data.get("layout", DEFAULT_LAYOUT)

    if layout_name not in SUPPORTED_LAYOUTS:
        layout_name = DEFAULT_LAYOUT

    # --- Handle empty graph ---
    if not nodes:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        fig.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.text(
            0.5, 0.5,
            "No data to display",
            ha="center", va="center",
            fontsize=14, color=MUTED_COLOR,
            transform=ax.transAxes,
        )
        ax.axis("off")
        if title:
            fig.suptitle(title, fontsize=16, fontweight="bold", color=TEXT_COLOR, y=0.97)
        if subtitle:
            fig.text(0.5, 0.935, subtitle, ha="center", fontsize=11, color=MUTED_COLOR)
        save(fig, output, dpi=dpi)
        return

    # --- Build graph ---
    G = nx.Graph()
    node_ids: list[str] = []
    for n in nodes:
        nid = n["id"]
        node_ids.append(nid)
        G.add_node(nid, label=n.get("label", nid), group=n.get("group", "default"), size=n.get("size", 10))

    # Build a set of valid node ids for edge filtering
    valid_ids = set(node_ids)
    valid_edges: list[dict[str, Any]] = []
    for e in edges:
        src, tgt = e.get("source", ""), e.get("target", "")
        if src in valid_ids and tgt in valid_ids:
            G.add_edge(src, tgt, weight=e.get("weight", 1))
            valid_edges.append(e)

    # --- Layout ---
    pos = compute_layout(G, layout_name)

    # --- Styling ---
    group_colors = build_group_color_map(nodes)
    node_colors = [group_colors.get(n.get("group", "default"), PALETTE[0]) for n in nodes]
    node_sizes = scale_node_sizes(nodes)
    edge_widths = scale_edge_widths(valid_edges)

    # --- Figure ---
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Draw edges
    if valid_edges and edge_widths:
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            width=edge_widths,
            edge_color=EDGE_COLOR,
            alpha=EDGE_ALPHA,
        )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=node_ids,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors=BG_COLOR,   # thin white border around nodes
        linewidths=1.0,
        alpha=0.9,
    )

    # --- Labels ---
    font_size = auto_font_size(len(nodes))
    labeled_ids = select_labeled_nodes(nodes, node_ids)

    labels = {}
    for n in nodes:
        nid = n["id"]
        if nid in labeled_ids:
            raw_label = n.get("label", nid)
            labels[nid] = truncate_label(raw_label, max_len=20)

    if labels:
        nx.draw_networkx_labels(
            G, pos, labels, ax=ax,
            font_size=font_size,
            font_color=TEXT_COLOR,
            font_weight="bold",
        )

    # --- Legend ---
    legend_handles = [
        mpatches.Patch(color=color, label=group)
        for group, color in group_colors.items()
    ]
    if legend_handles:
        legend = ax.legend(
            handles=legend_handles,
            loc="lower left",
            frameon=True,
            framealpha=0.9,
            facecolor=BG_COLOR,
            edgecolor=MUTED_COLOR,
            fontsize=9,
            title="Groups",
            title_fontsize=10,
        )
        legend.get_title().set_color(TEXT_COLOR)
        for text in legend.get_texts():
            text.set_color(TEXT_COLOR)

    # --- Title / subtitle ---
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", color=TEXT_COLOR, y=0.97)
    if subtitle:
        fig.text(0.5, 0.935, subtitle, ha="center", fontsize=11, color=MUTED_COLOR)

    # --- Cleanup ---
    ax.axis("off")

    # Add node count annotation
    node_count_text = f"{len(nodes)} nodes, {len(valid_edges)} edges"
    fig.text(0.98, 0.02, node_count_text, ha="right", fontsize=8, color=MUTED_COLOR)

    save(fig, output, dpi=dpi)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    data = read_input()
    render(data, args.output, args.dpi)


if __name__ == "__main__":
    main()
