"""
visualize.py — Tất cả hàm vẽ chart bằng Plotly.
Mỗi hàm nhận DataFrame đã chuẩn hóa, trả về plotly Figure.
"""
from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.schema import OUTCOME_COLORS, SCENARIO_GROUP_DESC


def plot_outcome_distribution(df_conv: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối outcome."""
    counts = df_conv["outcome"].value_counts().reset_index()
    counts.columns = ["outcome", "count"]
    fig = px.bar(
        counts, x="outcome", y="count",
        color="outcome",
        color_discrete_map=OUTCOME_COLORS,
        title="Outcome Distribution",
        labels={"outcome": "Outcome", "count": "Count"},
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_scenario_distribution(df_conv: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối scenario_group và scenario_name."""
    if df_conv["scenario_group"].nunique() == 0:
        return _empty_fig("No scenario data")

    # Scenario group
    grp = df_conv["scenario_group"].value_counts().reset_index()
    grp.columns = ["group", "count"]
    grp["label"] = grp["group"].map(
        lambda x: f"{x}: {SCENARIO_GROUP_DESC.get(x, '')}"
    )
    fig = px.bar(
        grp, x="group", y="count",
        text="count",
        title="Scenario Group Distribution",
        labels={"group": "Scenario Group", "count": "Count"},
        color="group",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_scenario_name_distribution(df_conv: pd.DataFrame, top_k: int = 15) -> go.Figure:
    """Bar chart scenario_name (top-k)."""
    counts = df_conv["scenario_name"].value_counts().head(top_k).reset_index()
    counts.columns = ["scenario_name", "count"]
    fig = px.bar(
        counts, x="count", y="scenario_name",
        orientation="h",
        text="count",
        title=f"Scenario Name Distribution (Top {top_k})",
        labels={"scenario_name": "Scenario", "count": "Count"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig


def plot_conversation_length_hist(df_conv: pd.DataFrame) -> go.Figure:
    """Histogram số turn mỗi conversation."""
    fig = px.histogram(
        df_conv, x="n_turns",
        nbins=20,
        title="Conversation Length Distribution (# Turns)",
        labels={"n_turns": "Number of Turns", "count": "Conversations"},
        color_discrete_sequence=["#3498db"],
    )
    fig.update_layout(yaxis_title="Count")
    return fig


def plot_token_count_hist(df_conv: pd.DataFrame) -> go.Figure:
    """Histogram số token mỗi conversation."""
    fig = px.histogram(
        df_conv, x="n_tokens",
        nbins=20,
        title="Token Count Distribution per Conversation",
        labels={"n_tokens": "Token Count", "count": "Conversations"},
        color_discrete_sequence=["#9b59b6"],
    )
    fig.update_layout(yaxis_title="Count")
    return fig


def plot_speaker_turn_counts(df_turn: pd.DataFrame) -> go.Figure:
    """Bar chart scammer vs victim turn counts."""
    counts = df_turn["speaker"].value_counts().reset_index()
    counts.columns = ["speaker", "count"]
    color_map = {"scammer": "#e74c3c", "victim": "#3498db"}
    fig = px.bar(
        counts, x="speaker", y="count",
        color="speaker",
        color_discrete_map=color_map,
        text="count",
        title="Turn Count by Speaker",
        labels={"speaker": "Speaker", "count": "Turn Count"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_ambiguity_distribution(df_conv: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối ambiguity level."""
    counts = df_conv["ambiguity_level"].value_counts().reset_index()
    counts.columns = ["level", "count"]
    counts = counts.sort_values("level")
    fig = px.bar(
        counts, x="level", y="count",
        text="count",
        title="Ambiguity Level Distribution",
        labels={"level": "Ambiguity Level", "count": "Count"},
        color="level",
        color_discrete_sequence=px.colors.sequential.Oranges,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_phase_transition_heatmap(df_turn: pd.DataFrame) -> go.Figure:
    """Heatmap ma trận chuyển phase."""
    from src.stats import compute_phase_transitions
    matrix = compute_phase_transitions(df_turn)
    if matrix.empty:
        return _empty_fig("No phase transition data")

    fig = px.imshow(
        matrix,
        text_auto=True,
        title="Phase Transition Matrix",
        labels={"x": "To Phase", "y": "From Phase", "color": "Count"},
        color_continuous_scale="Blues",
        aspect="auto",
    )
    return fig


def plot_tactic_phase_heatmap(df_turn: pd.DataFrame) -> go.Figure:
    """Heatmap Tactic (SSAT) x Phase."""
    from src.stats import compute_tactic_phase_matrix
    matrix = compute_tactic_phase_matrix(df_turn)
    if matrix.empty:
        return _empty_fig("No tactic-phase data")

    fig = px.imshow(
        matrix,
        text_auto=True,
        title="Tactic × Phase Heatmap (SSAT)",
        labels={"x": "SSAT Label", "y": "Phase", "color": "Count"},
        color_continuous_scale="Reds",
        aspect="auto",
    )
    return fig


def plot_vcs_transition_heatmap(df_turn: pd.DataFrame) -> go.Figure:
    """Heatmap chuyển trạng thái VCS."""
    from src.stats import compute_vcs_transitions
    matrix = compute_vcs_transitions(df_turn)
    if matrix.empty:
        return _empty_fig("No VCS transition data")

    fig = px.imshow(
        matrix,
        text_auto=True,
        title="Victim State Transition Heatmap (VCS)",
        labels={"x": "To VCS", "y": "From VCS", "color": "Count"},
        color_continuous_scale="Purples",
        aspect="auto",
    )
    return fig


def plot_ssat_cooccurrence(df_turn: pd.DataFrame) -> go.Figure:
    """Heatmap SSAT co-occurrence."""
    from src.stats import compute_ssat_cooccurrence
    matrix = compute_ssat_cooccurrence(df_turn)
    if matrix.empty:
        return _empty_fig("No SSAT co-occurrence data")

    fig = px.imshow(
        matrix,
        text_auto=True,
        title="SSAT Co-occurrence Heatmap",
        labels={"x": "SSAT Label", "y": "SSAT Label", "color": "Co-occurrence"},
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    return fig


def plot_ssat_distribution(df_turn: pd.DataFrame) -> go.Figure:
    """Bar chart tần suất SSAT labels."""
    scammer = df_turn[df_turn["speaker"] == "scammer"]
    counter: dict = {}
    for ssat_list in scammer["ssat"]:
        if isinstance(ssat_list, list):
            for s in ssat_list:
                counter[s] = counter.get(s, 0) + 1

    if not counter:
        return _empty_fig("No SSAT data")

    df = pd.DataFrame(list(counter.items()), columns=["label", "count"]).sort_values("count", ascending=False)
    fig = px.bar(
        df, x="label", y="count",
        text="count",
        title="SSAT Label Distribution",
        labels={"label": "SSAT Label", "count": "Count"},
        color="label",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_vrt_distribution(df_turn: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối VRT labels."""
    victim = df_turn[(df_turn["speaker"] == "victim") & (df_turn["vrt"] != "")]
    counts = victim["vrt"].value_counts().reset_index()
    counts.columns = ["label", "count"]
    if counts.empty:
        return _empty_fig("No VRT data")

    fig = px.bar(
        counts, x="label", y="count",
        text="count",
        title="Victim Response Type (VRT) Distribution",
        labels={"label": "VRT Label", "count": "Count"},
        color="label",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_vcs_distribution(df_turn: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối VCS labels."""
    victim = df_turn[(df_turn["speaker"] == "victim") & (df_turn["vcs"] != "")]
    counts = victim["vcs"].value_counts().reset_index()
    counts.columns = ["label", "count"]
    if counts.empty:
        return _empty_fig("No VCS data")

    fig = px.bar(
        counts, x="label", y="count",
        text="count",
        title="Victim Cognitive State (VCS) Distribution",
        labels={"label": "VCS Label", "count": "Count"},
        color="label",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_span_label_distribution(df_span: pd.DataFrame) -> go.Figure:
    """Bar chart phân phối span labels."""
    if df_span.empty:
        return _empty_fig("No span data")

    counts = df_span["span_label"].value_counts().reset_index()
    counts.columns = ["label", "count"]
    fig = px.bar(
        counts, x="label", y="count",
        text="count",
        title="Span Label Distribution",
        labels={"label": "Span Label", "count": "Count"},
        color="label",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig


def plot_scenario_ambiguity_heatmap(df_conv: pd.DataFrame) -> go.Figure:
    """Heatmap scenario_group x ambiguity_level."""
    if df_conv.empty:
        return _empty_fig("No data")

    matrix = df_conv.groupby(["scenario_group", "ambiguity_level"]).size().reset_index(name="count")
    if matrix.empty:
        return _empty_fig("No scenario-ambiguity data")

    pivot = matrix.pivot(index="scenario_group", columns="ambiguity_level", values="count").fillna(0)
    fig = px.imshow(
        pivot,
        text_auto=True,
        title="Scenario Group × Ambiguity Level Heatmap",
        labels={"x": "Ambiguity Level", "y": "Scenario Group", "color": "Count"},
        color_continuous_scale="Greens",
        aspect="auto",
    )
    return fig


def plot_phase_sequence_frequency(df_conv: pd.DataFrame, top_k: int = 10) -> go.Figure:
    """Bar chart top phase sequences phổ biến nhất."""
    counts = df_conv["phase_sequence"].value_counts().head(top_k).reset_index()
    counts.columns = ["sequence", "count"]
    if counts.empty:
        return _empty_fig("No phase sequence data")

    fig = px.bar(
        counts, x="count", y="sequence",
        orientation="h",
        text="count",
        title=f"Top {top_k} Phase Sequences",
        labels={"sequence": "Phase Sequence", "count": "Count"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig


def plot_sankey_scenario_outcome(df_conv: pd.DataFrame) -> go.Figure:
    """Sankey chart: scenario_group → outcome."""
    if df_conv.empty:
        return _empty_fig("No data")

    groups = sorted(df_conv["scenario_group"].dropna().unique().tolist())
    outcomes = sorted(df_conv["outcome"].dropna().unique().tolist())

    nodes = groups + outcomes
    node_idx = {n: i for i, n in enumerate(nodes)}

    source, target, value = [], [], []
    for _, row in df_conv.iterrows():
        sg = row["scenario_group"]
        oc = row["outcome"]
        if sg and oc:
            source.append(node_idx.get(sg, 0))
            target.append(node_idx.get(oc, len(groups)))
            value.append(1)

    if not source:
        return _empty_fig("No sankey data")

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, pad=15, thickness=20),
        link=dict(source=source, target=target, value=value),
    ))
    fig.update_layout(title="Scenario Group → Outcome (Sankey)")
    return fig


def plot_prefix_evidence_curve(df_prefix: pd.DataFrame) -> go.Figure:
    """Line chart prefix evidence: trung bình tín hiệu scam theo % turn."""
    if df_prefix.empty:
        return _empty_fig("No prefix data")

    agg = df_prefix.groupby(["outcome", "prefix_pct"])["n_signals"].mean().reset_index()
    fig = px.line(
        agg, x="prefix_pct", y="n_signals",
        color="outcome",
        markers=True,
        color_discrete_map=OUTCOME_COLORS,
        title="Prefix Evidence Curve (Avg Scam Signals vs Turn Prefix %)",
        labels={"prefix_pct": "Prefix % of Turns", "n_signals": "Avg # Scam Signals"},
    )
    fig.update_xaxes(tickformat=".0%")
    return fig


def _empty_fig(message: str) -> go.Figure:
    """Trả về figure trống với message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray"),
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig
