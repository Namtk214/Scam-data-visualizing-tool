"""
page_overview.py — Dataset Overview.
Tổ chức theo 7 section, khai thác đầy đủ schema v2 của demo_data.json.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from collections import Counter

from src.schema import OUTCOME_COLORS, DOMAIN_COLORS, SSAT_COLORS, VCS_COLORS, SPAN_COLORS
from src.stats import compute_stats, build_conversation_df, flatten_to_turn_df, flatten_to_span_df
from src.visualize import (
    plot_phase_transition_heatmap,
    plot_vcs_transition_heatmap,
    plot_tactic_phase_heatmap,
)

_TPL = "plotly_white"
_H = 300   # default chart height
_H2 = 340  # taller charts


def render(session):
    st.header("📊 Dataset Overview")
    convs = session.get_filtered()
    if not convs:
        st.info("No data. Load conversations in Data Input tab.")
        return

    stats = compute_stats(convs)
    df_c = build_conversation_df(convs)
    df_t = flatten_to_turn_df(convs)
    df_s = flatten_to_span_df(convs)

    # ── KPIs ──────────────────────────────────────────────────────
    gold_n = sum(1 for c in convs if (c.get("quality") or {}).get("is_gold"))
    avg_ai = _mean_field(convs, lambda c: c.get("conversation_meta", {}).get("ambiguity_score"))
    avg_ds = _mean_field(convs, lambda c: c.get("conversation_meta", {}).get("difficulty_score"))
    avg_iaa = _mean_field(convs, lambda c: (c.get("quality") or {}).get("iaa_score"))

    k = st.columns(7)
    _kpi(k[0], "Conversations", stats["n_conversations"])
    _kpi(k[1], "Total Turns", stats["n_turns"])
    _kpi(k[2], "Avg Turns/Conv", stats["avg_turns_per_conv"])
    _kpi(k[3], "Total Spans", stats["n_spans"])
    _kpi(k[4], "Gold Samples", gold_n)
    _kpi(k[5], "Avg AI Score", f"{avg_ai:.3f}" if avg_ai else "—")
    _kpi(k[6], "Avg IAA", f"{avg_iaa:.3f}" if avg_iaa else "—")

    k2 = st.columns(5)
    _kpi(k2[0], "Scammer Turns", stats["n_scammer_turns"])
    _kpi(k2[1], "Victim Turns", stats["n_victim_turns"])
    _kpi(k2[2], "Avg DS Score", f"{avg_ds:.3f}" if avg_ds else "—")
    _kpi(k2[3], "Unique Scenarios", len({c.get("scenario", {}).get("id", "") for c in convs}))
    _kpi(k2[4], "Avg Tokens/Turn", stats.get("avg_tokens_per_turn", "—"))

    st.markdown("---")

    # ── SECTION 1: Dataset Composition ────────────────────────────
    st.subheader("1 · Dataset Composition")

    c1, c2 = st.columns(2)
    with c1:
        # Outcome — pie
        outcome_counts = df_c["outcome"].value_counts().reset_index()
        outcome_counts.columns = ["outcome", "count"]
        fig = px.pie(
            outcome_counts, names="outcome", values="count",
            title="Outcome Distribution",
            color="outcome", color_discrete_map=OUTCOME_COLORS,
            hole=0.38, template=_TPL,
        )
        fig.update_traces(textinfo="percent+label", textfont_size=10)
        fig.update_layout(height=_H, margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(font_size=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Domain L1 — bar
        domain_counts = Counter(c.get("scenario", {}).get("domain_l1", "UNKNOWN") for c in convs)
        df_dom = pd.DataFrame(list(domain_counts.items()), columns=["Domain", "Count"]).sort_values("Count")
        fig = px.bar(
            df_dom, x="Count", y="Domain", orientation="h",
            title="Domain L1 Distribution",
            color="Domain", color_discrete_map=DOMAIN_COLORS,
            template=_TPL, text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=_H, showlegend=False,
                          margin=dict(t=50, b=20, l=20, r=60),
                          yaxis_tickfont_size=9)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        # Ambiguity Level — donut
        amb_counts = Counter(c.get("conversation_meta", {}).get("ambiguity_level", "unknown") for c in convs)
        amb_colors = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444", "unknown": "#94a3b8"}
        fig = px.pie(
            names=list(amb_counts.keys()), values=list(amb_counts.values()),
            title="Ambiguity Level",
            color=list(amb_counts.keys()), color_discrete_map=amb_colors,
            hole=0.42, template=_TPL,
        )
        fig.update_traces(textinfo="percent+label", textfont_size=10)
        fig.update_layout(height=_H, margin=dict(t=50, b=20, l=20, r=20),
                          legend=dict(font_size=10))
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        # Difficulty Tier — bar
        tier_counts = Counter(c.get("conversation_meta", {}).get("difficulty_tier", "unknown") for c in convs)
        tier_order = ["easy", "medium", "hard", "expert", "unknown"]
        tier_colors = {"easy": "#22c55e", "medium": "#3b82f6", "hard": "#f59e0b",
                       "expert": "#ef4444", "unknown": "#94a3b8"}
        tiers = [t for t in tier_order if t in tier_counts]
        fig = go.Figure(go.Bar(
            x=tiers,
            y=[tier_counts[t] for t in tiers],
            marker_color=[tier_colors[t] for t in tiers],
            text=[tier_counts[t] for t in tiers],
            textposition="outside",
        ))
        fig.update_layout(
            title="Difficulty Tier", template=_TPL,
            height=_H, showlegend=False,
            margin=dict(t=50, b=20, l=20, r=20),
            yaxis=dict(range=[0, max(tier_counts.values(), default=1) * 1.25]),
            xaxis_title="Tier", yaxis_title="Count",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── SECTION 2: Scenario Analysis ──────────────────────────────
    st.subheader("2 · Scenario Analysis")

    c5, c6 = st.columns(2)
    with c5:
        # Scenario Name — horizontal bar
        scen_counts = Counter(c.get("scenario", {}).get("name", "UNKNOWN") for c in convs)
        df_scen = pd.DataFrame(
            list(scen_counts.items()), columns=["Scenario", "Count"]
        ).sort_values("Count")
        fig = px.bar(
            df_scen, x="Count", y="Scenario", orientation="h",
            title="Scenario Distribution",
            color_discrete_sequence=["#6366f1"], template=_TPL, text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=max(_H, len(df_scen) * 34 + 70),
            showlegend=False,
            margin=dict(t=50, b=20, l=20, r=60),
            yaxis_tickfont_size=9,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        # Fraud Goal — bar
        goal_counts = Counter(
            c.get("scenario", {}).get("fraud_goal", "unknown") for c in convs
        )
        df_goal = pd.DataFrame(
            list(goal_counts.items()), columns=["Fraud Goal", "Count"]
        ).sort_values("Count")
        fig = px.bar(
            df_goal, x="Count", y="Fraud Goal", orientation="h",
            title="Fraud Goal Distribution",
            color_discrete_sequence=["#f59e0b"], template=_TPL, text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=max(_H, len(df_goal) * 34 + 70),
            showlegend=False,
            margin=dict(t=50, b=20, l=20, r=60),
            yaxis_tickfont_size=9,
        )
        st.plotly_chart(fig, use_container_width=True)

    c7, c8 = st.columns(2)
    with c7:
        # Real-world Prevalence — bar (sorted: very_high → low)
        prev_counts = Counter(
            c.get("scenario", {}).get("real_world_prevalence", "unknown") for c in convs
        )
        prev_order = ["very_high", "high", "medium", "low", "unknown"]
        prev_colors_map = {
            "very_high": "#ef4444", "high": "#f97316", "medium": "#f59e0b",
            "low": "#22c55e", "unknown": "#94a3b8",
        }
        labels = [p for p in prev_order if p in prev_counts]
        fig = go.Figure(go.Bar(
            x=labels,
            y=[prev_counts[l] for l in labels],
            marker_color=[prev_colors_map[l] for l in labels],
            text=[prev_counts[l] for l in labels],
            textposition="outside",
        ))
        fig.update_layout(
            title="Real-World Prevalence", template=_TPL,
            height=_H, showlegend=False,
            margin=dict(t=50, b=40, l=20, r=20),
            xaxis_title="Prevalence", yaxis_title="Count",
            yaxis=dict(range=[0, max(prev_counts.values(), default=1) * 1.25]),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c8:
        # Domain × Outcome — grouped bar
        rows_do = []
        for conv in convs:
            rows_do.append({
                "Domain": conv.get("scenario", {}).get("domain_l1", "UNKNOWN"),
                "Outcome": conv.get("conversation_meta", {}).get("outcome", "UNKNOWN"),
            })
        df_do = pd.DataFrame(rows_do)
        pivot_do = df_do.groupby(["Domain", "Outcome"]).size().reset_index(name="Count")
        fig = px.bar(
            pivot_do, x="Domain", y="Count", color="Outcome",
            color_discrete_map=OUTCOME_COLORS,
            barmode="stack",
            title="Domain × Outcome",
            template=_TPL,
        )
        fig.update_layout(
            height=_H, margin=dict(t=50, b=50, l=20, r=20),
            xaxis_tickangle=-15, xaxis_tickfont_size=9,
            legend=dict(font_size=9),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── SECTION 3: Conversation Properties ────────────────────────
    st.subheader("3 · Conversation Properties")

    c9, c10 = st.columns(2)
    with c9:
        # AI vs DS scatter (from conversation_meta pre-computed scores)
        scatter_rows = []
        for conv in convs:
            cm = conv.get("conversation_meta", {})
            ai = cm.get("ambiguity_score")
            ds = cm.get("difficulty_score")
            if ai is not None and ds is not None:
                scatter_rows.append({
                    "AI Score": ai,
                    "DS Score": ds,
                    "Outcome": cm.get("outcome", "UNKNOWN"),
                    "Tier": cm.get("difficulty_tier", ""),
                    "ID": conv.get("conversation_id", ""),
                })
        if scatter_rows:
            df_sc = pd.DataFrame(scatter_rows)
            fig = px.scatter(
                df_sc, x="AI Score", y="DS Score",
                color="Outcome", color_discrete_map=OUTCOME_COLORS,
                symbol="Tier",
                hover_data=["ID", "Tier"],
                title="Ambiguity Score vs Difficulty Score",
                template=_TPL,
            )
            fig.add_shape(type="rect", x0=0.3, x1=0.55, y0=0.45, y1=0.70,
                          line=dict(dash="dash", color="#22c55e"),
                          fillcolor="rgba(34,197,94,0.07)")
            fig.add_annotation(x=0.425, y=0.575, text="Sweet Spot",
                               showarrow=False, font=dict(size=9, color="#16a34a"))
            fig.update_layout(height=_H2, margin=dict(t=50, b=40, l=40, r=20),
                              legend=dict(font_size=9))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có ambiguity_score / difficulty_score trong dữ liệu.")

    with c10:
        # Cialdini Principles — multi-label bar
        cialdini_counter: Counter = Counter()
        for conv in convs:
            for p in conv.get("conversation_meta", {}).get("cialdini_principles") or []:
                cialdini_counter[p] += 1
        if cialdini_counter:
            df_ci = pd.DataFrame(
                list(cialdini_counter.items()), columns=["Principle", "Count"]
            ).sort_values("Count")
            fig = px.bar(
                df_ci, x="Count", y="Principle", orientation="h",
                title="Cialdini Principles Used",
                color_discrete_sequence=["#8b5cf6"], template=_TPL, text="Count",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=_H2, showlegend=False,
                margin=dict(t=50, b=20, l=20, r=60),
                yaxis_tickfont_size=9,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có cialdini_principles trong dữ liệu.")

    c11, c12 = st.columns(2)
    with c11:
        # Cognitive Mechanisms — multi-label bar
        mech_counter: Counter = Counter()
        for conv in convs:
            for m in conv.get("conversation_meta", {}).get("cognitive_mechanisms") or []:
                mech_counter[m] += 1
        if mech_counter:
            df_mech = pd.DataFrame(
                list(mech_counter.items()), columns=["Mechanism", "Count"]
            ).sort_values("Count")
            fig = px.bar(
                df_mech, x="Count", y="Mechanism", orientation="h",
                title="Cognitive Mechanisms Used",
                color_discrete_sequence=["#ec4899"], template=_TPL, text="Count",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=_H2, showlegend=False,
                margin=dict(t=50, b=20, l=20, r=60),
                yaxis_tickfont_size=9,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có cognitive_mechanisms trong dữ liệu.")

    with c12:
        # Phase Coverage — bar (% conversations having each phase)
        n_conv = len(convs)
        phase_counter: Counter = Counter()
        for conv in convs:
            for ph in set(conv.get("conversation_meta", {}).get("phases_present") or []):
                phase_counter[ph] += 1
        if phase_counter:
            from src.schema import PHASE_DESC
            phases_sorted = sorted(phase_counter.keys())
            vals = [phase_counter[p] / n_conv * 100 for p in phases_sorted]
            colors_ph = [
                "#22c55e" if v >= 80 else "#f59e0b" if v >= 40 else "#ef4444"
                for v in vals
            ]
            fig = go.Figure(go.Bar(
                x=phases_sorted,
                y=vals,
                marker_color=colors_ph,
                text=[f"{v:.0f}%" for v in vals],
                textposition="outside",
                hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
            ))
            fig.update_layout(
                title="Phase Coverage (% of conversations)",
                template=_TPL, height=_H2, showlegend=False,
                margin=dict(t=50, b=40, l=20, r=20),
                yaxis=dict(range=[0, 120], ticksuffix="%"),
                xaxis_title="Phase",
            )
            fig.add_hline(y=40, line_dash="dash", line_color="#ef4444",
                          annotation_text="P5 min 40%", annotation_font_size=9)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── SECTION 4: Annotation Analysis ────────────────────────────
    st.subheader("4 · Annotation Analysis")

    c13, c14 = st.columns(2)
    with c13:
        # SSAT frequency
        if not df_t.empty:
            ssat_counter: Counter = Counter()
            col = "speech_acts" if "speech_acts" in df_t.columns else "ssat"
            scammer_df = df_t[df_t["speaker"] == "scammer"]
            for acts in scammer_df[col]:
                if isinstance(acts, list):
                    ssat_counter.update(acts)
            if ssat_counter:
                df_sa = pd.DataFrame(
                    list(ssat_counter.items()), columns=["Tactic", "Count"]
                ).sort_values("Count")
                colors_sa = [SSAT_COLORS.get(t, "#94a3b8") for t in df_sa["Tactic"]]
                fig = go.Figure(go.Bar(
                    x=df_sa["Count"].tolist(), y=df_sa["Tactic"].tolist(),
                    orientation="h", marker_color=colors_sa,
                    text=df_sa["Count"].tolist(), textposition="outside",
                ))
                fig.update_layout(
                    title="Scammer Speech Act (SSAT) Frequency",
                    template=_TPL, height=_H2, showlegend=False,
                    margin=dict(t=50, b=20, l=20, r=60),
                    yaxis_tickfont_size=9,
                )
                st.plotly_chart(fig, use_container_width=True)

    with c14:
        # VCS distribution
        if not df_t.empty:
            vcs_col = "cognitive_state" if "cognitive_state" in df_t.columns else "vcs"
            victim_df = df_t[df_t["speaker"] == "victim"]
            vcs_counts = victim_df[vcs_col].dropna().value_counts().reset_index()
            vcs_counts.columns = ["State", "Count"]
            if not vcs_counts.empty:
                colors_vcs = [VCS_COLORS.get(s, "#94a3b8") for s in vcs_counts["State"]]
                fig = go.Figure(go.Bar(
                    x=vcs_counts["State"].tolist(),
                    y=vcs_counts["Count"].tolist(),
                    marker_color=colors_vcs,
                    text=vcs_counts["Count"].tolist(),
                    textposition="outside",
                ))
                fig.update_layout(
                    title="Victim Cognitive State (VCS) Distribution",
                    template=_TPL, height=_H2, showlegend=False,
                    margin=dict(t=50, b=50, l=20, r=20),
                    xaxis_tickangle=-20, xaxis_tickfont_size=9,
                )
                st.plotly_chart(fig, use_container_width=True)

    c15, c16 = st.columns(2)
    with c15:
        # Manipulation Intensity histogram
        intensities = df_t["manipulation_intensity"].dropna().tolist() if not df_t.empty else []
        if intensities:
            fig = px.histogram(
                x=intensities, nbins=5,
                title="Manipulation Intensity Distribution (Scammer Turns)",
                labels={"x": "Intensity (1–5)", "y": "Số turns"},
                color_discrete_sequence=["#ef4444"],
                template=_TPL,
            )
            fig.update_layout(
                height=_H, margin=dict(t=50, b=40, l=40, r=20),
                xaxis=dict(dtick=1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có manipulation_intensity trong dữ liệu.")

    with c16:
        # Span Label Distribution
        if not df_s.empty:
            span_counts = df_s["span_label"].value_counts().reset_index()
            span_counts.columns = ["Label", "Count"]
            colors_sp = [SPAN_COLORS.get(l, "#94a3b8") for l in span_counts["Label"]]
            fig = go.Figure(go.Bar(
                x=span_counts["Count"].tolist(),
                y=span_counts["Label"].tolist(),
                orientation="h",
                marker_color=colors_sp,
                text=span_counts["Count"].tolist(),
                textposition="outside",
            ))
            fig.update_layout(
                title="Span Label Distribution",
                template=_TPL, height=_H, showlegend=False,
                margin=dict(t=50, b=20, l=20, r=60),
                yaxis_tickfont_size=9,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có span annotations.")

    st.markdown("---")

    # ── SECTION 5: Turn Structure ──────────────────────────────────
    st.subheader("5 · Turn Structure Analysis")

    c17, c18 = st.columns(2)
    with c17:
        # Conversation Length histogram
        fig = px.histogram(
            df_c, x="n_turns", nbins=15,
            title="Conversation Length Distribution (# Turns)",
            labels={"n_turns": "Số turns", "count": "Conversations"},
            color_discrete_sequence=["#3b82f6"], template=_TPL,
        )
        fig.update_layout(height=_H, margin=dict(t=50, b=40, l=40, r=20),
                          yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

    with c18:
        # Victim Response Type distribution
        if not df_t.empty:
            vrt_col = "response_type" if "response_type" in df_t.columns else "vrt"
            vrt_counts = (
                df_t[df_t["speaker"] == "victim"][vrt_col]
                .dropna()
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .reset_index()
            )
            vrt_counts.columns = ["Response Type", "Count"]
            if not vrt_counts.empty:
                fig = px.bar(
                    vrt_counts, x="Count", y="Response Type", orientation="h",
                    title="Victim Response Type Distribution",
                    color_discrete_sequence=["#06b6d4"], template=_TPL, text="Count",
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=_H, showlegend=False,
                    margin=dict(t=50, b=20, l=20, r=60),
                    yaxis_tickfont_size=9,
                )
                st.plotly_chart(fig, use_container_width=True)

    st.plotly_chart(plot_tactic_phase_heatmap(df_t), use_container_width=True)

    c19, c20 = st.columns(2)
    with c19:
        st.plotly_chart(plot_phase_transition_heatmap(df_t), use_container_width=True)
    with c20:
        st.plotly_chart(plot_vcs_transition_heatmap(df_t), use_container_width=True)

    st.markdown("---")

    # ── SECTION 6: Persona Analysis ───────────────────────────────
    st.subheader("6 · Persona Analysis")

    personas_convs = [c for c in convs if c.get("personas")]
    if not personas_convs:
        st.info("Không có dữ liệu personas.")
    else:
        c21, c22 = st.columns(2)
        with c21:
            # Victim Age Range
            age_counts = Counter(
                c.get("personas", {}).get("victim", {}).get("age_range", "unknown")
                for c in personas_convs
            )
            df_age = pd.DataFrame(list(age_counts.items()), columns=["Age Range", "Count"])
            fig = px.bar(
                df_age, x="Age Range", y="Count",
                title="Victim Age Range",
                color_discrete_sequence=["#3b82f6"], template=_TPL, text="Count",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=_H, margin=dict(t=50, b=40, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

        with c22:
            # Victim Vulnerability Profile
            vuln_counts = Counter(
                c.get("personas", {}).get("victim", {}).get("vulnerability_profile", "unknown")
                for c in personas_convs
            )
            df_vuln = pd.DataFrame(list(vuln_counts.items()), columns=["Profile", "Count"]).sort_values("Count")
            vuln_colors = {
                "low_digital_literacy": "#ef4444",
                "moderate_digital_literacy": "#f59e0b",
                "high_digital_literacy": "#22c55e",
                "unknown": "#94a3b8",
            }
            colors_v = [vuln_colors.get(p, "#94a3b8") for p in df_vuln["Profile"]]
            fig = go.Figure(go.Bar(
                x=df_vuln["Count"].tolist(), y=df_vuln["Profile"].tolist(),
                orientation="h", marker_color=colors_v,
                text=df_vuln["Count"].tolist(), textposition="outside",
            ))
            fig.update_layout(
                title="Victim Vulnerability Profile",
                template=_TPL, height=_H, showlegend=False,
                margin=dict(t=50, b=20, l=20, r=60),
                yaxis_tickfont_size=9,
            )
            st.plotly_chart(fig, use_container_width=True)

        c23, c24 = st.columns(2)
        with c23:
            # Scammer Speaking Register
            reg_counts = Counter(
                c.get("personas", {}).get("scammer", {}).get("speaking_register", "unknown")
                for c in personas_convs
            )
            reg_colors = {
                "formal_professional": "#6366f1", "authoritative": "#ef4444",
                "semi_formal": "#f59e0b", "casual": "#22c55e",
                "intimate": "#ec4899", "unknown": "#94a3b8",
            }
            labels_r = list(reg_counts.keys())
            fig = go.Figure(go.Pie(
                labels=labels_r,
                values=[reg_counts[l] for l in labels_r],
                hole=0.40,
                marker_colors=[reg_colors.get(l, "#94a3b8") for l in labels_r],
                textinfo="percent+label", textfont_size=10,
            ))
            fig.update_layout(
                title="Scammer Speaking Register",
                template=_TPL, height=_H,
                margin=dict(t=50, b=20, l=20, r=20),
                legend=dict(font_size=9),
            )
            st.plotly_chart(fig, use_container_width=True)

        with c24:
            # Prior Scam Knowledge of Victim
            know_counts = Counter(
                c.get("personas", {}).get("victim", {}).get("prior_scam_knowledge", "unknown")
                for c in personas_convs
            )
            know_order = ["none", "low", "medium", "high", "unknown"]
            know_colors_map = {
                "none": "#ef4444", "low": "#f97316", "medium": "#f59e0b",
                "high": "#22c55e", "unknown": "#94a3b8",
            }
            k_labels = [k for k in know_order if k in know_counts]
            fig = go.Figure(go.Bar(
                x=k_labels,
                y=[know_counts[k] for k in k_labels],
                marker_color=[know_colors_map[k] for k in k_labels],
                text=[know_counts[k] for k in k_labels],
                textposition="outside",
            ))
            fig.update_layout(
                title="Victim Prior Scam Knowledge",
                template=_TPL, height=_H, showlegend=False,
                margin=dict(t=50, b=40, l=20, r=20),
                xaxis_title="Level", yaxis_title="Count",
                yaxis=dict(range=[0, max(know_counts.values(), default=1) * 1.3]),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── SECTION 7: Quality Signals ────────────────────────────────
    st.subheader("7 · Quality Signals")

    quality_rows = []
    for conv in convs:
        q = conv.get("quality") or {}
        quality_rows.append({
            "conversation_id": conv.get("conversation_id", ""),
            "writer_id": q.get("writer_id", "unknown"),
            "iaa_score": q.get("iaa_score"),
            "expert_score": q.get("expert_authenticity_score"),
            "is_gold": q.get("is_gold", False),
            "method": q.get("annotation_method", "unknown"),
        })
    df_q = pd.DataFrame(quality_rows)

    c25, c26 = st.columns(2)
    with c25:
        # IAA Score distribution
        iaa_vals = df_q["iaa_score"].dropna().tolist()
        if iaa_vals:
            fig = px.histogram(
                x=iaa_vals, nbins=10,
                title="IAA Score Distribution",
                labels={"x": "IAA Score (Cohen's Kappa)", "y": "Conversations"},
                color_discrete_sequence=["#6366f1"], template=_TPL,
            )
            fig.add_vline(x=0.75, line_dash="dash", line_color="#22c55e",
                          annotation_text="Target ≥0.75", annotation_font_size=9)
            fig.add_vline(x=0.65, line_dash="dash", line_color="#ef4444",
                          annotation_text="Min 0.65", annotation_font_size=9)
            fig.update_layout(height=_H, margin=dict(t=50, b=40, l=40, r=20))
            st.plotly_chart(fig, use_container_width=True)

    with c26:
        # Expert Authenticity Score distribution
        exp_vals = df_q["expert_score"].dropna().tolist()
        if exp_vals:
            score_counts = Counter(int(v) for v in exp_vals)
            scores = sorted(score_counts.keys())
            score_colors_map = {1: "#ef4444", 2: "#f97316", 3: "#f59e0b", 4: "#84cc16", 5: "#22c55e"}
            fig = go.Figure(go.Bar(
                x=[str(s) for s in scores],
                y=[score_counts[s] for s in scores],
                marker_color=[score_colors_map.get(s, "#94a3b8") for s in scores],
                text=[score_counts[s] for s in scores],
                textposition="outside",
            ))
            fig.update_layout(
                title="Expert Authenticity Score (1–5)",
                template=_TPL, height=_H, showlegend=False,
                margin=dict(t=50, b=40, l=20, r=20),
                xaxis_title="Score", yaxis_title="Conversations",
            )
            st.plotly_chart(fig, use_container_width=True)

    c27, c28 = st.columns(2)
    with c27:
        # Gold vs Non-gold
        gold_c = df_q["is_gold"].sum()
        non_gold_c = len(df_q) - gold_c
        fig = go.Figure(go.Pie(
            labels=["Gold", "Non-gold"],
            values=[gold_c, non_gold_c],
            hole=0.42,
            marker_colors=["#f59e0b", "#e2e8f0"],
            textinfo="percent+label+value",
            textfont_size=10,
        ))
        fig.update_layout(
            title="Gold vs Non-Gold Samples",
            template=_TPL, height=_H,
            margin=dict(t=50, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c28:
        # Annotation Method distribution
        method_counts = df_q["method"].value_counts().reset_index()
        method_counts.columns = ["Method", "Count"]
        fig = px.bar(
            method_counts, x="Count", y="Method", orientation="h",
            title="Annotation Method",
            color_discrete_sequence=["#10b981"], template=_TPL, text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=_H, showlegend=False,
            margin=dict(t=50, b=20, l=20, r=60),
            yaxis_tickfont_size=9,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Raw Tables ─────────────────────────────────────────────────
    st.subheader("Raw Tables")
    with st.expander("Conversation Table"):
        st.dataframe(df_c, use_container_width=True)
        st.download_button(
            "⬇ CSV", df_c.to_csv(index=False).encode("utf-8"),
            "conversations_v2.csv", "text/csv",
        )
    with st.expander("Turn Table"):
        df_t_disp = df_t.drop(columns=["ssat", "speech_acts"], errors="ignore")
        st.dataframe(df_t_disp, use_container_width=True)


# ─── Helpers ──────────────────────────────────────────────────────

def _kpi(col, label: str, value):
    col.metric(label, value)


def _mean_field(convs, getter) -> float | None:
    vals = [getter(c) for c in convs if getter(c) is not None]
    return round(sum(vals) / len(vals), 3) if vals else None
