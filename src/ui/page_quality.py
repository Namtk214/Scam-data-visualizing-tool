"""
page_quality.py — Quality Metrics page: 9 subtabs AI, DS, TCS, LDS, PCS, VSVS, AQS, DBR, MER.
Render 25 benchmark visualizations theo implementation_plan.md.
"""
import streamlit as st
import pandas as pd

from src.metrics.ambiguity_index import dataset_ai_report
from src.metrics.difficulty_score import dataset_ds_report
from src.metrics.tactic_coverage import compute_tcs
from src.metrics.linguistic_diversity import compute_lds
from src.metrics.phase_completeness import compute_pcs
from src.metrics.victim_state_validity import dataset_vsvs_report, compute_vsvs
from src.metrics.annotation_quality import compute_aqs
from src.metrics.dataset_balance import compute_dbr
from src.metrics.master_report import compute_mer

from src.viz.charts_quality import (
    # AI
    plot_ai_badge,
    plot_ai_intensity_flow,
    plot_ai_register_donut,
    plot_ai_confusion_bubble,
    plot_ai_attack_deflect,
    plot_ai_outcome_pie,
    # DS
    plot_ds_ai_scatter,
    plot_ds_tactic_bar,
    plot_ds_phase_progress,
    plot_ds_ttr_histogram,
    plot_ds_state_transition,
    plot_ds_adaptability_timeline,
    # TCS
    plot_tcs_horizontal_bar,
    plot_tcs_lorenz_curve,
    # LDS
    plot_lds_wordcloud,
    plot_lds_similarity_heatmap,
    plot_lds_summary_cards,
    # PCS
    plot_pcs_stacked_area,
    plot_pcs_sankey,
    # VSVS
    plot_vsvs_transition_heatmap,
    # AQS
    plot_aqs_confusion_matrix,
    plot_aqs_annotator_radar,
    plot_aqs_span_heatmap,
    # DBR
    plot_dbr_radar,
    plot_dbr_stacked_bar,
    # MER
    plot_mer_dashboard,
)


