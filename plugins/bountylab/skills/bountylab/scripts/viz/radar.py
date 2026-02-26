#!/usr/bin/env python3
"""
Radar / spider chart for cohort comparison.

Reads JSON from stdin, writes a PNG to the path given by --output.

Input JSON schema:
{
  "title": "Team Comparison: Stripe vs Coinbase",
  "subtitle": "Normalized scores (0-100)",
  "axes": ["DevRank", "Experience", "OSS Activity", "Network Size", "Specialization", "Education"],
  "series": [
    {"name": "Stripe Eng", "values": [85, 75, 90, 70, 60, 80]},
    {"name": "Coinbase Eng", "values": [70, 80, 65, 85, 75, 70]}
  ]
}
"""

from __future__ import annotations

import argparse
import json
import sys
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import PALETTE, BG_COLOR, TEXT_COLOR, GRID_COLOR, MUTED_COLOR, save, get_color

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_SERIES = 6
MIN_AXES = 3
GRID_LEVELS = [20, 40, 60, 80, 100]
FILL_ALPHA = 0.25
LINE_WIDTH = 2.0
FIGURE_SIZE = 12  # square

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(data: dict) -> None:
    """Validate input data, exit with a clear message on failure."""
    axes = data.get("axes")
    if not axes or not isinstance(axes, list):
        print("Error: 'axes' must be a non-empty list of axis labels.", file=sys.stderr)
        sys.exit(1)

    if len(axes) < MIN_AXES:
        print(
            f"Error: At least {MIN_AXES} axes are required for a radar chart "
            f"(got {len(axes)}).",
            file=sys.stderr,
        )
        sys.exit(1)

    series = data.get("series")
    if not series or not isinstance(series, list):
        print("Error: 'series' must be a non-empty list.", file=sys.stderr)
        sys.exit(1)

    if len(series) > MAX_SERIES:
        print(
            f"Error: A maximum of {MAX_SERIES} series is supported (got {len(series)}).",
            file=sys.stderr,
        )
        sys.exit(1)

    n_axes = len(axes)
    for i, s in enumerate(series):
        name = s.get("name", f"series[{i}]")
        values = s.get("values")
        if not values or not isinstance(values, list):
            print(f"Error: Series '{name}' must have a 'values' list.", file=sys.stderr)
            sys.exit(1)
        if len(values) != n_axes:
            print(
                f"Error: Series '{name}' has {len(values)} values but {n_axes} axes "
                f"are defined. These must match.",
                file=sys.stderr,
            )
            sys.exit(1)


# ---------------------------------------------------------------------------
# Chart construction
# ---------------------------------------------------------------------------


def _build_chart(data: dict, dpi: int) -> plt.Figure:
    """Build the radar chart and return the figure."""
    axes_labels: list[str] = data["axes"]
    series: list[dict] = data["series"]
    title: str | None = data.get("title")
    subtitle: str | None = data.get("subtitle")

    n_axes = len(axes_labels)

    # Compute angle for each axis (evenly spaced around the circle).
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False).tolist()
    # Close the polygon by wrapping back to the first angle.
    angles += angles[:1]

    # --- Figure setup ---
    fig = plt.figure(figsize=(FIGURE_SIZE, FIGURE_SIZE), dpi=dpi)
    fig.set_facecolor(BG_COLOR)

    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor(BG_COLOR)

    # --- Grid rings ---
    ax.set_ylim(0, 100)
    ax.set_yticks(GRID_LEVELS)
    ax.set_yticklabels(
        [str(g) for g in GRID_LEVELS],
        fontsize=8,
        color=MUTED_COLOR,
    )
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.7)

    # --- Axis labels ---
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(axes_labels, fontsize=11, color=TEXT_COLOR, fontweight="medium")

    # Rotate the chart so the first axis is at the top.
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Style the outer spine.
    ax.spines["polar"].set_color(GRID_COLOR)
    ax.spines["polar"].set_linewidth(0.5)

    # --- Plot each series ---
    for i, s in enumerate(series):
        color = get_color(i)
        values = s["values"] + s["values"][:1]  # close the polygon
        label = s.get("name", f"Series {i + 1}")

        ax.plot(angles, values, color=color, linewidth=LINE_WIDTH, label=label)
        ax.fill(angles, values, color=color, alpha=FILL_ALPHA)

    # --- Title / subtitle ---
    if title:
        fig.suptitle(
            title,
            fontsize=16,
            fontweight="bold",
            color=TEXT_COLOR,
            y=0.97,
        )
    if subtitle:
        fig.text(
            0.5,
            0.935,
            subtitle,
            ha="center",
            fontsize=11,
            color=MUTED_COLOR,
        )

    # --- Legend ---
    legend = ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.25, 1.1),
        fontsize=10,
        frameon=True,
        facecolor=BG_COLOR,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
    )
    legend.get_frame().set_linewidth(0.5)

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a radar/spider chart from JSON on stdin.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output PNG file path.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Output DPI (default: 150).",
    )
    args = parser.parse_args()

    # Read JSON from stdin.
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON on stdin: {exc}", file=sys.stderr)
        sys.exit(1)

    _validate(data)

    fig = _build_chart(data, dpi=args.dpi)
    save(fig, args.output, dpi=args.dpi)


if __name__ == "__main__":
    main()
