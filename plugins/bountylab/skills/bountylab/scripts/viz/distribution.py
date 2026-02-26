"""
Multi-panel team demographics visualization.

Reads JSON from stdin describing panels (bar, pie, histogram) and renders
them into a single PNG with an auto-computed grid layout.

Usage:
    echo '{"title":"Team DNA","panels":[...]}' | python distribution.py -o out.png
"""

import argparse
import json
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import (
    PALETTE,
    TIER_COLORS,
    BG_COLOR,
    TEXT_COLOR,
    GRID_COLOR,
    MUTED_COLOR,
    setup_multi,
    style_ax,
    save,
    get_color,
    truncate_label,
)

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITEMS = 10  # Group everything beyond top-N into "Other"
TIER_NAMES = set(TIER_COLORS.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grid_dimensions(n: int) -> tuple[int, int]:
    """Return (nrows, ncols) for *n* panels.

    Layout rules:
        1  -> 1x1
        2  -> 1x2
        3-4 -> 2x2
        5-6 -> 2x3
        7-9 -> 3x3
        ...
    """
    if n <= 0:
        return (1, 1)
    if n == 1:
        return (1, 1)
    if n == 2:
        return (1, 2)
    ncols = math.ceil(math.sqrt(n))
    nrows = math.ceil(n / ncols)
    return (nrows, ncols)


def _is_tier_data(keys: list[str]) -> bool:
    """Return True when a majority of keys are recognised DevRank tier names."""
    lower_keys = {k.lower() for k in keys}
    return len(lower_keys & TIER_NAMES) >= len(keys) / 2


def _collapse_other(data: dict[str, float]) -> dict[str, float]:
    """Keep the top MAX_ITEMS entries; sum the rest into 'Other'."""
    if len(data) <= MAX_ITEMS:
        return data
    sorted_items = sorted(data.items(), key=lambda kv: kv[1], reverse=True)
    top = dict(sorted_items[:MAX_ITEMS])
    other_total = sum(v for _, v in sorted_items[MAX_ITEMS:])
    if other_total > 0:
        top["Other"] = other_total
    return top


def _bar_colors(keys: list[str]) -> list[str]:
    """Choose colors for bar chart labels -- tier-aware."""
    if _is_tier_data(keys):
        return [TIER_COLORS.get(k.lower(), MUTED_COLOR) for k in keys]
    return [get_color(i) for i in range(len(keys))]


# ---------------------------------------------------------------------------
# Panel renderers
# ---------------------------------------------------------------------------


def _render_bar(ax: plt.Axes, panel: dict) -> None:
    """Horizontal bar chart, sorted descending, values annotated."""
    raw_data: dict[str, float] = panel.get("data", {})
    if not raw_data:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color=MUTED_COLOR, fontsize=11)
        return

    data = _collapse_other(raw_data)

    # Sort ascending so the largest bar is at the top after barh
    sorted_items = sorted(data.items(), key=lambda kv: kv[1])
    labels = [truncate_label(k) for k, _ in sorted_items]
    values = [v for _, v in sorted_items]
    raw_keys = [k for k, _ in sorted_items]

    # Reverse the color list to match ascending sort (top bar = largest)
    colors = list(reversed(_bar_colors([k for k, _ in sorted(data.items(), key=lambda kv: kv[1], reverse=True)])))

    bars = ax.barh(labels, values, color=colors, edgecolor="none", height=0.65)

    # Annotate values
    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        offset = max_val * 0.02
        ax.text(
            bar.get_width() + offset,
            bar.get_y() + bar.get_height() / 2,
            f"{val:g}",
            va="center",
            ha="left",
            fontsize=9,
            color=TEXT_COLOR,
            fontweight="bold",
        )

    ax.set_xlim(0, max_val * 1.15)
    style_ax(ax)
    ax.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.7)
    ax.grid(False, axis="y")
    ax.tick_params(axis="y", length=0)


