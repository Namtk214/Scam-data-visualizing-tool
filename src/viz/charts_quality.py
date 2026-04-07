"""
charts_quality.py — 25 benchmark visualizations cho 9 quality metrics.
Mỗi biểu đồ có title + subtitle mô tả ý nghĩa và cách đọc kết quả.
Graceful degradation: nếu thiếu field, trả về empty figure với giải thích.
"""
from typing import Dict, Any, List, Optional
from collections import Counter
import math

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from src.schema import (
    SSAT_COLORS, VCS_COLORS, DOMAIN_COLORS, OUTCOME_COLORS, SPAN_COLORS,
    PHASE_DESC, SPAN_COLORS, ALL_SPAN_TAGS, get_turn_span_tags,
)


# ─────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────
_TEMPLATE = "plotly_white"
_TITLE_FONT = dict(size=13)
_SUB_COLOR = "#6b7280"


def _title(main: str, sub: str) -> str:
    return f"{main}<br><sup style='color:{_SUB_COLOR};font-size:10px'>{sub}</sup>"


def _hex_rgba(hex_color: str, alpha: float = 0.5) -> str:
    """Convert '#rrggbb' + alpha float → 'rgba(r,g,b,a)' for Plotly compatibility."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return hex_color  # fallback


def _empty_fig(msg: str = "Không đủ dữ liệu") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False,
                       font=dict(size=12, color="#999"), xref="paper", yref="paper")
    fig.update_layout(template=_TEMPLATE, height=220,
                      margin=dict(l=20, r=20, t=40, b=20))
    return fig


def _base_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=40, r=20, t=65, b=40),
        title_font=_TITLE_FONT,
        font=dict(size=11),
        legend=dict(font=dict(size=10)),
        template=_TEMPLATE,
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# AI — 6 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_ai_badge(ai_report: Dict) -> go.Figure:
    """#1 — Indicator badge: mean AI score có trong target range không."""
    mean_score = ai_report.get("mean_score", 0.0)
    in_range = 0.30 <= mean_score <= 0.55
    color = "#22c55e" if in_range else "#ef4444"
    status_text = "IN TARGET" if in_range else "OUT OF TARGET"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(mean_score, 3),
        delta={"reference": 0.425, "valueformat": ".3f"},
        title={
            "text": _title(
                "AI Score Badge — Mean Ambiguity Index",
                "Target range: 0.30–0.55. Xanh = dataset đạt chuẩn nhập nhằng. "
                "Đỏ = cần thêm kịch bản hoặc review annotation."
            ),
            "font": {"size": 12},
        },
        gauge={
            "axis": {"range": [0, 1], "tickwidth": 1},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 0.30], "color": "#fef9c3"},
                {"range": [0.30, 0.55], "color": "#dcfce7"},
                {"range": [0.55, 1.0], "color": "#fee2e2"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": mean_score,
            },
        },
        number={"font": {"color": color, "size": 28}, "suffix": f"  {status_text}"},
    ))
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=80, b=20),
                      template=_TEMPLATE, font=dict(size=11))
    return fig


def plot_ai_intensity_flow(convs: List[Dict], conv_id: Optional[str] = None) -> go.Figure:
    """#2 — Line chart: manipulation_intensity per turn theo conversation."""
    if conv_id:
        target = next((c for c in convs if c.get("conversation_id") == conv_id), None)
        if not target:
            return _empty_fig(f"Không tìm thấy conversation: {conv_id}")
        scammer_turns = [t for t in target.get("turns", []) if t.get("speaker") == "scammer"]
        intensities = [t.get("manipulation_intensity") for t in scammer_turns]
        if all(v is None for v in intensities):
            return _empty_fig("manipulation_intensity chưa có trong dữ liệu (field mới)")
        y = [v if v is not None else 0 for v in intensities]
        x = list(range(1, len(y) + 1))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=6),
            name=conv_id,
        ))
        fig.add_hline(y=2.5, line_dash="dash", line_color="#f59e0b",
                      annotation_text="Low/High threshold (2.5)", annotation_font_size=9)
        title_text = _title(
            f"Manipulation Intensity Flow — {conv_id}",
            "Cường độ thao túng của scammer theo từng turn. "
            "Giá trị 1–5: 1=nhẹ nhàng, 5=cực kỳ hung hăng. "
            "Thấp toàn bộ → kịch bản tinh vi, khó phát hiện (AI cao)."
        )
    else:
        # Average intensity per turn position across all convs
        from collections import defaultdict
        pos_sums: Dict[int, float] = defaultdict(float)
        pos_counts: Dict[int, int] = defaultdict(int)
        for conv in convs:
            scammer_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "scammer"]
            for i, t in enumerate(scammer_turns):
                v = t.get("manipulation_intensity")
                if v is not None:
                    pos_sums[i] += v
                    pos_counts[i] += 1
        if not pos_counts:
            return _empty_fig("manipulation_intensity chưa có trong dữ liệu (field mới)")
        positions = sorted(pos_counts.keys())
        x = [p + 1 for p in positions]
        y = [round(pos_sums[p] / pos_counts[p], 3) for p in positions]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
            name="Avg intensity",
        ))
        fig.add_hline(y=2.5, line_dash="dash", line_color="#f59e0b",
                      annotation_text="Low/High threshold (2.5)", annotation_font_size=9)
        title_text = _title(
            "Manipulation Intensity Flow — Dataset Average",
            "Cường độ thao túng trung bình của scammer theo vị trí turn. "
            "Dốc lên cuối = leo thang áp lực. Phẳng thấp = kịch bản tinh vi."
        )

    fig.update_layout(
        title=title_text,
        xaxis_title="Turn #",
        yaxis_title="Intensity (1–5)",
        yaxis=dict(range=[0, 5.5]),
    )
    return _base_layout(fig, height=320)


def plot_ai_register_donut(convs: List[Dict]) -> go.Figure:
    """#3 — Donut chart: speaking_register distribution của scammer."""
    register_counts: Counter = Counter()
    for conv in convs:
        for t in conv.get("turns", []):
            if t.get("speaker") != "scammer":
                continue
            reg = (
                (t.get("personas") or {}).get("scammer", {}).get("speaking_register")
                or (conv.get("personas") or {}).get("scammer", {}).get("speaking_register")
                or ""
            )
            if reg:
                register_counts[reg] += 1

    if not register_counts:
        return _empty_fig("speaking_register chưa có trong dữ liệu (field mới)")

    labels = list(register_counts.keys())
    values = list(register_counts.values())
    register_colors = {
        "formal_professional": "#6366f1",
        "authoritative": "#ef4444",
        "semi_formal": "#f59e0b",
        "casual": "#22c55e",
        "intimate": "#ec4899",
    }
    colors = [register_colors.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.45,
        marker_colors=colors,
        textinfo="percent+label",
        textfont_size=10,
    ))
    fig.update_layout(
        title=_title(
            "Register Mix — Phong Cách Nói Chuyện Scammer",
            "Phân bổ register trong các turn của scammer. "
            "formal_professional + authoritative nhiều = kịch bản tinh vi, đáng tin cậy hơn → AI score cao. "
            "casual = kịch bản trực tiếp, dễ nhận ra."
        ),
    )
    return _base_layout(fig, height=340)


