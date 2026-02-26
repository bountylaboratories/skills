# BountyLab Visualization Scripts

Python scripts for generating publication-quality charts from BountyLab data. Each script reads JSON from stdin and outputs a PNG.

## Installation

```bash
pip install matplotlib numpy networkx seaborn scipy adjustText
# or with UV:
uv pip install matplotlib numpy networkx seaborn scipy adjustText
```

In the recruiter bot container, these are pre-installed in `/home/claude/.venv`.

## Usage

```bash
echo '{"title": "...", ...}' | python3 <script>.py -o output.png
```

All scripts accept:
- `-o` / `--output` (required): output PNG path
- `--dpi` (optional, default 150): output resolution

## Scripts

| Script | Purpose | Input Shape |
|--------|---------|-------------|
| `sankey.py` | Talent flow between companies | `{flows: [{source, target, value}]}` |
| `distribution.py` | Multi-panel bar/pie/histogram | `{panels: [{name, type, data}]}` |
| `network.py` | Network graphs | `{nodes: [...], edges: [...]}` |
| `scatter.py` | Labeled scatter plots | `{points: [{x, y, label, group?}]}` |
| `radar.py` | Radar/spider charts | `{axes: [...], series: [{name, values}]}` |
| `heatmap.py` | Heatmaps and matrices | `{row_labels, col_labels, matrix}` |

## Shared Theme

`_theme.py` provides consistent styling across all scripts:
- DevRank tier colors (`TIER_COLORS`)
- 10-color categorical palette (`PALETTE`)
- Figure setup helpers (`setup_figure`, `setup_multi`)
- Axis styling (`style_ax`)
- Save helper (`save`)