def _render_pie(ax: plt.Axes, panel: dict) -> None:
    """Donut / pie chart with percentage labels."""
    raw_data: dict[str, float] = panel.get("data", {})
    if not raw_data:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color=MUTED_COLOR, fontsize=11)
        return

    data = _collapse_other(raw_data)

    labels = list(data.keys())
    values = list(data.values())
    colors = [get_color(i) for i in range(len(labels))]

    wedges, texts, autotexts = ax.pie(
        values,
        labels=[truncate_label(l) for l in labels],
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        startangle=140,
        colors=colors,
        wedgeprops=dict(width=0.4, edgecolor=BG_COLOR, linewidth=2),
        textprops=dict(color=TEXT_COLOR, fontsize=9),
        pctdistance=0.78,
    )

    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")
        t.set_color(TEXT_COLOR)

    ax.set_aspect("equal")
    # Remove spines for pie (style_ax not needed, but clean up)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _render_histogram(ax: plt.Axes, panel: dict) -> None:
    """Histogram with auto-binning and count annotations on each bin."""
    raw_data = panel.get("data", [])
    if not raw_data:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color=MUTED_COLOR, fontsize=11)
        return

    values = [float(v) for v in raw_data]

    # Auto-bin: Sturges' rule, clamped to [5, 30]
    n_bins = max(5, min(30, int(math.ceil(math.log2(len(values)) + 1))))

    counts, bin_edges, patches = ax.hist(
        values,
        bins=n_bins,
        color=PALETTE[0],
        edgecolor=BG_COLOR,
        linewidth=1,
        alpha=0.9,
    )

    # Annotate counts on each bin
    for count, patch in zip(counts, patches):
        if count > 0:
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                count,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color=TEXT_COLOR,
            )

    ax.set_ylabel("Count", fontsize=9, color=TEXT_COLOR)
    style_ax(ax)


# Renderer dispatch
_RENDERERS = {
    "bar": _render_bar,
    "pie": _render_pie,
    "histogram": _render_histogram,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render multi-panel team demographics chart."
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output PNG file path."
    )
    parser.add_argument(
        "--dpi", type=int, default=150, help="Output DPI (default: 150)."
    )
    args = parser.parse_args()

    # ---- Read input -------------------------------------------------------
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON on stdin: {exc}", file=sys.stderr)
        sys.exit(1)

    title: str | None = payload.get("title")
    subtitle: str | None = payload.get("subtitle")
    panels: list[dict] = payload.get("panels", [])

    if not panels:
        print("Error: no panels provided in input JSON.", file=sys.stderr)
        sys.exit(1)

    # ---- Layout -----------------------------------------------------------
    n_panels = len(panels)
    nrows, ncols = _grid_dimensions(n_panels)

    fig, axes = setup_multi(
        nrows=nrows,
        ncols=ncols,
        width=18,
        height=12,
        title=title,
        subtitle=subtitle,
    )

    # ---- Render each panel ------------------------------------------------
    for idx, panel in enumerate(panels):
        ax = axes[idx]
        panel_type = panel.get("type", "bar")
        panel_name = panel.get("name", "")

        renderer = _RENDERERS.get(panel_type)
        if renderer is None:
            ax.text(
                0.5,
                0.5,
                f"Unknown type: {panel_type}",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=MUTED_COLOR,
                fontsize=11,
            )
        else:
            try:
                renderer(ax, panel)
            except Exception as exc:
                ax.text(
                    0.5,
                    0.5,
                    f"Render error:\n{exc}",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    color="#EF4444",
                    fontsize=9,
                    wrap=True,
                )

        if panel_name:
            ax.set_title(
                panel_name,
                fontsize=12,
                fontweight="bold",
                color=TEXT_COLOR,
                pad=12,
            )

    # ---- Hide unused axes -------------------------------------------------
    for idx in range(n_panels, len(axes)):
        axes[idx].set_visible(False)

    # ---- Save -------------------------------------------------------------
    save(fig, args.output, dpi=args.dpi)


if __name__ == "__main__":
    main()