def plot_ai_confusion_bubble(per_conv: List[Dict], convs: List[Dict]) -> go.Figure:
    """#4 — Bubble chart: confusion density per conversation."""
    conv_map = {c.get("conversation_id"): c for c in convs}
    data = []
    for i, r in enumerate(per_conv):
        cid = r.get("conversation_id", f"conv_{i}")
        conv = conv_map.get(cid, {})
        victim_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "victim"]
        # "Confusion density" = proportion of victim turns adjacent to a THREAT/URGENT span
        scammer_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "scammer"]
        threat_turns = sum(
            1 for t in scammer_turns
            if any(sp.get("tag") in {"THREAT_PHRASE", "URGENT_CLAIM"}
                   for sp in (t.get("span_annotations") or []))
        )
        total_scammer = len(scammer_turns) or 1
        data.append({
            "id": cid,
            "confusion_count": threat_turns,
            "confusion_density": round(threat_turns / total_scammer, 3),
            "ai_score": r.get("ambiguity_score", 0),
            "label": r.get("ambiguity_level", ""),
        })

    if not data:
        return _empty_fig()

    df = pd.DataFrame(data)
    level_color = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}
    df["color"] = df["label"].map(level_color).fillna("#94a3b8")

    fig = go.Figure()
    for level, grp in df.groupby("label"):
        fig.add_trace(go.Scatter(
            x=grp.index.tolist(),
            y=grp["confusion_density"].tolist(),
            mode="markers",
            marker=dict(
                size=grp["ai_score"] * 40 + 5,
                color=level_color.get(level, "#94a3b8"),
                opacity=0.65,
                line=dict(width=1, color="white"),
            ),
            name=level,
            text=grp["id"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Confusion density: %{y:.3f}<br>"
                "AI score: %{marker.size:.0f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        title=_title(
            "Confusion Density Bubble — Mật Độ Bối Rối Nạn Nhân",
            "Trục Y = tỷ lệ turns scammer có THREAT_PHRASE/URGENT_CLAIM. Kích thước bong bóng = AI score. "
            "Bong bóng to + đỏ = conversation áp lực cao với nhiều span đe dọa/gấp."
        ),
        xaxis_title="Conversation #",
        yaxis_title="Confusion Density",
        yaxis=dict(range=[-0.05, 1.1]),
    )
    return _base_layout(fig, height=340)


def plot_ai_attack_deflect(convs: List[Dict]) -> go.Figure:
    """#5 — Sankey: THREAT_PHRASE/URGENT_CLAIM → DEFLECT_BLAME span flow."""
    source_deflect = {"THREAT_PHRASE": 0, "URGENT_CLAIM": 0}
    for conv in convs:
        has_deflect = any(
            any(sp.get("tag") == "DEFLECT_BLAME"
                for sp in (t.get("span_annotations") or []))
            for t in conv.get("turns", [])
            if t.get("speaker") == "scammer"
        )
        if has_deflect:
            for t in conv.get("turns", []):
                if t.get("speaker") != "scammer":
                    continue
                tags = {sp.get("tag", "") for sp in (t.get("span_annotations") or [])}
                if "THREAT_PHRASE" in tags and "DEFLECT_BLAME" in tags:
                    source_deflect["THREAT_PHRASE"] += 1
                if "URGENT_CLAIM" in tags and "DEFLECT_BLAME" in tags:
                    source_deflect["URGENT_CLAIM"] += 1

    pure_threat = sum(
        1 for conv in convs for t in conv.get("turns", [])
        if t.get("speaker") == "scammer"
        and any(sp.get("tag") == "THREAT_PHRASE" for sp in (t.get("span_annotations") or []))
        and not any(sp.get("tag") == "DEFLECT_BLAME" for sp in (t.get("span_annotations") or []))
    )
    pure_urgency = sum(
        1 for conv in convs for t in conv.get("turns", [])
        if t.get("speaker") == "scammer"
        and any(sp.get("tag") == "URGENT_CLAIM" for sp in (t.get("span_annotations") or []))
        and not any(sp.get("tag") == "DEFLECT_BLAME" for sp in (t.get("span_annotations") or []))
    )
    deflect_only = sum(
        1 for conv in convs for t in conv.get("turns", [])
        if t.get("speaker") == "scammer"
        and any(sp.get("tag") == "DEFLECT_BLAME" for sp in (t.get("span_annotations") or []))
        and not any(sp.get("tag") in {"THREAT_PHRASE", "URGENT_CLAIM"}
                    for sp in (t.get("span_annotations") or []))
    )

    total_links = sum(source_deflect.values()) + pure_threat + pure_urgency
    if total_links == 0:
        return _empty_fig("Không có span THREAT_PHRASE / URGENT_CLAIM / DEFLECT_BLAME trong dữ liệu")

    node_labels = ["THREAT_PHRASE", "URGENT_CLAIM", "DEFLECT_BLAME", "Không deflect"]
    node_colors = ["#c0392b", "#e67e22", "#7f8c8d", "#27ae60"]

    links = {"source": [], "target": [], "value": [], "color": []}

    def _add(src, tgt, val, col):
        if val > 0:
            links["source"].append(src)
            links["target"].append(tgt)
            links["value"].append(val)
            links["color"].append(col)

    _add(0, 2, source_deflect["THREAT_PHRASE"], "rgba(192,57,43,0.4)")
    _add(1, 2, source_deflect["URGENT_CLAIM"], "rgba(230,126,36,0.4)")
    _add(0, 3, pure_threat, "rgba(39,174,96,0.3)")
    _add(1, 3, pure_urgency, "rgba(39,174,96,0.3)")

    fig = go.Figure(go.Sankey(
        node=dict(label=node_labels, color=node_colors, pad=20, thickness=20),
        link=dict(
            source=links["source"],
            target=links["target"],
            value=links["value"],
            color=links["color"],
        ),
    ))
    fig.update_layout(
        title=_title(
            "Attack → Deflect Span Flow Map",
            "Luồng từ span tấn công (THREAT_PHRASE / URGENT_CLAIM) sang phòng thủ (DEFLECT_BLAME). "
            "Luồng lớn vào DEFLECT_BLAME = scammer chuyển hướng nhiều → kịch bản nhập nhằng cao."
        ),
    )
    return _base_layout(fig, height=340)


def plot_ai_outcome_pie(per_conv: List[Dict], convs: List[Dict]) -> go.Figure:
    """#6 — Pie chart: outcome distribution weighted by ambiguity score."""
    conv_map = {c.get("conversation_id"): c for c in convs}
    outcome_weight: Counter = Counter()
    outcome_count: Counter = Counter()

    for r in per_conv:
        cid = r.get("conversation_id", "")
        conv = conv_map.get(cid, {})
        outcome = conv.get("conversation_meta", {}).get("outcome", "UNKNOWN")
        ai = r.get("ambiguity_score", 0.0)
        outcome_weight[outcome] += ai
        outcome_count[outcome] += 1

    if not outcome_count:
        return _empty_fig("Không có dữ liệu outcome")

    labels = list(outcome_count.keys())
    weights = [outcome_weight[l] for l in labels]
    counts = [outcome_count[l] for l in labels]
    colors = [OUTCOME_COLORS.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=weights,
        customdata=counts,
        marker_colors=colors,
        textinfo="percent+label",
        textfont_size=10,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Tổng AI weight: %{value:.3f}<br>"
            "Số conversations: %{customdata}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=_title(
            "Outcome × Ambiguity Weight Pie",
            "Tỷ lệ diện tích = tổng AI score tích lũy theo outcome. "
            "PARTIAL_COMPLIANCE chiếm nhiều → kịch bản nhập nhằng phần lớn kết thúc không rõ ràng."
        ),
    )
    return _base_layout(fig, height=340)