def render(session):
    st.header("📈 Quality Metrics")
    st.caption(
        "25 benchmark visualizations đánh giá chất lượng dataset ViScamDial-Bench theo 9 modules. "
        "Mỗi tab hiển thị các biểu đồ chi tiết kèm giải thích ý nghĩa."
    )
    convs = session.get_filtered()
    if not convs:
        st.info("No data. Load conversations in Data Input tab.")
        return

    tabs = st.tabs(["🎯 AI", "🔥 DS", "🧩 TCS", "📝 LDS", "🔗 PCS", "🧠 VSVS", "✅ AQS", "⚖️ DBR", "🏅 MER"])

    # ── AI ─────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Ambiguity Index (AI)")
        st.caption(
            "Đo mức độ tinh vi / khó nhận diện của kịch bản lừa đảo. "
            "Score [0–1]: thấp = rõ ràng, cao = nhập nhằng. "
            "6 factors: thiếu SA_REQUEST, intensity thấp, register trang trọng, victim rối, deflect nhiều, outcome partial. "
            "Target: Mean AI 0.30–0.55 | Low 25–35% | Medium 40–50% | High 20–30%."
        )
        with st.spinner("Computing AI..."):
            ai_report = dataset_ai_report(convs)
        _show_warnings(ai_report.get("warnings", []))

        lvl_dist = ai_report.get("level_distribution", {})
        _kpi_row({
            "Mean AI Score": f"{ai_report.get('mean_score', 0):.3f}",
            "Low": str(lvl_dist.get("low", 0)),
            "Medium": str(lvl_dist.get("medium", 0)),
            "High": str(lvl_dist.get("high", 0)),
        })

        # Chart 1: Badge
        st.caption("**#1 — Indicator Badge**: Mean AI score có nằm trong target range (0.30–0.55) không.")
        st.plotly_chart(plot_ai_badge(ai_report), use_container_width=True)

        # Chart 2: Intensity Flow
        st.caption("**#2 — Intensity Flow**: Diễn biến cường độ thao túng của scammer qua các turns.")
        conv_ids = [c["conversation_id"] for c in convs]
        sel_intensity = st.selectbox(
            "Chọn conversation (để trống = xem trung bình dataset):",
            ["— Dataset average —"] + conv_ids,
            key="ai_intensity_sel",
        )
        selected_id = None if sel_intensity == "— Dataset average —" else sel_intensity
        st.plotly_chart(plot_ai_intensity_flow(convs, selected_id), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            # Chart 3: Register Donut
            st.caption("**#3 — Register Donut**: Phân bổ phong cách nói chuyện (speaking_register) của scammer.")
            st.plotly_chart(plot_ai_register_donut(convs), use_container_width=True)
        with c2:
            # Chart 4: Confusion Bubble
            st.caption("**#4 — Confusion Bubble**: Mật độ bối rối nạn nhân theo conversation (bong bóng = AI score).")
            st.plotly_chart(
                plot_ai_confusion_bubble(ai_report.get("per_conversation", []), convs),
                use_container_width=True,
            )

        # Chart 5: Attack-Deflect Sankey
        st.caption("**#5 — Attack→Deflect Flow**: Sankey luồng chuyển từ SA_THREAT/SA_URGENCY sang SA_DEFLECT.")
        st.plotly_chart(plot_ai_attack_deflect(convs), use_container_width=True)

        # Chart 6: Outcome Pie
        st.caption("**#6 — Outcome Weight Pie**: Phân bổ outcomes được tính theo trọng số AI score.")
        st.plotly_chart(
            plot_ai_outcome_pie(ai_report.get("per_conversation", []), convs),
            use_container_width=True,
        )

    # ── DS ─────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Difficulty Score (DS)")
        st.caption(
            "Đo độ khó tổng thể cho NLP model. "
            "Tổng hợp 6 sub-scores: ambiguity, tactic density, phase complexity, TTR, victim confusion, scammer adaptability. "
            "Tiers: Easy <0.30 | Medium 0.30–0.55 | Hard 0.55–0.75 | Expert ≥0.75."
        )
        with st.spinner("Computing DS..."):
            ds_report = dataset_ds_report(convs)
        _show_warnings(ds_report.get("warnings", []))

        tier_dist = ds_report.get("tier_distribution", {})
        _kpi_row({
            "Mean DS Score": f"{ds_report.get('mean_score', 0):.3f}",
            "Easy": str(tier_dist.get("easy", 0)),
            "Medium": str(tier_dist.get("medium", 0)),
            "Hard": str(tier_dist.get("hard", 0)),
            "Expert": str(tier_dist.get("expert", 0)),
        })

        # Chart 7: AI vs DS Scatter
        st.caption("**#7 — AI vs DS Scatter**: Tương quan giữa Ambiguity Index và Difficulty Score per conversation.")
        with st.spinner("Computing AI for scatter..."):
            ai_per = dataset_ai_report(convs).get("per_conversation", [])
        ds_per = ds_report.get("per_conversation", [])
        st.plotly_chart(plot_ds_ai_scatter(ai_per, ds_per), use_container_width=True)

        # Chart 8: Tactic Bar
        st.caption("**#8 — Tactic Distribution per Conv**: Số lượng từng speech act trong top 15 conversations.")
        st.plotly_chart(plot_ds_tactic_bar(convs), use_container_width=True)

        # Chart 9: Phase Progress
        st.caption("**#9 — Phase Completion Progress**: Tỷ lệ phủ từng phase dạng thanh tiến độ.")
        with st.spinner("Computing PCS for phase progress..."):
            pcs_quick = compute_pcs(convs)
        st.plotly_chart(plot_ds_phase_progress(pcs_quick), use_container_width=True)

        # Chart 10: TTR Histogram
        st.caption("**#10 — TTR Histogram**: Phân phối Type-Token Ratio của scammer text per conversation.")
        st.plotly_chart(plot_ds_ttr_histogram(convs), use_container_width=True)

        # Chart 11: State Transition Sankey
        st.caption("**#11 — VCS State Transition**: Sankey luồng chuyển trạng thái tâm lý nạn nhân.")
        with st.spinner("Computing VSVS for state transition..."):
            vsvs_quick = dataset_vsvs_report(convs)
        st.plotly_chart(plot_ds_state_transition(vsvs_quick), use_container_width=True)

        # Chart 12: Adaptability Timeline
        st.caption("**#12 — Adaptability Timeline**: Thời điểm scammer thay đổi chiến thuật trong một conversation.")
        sel_adapt = st.selectbox(
            "Chọn conversation để xem timeline:",
            [c["conversation_id"] for c in convs],
            key="ds_adapt_sel",
        )
        if sel_adapt:
            conv_adapt = next((c for c in convs if c["conversation_id"] == sel_adapt), None)
            if conv_adapt:
                st.plotly_chart(plot_ds_adaptability_timeline(conv_adapt), use_container_width=True)

    # ── TCS ────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Tactic Coverage Score (TCS)")
        st.caption(
            "Kiểm tra đa dạng và cân bằng của span tags trong dataset. "
            "Gini coefficient đo mức độ lệch phân phối — Gini > 0.40 = mất cân bằng. "
            "TCS cao = dataset phủ đều nhiều loại chiến thuật."
        )
        with st.spinner("Computing TCS..."):
            tcs = compute_tcs(convs)
        _show_warnings(tcs.get("warnings", []))

        _kpi_row({
            "TCS Score": f"{tcs.get('tcs_score', 0):.3f}",
            "Gini Coefficient": f"{tcs.get('gini_coefficient', 0):.3f}",
            "Uncovered Tactics": str(len(tcs.get("uncovered_tactics", []))),
        })

        # Chart 13: Horizontal Bar
        st.caption("**#13 — Span Tag Frequency**: Tần suất xuất hiện của mỗi span tag trong scammer turns.")
        st.plotly_chart(plot_tcs_horizontal_bar(tcs), use_container_width=True)

        # Chart 14: Lorenz Curve
        st.caption("**#14 — Lorenz Curve**: Đường bất bình đẳng phân phối tactic. Gini cao = mất cân bằng.")
        st.plotly_chart(plot_tcs_lorenz_curve(tcs), use_container_width=True)

        if tcs.get("uncovered_tactics"):
            with st.expander(f"Span tags chưa xuất hiện ({len(tcs['uncovered_tactics'])})"):
                st.write(", ".join(tcs["uncovered_tactics"]))

    # ── LDS ────────────────────────────────────────────────────────
    with tabs[3]:
        st.subheader("Linguistic Diversity Score (LDS)")
        st.caption(
            "Đánh giá đa dạng ngôn ngữ của scammer text. "
            "TTR: tỷ lệ từ vựng độc đáo (cần >0.30). "
            "Mean cosine sim: độ trùng lặp nội dung (cần <0.35). "
            "Near-dup: cặp quá giống nhau (cần <5%)."
        )
        with st.spinner("Computing LDS..."):
            lds = compute_lds(convs)
        _show_warnings(lds.get("warnings", []))

        # Summary cards
        cards = plot_lds_summary_cards(lds)
        cols = st.columns(len(cards))
        for col, card in zip(cols, cards):
            icon = "✅" if card["ok"] else "❌"
            ok_bg = "#f0fdf4" if card["ok"] else "#fef2f2"
            border = "#86efac" if card["ok"] else "#fca5a5"
            txt = "#166534" if card["ok"] else "#991b1b"
            col.markdown(
                f'<div style="background:{ok_bg};border:1px solid {border};border-radius:8px;padding:10px 13px;">'
                f'<div style="font-size:10px;color:#6b7280;margin-bottom:3px">{icon} {card["label"]}</div>'
                f'<div style="font-size:16px;font-weight:700;color:{txt}">{card["value"]}</div>'
                f'<div style="font-size:10px;color:#9ca3af;margin-top:2px">target: {card["target"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")

        # Chart 15: Word Cloud (bar)
        st.caption("**#15 — Scammer Vocabulary**: Top 30 từ phổ biến nhất trong utterances của scammer.")
        st.plotly_chart(plot_lds_wordcloud(convs), use_container_width=True)

        # Chart 16: Similarity Heatmap
        st.caption(
            "**#16 — Similarity Heatmap**: Ma trận cosine similarity giữa các conversations "
            f"(sample ≤ 20, hiện n={min(20, len(convs))})."
        )
        st.plotly_chart(plot_lds_similarity_heatmap(convs), use_container_width=True)

        if lds.get("near_duplicate_pairs"):
            with st.expander(f"Near-duplicate pairs ({lds.get('near_dup_count', 0)})"):
                for p in lds["near_duplicate_pairs"][:10]:
                    st.write(f"**{p['conv_a']}** ↔ **{p['conv_b']}** — Sim: {p['similarity']:.3f}")

    # ── PCS ────────────────────────────────────────────────────────
    with tabs[4]:
        st.subheader("Phase Completeness Score (PCS)")
        st.caption(
            "Kiểm tra tỷ lệ phủ 6 giai đoạn (P1–P6) và tính hợp lệ của sequence. "
            "P5 (Compliance Extract) phải ≥40% để đảm bảo benchmark task T5. "
            "Sequence không hợp lệ = phase giảm dần (P3→P1) thay vì tăng."
        )
        with st.spinner("Computing PCS..."):
            pcs = compute_pcs(convs)
        _show_warnings(pcs.get("warnings", []))

        _compact_stats([
            ("PCS Score", f"{pcs.get('pcs_score', 0):.3f}"),
            ("P5 Coverage", f"{pcs.get('p5_ratio', 0):.1%}"),
            ("Invalid Seqs", str(pcs.get("invalid_seq_count", 0))),
            ("P5 Status", "✅ Pass" if pcs.get("p5_ok") else "❌ Fail"),
        ])

        # Chart 17: Stacked Area
        st.caption("**#17 — Phase Distribution Stacked Area**: Tỷ lệ tích lũy conversations có mỗi phase theo thứ tự dataset.")
        st.plotly_chart(plot_pcs_stacked_area(convs), use_container_width=True)

        # Chart 18: Sankey
        st.caption("**#18 — Phase Transition Sankey**: Luồng chuyển tiếp giữa các giai đoạn conversation.")
        st.plotly_chart(plot_pcs_sankey(convs), use_container_width=True)

        if pcs.get("invalid_sequences"):
            with st.expander("Invalid phase sequences"):
                for inv in pcs["invalid_sequences"]:
                    st.write(f"**{inv['conversation_id']}**: {inv['violations']}")

    # ── VSVS ───────────────────────────────────────────────────────
    with tabs[5]:
        st.subheader("Victim State Validity Score (VSVS)")
        st.caption(
            "Kiểm tra chuỗi trạng thái tâm lý nạn nhân có logic không (NEUTRAL→CURIOUS→FEARFUL→COMPLIANT…). "
            "Transition không hợp lệ = nhảy trạng thái bất hợp lý theo schema VALID_TRANSITIONS. "
            "Validity ratio ≥0.85 = hợp lệ."
        )
        with st.spinner("Computing VSVS..."):
            vsvs = dataset_vsvs_report(convs)
        _show_warnings(vsvs.get("warnings", []))

        _compact_stats([
            ("Mean Validity", f"{vsvs.get('mean_validity_ratio', 0):.3f}"),
            ("Valid convs", str(vsvs.get("n_valid", 0))),
            ("Invalid convs", str(vsvs.get("n_invalid", 0))),
        ])

        # Chart 19: Transition Heatmap
        st.caption(
            "**#19 — Transition Matrix Heatmap**: Ma trận xác suất chuyển trạng thái tâm lý nạn nhân. "
            "Ô sáng ở vị trí không mong đợi = lỗi annotation."
        )
        st.plotly_chart(
            plot_vsvs_transition_heatmap(vsvs.get("transition_matrix", {})),
            use_container_width=True,
        )

        if vsvs.get("all_invalid_transitions"):
            with st.expander("Invalid transitions detail"):
                df_inv = pd.DataFrame(vsvs["all_invalid_transitions"][:20])
                st.dataframe(df_inv, use_container_width=True)

    # ── AQS ────────────────────────────────────────────────────────
    with tabs[6]:
        st.subheader("Annotation Quality Score (AQS)")
        st.caption(
            "3 chiều: (1) Cohen's Kappa so với gold set — cần ≥0.75. "
            "(2) Annotator entropy — phát hiện lazy annotation. "
            "(3) Span completeness — turns dùng SA_REQUEST/THREAT phải có span ≥80%. "
            "Upload gold set ở sidebar để tính đầy đủ Kappa."
        )
        gold_set = session.gold_set if hasattr(session, "gold_set") else None
        if not gold_set:
            st.info("💡 Upload gold set in sidebar for full Kappa computation (Charts #20, #21).")
        with st.spinner("Computing AQS..."):
            aqs = compute_aqs(convs, gold_set)
        _show_warnings(aqs.get("warnings", []))

        sc = aqs.get("span_completeness", {})
        _compact_stats([
            ("AQS Score", f"{aqs.get('aqs_score', 0):.3f}"),
            ("Span Completeness", f"{sc.get('completeness_ratio', 0):.1%}"),
            ("Mean Kappa", str(aqs.get("mean_kappa") or "N/A (no gold set)")),
        ])

        # Chart 20: Confusion Matrix (kappa heatmap)
        st.caption("**#20 — Confusion Matrix (Kappa)**: Mức độ đồng thuận annotator vs gold set per label.")
        st.plotly_chart(plot_aqs_confusion_matrix(aqs), use_container_width=True)

        # Chart 21: Annotator Radar
        st.caption("**#21 — Annotator Radar**: Độ đa dạng nhãn (entropy) của từng annotator — phát hiện lazy.")
        ent_data = aqs.get("annotator_entropy", {})
        st.plotly_chart(plot_aqs_annotator_radar(ent_data), use_container_width=True)

        # Chart 22: Span Heatmap
        st.caption("**#22 — Span Coverage Heatmap**: % turns có span annotation per tactic × annotator.")
        st.plotly_chart(plot_aqs_span_heatmap(convs), use_container_width=True)

    # ── DBR ────────────────────────────────────────────────────────
    with tabs[7]:
        st.subheader("Dataset Balance Report (DBR)")
        st.caption(
            "Đo cân bằng dataset qua 8 chiều: scenario, outcome, length_class, speech_acts, "
            "victim_state, domain_l1, difficulty_tier, ambiguity_level. "
            "Dùng normalized Shannon entropy [0–1]. Mean ≥0.65 = acceptable."
        )
        with st.spinner("Computing DBR..."):
            dbr = compute_dbr(convs)
        _show_warnings(dbr.get("warnings", []))

        dbr_ok = "✅ OK" if dbr.get("balance_ok") else "❌ Below target"
        _compact_stats([
            ("Mean Balance Score", f"{dbr.get('mean_balance_score', 0):.3f}"),
            ("Status (≥0.65)", dbr_ok),
        ])

        # Chart 23: Radar
        st.caption("**#23 — DBR Radar**: Cân bằng dataset trên 8 chiều phân loại (normalized entropy).")
        st.plotly_chart(plot_dbr_radar(dbr.get("normalized_entropy", {})), use_container_width=True)

        # Chart 24: Stacked Bar
        st.caption("**#24 — Scenario Representativeness**: Số conversations theo domain_l1 × outcome.")
        st.plotly_chart(plot_dbr_stacked_bar(convs), use_container_width=True)

    # ── MER ────────────────────────────────────────────────────────
    with tabs[8]:
        st.subheader("Master Evaluation Report (MER)")
        st.caption(
            "Tổng hợp tất cả 8 modules → quyết định Release Readiness. "
            "READY FOR RELEASE (≤3 warnings, 0 errors) | "
            "NEEDS REVISION (>3 warnings) | "
            "BLOCKED (có errors nghiêm trọng như near-dup >5% hoặc kappa <0.65)."
        )
        gold_set = session.gold_set if hasattr(session, "gold_set") else None
        with st.spinner("Computing MER (running all modules)..."):
            mer = compute_mer(convs, gold_set)

        summary = mer.get("summary", {})
        status = mer.get("status", "UNKNOWN")

        # Status banner
        status_color = {
            "READY FOR RELEASE": "#22c55e",
            "NEEDS REVISION": "#f59e0b",
            "BLOCKED": "#ef4444",
        }
        color = status_color.get(status, "#6b7280")
        st.markdown(
            f'<div style="background:{color}22;border:2px solid {color};border-radius:10px;'
            f'padding:12px 16px;text-align:center;">'
            f'<div style="color:{color};font-size:18px;font-weight:700;margin:0">🏁 {status}</div>'
            f'<div style="color:{color};font-size:12px;margin-top:6px">{mer.get("recommendation", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        # Chart 25: MER Dashboard
        st.caption("**#25 — MER Dashboard**: 5 điều kiện release với trạng thái PASS/FAIL.")
        summary["status"] = status
        st.plotly_chart(plot_mer_dashboard(summary), use_container_width=True)

        _compact_stats([
            ("Total Conversations", str(summary.get("total_conversations", 0))),
            ("Errors", str(summary.get("error_count", 0))),
            ("Warnings", str(summary.get("warning_count", 0))),
            ("Mean AI Score", f"{summary.get('mean_ambiguity') or 0:.3f}"),
        ])

        if mer.get("all_errors"):
            with st.expander(f"❌ Errors ({len(mer['all_errors'])})"):
                for e in mer["all_errors"]:
                    st.error(e)
        if mer.get("all_warnings"):
            with st.expander(f"⚠️ Warnings ({len(mer['all_warnings'])})"):
                for w in mer["all_warnings"]:
                    st.warning(w)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _kpi_row(metrics: dict):
    """Compact stat row — custom HTML card."""
    cols = st.columns(len(metrics))
    for col, (label, val) in zip(cols, metrics.items()):
        col.markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:11px 14px;">'
            f'<div style="font-size:12px;color:#6b7280;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:17px;font-weight:700;color:#1e293b;word-break:break-word">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _compact_stats(items: list):
    """Hiển thị stats theo hàng ngang."""
    cols = st.columns(len(items))
    for col, (label, val) in zip(cols, items):
        is_long = len(str(val)) > 20
        val_size = "13px" if is_long else "17px"
        col.markdown(
            f'<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:7px;padding:9px 13px;">'
            f'<div style="font-size:11px;color:#0369a1;margin-bottom:3px;font-weight:600">{label}</div>'
            f'<div style="font-size:{val_size};color:#0c4a6e;word-break:break-word;line-height:1.4">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _show_warnings(warnings: list):
    if warnings:
        with st.expander(f"⚠️ {len(warnings)} warnings", expanded=False):
            for w in warnings:
                st.warning(w)
