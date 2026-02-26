"""
Labeled scatter plot for talent arbitrage discovery.

Reads JSON from stdin, produces a PNG scatter plot with group-colored points,
optional semi-transparent zone rectangles, smart label placement, and a legend.

Usage:
    echo '{"title":"...","points":[...]}' | python scatter.py -o output.png
"""

import argparse
import json
import sys
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from adjustText import adjust_text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import (
    PALETTE,
    BG_COLOR,
    TEXT_COLOR,
    GRID_COLOR,
    MUTED_COLOR,
    setup_figure,
    style_ax,
    save,
    get_color,
    truncate_label,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_POINT_SIZE = 80
MAX_LABELS = 20
LABEL_THRESHOLD = 30
FIGURE_WIDTH = 18
FIGURE_HEIGHT = 12

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a labeled scatter plot from JSON on stdin.")
    parser.add_argument("-o", "--output", required=True, help="Output PNG file path")
    parser.add_argument("--dpi", type=int, default=150, help="Output DPI (default: 150)")
    return parser.parse_args()


def read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        print("Error: no JSON received on stdin", file=sys.stderr)
        sys.exit(1)
    return json.loads(raw)


def assign_group_colors(points: list[dict]) -> dict[str, str]:
    """Build a mapping from group name to palette color."""
    groups_seen: list[str] = []
    for pt in points:
        grp = pt.get("group", "default")
        if grp not in groups_seen:
            groups_seen.append(grp)
    return {grp: get_color(i) for i, grp in enumerate(groups_seen)}


def select_labels(points: list[dict]) -> set[int]:
    """
    When there are more than LABEL_THRESHOLD points, select only the top
    MAX_LABELS indices for labeling (by size if present, otherwise by y value).
    """
    if len(points) <= LABEL_THRESHOLD:
        return set(range(len(points)))

    has_size = any("size" in pt for pt in points)
    key_fn = (lambda i: points[i].get("size", DEFAULT_POINT_SIZE)) if has_size else (lambda i: points[i]["y"])
    ranked = sorted(range(len(points)), key=key_fn, reverse=True)
    return set(ranked[:MAX_LABELS])


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def draw_zones(ax: plt.Axes, zones: list[dict]) -> None:
    """Draw semi-transparent rectangular zones with labels."""
    for zone in zones:
        x_min = zone["x_min"]
        y_min = zone["y_min"]
        width = zone["x_max"] - x_min
        height = zone["y_max"] - y_min
        color = zone.get("color", "#10B98133")

        # Parse alpha from hex color if 8-char hex, otherwise use 0.2
        if len(color) == 9 and color.startswith("#"):
            base_color = color[:7]
            alpha = int(color[7:9], 16) / 255.0
        else:
            base_color = color
            alpha = 0.2

        rect = Rectangle(
            (x_min, y_min),
            width,
            height,
            linewidth=1.5,
            edgecolor=base_color,
            facecolor=base_color,
            alpha=alpha,
            zorder=1,
        )
        ax.add_patch(rect)

        label = zone.get("label", "")
        if label:
            ax.text(
                x_min + width * 0.02,
                zone["y_max"] - height * 0.04,
                label,
                fontsize=9,
                fontweight="bold",
                color=base_color,
                alpha=min(1.0, alpha + 0.5),
                va="top",
                ha="left",
                zorder=2,
            )


def draw_scatter(
    ax: plt.Axes,
    points: list[dict],
    group_colors: dict[str, str],
    label_indices: set[int],
) -> None:
    """Plot points grouped by color, then add text labels."""
    # Group points by their group for legend entries
    groups: dict[str, list[int]] = {}
    for i, pt in enumerate(points):
        grp = pt.get("group", "default")
        groups.setdefault(grp, []).append(i)

    # Scatter each group
    for grp, indices in groups.items():
        xs = [points[i]["x"] for i in indices]
        ys = [points[i]["y"] for i in indices]
        sizes = [points[i].get("size", DEFAULT_POINT_SIZE) for i in indices]
        color = group_colors[grp]

        ax.scatter(
            xs,
            ys,
            s=sizes,
            c=color,
            label=grp,
            alpha=0.8,
            edgecolors="white",
            linewidths=0.5,
            zorder=3,
        )

    # Add text labels with adjustText for overlap avoidance
    texts = []
    for i in label_indices:
        pt = points[i]
        lbl = truncate_label(pt.get("label", ""), 20)
        if not lbl:
            continue
        texts.append(
            ax.text(
                pt["x"],
                pt["y"],
                lbl,
                fontsize=8,
                color=TEXT_COLOR,
                ha="center",
                va="bottom",
                zorder=5,
            )
        )

    if texts:
        adjust_text(
            texts,
            ax=ax,
            arrowprops=dict(arrowstyle="-", color=MUTED_COLOR, lw=0.5),
            expand=(1.2, 1.4),
            force_text=(0.8, 1.0),
            force_points=(0.5, 0.5),
            ensure_inside_axes=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    data = read_input()

    title = data.get("title")
    subtitle = data.get("subtitle")
    x_label = data.get("x_label", "")
    y_label = data.get("y_label", "")
    points = data.get("points", [])
    zones = data.get("zones", [])

    # Handle empty points gracefully
    if not points:
        fig, ax = setup_figure(FIGURE_WIDTH, FIGURE_HEIGHT, dpi=args.dpi, title=title, subtitle=subtitle)
        ax.text(
            0.5,
            0.5,
            "No data points provided",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            color=MUTED_COLOR,
        )
        style_ax(ax)
        save(fig, args.output, dpi=args.dpi)
        return

    group_colors = assign_group_colors(points)
    label_indices = select_labels(points)

    fig, ax = setup_figure(FIGURE_WIDTH, FIGURE_HEIGHT, dpi=args.dpi, title=title, subtitle=subtitle)

    # Draw zones first (background layer)
    if zones:
        draw_zones(ax, zones)

    # Draw scatter points and labels
    draw_scatter(ax, points, group_colors, label_indices)

    # Axis labels
    if x_label:
        ax.set_xlabel(x_label, fontsize=11, color=TEXT_COLOR, labelpad=10)
    if y_label:
        ax.set_ylabel(y_label, fontsize=11, color=TEXT_COLOR, labelpad=10)

    # Style
    style_ax(ax, grid=True)
    # Enable both x and y grid lines for scatter readability
    ax.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.7)

    # Add some padding to axis limits so edge points aren't clipped
    all_x = [pt["x"] for pt in points]
    all_y = [pt["y"] for pt in points]
    x_pad = (max(all_x) - min(all_x)) * 0.05 or 1.0
    y_pad = (max(all_y) - min(all_y)) * 0.05 or 1.0
    ax.set_xlim(min(all_x) - x_pad, max(all_x) + x_pad)
    ax.set_ylim(min(all_y) - y_pad, max(all_y) + y_pad)

    # Expand limits to include zones if they extend beyond data
    if zones:
        zone_x_min = min(z["x_min"] for z in zones)
        zone_x_max = max(z["x_max"] for z in zones)
        zone_y_min = min(z["y_min"] for z in zones)
        zone_y_max = max(z["y_max"] for z in zones)
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        ax.set_xlim(min(cur_xlim[0], zone_x_min - x_pad), max(cur_xlim[1], zone_x_max + x_pad))
        ax.set_ylim(min(cur_ylim[0], zone_y_min - y_pad), max(cur_ylim[1], zone_y_max + y_pad))

    # Legend
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        legend = ax.legend(
            loc="upper left",
            frameon=True,
            framealpha=0.9,
            facecolor=BG_COLOR,
            edgecolor=GRID_COLOR,
            fontsize=9,
            title="Group",
            title_fontsize=10,
        )
        legend.get_title().set_color(TEXT_COLOR)
        for text in legend.get_texts():
            text.set_color(TEXT_COLOR)

    save(fig, args.output, dpi=args.dpi)


if __name__ == "__main__":
    main()