# ─────────────────────────────────────────────────────────────────
# DS — 6 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_ds_ai_scatter(ai_per: List[Dict], ds_per: List[Dict]) -> go.Figure:
    """#7 — Scatter: AI vs DS per conversation (refactor)."""
    ai_map = {r["conversation_id"]: r["ambiguity_score"] for r in ai_per if "conversation_id" in r}
    ds_map = {r["conversation_id"]: r["difficulty_score"] for r in ds_per if "conversation_id" in r}
    tier_map = {r["conversation_id"]: r.get("difficulty_tier", "") for r in ds_per if "conversation_id" in r}
    shared = sorted(set(ai_map) & set(ds_map))
    if not shared:
        return _empty_fig("Không có conversation khớp giữa AI và DS")

    df = pd.DataFrame([{
        "AI": ai_map[cid],
        "DS": ds_map[cid],
        "tier": tier_map.get(cid, ""),
        "id": cid,
    } for cid in shared])

    tier_colors = {"easy": "#22c55e", "medium": "#3b82f6", "hard": "#f59e0b", "expert": "#ef4444"}

    fig = go.Figure()
    for tier, grp in df.groupby("tier"):
        fig.add_trace(go.Scatter(
            x=grp["AI"].tolist(), y=grp["DS"].tolist(),
            mode="markers",
            marker=dict(color=tier_colors.get(tier, "#94a3b8"), size=8, opacity=0.75),
            name=tier,
            text=grp["id"].tolist(),
            hovertemplate="<b>%{text}</b><br>AI=%{x:.3f}, DS=%{y:.3f}<extra></extra>",
        ))
    fig.add_shape(type="rect", x0=0.3, x1=0.55, y0=0.45, y1=0.70,
                  line=dict(dash="dash", color="#22c55e"),
                  fillcolor="rgba(34,197,94,0.07)")
    fig.add_annotation(x=0.425, y=0.575, text="Sweet Spot",
                       showarrow=False, font=dict(size=9, color="#16a34a"))
    fig.update_layout(
        title=_title(
            "AI vs DS Scatter — Tương Quan Nhập Nhằng / Khó",
            "Mỗi điểm = 1 conversation, màu theo tier khó. "
            "Vùng xanh = Sweet Spot lý tưởng (AI 0.30–0.55, DS 0.45–0.70). "
            "Ngoài vùng = cần review."
        ),
        xaxis_title="Ambiguity Index (AI)",
        yaxis_title="Difficulty Score (DS)",
    )
    return _base_layout(fig, height=360)


def plot_ds_tactic_bar(convs: List[Dict]) -> go.Figure:
    """#8 — Grouped bar: span tag count per conversation (top 15 convs by span diversity)."""
    rows = []
    for conv in convs:
        cid = conv.get("conversation_id", "")
        tag_counts: Counter = Counter()
        for t in conv.get("turns", []):
            if t.get("speaker") == "scammer":
                for sp in (t.get("span_annotations") or []):
                    tag = sp.get("tag", "")
                    if tag:
                        tag_counts[tag] += 1
        if tag_counts:
            for tag, cnt in tag_counts.items():
                rows.append({"conv": cid, "tactic": tag, "count": cnt})

    if not rows:
        return _empty_fig("Không có span annotations trong dữ liệu")

    df = pd.DataFrame(rows)
    top_convs = (
        df.groupby("conv")["count"].sum()
        .nlargest(15).index.tolist()
    )
    df_top = df[df["conv"].isin(top_convs)].copy()
    df_top["conv_short"] = df_top["conv"].apply(lambda x: x[-12:] if len(x) > 12 else x)

    colors_map = {t: SPAN_COLORS.get(t, "#94a3b8") for t in df_top["tactic"].unique()}
    fig = px.bar(
        df_top, x="conv_short", y="count", color="tactic",
        color_discrete_map=colors_map,
        barmode="group",
        title=_title(
            "Span Tag Distribution per Conversation (Top 15)",
            "Số spans của từng span tag trong 15 conversations nhiều span nhất. "
            "Phân bổ đều giữa các tag = scammer linh hoạt = DS cao hơn."
        ),
        labels={"conv_short": "Conversation", "count": "Số spans", "tactic": "Span Tag"},
    )
    fig.update_layout(xaxis_tickangle=-30, xaxis_tickfont_size=8, legend_font_size=9)
    return _base_layout(fig, height=380)


