"""
page_benchmark.py — Benchmark Readiness page: T1-T7 summary.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from collections import Counter

from src.constants import BENCHMARK_TASKS
from src.schema import VALID_SSAT, VALID_VCS_V2


def render(session):
    st.header("🏆 Benchmark Readiness")
    convs = session.get_filtered()
    if not convs:
        st.info("No data. Load conversations in Data Input tab.")
        return

    st.markdown("Thống kê data coverage cho 7 benchmark tasks (T1–T7). Tool không train/eval model — chỉ hiển thị phân phối nhãn và sẵn sàng data.")

    task_tabs = st.tabs([f"T{i}" for i in range(1, 8)])

    # T1: Scam Detection
    with task_tabs[0]:
        _task_header("T1", "Scam Detection", "Phân loại scam/not-scam từ toàn bộ hội thoại.")
        outcome_counts = Counter(
            c.get("conversation_meta", {}).get("outcome", "UNKNOWN") for c in convs
        )
        df = pd.DataFrame(list(outcome_counts.items()), columns=["Label", "Count"])
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df, names="Label", values="Count", title="T1 Label Distribution",
                         template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df, use_container_width=True)
            st.metric("Total samples", len(convs))
            binary_count = sum(1 for c in convs if c.get("conversation_meta", {}).get("outcome") in
                               {"FULL_COMPLIANCE", "SCAM"})
            st.metric("Clear scam samples", binary_count)

    # T2: Scenario Classification
    with task_tabs[1]:
        _task_header("T2", "Scenario Classification", "Phân loại kịch bản lừa đảo (30 classes trong full dataset).")
        scen_counts = Counter(
            c.get("scenario", {}).get("id", "UNKNOWN") for c in convs
        )
        df = pd.DataFrame(list(scen_counts.items()), columns=["Scenario ID", "Count"]).sort_values("Count", ascending=False)
        st.dataframe(df, use_container_width=True)
        fig = px.bar(df.head(15), x="Count", y="Scenario ID", orientation="h",
                     title="T2 Scenario Distribution (top 15)",
                     template="plotly_white", color_discrete_sequence=["#6366f1"])
        st.plotly_chart(fig, use_container_width=True)
        st.metric("Unique scenarios", len(scen_counts))

    # T3: Phase Segmentation
    with task_tabs[2]:
        _task_header("T3", "Phase Segmentation", "Gắn nhãn giai đoạn cho từng turn.")
        from src.stats import flatten_to_turn_df
        df_t = flatten_to_turn_df(convs)
        phase_counts = Counter()
        turn_per_phase: Counter = Counter()
        for conv in convs:
            for t in conv.get("turns", []):
                ph = t.get("phase") or "NONE"
                phase_counts[ph] += 1
                turn_per_phase[ph] += 1

        df_ph = pd.DataFrame(list(phase_counts.items()), columns=["Phase", "Turn Count"]).sort_values("Phase")
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_ph, x="Phase", y="Turn Count", title="T3 Phase Turn Distribution",
                         template="plotly_white", color_discrete_sequence=["#f59e0b"])
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df_ph, use_container_width=True)
            annotated = sum(1 for conv in convs for t in conv.get("turns", []) if t.get("phase"))
            total_turns = sum(len(c.get("turns", [])) for c in convs)
            st.metric("Phase-annotated turns", f"{annotated}/{total_turns} ({annotated/max(total_turns,1):.0%})")

    # T4: Tactic Classification
    with task_tabs[3]:
        _task_header("T4", "Tactic Classification (SSAT)", "Multi-label classification của speech acts cho từng scammer turn.")
        ssat_counts: Counter = Counter()
        for conv in convs:
            for t in conv.get("turns", []):
                if t.get("speaker") == "scammer":
                    for sa in (t.get("speech_acts") or []):
                        ssat_counts[sa] += 1
        df_sa = pd.DataFrame(list(ssat_counts.items()), columns=["Tactic", "Count"]).sort_values("Count", ascending=False)
        fig = px.bar(df_sa, x="Tactic", y="Count", title="T4 SSAT Label Frequency",
                     template="plotly_white", color="Tactic",
                     color_discrete_map=__import__("src.schema", fromlist=["SSAT_COLORS"]).SSAT_COLORS)
        st.plotly_chart(fig, use_container_width=True)
        scammer_turns = sum(1 for c in convs for t in c.get("turns", []) if t.get("speaker") == "scammer")
        st.metric("Total scammer turns (T4 samples)", scammer_turns)
        annotated_turns = sum(1 for c in convs for t in c.get("turns", [])
                              if t.get("speaker") == "scammer" and t.get("speech_acts"))
        st.metric("SSAT-annotated turns", f"{annotated_turns} ({annotated_turns/max(scammer_turns,1):.0%})")

    # T5: Outcome Prediction
    with task_tabs[4]:
        _task_header("T5", "Outcome Prediction", "Dự đoán outcome từ P1-P3 prefix của hội thoại.")
        p1_p3_phases = {"P1", "P2", "P3"}
        available = 0
        for conv in convs:
            turns = conv.get("turns", [])
            phases = {t.get("phase") for t in turns if t.get("phase")}
            if phases & p1_p3_phases:
                available += 1
        col1, col2, col3 = st.columns(3)
        col1.metric("Total conversations", len(convs))
        col2.metric("With P1-P3 prefix", available)
        col3.metric("Coverage", f"{available/max(len(convs),1):.0%}")
        st.info("T5 dùng prefix P1-P3 để dự đoán outcome. Coverage thể hiện % conversations có đủ dữ liệu prefix.")

    # T6: Victim State Tracking
    with task_tabs[5]:
        _task_header("T6", "Victim State Tracking (VCS)", "Dự đoán cognitive state sequence cho victim.")
        vcs_counts: Counter = Counter()
        for conv in convs:
            for t in conv.get("turns", []):
                if t.get("speaker") == "victim" and t.get("cognitive_state"):
                    vcs_counts[t["cognitive_state"]] += 1
        victim_turns = sum(1 for c in convs for t in c.get("turns", []) if t.get("speaker") == "victim")
        annotated_vcs = sum(vcs_counts.values())
        df_vcs = pd.DataFrame(list(vcs_counts.items()), columns=["State", "Count"]).sort_values("Count", ascending=False)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_vcs, x="State", y="Count", title="T6 VCS Distribution",
                         template="plotly_white",
                         color_discrete_sequence=["#8b5cf6"])
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(df_vcs, use_container_width=True)
            st.metric("Victim turns (T6 samples)", victim_turns)
            st.metric("VCS-annotated turns", f"{annotated_vcs} ({annotated_vcs/max(victim_turns,1):.0%})")

    # T7: Ambiguity-Stratified Evaluation
    with task_tabs[6]:
        _task_header("T7", "Ambiguity-Stratified Evaluation", "Đánh giá model per ambiguity tier — tier counts & benchmark readiness.")
        amb_counts = Counter(
            c.get("conversation_meta", {}).get("ambiguity_level", "unknown") for c in convs
        )
        df_amb = pd.DataFrame(list(amb_counts.items()), columns=["Ambiguity Level", "Count"])
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_amb, x="Ambiguity Level", y="Count", title="T7 Tier Distribution",
                         template="plotly_white", color_discrete_sequence=["#ec4899"])
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            total = len(convs)
            for tier, cnt in sorted(amb_counts.items()):
                pct = cnt / total * 100
                icon = "✅" if cnt >= 20 else "⚠️"
                st.write(f"{icon} **{tier}**: {cnt} conversations ({pct:.0f}%)")
            st.info("Target: ≥ 20 conversations per tier for reliable stratified evaluation.")


def _task_header(tid: str, name: str, desc: str):
    task = BENCHMARK_TASKS.get(tid, {})
    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:16px;">
        <h3 style="margin:0;color:#1e293b">{tid}: {name}</h3>
        <p style="color:#64748b;margin:4px 0 0 0">{desc}</p>
        <div style="margin-top:8px;font-size:12px;color:#94a3b8">
            Input: <code>{task.get('input','')}</code> → Output: <code>{task.get('output','')}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)
