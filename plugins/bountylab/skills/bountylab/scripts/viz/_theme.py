"""
Shared BountyLab visualization theme.

Provides consistent colors, figure setup, and save helpers across all viz scripts.
Import with: from _theme import ...
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

# DevRank tier colors (ordered: cracked → legendary → ... → unranked)
TIER_COLORS = {
    "cracked":   "#6D28D9",
    "legendary": "#F59E0B",
    "elite":     "#3B82F6",
    "skilled":   "#10B981",
    "rising":    "#8B5CF6",
    "notable":   "#6B7280",
    "unranked":  "#D1D5DB",
}

# General-purpose categorical palette (10 colors, colorblind-friendly)
PALETTE = [
    "#6D28D9",  # purple
    "#3B82F6",  # blue
    "#10B981",  # green
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#EC4899",  # pink
    "#14B8A6",  # teal
    "#F97316",  # orange
    "#6B7280",  # gray
]

# Background / text
BG_COLOR = "#FFFFFF"
TEXT_COLOR = "#1F2937"
GRID_COLOR = "#E5E7EB"
MUTED_COLOR = "#9CA3AF"

# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def setup_figure(
    width: float = 18,
    height: float = 12,
    dpi: int = 150,
    title: str | None = None,
    subtitle: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Create a styled figure with optional title/subtitle."""
    fig, ax = plt.subplots(figsize=(width / dpi * 100 / 100, height / dpi * 100 / 100), dpi=dpi)
    # The above simplifies to figsize=(width, height) in inches at 100 dpi;
    # we set dpi on savefig instead. Let's just do it simply:
    fig, ax = plt.subplots(figsize=(width, height))
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", color=TEXT_COLOR, y=0.97)
    if subtitle:
        fig.text(0.5, 0.935, subtitle, ha="center", fontsize=11, color=MUTED_COLOR)

    return fig, ax


def setup_multi(
    nrows: int,
    ncols: int,
    width: float = 18,
    height: float = 12,
    title: str | None = None,
    subtitle: str | None = None,
) -> tuple[plt.Figure, list]:
    """Create a multi-panel figure."""
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, height))
    fig.set_facecolor(BG_COLOR)

    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", color=TEXT_COLOR, y=0.97)
    if subtitle:
        fig.text(0.5, 0.935, subtitle, ha="center", fontsize=11, color=MUTED_COLOR)

    # Flatten to list for uniform access
    import numpy as np
    if isinstance(axes, np.ndarray):
        axes_list = axes.flatten().tolist()
    else:
        axes_list = [axes]

    for a in axes_list:
        a.set_facecolor(BG_COLOR)

    return fig, axes_list


def style_ax(ax: plt.Axes, grid: bool = True) -> None:
    """Apply consistent axis styling."""
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    if grid:
        ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)


def save(fig: plt.Figure, path: str, dpi: int = 150) -> None:
    """Save figure to path with tight layout and proper DPI."""
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=BG_COLOR, pad_inches=0.3)
    plt.close(fig)
    print(f"Saved: {Path(path).resolve()}")


def get_color(index: int) -> str:
    """Get a color from the palette by index (wraps around)."""
    return PALETTE[index % len(PALETTE)]


def truncate_label(label: str, max_len: int = 25) -> str:
    """Truncate a label for display, adding ellipsis if needed."""
    return label if len(label) <= max_len else label[: max_len - 1] + "\u2026"