def plot_ds_phase_progress(pcs_report: Dict) -> go.Figure:
    """#9 — Horizontal progress gauge: phase completion ratio per phase."""
    ratio = pcs_report.get("phase_coverage_ratio", {})
    if not ratio:
        return _empty_fig("Không có dữ liệu phase coverage")

    phases = list(ratio.keys())
    vals = [ratio[p] * 100 for p in phases]
    phase_labels = [f"{p} — {PHASE_DESC.get(p, p)}" for p in phases]

    colors = []
    for v in vals:
        if v >= 80:
            colors.append("#22c55e")
        elif v >= 40:
            colors.append("#f59e0b")
        else:
            colors.append("#ef4444")

    fig = go.Figure()
    for i, (phase, val, color, label) in enumerate(zip(phases, vals, colors, phase_labels)):
        fig.add_trace(go.Bar(
            x=[val], y=[label],
            orientation="h",
            marker_color=color,
            text=[f"{val:.0f}%"],
            textposition="inside",
            textfont=dict(size=10, color="white"),
            showlegend=False,
            name=phase,
        ))
        # Background bar (100%)
        fig.add_trace(go.Bar(
            x=[100 - val], y=[label],
            orientation="h",
            marker_color="#f1f5f9",
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=_title(
            "Phase Completion Progress",
            "% conversations có ít nhất 1 turn ở mỗi phase. "
            "🟢 ≥80% hoàn chỉnh | 🟡 40–80% cần bổ sung | 🔴 <40% thiếu nghiêm trọng. "
            "P5 (Compliance Extract) tối thiểu 40%."
        ),
        barmode="stack",
        xaxis=dict(range=[0, 100], title="%", ticksuffix="%"),
        yaxis=dict(tickfont=dict(size=9)),
    )
    return _base_layout(fig, height=320)


def plot_ds_ttr_histogram(convs: List[Dict]) -> go.Figure:
    """#10 — Histogram: TTR distribution của scammer text per conversation."""
    ttr_values = []
    for conv in convs:
        scammer_text = " ".join(
            t.get("text", "") for t in conv.get("turns", [])
            if t.get("speaker") == "scammer"
        ).lower()
        tokens = scammer_text.split()
        if tokens:
            ttr = round(len(set(tokens)) / len(tokens), 4)
            ttr_values.append(ttr)

    if not ttr_values:
        return _empty_fig("Không có text của scammer")

    fig = px.histogram(
        x=ttr_values, nbins=25,
        title=_title(
            "TTR Distribution — Đa Dạng Từ Vựng Scammer",
            "Type-Token Ratio của scammer text trong từng conversation. "
            "TTR cao = từ vựng phong phú = khó nhận diện pattern. "
            "TTR thấp (<0.30) = lặp từ nhiều, dễ phát hiện."
        ),
        labels={"x": "TTR (Type-Token Ratio)", "y": "Số conversations"},
        color_discrete_sequence=["#f59e0b"],
    )
    fig.add_vline(x=0.30, line_dash="dash", line_color="#ef4444",
                  annotation_text="Min 0.30", annotation_font_size=9)
    fig.add_vline(x=0.50, line_dash="dot", line_color="#22c55e",
                  annotation_text="Good ≥0.50", annotation_font_size=9)
    return _base_layout(fig, height=320)


def plot_ds_state_transition(vsvs_report: Dict) -> go.Figure:
    """#11 — Sankey: Span tag transitions between consecutive scammer turns."""
    trans_matrix = vsvs_report.get("transition_matrix", {})

    # trans_matrix keys: "TAG_A,TAG_B" (sorted, comma-joined tag-sets)
    # Explode tag-sets into individual tag → tag transitions
    transitions: Dict[str, Dict[str, int]] = {}
    for fr_str, tos in trans_matrix.items():
        fr_tags = [t.strip() for t in fr_str.split(",") if t.strip() and t.strip() != "(none)"]
        for to_str, cnt in tos.items():
            to_tags = [t.strip() for t in to_str.split(",") if t.strip() and t.strip() != "(none)"]
            if not fr_tags or not to_tags:
                continue
            for fr in fr_tags:
                for to in to_tags:
                    transitions.setdefault(fr, {})
                    transitions[fr][to] = transitions[fr].get(to, 0) + cnt

    if not transitions:
        return _empty_fig(
            "Chưa có transition data — VSVS chưa ghi nhận span tag sequence.\n"
            "Hãy đảm bảo conversations có đủ ≥2 scammer turns với span_annotations."
        )

    # ── Node & color setup ────────────────────────────────────────
    # Vivid distinct palette per span tag
    _TAG_PALETTE = {
        "FAKE_ORG":        "#6366f1",   # indigo
        "FAKE_ID":         "#8b5cf6",   # violet
        "FAKE_VALIDATION": "#a855f7",   # purple
        "REQUEST_INFO":    "#ef4444",   # red
        "URGENT_CLAIM":    "#f97316",   # orange
        "THREAT_PHRASE":   "#dc2626",   # dark-red
        "SOCIAL_PROOF":    "#22c55e",   # green
        "DEFLECT_BLAME":   "#14b8a6",   # teal
        "GROOMING":        "#ec4899",   # pink
        "ISOLATION":       "#f59e0b",   # amber
        "AUTHORITY_CUE":   "#3b82f6",   # blue
        "SCARCITY":        "#84cc16",   # lime
    }
    fallback_colors = [
        "#6366f1", "#ef4444", "#f97316", "#22c55e",
        "#8b5cf6", "#14b8a6", "#ec4899", "#3b82f6",
        "#f59e0b", "#a855f7", "#dc2626", "#84cc16",
    ]

    all_tags = sorted(set(
        list(transitions.keys()) + [k for v in transitions.values() for k in v]
    ))
    if not all_tags:
        return _empty_fig("Không có span tags để hiển thị")

    tag_idx = {t: i for i, t in enumerate(all_tags)}
    node_colors = [
        _TAG_PALETTE.get(t, fallback_colors[i % len(fallback_colors)])
        for i, t in enumerate(all_tags)
    ]

    sources, targets, values, link_colors = [], [], [], []
    for fr, tos in transitions.items():
        fr_color = _TAG_PALETTE.get(fr, "#94a3b8")
        for to, cnt in tos.items():
            if cnt > 0:
                sources.append(tag_idx[fr])
                targets.append(tag_idx[to])
                values.append(cnt)
                link_colors.append(_hex_rgba(fr_color, 0.55))

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=all_tags,
            color=node_colors,
            pad=20,
            thickness=22,
            line=dict(color="white", width=1.5),
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
        ),
        textfont=dict(
            family="Inter, Arial, sans-serif",
            size=13,
            color="#1e293b",
        ),
    ))
    fig.update_layout(
        title=_title(
            "Span Tag Transition Sankey",
            "Luồng chuyển đổi span tags giữa các scammer turns liên tiếp. "
            "Luồng rộng = transition phổ biến. "
            "FAKE_ORG → REQUEST_INFO = setup danh tính trước khi yêu cầu thông tin (điển hình).",
        ),
        font=dict(family="Inter, Arial, sans-serif", size=12, color="#1e293b"),
        paper_bgcolor="white",
    )
    return _base_layout(fig, height=420)


def plot_ds_adaptability_timeline(conv: Dict) -> go.Figure:
    """#12 — Event timeline: moments khi scammer thay đổi tactic."""
    turns = conv.get("turns", [])
    scammer_turns = [(i, t) for i, t in enumerate(turns) if t.get("speaker") == "scammer"]

    events = []
    prev_acts: frozenset = frozenset()
    for turn_idx, t in scammer_turns:
        tags = frozenset(
            sp.get("tag", "")
            for sp in (t.get("span_annotations") or [])
            if sp.get("tag")
        )
        if tags != prev_acts and prev_acts:  # span tag set changed
            added = tags - prev_acts
            removed = prev_acts - tags
            events.append({
                "turn": turn_idx + 1,
                "added": ", ".join(sorted(added)) or "—",
                "removed": ", ".join(sorted(removed)) or "—",
                "acts": ", ".join(sorted(tags)),
            })
        prev_acts = tags

    if not scammer_turns:
        return _empty_fig("Không có scammer turns")

    # All scammer turns for baseline
    all_turn_nums = [ti + 1 for ti, _ in scammer_turns]
    fig = go.Figure()

    # Baseline timeline
    fig.add_trace(go.Scatter(
        x=all_turn_nums, y=[0] * len(all_turn_nums),
        mode="lines",
        line=dict(color="#e2e8f0", width=3),
        showlegend=False, hoverinfo="skip",
    ))

    # Event markers
    if events:
        ex = [e["turn"] for e in events]
        ey = [0] * len(events)
        etexts = [f"Turn {e['turn']}<br>+{e['added']}<br>-{e['removed']}" for e in events]
        fig.add_trace(go.Scatter(
            x=ex, y=ey,
            mode="markers+text",
            marker=dict(size=14, color="#ef4444", symbol="diamond",
                        line=dict(width=2, color="white")),
            text=[str(e["turn"]) for e in events],
            textposition="top center",
            textfont=dict(size=9),
            hovertext=etexts,
            hoverinfo="text",
            name="Tactic Change",
        ))

    cid = conv.get("conversation_id", "")
    fig.update_layout(
        title=_title(
            f"Adaptability Timeline — {cid}",
            "Kim cương đỏ = thời điểm scammer thay đổi chiến thuật. "
            "Nhiều thay đổi = scammer linh hoạt, thích nghi cao → DS cao hơn."
        ),
        xaxis_title="Turn #",
        yaxis=dict(visible=False),
        showlegend=True,
    )
    return _base_layout(fig, height=260)


