#!/usr/bin/env python3
"""Sankey diagram for talent flow between companies.

Reads JSON from stdin describing flows between source and target companies,
then renders a Sankey-style diagram with bezier-curved flow bands connecting
source nodes (left column) to target nodes (right column).

Input JSON schema:
    {
        "title": "Talent Flow: Stripe Alumni",
        "subtitle": "Where they went after Stripe",
        "flows": [
            {"source": "Stripe", "target": "Coinbase", "value": 12},
            {"source": "Stripe", "target": "Plaid", "value": 8},
            ...
        ]
    }
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import (
    PALETTE,
    BG_COLOR,
    TEXT_COLOR,
    MUTED_COLOR,
    GRID_COLOR,
    setup_figure,
    save,
    get_color,
    truncate_label,
)

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MPath
import matplotlib.patheffects as pe
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_NODES = 15  # Group into "Other" if more than this many sources or targets
NODE_WIDTH = 0.04  # Width of node rectangles as fraction of plot width
NODE_PAD_FRAC = 0.35  # Fraction of total node height reserved for padding
FLOW_ALPHA = 0.38
FLOW_ALPHA_HOVER = 0.55  # Slightly higher alpha for larger flows
LABEL_FONTSIZE = 10
VALUE_FONTSIZE = 9
MIN_NODE_HEIGHT_FRAC = 0.008  # Minimum visible height for tiny nodes


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def _aggregate_flows(
    flows: list[dict],
) -> tuple[dict[str, float], dict[str, float], list[dict]]:
    """Compute total values per source/target and clean flow list.

    Returns (source_totals, target_totals, cleaned_flows).
    """
    source_totals: dict[str, float] = {}
    target_totals: dict[str, float] = {}

    for f in flows:
        src = str(f.get("source", ""))
        tgt = str(f.get("target", ""))
        val = float(f.get("value", 0))
        if val <= 0 or not src or not tgt:
            continue
        source_totals[src] = source_totals.get(src, 0) + val
        target_totals[tgt] = target_totals.get(tgt, 0) + val

    return source_totals, target_totals, flows


def _group_small_nodes(
    totals: dict[str, float], max_nodes: int
) -> tuple[dict[str, float], set[str]]:
    """If there are more nodes than max_nodes, group the smallest into 'Other'.

    Returns (new_totals, set_of_grouped_names).
    """
    if len(totals) <= max_nodes:
        return totals, set()

    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    kept = dict(sorted_items[: max_nodes - 1])
    grouped = {name for name, _ in sorted_items[max_nodes - 1 :]}
    other_total = sum(val for name, val in sorted_items[max_nodes - 1 :])
    kept["Other"] = other_total
    return kept, grouped


def _rewrite_flows(
    flows: list[dict], grouped_sources: set[str], grouped_targets: set[str]
) -> list[dict]:
    """Rewrite flow source/target names, merging grouped nodes into 'Other'."""
    merged: dict[tuple[str, str], float] = {}
    for f in flows:
        src = str(f.get("source", ""))
        tgt = str(f.get("target", ""))
        val = float(f.get("value", 0))
        if val <= 0 or not src or not tgt:
            continue
        if src in grouped_sources:
            src = "Other"
        if tgt in grouped_targets:
            tgt = "Other"
        key = (src, tgt)
        merged[key] = merged.get(key, 0) + val
    return [{"source": s, "target": t, "value": v} for (s, t), v in merged.items()]


def prepare_data(
    raw_flows: list[dict],
) -> tuple[dict[str, float], dict[str, float], list[dict]]:
    """Full pipeline: aggregate, group, rewrite. Returns (src_totals, tgt_totals, flows)."""
    source_totals, target_totals, flows = _aggregate_flows(raw_flows)

    source_totals, grouped_src = _group_small_nodes(source_totals, MAX_NODES)
    target_totals, grouped_tgt = _group_small_nodes(target_totals, MAX_NODES)

    flows = _rewrite_flows(flows, grouped_src, grouped_tgt)

    # Re-aggregate after rewriting (to ensure consistency)
    source_totals_final: dict[str, float] = {}
    target_totals_final: dict[str, float] = {}
    for f in flows:
        source_totals_final[f["source"]] = (
            source_totals_final.get(f["source"], 0) + f["value"]
        )
        target_totals_final[f["target"]] = (
            target_totals_final.get(f["target"], 0) + f["value"]
        )

    return source_totals_final, target_totals_final, flows


# ---------------------------------------------------------------------------
# Layout computation
# ---------------------------------------------------------------------------


def _compute_node_positions(
    totals: dict[str, float],
    x: float,
    y_start: float,
    y_end: float,
) -> dict[str, tuple[float, float, float]]:
    """Compute vertical positions for nodes.

    Returns {name: (y_center, y_top, height)} sorted by total descending.
    """
    if not totals:
        return {}

    sorted_nodes = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    total_value = sum(v for _, v in sorted_nodes)
    if total_value <= 0:
        return {}

    available_height = y_end - y_start
    node_count = len(sorted_nodes)
    pad_total = available_height * NODE_PAD_FRAC
    pad_each = pad_total / max(node_count - 1, 1) if node_count > 1 else 0
    drawable_height = available_height - pad_total

    # Compute raw heights proportional to value
    raw_heights = [(name, (val / total_value) * drawable_height) for name, val in sorted_nodes]

    # Enforce minimum height
    min_h = available_height * MIN_NODE_HEIGHT_FRAC
    adjusted = []
    stolen = 0.0
    for name, h in raw_heights:
        if h < min_h:
            stolen += min_h - h
            adjusted.append((name, min_h))
        else:
            adjusted.append((name, h))

    # Redistribute stolen height from largest nodes
    if stolen > 0:
        large_total = sum(h for _, h in adjusted if h > min_h)
        if large_total > 0:
            adjusted = [
                (name, h - (h / large_total) * stolen if h > min_h else h)
                for name, h in adjusted
            ]

    # Assign y positions top-to-bottom
    positions: dict[str, tuple[float, float, float]] = {}
    y_cursor = y_end  # Start from top
    for name, h in adjusted:
        y_top = y_cursor
        y_center = y_top - h / 2
        positions[name] = (y_center, y_top, h)
        y_cursor -= h + pad_each

    return positions


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _draw_node(
    ax: plt.Axes,
    x: float,
    y_top: float,
    height: float,
    width: float,
    color: str,
    label: str,
    value: float,
    side: str,
) -> None:
    """Draw a single node rectangle with label."""
    rect = mpatches.FancyBboxPatch(
        (x, y_top - height),
        width,
        height,
        boxstyle=mpatches.BoxStyle.Round(pad=0.003),
        facecolor=color,
        edgecolor="white",
        linewidth=1.2,
        zorder=3,
    )
    ax.add_patch(rect)

    # Label text
    display_label = truncate_label(label, 22)
    value_str = f"{int(value):,}" if value == int(value) else f"{value:,.1f}"
    full_label = f"{display_label}  ({value_str})"

    if side == "left":
        text_x = x - 0.012
        ha = "right"
    else:
        text_x = x + width + 0.012
        ha = "left"

    text_y = y_top - height / 2

    ax.text(
        text_x,
        text_y,
        full_label,
        ha=ha,
        va="center",
        fontsize=LABEL_FONTSIZE,
        fontweight="bold",
        color=TEXT_COLOR,
        zorder=5,
        path_effects=[pe.withStroke(linewidth=3, foreground=BG_COLOR)],
    )


def _draw_flow(
    ax: plt.Axes,
    x_src: float,
    y_src_top: float,
    y_src_bot: float,
    x_tgt: float,
    y_tgt_top: float,
    y_tgt_bot: float,
    color: str,
    alpha: float,
) -> None:
    """Draw a single flow band as a filled bezier curve between source and target."""
    # Control point x offset for smooth curves
    cx = (x_src + x_tgt) / 2

    # Top edge of the band: src_top -> tgt_top
    # Bottom edge of the band: tgt_bot -> src_bot (reversed)
    verts = [
        # Top edge (left to right)
        (x_src, y_src_top),
        (cx, y_src_top),
        (cx, y_tgt_top),
        (x_tgt, y_tgt_top),
        # Right edge down
        (x_tgt, y_tgt_bot),
        # Bottom edge (right to left)
        (cx, y_tgt_bot),
        (cx, y_src_bot),
        (x_src, y_src_bot),
        # Close
        (x_src, y_src_top),
    ]

    codes = [
        MPath.MOVETO,
        MPath.CURVE4,
        MPath.CURVE4,
        MPath.CURVE4,
        MPath.LINETO,
        MPath.CURVE4,
        MPath.CURVE4,
        MPath.CURVE4,
        MPath.CLOSEPOLY,
    ]

    path = MPath(verts, codes)
    patch = mpatches.PathPatch(
        path,
        facecolor=color,
        edgecolor="none",
        alpha=alpha,
        zorder=2,
    )
    ax.add_patch(patch)


# ---------------------------------------------------------------------------
# Assign colors
# ---------------------------------------------------------------------------


def _assign_colors(
    source_names: list[str], target_names: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Assign colors to source and target nodes from the palette."""
    src_colors = {}
    for i, name in enumerate(source_names):
        src_colors[name] = get_color(i)

    tgt_colors = {}
    for i, name in enumerate(target_names):
        # Offset by source count to avoid color collisions when possible
        tgt_colors[name] = get_color(len(source_names) + i)

    return src_colors, tgt_colors


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def render_sankey(
    data: dict,
    output_path: str,
    dpi: int = 150,
) -> None:
    """Render a Sankey diagram from the input data and save to output_path."""
    title = data.get("title", "Talent Flow")
    subtitle = data.get("subtitle")
    raw_flows = data.get("flows", [])

    # Handle empty flows
    if not raw_flows or all(float(f.get("value", 0)) <= 0 for f in raw_flows):
        print("No flows to display. Generating blank chart.", file=sys.stderr)
        fig, ax = setup_figure(width=18, height=12, title=title, subtitle=subtitle)
        ax.text(
            0.5,
            0.5,
            "No talent flow data available",
            ha="center",
            va="center",
            fontsize=16,
            color=MUTED_COLOR,
            transform=ax.transAxes,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        save(fig, output_path, dpi=dpi)
        return

    # Prepare data
    source_totals, target_totals, flows = prepare_data(raw_flows)

    if not source_totals or not target_totals:
        print("No valid flows after processing. Generating blank chart.", file=sys.stderr)
        fig, ax = setup_figure(width=18, height=12, title=title, subtitle=subtitle)
        ax.text(
            0.5,
            0.5,
            "No talent flow data available",
            ha="center",
            va="center",
            fontsize=16,
            color=MUTED_COLOR,
            transform=ax.transAxes,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        save(fig, output_path, dpi=dpi)
        return

    # Figure setup
    fig, ax = setup_figure(width=18, height=12, title=title, subtitle=subtitle)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Layout parameters
    left_x = 0.18  # Left column x position
    right_x = 0.78  # Right column x position
    y_start = 0.05  # Bottom margin
    y_end = 0.92  # Top margin

    # Compute node positions
    src_positions = _compute_node_positions(source_totals, left_x, y_start, y_end)
    tgt_positions = _compute_node_positions(target_totals, right_x, y_start, y_end)

    # Assign colors
    src_names_sorted = sorted(source_totals.keys(), key=lambda k: source_totals[k], reverse=True)
    tgt_names_sorted = sorted(target_totals.keys(), key=lambda k: target_totals[k], reverse=True)
    src_colors, tgt_colors = _assign_colors(src_names_sorted, tgt_names_sorted)

    # Track how much of each node's height has been consumed by flows
    src_consumed: dict[str, float] = {name: 0.0 for name in src_positions}
    tgt_consumed: dict[str, float] = {name: 0.0 for name in tgt_positions}

    # Sort flows by value descending so larger flows are drawn first (behind)
    sorted_flows = sorted(flows, key=lambda f: f["value"], reverse=True)

    # Draw flows
    for f in sorted_flows:
        src = f["source"]
        tgt = f["target"]
        val = f["value"]

        if src not in src_positions or tgt not in tgt_positions:
            continue

        src_center, src_y_top, src_h = src_positions[src]
        tgt_center, tgt_y_top, tgt_h = tgt_positions[tgt]

        src_total = source_totals[src]
        tgt_total = target_totals[tgt]

        # Flow height on source side (proportional to source node)
        flow_h_src = (val / src_total) * src_h if src_total > 0 else 0
        # Flow height on target side (proportional to target node)
        flow_h_tgt = (val / tgt_total) * tgt_h if tgt_total > 0 else 0

        # Source band position (stacking top-down within the node)
        flow_src_top = src_y_top - src_consumed[src]
        flow_src_bot = flow_src_top - flow_h_src
        src_consumed[src] += flow_h_src

        # Target band position (stacking top-down within the node)
        flow_tgt_top = tgt_y_top - tgt_consumed[tgt]
        flow_tgt_bot = flow_tgt_top - flow_h_tgt
        tgt_consumed[tgt] += flow_h_tgt

        # Use source color for the flow
        color = src_colors.get(src, PALETTE[0])

        # Slightly higher alpha for larger flows for visual weight
        max_val = sorted_flows[0]["value"] if sorted_flows else 1
        alpha = FLOW_ALPHA + (FLOW_ALPHA_HOVER - FLOW_ALPHA) * (val / max_val)

        _draw_flow(
            ax,
            x_src=left_x + NODE_WIDTH,
            y_src_top=flow_src_top,
            y_src_bot=flow_src_bot,
            x_tgt=right_x,
            y_tgt_top=flow_tgt_top,
            y_tgt_bot=flow_tgt_bot,
            color=color,
            alpha=alpha,
        )

    # Draw source nodes
    for name in src_names_sorted:
        if name not in src_positions:
            continue
        center, y_top, h = src_positions[name]
        _draw_node(
            ax,
            x=left_x,
            y_top=y_top,
            height=h,
            width=NODE_WIDTH,
            color=src_colors[name],
            label=name,
            value=source_totals[name],
            side="left",
        )

    # Draw target nodes
    for name in tgt_names_sorted:
        if name not in tgt_positions:
            continue
        center, y_top, h = tgt_positions[name]
        _draw_node(
            ax,
            x=right_x,
            y_top=y_top,
            height=h,
            width=NODE_WIDTH,
            color=tgt_colors[name],
            label=name,
            value=target_totals[name],
            side="right",
        )

    # Column headers
    ax.text(
        left_x + NODE_WIDTH / 2,
        y_end + 0.03,
        "Source",
        ha="center",
        va="bottom",
        fontsize=13,
        fontweight="bold",
        color=MUTED_COLOR,
    )
    ax.text(
        right_x + NODE_WIDTH / 2,
        y_end + 0.03,
        "Destination",
        ha="center",
        va="bottom",
        fontsize=13,
        fontweight="bold",
        color=MUTED_COLOR,
    )

    # Total flow annotation
    grand_total = sum(f["value"] for f in flows)
    total_str = f"{int(grand_total):,}" if grand_total == int(grand_total) else f"{grand_total:,.1f}"
    ax.text(
        0.5,
        0.01,
        f"Total flow: {total_str}",
        ha="center",
        va="bottom",
        fontsize=10,
        color=MUTED_COLOR,
        style="italic",
    )

    save(fig, output_path, dpi=dpi)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Sankey diagram of talent flow between companies."
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output PNG file path",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Output DPI (default: 150)",
    )
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)

    render_sankey(data, args.output, dpi=args.dpi)


if __name__ == "__main__":
    main()
