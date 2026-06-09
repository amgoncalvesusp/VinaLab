# -*- coding: utf-8 -*-
"""Interactive Plotly charts for the results tab.

Plotly figures are rendered to a self-contained HTML file (Plotly.js inlined, no
internet needed) and shown in a QWebEngineView, so hovering a point reveals the
molecule name. Kept separate from results_tab so the charting can fail soft: when
Plotly or QtWebEngine is unavailable the tab falls back to the matplotlib canvas.
"""

from __future__ import annotations

from pathlib import Path
import tempfile


def plotly_available() -> bool:
    """Return True when Plotly can be imported."""
    try:
        import plotly.graph_objects  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means no Plotly charts
        return False
    return True


def _write_html(fig, prefix: str) -> Path:
    """Write a Plotly figure to a temp self-contained HTML file and return its path."""
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", prefix=prefix, delete=False, encoding="utf-8"
    )
    try:
        fig.write_html(handle, include_plotlyjs="inline", full_html=True)
    finally:
        handle.close()
    return Path(handle.name)


def affinity_chart_html(rows: list[dict], y_label: str, title: str) -> Path:
    """Build an interactive affinity scatter; hover shows the molecule name.

    x = pose index, y = docking affinity, one marker per pose. Hover text carries
    the ligand name, scoring function and pose number.
    """
    import plotly.graph_objects as go

    xs = list(range(len(rows)))
    ys = [float(row.get("affinity", 0.0)) for row in rows]
    hover = [
        f"{row.get('ligand_name', '')}<br>"
        f"{row.get('scoring_function', row.get('scoring_key', ''))}<br>"
        f"pose {int(row.get('pose_rank', row.get('mode', 0)))}<br>"
        f"{y_label}: {float(row.get('affinity', 0.0)):.3f}"
        for row in rows
    ]
    figure = go.Figure(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker={
                "size": 10,
                "color": ys,
                "colorscale": "Viridis",
                "showscale": False,
            },
            hovertext=hover,
            hoverinfo="text",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="pose",
        yaxis_title=y_label,
        margin={"l": 60, "r": 20, "t": 50, "b": 50},
        template="plotly_white",
    )
    return _write_html(figure, "vinalab_affinity_")


def cluster_chart_html(clusters: list[dict], size_label: str) -> Path:
    """Build an interactive cluster-size bar chart; hover shows ligand and cluster."""
    import plotly.graph_objects as go

    labels = [f"{c.get('ligand', '')} C{c.get('cluster_id', '')}" for c in clusters]
    sizes = [int(c.get("size", 0)) for c in clusters]
    hover = [
        f"{c.get('ligand', '')}<br>cluster {c.get('cluster_id', '')}<br>"
        f"{size_label}: {int(c.get('size', 0))}<br>"
        f"best score: {float(c.get('best_score', 0.0)):.3f}"
        for c in clusters
    ]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=sizes,
            hovertext=hover,
            hoverinfo="text",
            marker_color="#4f7cac",
        )
    )
    figure.update_layout(
        yaxis_title=size_label,
        margin={"l": 60, "r": 20, "t": 30, "b": 80},
        template="plotly_white",
    )
    return _write_html(figure, "vinalab_clusters_")