# ─────────────────────────────────────────────────────────────────
# TCS — 2 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_tcs_horizontal_bar(tcs_report: Dict) -> go.Figure:
    """#13 — Horizontal bar: tactic frequency (refactor)."""
    counts = tcs_report.get("tactic_counts", {})
    if not counts:
        return _empty_fig("Không có dữ liệu tactic")

    df = pd.DataFrame(
        list(counts.items()), columns=["Tactic", "Count"]
    ).sort_values("Count")

    total = tcs_report.get("total_scammer_turns", sum(counts.values())) or 1
    df["Freq%"] = (df["Count"] / total * 100).round(1)

    colors = [SSAT_COLORS.get(t, "#94a3b8") for t in df["Tactic"]]

    fig = go.Figure(go.Bar(
        x=df["Count"].tolist(),
        y=df["Tactic"].tolist(),
        orientation="h",
        marker_color=colors,
        text=[f"{c} ({f:.1f}%)" for c, f in zip(df["Count"], df["Freq%"])],
        textposition="outside",
        textfont_size=9,
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#ef4444",
                  annotation_text="Min 50", annotation_font_size=9)
    fig.update_layout(
        title=_title(
            "Tactic Frequency — Tần Suất Speech Act",
            "Số scammer turns chứa mỗi loại speech act + % tổng. "
            "Đường đỏ đứt = ngưỡng tối thiểu 50 examples. "
            "Dưới ngưỡng = cần bổ sung thêm dữ liệu huấn luyện."
        ),
        showlegend=False,
        yaxis_tickfont_size=9,
        xaxis_title="Số turns",
    )
    return _base_layout(fig, height=370)


def plot_tcs_lorenz_curve(tcs_report: Dict) -> go.Figure:
    """#14 — Lorenz curve: tactic distribution inequality."""
    counts = tcs_report.get("tactic_counts", {})
    if not counts:
        return _empty_fig("Không có dữ liệu tactic")

    sorted_counts = sorted(counts.values())
    n = len(sorted_counts)
    total = sum(sorted_counts) or 1

    cum_pop = [i / n for i in range(n + 1)]
    cum_share = [0.0]
    running = 0.0
    for v in sorted_counts:
        running += v / total
        cum_share.append(round(running, 5))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_pop, y=cum_pop,
        mode="lines", name="Equality line",
        line=dict(color="#94a3b8", dash="dash", width=1.5),
    ))
    gini = tcs_report.get("gini_coefficient", 0.0)
    fig.add_trace(go.Scatter(
        x=cum_pop, y=cum_share,
        mode="lines+markers",
        name=f"Lorenz (Gini={gini:.3f})",
        line=dict(color="#6366f1", width=2),
        marker=dict(size=5),
        fill="tonexty",
        fillcolor="rgba(99,102,241,0.12)",
    ))
    fig.update_layout(
        title=_title(
            "Lorenz Curve — Bất Bình Đẳng Phân Phối Tactic",
            f"Đường tím = phân phối thực tế; đường xám = phân phối hoàn toàn đều. "
            f"Gini = {gini:.3f} — Gini > 0.40 = mất cân bằng (một số tactic chiếm ưu thế)."
        ),
        xaxis_title="Tỷ lệ tích lũy của tactic (số lượng)",
        yaxis_title="Tỷ lệ tích lũy của turns",
        xaxis=dict(range=[0, 1.02], tickformat=".0%"),
        yaxis=dict(range=[0, 1.05], tickformat=".0%"),
    )
    return _base_layout(fig, height=340)


# ─────────────────────────────────────────────────────────────────
# LDS — 2 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "tôi", "bạn", "anh", "chị", "ông", "bà", "em", "mình", "chúng", "các",
    "của", "và", "là", "có", "không", "được", "một", "cho", "với", "để",
    "trong", "này", "đó", "những", "thì", "đã", "sẽ", "như", "hay", "nếu",
    "khi", "từ", "về", "ra", "vào", "lên", "xuống", "đây", "kia", "nào",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "we", "they", "it", "my", "your", "our",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "or", "but",
}


def plot_lds_wordcloud(convs: List[Dict]) -> go.Figure:
    """#15 — Horizontal bar (word cloud): top 30 từ trong scammer text."""
    word_counter: Counter = Counter()
    for conv in convs:
        for t in conv.get("turns", []):
            if t.get("speaker") != "scammer":
                continue
            text = t.get("text", "").lower()
            for w in text.split():
                clean = w.strip(".,!?;:\"'()[]{}")
                if len(clean) > 2 and clean not in _STOPWORDS:
                    word_counter[clean] += 1

    if not word_counter:
        return _empty_fig("Không có text của scammer")

    top_words = word_counter.most_common(30)
    words = [w for w, _ in reversed(top_words)]
    freqs = [f for _, f in reversed(top_words)]

    # Gradient colors based on rank
    n = len(words)
    colors = [
        f"rgba(99,102,241,{0.3 + 0.7 * (i / max(n - 1, 1)):.2f})"
        for i in range(n)
    ]

    fig = go.Figure(go.Bar(
        x=freqs, y=words,
        orientation="h",
        marker_color=colors,
        text=freqs,
        textposition="outside",
        textfont_size=9,
    ))
    fig.update_layout(
        title=_title(
            "Scammer Vocabulary — Top 30 Từ Phổ Biến",
            "Tần suất từ trong toàn bộ scammer utterances (loại bỏ stopwords). "
            "Màu đậm = từ xuất hiện nhiều nhất. "
            "Từ lặp nhiều = keyword của kịch bản lừa đảo điển hình."
        ),
        showlegend=False,
        xaxis_title="Tần suất",
        yaxis_tickfont_size=9,
    )
    return _base_layout(fig, height=max(300, n * 18 + 80))


def plot_lds_similarity_heatmap(convs: List[Dict]) -> go.Figure:
    """#16 — Heatmap: pairwise cosine similarity matrix (sample ≤ 20 convs)."""
    # Build text blobs for a sample
    sample_size = min(20, len(convs))
    sample = convs[:sample_size]
    texts, ids = [], []
    for conv in sample:
        blob = " ".join(
            t.get("text", "") for t in conv.get("turns", [])
            if t.get("speaker") == "scammer"
        ).strip().lower()
        if blob:
            texts.append(blob)
            ids.append(conv.get("conversation_id", "")[-10:])

    if len(texts) < 2:
        return _empty_fig("Cần ít nhất 2 conversations để tính similarity")

    # Simple TF-IDF cosine (same logic as linguistic_diversity.py)
    tokenized = [t.split() for t in texts]
    vocab = sorted(set(tok for doc in tokenized for tok in doc))
    vocab_idx = {w: i for i, w in enumerate(vocab)}
    n, v = len(texts), len(vocab)

    tf = [[0.0] * v for _ in range(n)]
    for i, tokens in enumerate(tokenized):
        cnt: Counter = Counter(tokens)
        total = len(tokens)
        for tok, c in cnt.items():
            if tok in vocab_idx:
                tf[i][vocab_idx[tok]] = c / total

    idf = [math.log((n + 1) / (sum(1 for i in range(n) if tf[i][j] > 0) + 1)) + 1
           for j in range(v)]
    tfidf = [[tf[i][j] * idf[j] for j in range(v)] for i in range(n)]
    for i in range(n):
        norm = math.sqrt(sum(x * x for x in tfidf[i])) or 1.0
        tfidf[i] = [x / norm for x in tfidf[i]]

    matrix = [[round(sum(tfidf[i][k] * tfidf[j][k] for k in range(v)), 3)
               for j in range(n)] for i in range(n)]

    fig = px.imshow(
        matrix, x=ids, y=ids,
        color_continuous_scale="Blues",
        zmin=0, zmax=1,
        title=_title(
            f"Similarity Heatmap — Ma Trận Tương Đồng (n={n})",
            "Cosine similarity giữa các conversations (TF-IDF scammer text). "
            "Ô tối trên đường chéo phụ = 2 conversations quá giống nhau (near-duplicate). "
            "Target: phần lớn ô < 0.35."
        ),
        aspect="auto",
    )
    fig.update_layout(xaxis_tickfont_size=8, yaxis_tickfont_size=8)
    return _base_layout(fig, height=max(320, n * 22 + 80))


