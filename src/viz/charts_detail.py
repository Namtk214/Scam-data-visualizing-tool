"""
charts_detail.py — Conversation-level detail charts.
"""
from typing import Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from src.schema import SPAN_COLORS


_TEMPLATE = "plotly_white"


def plot_manipulation_timeline(conv: Dict[str, Any]) -> go.Figure:
    """Manipulation intensity timeline for one conversation."""
    turns = conv.get("turns", [])
    points = []
    for t in turns:
        if t.get("speaker") == "scammer" and t.get("manipulation_intensity") is not None:
            points.append({
                "turn_id": t.get("turn_id"),
                "intensity": t["manipulation_intensity"],
                "phase": t.get("phase", ""),
            })
    if not points:
        return _empty_fig("No manipulation intensity data")
    df = pd.DataFrame(points)
    fig = px.line(df, x="turn_id", y="intensity", markers=True,
                  title="Manipulation Intensity Timeline",
                  labels={"turn_id": "Turn", "intensity": "Intensity (1-5)"},
                  color_discrete_sequence=["#ef4444"], template=_TEMPLATE)
    fig.update_layout(yaxis=dict(range=[0, 5.5]))
    return fig


def plot_turn_phase_strip(conv: Dict[str, Any]) -> go.Figure:
    """Horizontal strip showing phase per turn."""
    turns = conv.get("turns", [])
    data = []
    phase_colors = {
        "P1": "#6366f1", "P2": "#3b82f6", "P3": "#f59e0b",
        "P4": "#f97316", "P5": "#ef4444", "P6": "#8b5cf6",
    }
    for t in turns:
        data.append({
            "turn_id": t.get("turn_id"),
            "speaker": t.get("speaker", ""),
            "phase": t.get("phase", "?"),
        })
    if not data:
        return _empty_fig()
    df = pd.DataFrame(data)
    fig = px.scatter(df, x="turn_id", y="speaker",
                     color="phase", color_discrete_map=phase_colors,
                     title="Turn Phase Strip",
                     template=_TEMPLATE, size_max=16)
    fig.update_traces(marker=dict(size=14, symbol="square"))
    return fig


def plot_ds_radar_single(sub_scores: Dict[str, float]) -> go.Figure:
    cats = list(sub_scores.keys())
    vals = [sub_scores[k] for k in cats]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        name="DS Sub-scores",
        line_color="#8b5cf6",
        fillcolor="rgba(139,92,246,0.15)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max(0.3, max(vals or [0.1]))])),
        title="DS Sub-score Radar",
        template=_TEMPLATE,
    )
    return fig


def _empty_fig(msg: str = "Không đủ dữ liệu") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#999"))
    fig.update_layout(template=_TEMPLATE, height=200)
    return fig
