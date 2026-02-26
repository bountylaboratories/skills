"""
Heatmap visualization for skill co-occurrence and technology matrices.

Reads JSON from stdin describing a matrix with row/column labels and renders
a heatmap PNG using seaborn.

Usage:
    echo '{"title":"Skill Co-occurrence","matrix":[[...],...],...}' | python heatmap.py -o out.png
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import BG_COLOR, TEXT_COLOR, MUTED_COLOR, save

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_FIG_WIDTH = 10
MIN_FIG_HEIGHT = 8
MAX_FIG_WIDTH = 20
MAX_FIG_HEIGHT = 16

LARGE_MATRIX_THRESHOLD = 20  # labels beyond this trigger smaller fonts
DEFAULT_COLORMAP = "YlOrRd"
DEFAULT_DPI = 150

FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 7
FONT_SIZE_TINY = 5
ANNOT_SIZE_NORMAL = 9
ANNOT_SIZE_SMALL = 7
ANNOT_SIZE_TINY = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_fig_size(nrows: int, ncols: int) -> tuple[float, float]:
    """Auto-scale figure size based on matrix dimensions.

    Scales linearly from the minimum to the maximum size, with a base of
    0.6 inches per label (clamped to min/max bounds).
    """
    width = max(MIN_FIG_WIDTH, min(MAX_FIG_WIDTH, ncols * 0.6 + 4))
    height = max(MIN_FIG_HEIGHT, min(MAX_FIG_HEIGHT, nrows * 0.6 + 3))
    return (width, height)


def _is_symmetric(matrix: np.ndarray, row_labels: list[str], col_labels: list[str]) -> bool:
    """Check if the matrix is square with identical labels and symmetric values."""
    if matrix.shape[0] != matrix.shape[1]:
        return False
    if row_labels != col_labels:
        return False
    return np.allclose(matrix, matrix.T, atol=1e-9, equal_nan=True)


def _build_upper_triangle_mask(n: int) -> np.ndarray:
    """Create a boolean mask that hides the upper triangle (above the diagonal)."""
    mask = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(i + 1, n):
            mask[i][j] = True
    return mask


def _choose_annotation_format(matrix: np.ndarray) -> str:
    """Pick an annotation format string based on the values in the matrix.

    - If all values are integers (or very close), format as int.
    - If values span a small range (0-1 style), use 2 decimal places.
    - Otherwise use 1 decimal place.
    """
    flat = matrix.flatten()
    flat = flat[~np.isnan(flat)]

    if len(flat) == 0:
        return ".1f"

    # Check if all values are effectively integers
    if np.all(np.abs(flat - np.round(flat)) < 1e-9):
        return ".0f"

    # Values in [0, 1] range benefit from 2 decimal places
    if np.nanmin(flat) >= 0 and np.nanmax(flat) <= 1:
        return ".2f"

    return ".1f"


def _label_font_size(n_labels: int) -> int:
    """Return an appropriate font size for axis tick labels."""
    if n_labels <= LARGE_MATRIX_THRESHOLD:
        return FONT_SIZE_NORMAL
    if n_labels <= 40:
        return FONT_SIZE_SMALL
    return FONT_SIZE_TINY


def _annot_font_size(n_labels: int) -> int:
    """Return an appropriate font size for cell annotations."""
    if n_labels <= LARGE_MATRIX_THRESHOLD:
        return ANNOT_SIZE_NORMAL
    if n_labels <= 40:
        return ANNOT_SIZE_SMALL
    return ANNOT_SIZE_TINY


# ---------------------------------------------------------------------------
# Main rendering
# ---------------------------------------------------------------------------


def _render_heatmap(
    matrix: np.ndarray,
    row_labels: list[str],
    col_labels: list[str],
    title: str | None,
    subtitle: str | None,
    colormap: str,
    annotate: bool,
    dpi: int,
    output: str,
) -> None:
    """Render and save the heatmap figure."""
    nrows, ncols = matrix.shape
    max_dim = max(nrows, ncols)

    fig_w, fig_h = _compute_fig_size(nrows, ncols)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Title / subtitle
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", color=TEXT_COLOR, y=0.97)
    if subtitle:
        fig.text(0.5, 0.935, subtitle, ha="center", fontsize=11, color=MUTED_COLOR)

    # Symmetric co-occurrence matrix: mask the upper triangle
    mask = None
    if _is_symmetric(matrix, row_labels, col_labels):
        mask = _build_upper_triangle_mask(nrows)

    # Annotation formatting
    fmt = _choose_annotation_format(matrix)
    annot_kws = {"size": _annot_font_size(max_dim)}

    # Draw heatmap
    sns.heatmap(
        matrix,
        ax=ax,
        mask=mask,
        annot=annotate,
        fmt=fmt,
        annot_kws=annot_kws,
        cmap=colormap,
        linewidths=0.5,
        linecolor=BG_COLOR,
        square=True,
        xticklabels=col_labels,
        yticklabels=row_labels,
        cbar_kws={"shrink": 0.8, "pad": 0.02},
    )

    # Style the colorbar
    cbar = ax.collections[0].colorbar
    if cbar is not None:
        cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        cbar.outline.set_edgecolor(MUTED_COLOR)
        cbar.outline.set_linewidth(0.5)

    # Axis label styling
    label_size = _label_font_size(max_dim)

    ax.set_xticklabels(
        ax.get_xticklabels(),
        rotation=45,
        ha="right",
        fontsize=label_size,
        color=TEXT_COLOR,
    )
    ax.set_yticklabels(
        ax.get_yticklabels(),
        rotation=0,
        fontsize=label_size,
        color=TEXT_COLOR,
    )

    ax.tick_params(axis="both", length=0)

    save(fig, output, dpi=dpi)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a heatmap from a JSON matrix on stdin."
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output PNG file path."
    )
    parser.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI, help=f"Output DPI (default: {DEFAULT_DPI})."
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
    row_labels: list[str] = payload.get("row_labels", [])
    col_labels: list[str] = payload.get("col_labels", [])
    raw_matrix: list[list[float]] = payload.get("matrix", [])
    colormap: str = payload.get("colormap", DEFAULT_COLORMAP)
    annotate: bool = payload.get("annotate", True)

    # ---- Validate ---------------------------------------------------------
    if not raw_matrix or not raw_matrix[0]:
        print("Error: empty or missing matrix in input JSON.", file=sys.stderr)
        sys.exit(1)

    matrix = np.array(raw_matrix, dtype=float)
    nrows, ncols = matrix.shape

    # Infer labels if not provided
    if not row_labels:
        row_labels = [str(i) for i in range(nrows)]
    if not col_labels:
        col_labels = [str(i) for i in range(ncols)]

    # Validate dimensions match
    if len(row_labels) != nrows:
        print(
            f"Error: row_labels length ({len(row_labels)}) does not match "
            f"matrix rows ({nrows}).",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(col_labels) != ncols:
        print(
            f"Error: col_labels length ({len(col_labels)}) does not match "
            f"matrix columns ({ncols}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # ---- Render -----------------------------------------------------------
    _render_heatmap(
        matrix=matrix,
        row_labels=row_labels,
        col_labels=col_labels,
        title=title,
        subtitle=subtitle,
        colormap=colormap,
        annotate=annotate,
        dpi=args.dpi,
        output=args.output,
    )


if __name__ == "__main__":
    main()