# ─────────────────────────────────────────────────────────────────
# PCS — 2 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_pcs_stacked_area(convs: List[Dict]) -> go.Figure:
    """#17 — Stacked area: phase distribution across conversations."""
    from src.schema import PHASE_ORDER
    phase_list = [f"P{i}" for i in range(1, 7)]

    rows = []
    for idx, conv in enumerate(convs):
        phases_present = set()
        for t in conv.get("turns", []):
            p = t.get("phase")
            if p:
                phases_present.add(p)
        if not phases_present:
            phases_present = set(conv.get("conversation_meta", {}).get("phases_present", []))
        row = {"conv_idx": idx}
        for p in phase_list:
            row[p] = 1 if p in phases_present else 0
        rows.append(row)

    if not rows:
        return _empty_fig("Không có dữ liệu phase")

    df = pd.DataFrame(rows)
    # Compute cumulative coverage ratio as we go through convs
    x = list(range(1, len(df) + 1))
    fig = go.Figure()
    phase_colors = {
        "P1": "#6366f1", "P2": "#8b5cf6", "P3": "#f59e0b",
        "P4": "#f97316", "P5": "#ef4444", "P6": "#22c55e",
    }
    # Rolling average presence
    for p in phase_list:
        rolling_avg = df[p].expanding().mean().round(3).tolist()
        fig.add_trace(go.Scatter(
            x=x, y=rolling_avg,
            stackgroup="one",
            name=f"{p} — {PHASE_DESC.get(p, p)}",
            line=dict(width=0.5, color=phase_colors.get(p, "#94a3b8")),
            fillcolor=_hex_rgba(phase_colors.get(p, "#94a3b8"), 0.6),
            mode="lines",
            hovertemplate=f"{p}: %{{y:.1%}}<extra></extra>",
        ))
    fig.update_layout(
        title=_title(
            "Phase Distribution — Stacked Area Over Dataset",
            "Tỷ lệ tích lũy conversations có từng phase theo thứ tự. "
            "P5 (đỏ) phải đạt ≥40%. Nếu P5 nhỏ = dataset thiếu kịch bản đến giai đoạn compliance."
        ),
        xaxis_title="Conversation #",
        yaxis_title="Tỷ lệ tích lũy",
        yaxis=dict(tickformat=".0%"),
    )
    return _base_layout(fig, height=360)


def plot_pcs_sankey(convs: List[Dict]) -> go.Figure:
    """#18 — Sankey: phase transition flow (P1→P2→P3→...)."""
    from src.schema import PHASE_ORDER
    phase_list = [f"P{i}" for i in range(1, 7)]

    trans_counts: Counter = Counter()
    for conv in convs:
        phases = []
        for t in conv.get("turns", []):
            p = t.get("phase")
            if p and (not phases or phases[-1] != p):
                phases.append(p)
        if not phases:
            phases = conv.get("conversation_meta", {}).get("phases_present", [])
        for i in range(len(phases) - 1):
            fr, to = phases[i], phases[i + 1]
            if fr in PHASE_ORDER and to in PHASE_ORDER:
                trans_counts[(fr, to)] += 1

    if not trans_counts:
        return _empty_fig("Không có phase transitions (cần phase annotation trong turns)")

    # Nodes: duplicate phases for source/target to avoid cycles
    # Use prefix s_ for source, t_ for target
    node_labels = (
        [f"{p} (out)" for p in phase_list] +
        [f"{p} (in)" for p in phase_list]
    )
    src_idx = {p: i for i, p in enumerate(phase_list)}
    tgt_idx = {p: i + len(phase_list) for i, p in enumerate(phase_list)}

    phase_colors_hex = {
        "P1": "#6366f1", "P2": "#8b5cf6", "P3": "#f59e0b",
        "P4": "#f97316", "P5": "#ef4444", "P6": "#22c55e",
    }
    node_colors = (
        [phase_colors_hex.get(p, "#94a3b8") for p in phase_list] +
        [_hex_rgba(phase_colors_hex.get(p, "#94a3b8"), 0.8) for p in phase_list]
    )

    sources, targets, values, link_colors = [], [], [], []
    for (fr, to), cnt in trans_counts.items():
        if fr in src_idx and to in tgt_idx:
            sources.append(src_idx[fr])
            targets.append(tgt_idx[to])
            values.append(cnt)
            link_colors.append(_hex_rgba(phase_colors_hex.get(fr, "#94a3b8"), 0.38))

    if not sources:
        return _empty_fig()

    fig = go.Figure(go.Sankey(
        node=dict(label=node_labels, color=node_colors, pad=12, thickness=18),
        link=dict(source=sources, target=targets, value=values, color=link_colors),
    ))
    fig.update_layout(
        title=_title(
            "Phase Transition Flow — Sankey",
            "Luồng chuyển tiếp giữa các giai đoạn conversation. "
            "Luồng rộng = transition phổ biến. "
            "P1→P2→P3→P4→P5 = kịch bản lừa đảo hoàn chỉnh."
        ),
    )
    return _base_layout(fig, height=380)


# ─────────────────────────────────────────────────────────────────
# VSVS — 1 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_vsvs_transition_heatmap(trans_matrix: Dict[str, Dict[str, int]]) -> go.Figure:
    """#19 — Heatmap: victim state transition matrix (refactor)."""
    if not trans_matrix:
        return _empty_fig("Không có dữ liệu transitions (cần cognitive_state trong victim turns)")

    states = sorted(set(
        list(trans_matrix.keys()) + [k for v in trans_matrix.values() for k in v]
    ))
    matrix = [[trans_matrix.get(fr, {}).get(to, 0) for to in states] for fr in states]

    # Normalize rows for readability (show probabilities)
    norm_matrix = []
    for row in matrix:
        total = sum(row) or 1
        norm_matrix.append([round(v / total, 3) for v in row])

    fig = px.imshow(
        norm_matrix, x=states, y=states,
        color_continuous_scale="Blues",
        zmin=0, zmax=1,
        title=_title(
            "Ma Trận Chuyển Trạng Thái Tâm Lý Nạn Nhân (VSVS)",
            "Hàng = trạng thái trước, Cột = trạng thái sau. Giá trị = xác suất chuyển tiếp. "
            "Transition không hợp lệ theo VALID_TRANSITIONS schema = lỗi annotation (ô sáng ở vị trí không mong đợi)."
        ),
        text_auto=".2f",
        aspect="auto",
    )
    fig.update_layout(
        xaxis_title="Trạng thái SAU",
        yaxis_title="Trạng thái TRƯỚC",
        xaxis_tickfont_size=9,
        yaxis_tickfont_size=9,
        coloraxis_colorbar=dict(title="P(transition)", tickformat=".1%"),
    )
    return _base_layout(fig, height=400)


# ─────────────────────────────────────────────────────────────────
# AQS — 3 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_aqs_confusion_matrix(aqs_report: Dict) -> go.Figure:
    """#20 — Heatmap: annotator agreement (kappa) per label."""
    kappa = aqs_report.get("cohen_kappa_per_label", {})
    if not kappa:
        return _empty_fig("Chưa có gold set — upload gold set ở sidebar để tính Kappa")

    labels = sorted(kappa.keys())
    # Build a 1-row heatmap (kappa per label)
    values = [[round(kappa.get(l, 0), 3) for l in labels]]

    color_scale = [
        [0.0, "#ef4444"],
        [0.65, "#f59e0b"],
        [0.75, "#22c55e"],
        [1.0, "#16a34a"],
    ]

    fig = px.imshow(
        values,
        x=labels,
        y=["Kappa"],
        color_continuous_scale=color_scale,
        zmin=-0.2, zmax=1.0,
        title=_title(
            "Annotator Agreement — Cohen's Kappa per Label",
            "Màu xanh = Kappa ≥ 0.75 (tốt) | Vàng = 0.65–0.75 (cần cải thiện) | "
            "Đỏ = <0.65 (cần re-annotate). So sánh dataset vs gold set."
        ),
        text_auto=".3f",
        aspect="auto",
    )
    fig.update_layout(
        xaxis_tickfont_size=9,
        yaxis_tickfont_size=10,
        coloraxis_colorbar=dict(title="Kappa"),
    )
    return _base_layout(fig, height=220)


def plot_aqs_annotator_radar(entropy_data: Dict) -> go.Figure:
    """#21 — Radar: label variety per annotator (entropy)."""
    per_ann = entropy_data.get("entropy_per_annotator", {})
    if not per_ann:
        return _empty_fig("Không có dữ liệu annotator (cần writer_id trong quality field)")

    mean_e = entropy_data.get("mean_entropy", 0.0)
    lazy = set(entropy_data.get("lazy_annotators", []))
    annotators = sorted(per_ann.keys())

    fig = go.Figure()
    for ann in annotators:
        e = per_ann[ann]
        is_lazy = ann in lazy
        color = "#ef4444" if is_lazy else "#6366f1"
        fig.add_trace(go.Scatterpolar(
            r=[e, e],
            theta=[ann, ann],
            mode="markers",
            marker=dict(size=12, color=color),
            name=f"{'⚠️ ' if is_lazy else ''}{ann} ({e:.3f})",
            showlegend=True,
        ))

    # Actual radar by annotator name as axis
    cats = annotators + [annotators[0]] if annotators else []
    vals_mean = [mean_e] * len(cats)

    fig2 = go.Figure()
    entropy_vals = [per_ann.get(a, 0) for a in annotators]
    fig2.add_trace(go.Scatterpolar(
        r=entropy_vals + [entropy_vals[0]],
        theta=cats,
        fill="toself",
        fillcolor="rgba(99,102,241,0.12)",
        line_color="#6366f1",
        name="Annotator entropy",
    ))
    fig2.add_trace(go.Scatterpolar(
        r=[mean_e] * (len(annotators) + 1),
        theta=cats,
        mode="lines",
        line=dict(color="#3b82f6", dash="dash", width=1.5),
        name=f"Team mean ({mean_e:.3f})",
    ))
    lazy_thresh = entropy_data.get("lazy_threshold", 0.0)
    fig2.add_trace(go.Scatterpolar(
        r=[lazy_thresh] * (len(annotators) + 1),
        theta=cats,
        mode="lines",
        line=dict(color="#ef4444", dash="dot", width=1),
        name=f"Lazy threshold ({lazy_thresh:.3f})",
    ))

    fig2.update_layout(
        title=_title(
            "Annotator Entropy Radar — Đa Dạng Nhãn",
            "Entropy của phân phối nhãn mỗi annotator. "
            "Entropy thấp (<60% team mean) = gán nhãn đơn điệu, có thể lazy. "
            "Đường đỏ đứt = ngưỡng phát hiện lazy."
        ),
        polar=dict(radialaxis=dict(visible=True, range=[0, max(entropy_vals + [mean_e * 1.2, 0.1])])),
    )
    return _base_layout(fig2, height=360)


def plot_aqs_span_heatmap(convs: List[Dict]) -> go.Figure:
    """#22 — Heatmap: span coverage % per tactic type × annotator."""
    from src.schema import ALL_SPAN_TAGS
    _TACTICS_REQUIRING_SPAN = {t: t for t in ALL_SPAN_TAGS}

    # {annotator: {tactic: [requiring, with_span]}}
    data: Dict[str, Dict[str, List[int]]] = {}

    for conv in convs:
        writer = (conv.get("quality") or {}).get("writer_id", "unknown")
        if writer not in data:
            data[writer] = {t: [0, 0] for t in _TACTICS_REQUIRING_SPAN}
        for turn in conv.get("turns", []):
            if turn.get("speaker") != "scammer":
                continue
            tags_present = {sp.get("tag", "") for sp in (turn.get("span_annotations") or [])}
            for tactic in _TACTICS_REQUIRING_SPAN:
                data[writer][tactic][0] += 1
                if tactic in tags_present:
                    data[writer][tactic][1] += 1

    if not data:
        return _empty_fig("Không có dữ liệu span annotation hoặc writer_id")

    annotators = sorted(data.keys())
    tactics = sorted(_TACTICS_REQUIRING_SPAN.keys())

    matrix = []
    for ann in annotators:
        row = []
        for tac in tactics:
            req, has = data[ann].get(tac, [0, 0])
            ratio = round(has / req, 3) if req > 0 else None
            row.append(ratio)
        matrix.append(row)

    # Replace None with 0 for display
    display_matrix = [[v if v is not None else 0.0 for v in row] for row in matrix]

    fig = px.imshow(
        display_matrix,
        x=tactics,
        y=annotators,
        color_continuous_scale=[[0, "#ef4444"], [0.8, "#f59e0b"], [1.0, "#22c55e"]],
        zmin=0, zmax=1,
        title=_title(
            "Span Coverage Heatmap — Tactic × Annotator",
            "% turns có span annotation / tổng turns yêu cầu span. "
            "Xanh = ≥80% đầy đủ | Vàng = thiếu một phần | Đỏ = thiếu nghiêm trọng. "
            "Target: toàn bộ ô ≥ 0.80."
        ),
        text_auto=".0%",
        aspect="auto",
    )
    fig.update_layout(xaxis_tickfont_size=9, yaxis_tickfont_size=9)
    return _base_layout(fig, height=max(280, len(annotators) * 30 + 100))


# ─────────────────────────────────────────────────────────────────
# DBR — 2 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_dbr_radar(normalized_entropy: Dict[str, float]) -> go.Figure:
    """#23 — Radar: balance across 8 dimensions."""
    if not normalized_entropy:
        return _empty_fig("Không có dữ liệu DBR")

    dims = list(normalized_entropy.keys())
    vals = [normalized_entropy[d] for d in dims]
    cats = dims + [dims[0]]
    r_vals = vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_vals, theta=cats,
        fill="toself",
        fillcolor="rgba(99,102,241,0.12)",
        line_color="#6366f1",
        name="Normalized Entropy",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[0.65] * len(cats), theta=cats,
        mode="lines",
        line=dict(color="#22c55e", dash="dash", width=1.5),
        name="Target ≥0.65",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[0.50] * len(cats), theta=cats,
        mode="lines",
        line=dict(color="#f59e0b", dash="dot", width=1),
        name="Warning <0.50",
    ))
    fig.update_layout(
        title=_title(
            "DBR Radar — Cân Bằng 8 Chiều Dataset",
            "Mỗi trục = 1 chiều phân loại. 1.0 = hoàn toàn đều. "
            "Đường xanh = target ≥0.65. Đường vàng = ngưỡng cảnh báo <0.50. "
            "Hình dạng nhỏ hoặc méo = dataset mất cân bằng."
        ),
        polar=dict(radialaxis=dict(visible=True, range=[0, 1.05], tickformat=".1f")),
    )
    return _base_layout(fig, height=380)


def plot_dbr_stacked_bar(convs: List[Dict]) -> go.Figure:
    """#24 — Stacked bar: scenario count per domain_l1 × outcome."""
    rows = []
    for conv in convs:
        domain = conv.get("scenario", {}).get("domain_l1", "UNKNOWN")
        outcome = conv.get("conversation_meta", {}).get("outcome", "UNKNOWN")
        rows.append({"domain": domain, "outcome": outcome})

    if not rows:
        return _empty_fig("Không có dữ liệu domain/outcome")

    df = pd.DataFrame(rows)
    pivot = df.groupby(["domain", "outcome"]).size().reset_index(name="count")

    outcomes = sorted(pivot["outcome"].unique())
    domains = sorted(pivot["domain"].unique())

    fig = go.Figure()
    for outcome in outcomes:
        sub = pivot[pivot["outcome"] == outcome]
        domain_counts = {row["domain"]: row["count"] for _, row in sub.iterrows()}
        fig.add_trace(go.Bar(
            name=outcome,
            x=domains,
            y=[domain_counts.get(d, 0) for d in domains],
            marker_color=OUTCOME_COLORS.get(outcome, "#94a3b8"),
        ))

    fig.update_layout(
        title=_title(
            "Scenario Representativeness — Domain × Outcome",
            "Số conversations theo từng domain_l1 và outcome. "
            "Mỗi domain nên có đại diện của tất cả outcomes để đảm bảo đa dạng. "
            "Cột đồng đều = dataset cân bằng tốt."
        ),
        barmode="stack",
        xaxis_tickangle=-15,
        xaxis_tickfont_size=9,
        xaxis_title="Domain",
        yaxis_title="Số conversations",
    )
    return _base_layout(fig, height=360)


# ─────────────────────────────────────────────────────────────────
# MER — 1 BIỂU ĐỒ
# ─────────────────────────────────────────────────────────────────

def plot_mer_dashboard(summary: Dict) -> go.Figure:
    """#25 — Indicator grid: pass/fail per condition (refactor traffic lights)."""
    checks = [
        ("Ambiguity\n0.30–0.55",
         summary.get("mean_ambiguity") is not None
         and 0.30 <= (summary.get("mean_ambiguity") or 0) <= 0.55,
         f"{summary.get('mean_ambiguity') or 0:.3f}"),
        ("Difficulty\n0.45–0.70",
         summary.get("mean_difficulty") is not None
         and 0.45 <= (summary.get("mean_difficulty") or 0) <= 0.70,
         f"{summary.get('mean_difficulty') or 0:.3f}"),
        ("IAA Kappa\n≥0.75",
         summary.get("mean_kappa") is not None
         and (summary.get("mean_kappa") or 0) >= 0.75,
         f"{summary.get('mean_kappa') or 'N/A'}"),
        ("Near-Dup\n< 5%",
         (summary.get("near_dup_ratio") or 0) < 0.05,
         f"{(summary.get('near_dup_ratio') or 0):.1%}"),
        ("Balance\n≥ 0.65",
         (summary.get("balance_score") or 0) >= 0.65,
         f"{summary.get('balance_score') or 0:.3f}"),
    ]

    n = len(checks)
    fig = go.Figure()

    for i, (label, ok, val) in enumerate(checks):
        color = "#22c55e" if ok else "#ef4444"
        sym = "✓ PASS" if ok else "✗ FAIL"
        fig.add_trace(go.Indicator(
            mode="number",
            value=1 if ok else 0,
            title={
                "text": (
                    f"<span style='font-size:20px;color:{color}'><b>{sym}</b></span><br>"
                    f"<span style='font-size:11px;color:#374151'>{label}</span><br>"
                    f"<span style='font-size:12px;color:{color};font-weight:600'>{val}</span>"
                ),
            },
            number={"font": {"color": "rgba(0,0,0,0)", "size": 1}},
            domain={"row": 0, "column": i},
        ))
        # Add colored background via shape
        fig.add_shape(
            type="rect",
            x0=i / n + 0.01, x1=(i + 1) / n - 0.01,
            y0=0.05, y1=0.95,
            xref="paper", yref="paper",
            fillcolor=_hex_rgba(color, 0.08),
            line=dict(color=_hex_rgba(color, 0.38), width=2),
        )

    fig.update_layout(
        grid={"rows": 1, "columns": n, "pattern": "independent"},
        title=_title(
            f"MER Dashboard — {summary.get('status', 'UNKNOWN')}",
            "5 điều kiện release chính. PASS tất cả = READY FOR RELEASE. "
            "Có FAIL = BLOCKED hoặc NEEDS REVISION."
        ),
        height=240,
        margin=dict(l=20, r=20, t=75, b=10),
        template=_TEMPLATE,
        font=dict(size=11),
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# BACKWARD COMPAT — kept for any external references
# ─────────────────────────────────────────────────────────────────
def plot_lds_summary_cards(lds_report: Dict) -> List[Dict]:
    """Card data for LDS metrics display in Streamlit."""
    return [
        {
            "label": "TTR (Type-Token Ratio)",
            "value": f"{lds_report.get('ttr', 0):.3f}",
            "ok": lds_report.get("ttr_ok", False),
            "target": "> 0.30",
            "desc": "Tỷ lệ từ vựng độc đáo / tổng tokens.",
        },
        {
            "label": "Mean Cosine Similarity",
            "value": f"{lds_report.get('mean_pairwise_sim', 0):.3f}",
            "ok": lds_report.get("sim_ok", False),
            "target": "< 0.35",
            "desc": "Độ tương đồng trung bình (TF-IDF).",
        },
        {
            "label": "Near-Duplicate Pairs",
            "value": str(lds_report.get("near_dup_count", 0)),
            "ok": lds_report.get("near_dup_ratio", 1) < 0.05,
            "target": "< 5% tổng",
            "desc": "Cặp conversations có cosine sim > 0.70.",
        },
        {
            "label": "Diversity Score",
            "value": f"{lds_report.get('diversity_score', 0):.3f}",
            "ok": lds_report.get("diversity_score", 0) >= 0.60,
            "target": "≥ 0.60",
            "desc": "Điểm tổng hợp đa dạng ngôn ngữ (0–1).",
        },
    ]
