"""
page_export.py — Export page: JSON, CSV, metric reports, summary.
"""
import json
import io
import streamlit as st
import pandas as pd

from src.stats import build_conversation_df, flatten_to_turn_df, flatten_to_span_df
from src.metrics.master_report import compute_mer
from src.metrics.ambiguity_index import dataset_ai_report
from src.metrics.difficulty_score import dataset_ds_report
from src.metrics.tactic_coverage import compute_tcs
from src.metrics.linguistic_diversity import compute_lds
from src.metrics.phase_completeness import compute_pcs
from src.metrics.victim_state_validity import dataset_vsvs_report
from src.metrics.dataset_balance import compute_dbr


def render(session):
    st.header("💾 Export / Reports")
    convs = session.get_filtered()

    if not convs:
        st.info("No data to export.")
        return

    st.info(f"Exporting **{len(convs)}** conversations (filtered).")

    df_c = build_conversation_df(convs)
    df_t = flatten_to_turn_df(convs)
    df_s = flatten_to_span_df(convs)

    # ── Tables ────────────────────────────────────────────────────
    st.subheader("📊 Tables (CSV)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇ Conversations CSV", df_c.to_csv(index=False).encode("utf-8"),
                           "conversations_v2.csv", "text/csv")
    with c2:
        dt = df_t.drop(columns=["ssat", "speech_acts"], errors="ignore")
        st.download_button("⬇ Turns CSV", dt.to_csv(index=False).encode("utf-8"),
                           "turns_v2.csv", "text/csv")
    with c3:
        if not df_s.empty:
            st.download_button("⬇ Spans CSV", df_s.to_csv(index=False).encode("utf-8"),
                               "spans_v2.csv", "text/csv")

    st.markdown("---")

    # ── Normalized Dataset JSON ────────────────────────────────────
    st.subheader("📄 Normalized Dataset JSON")
    dataset_json = json.dumps(convs, ensure_ascii=False, indent=2)
    st.download_button("⬇ normalized_dataset.json", dataset_json.encode("utf-8"),
                       "normalized_dataset.json", "application/json")

    st.markdown("---")

    # ── Metric Reports ─────────────────────────────────────────────
    st.subheader("📈 Individual Metric Reports (JSON)")
    gold_set = session.gold_set if hasattr(session, "gold_set") else None

    report_fns = {
        "ai_report.json": lambda: dataset_ai_report(convs),
        "ds_report.json": lambda: dataset_ds_report(convs),
        "tcs_report.json": lambda: compute_tcs(convs),
        "lds_report.json": lambda: compute_lds(convs),
        "pcs_report.json": lambda: compute_pcs(convs),
        "vsvs_report.json": lambda: dataset_vsvs_report(convs),
        "dbr_report.json": lambda: compute_dbr(convs),
    }

    col_r = st.columns(4)
    for i, (fname, fn) in enumerate(report_fns.items()):
        with col_r[i % 4]:
            if st.button(f"Generate {fname.replace('.json','').upper()}", key=f"gen_{fname}"):
                try:
                    data = fn()
                    st.download_button(
                        f"⬇ {fname}", 
                        json.dumps(_make_serializable(data), ensure_ascii=False, indent=2).encode("utf-8"),
                        fname, "application/json", key=f"dl_{fname}"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")

    # ── Master Report ──────────────────────────────────────────────
    st.subheader("🏅 Master Evaluation Report (MER)")
    if st.button("Generate MER (runs all metrics)", type="primary"):
        with st.spinner("Computing MER..."):
            mer = compute_mer(convs, gold_set)
        st.download_button(
            "⬇ master_report.json",
            json.dumps(_make_serializable(mer), ensure_ascii=False, indent=2).encode("utf-8"),
            "master_report.json", "application/json"
        )
        status = mer.get("status", "UNKNOWN")
        color = {"READY FOR RELEASE": "success", "NEEDS REVISION": "warning", "BLOCKED": "error"}
        getattr(st, color.get(status, "info"))(f"Status: {status} — {mer.get('recommendation', '')}")

    st.markdown("---")

    # ── Summary TXT ────────────────────────────────────────────────
    st.subheader("📝 Summary (Markdown)")
    with st.spinner("Building summary..."):
        summary_md = _build_summary_md(convs, df_c)
    st.download_button("⬇ summary.md", summary_md.encode("utf-8"), "summary.md", "text/markdown")
    with st.expander("Preview summary"):
        st.markdown(summary_md)


def _make_serializable(obj):
    """Recursively convert non-serializable types."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(i) for i in obj]
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


def _build_summary_md(convs, df_c) -> str:
    n = len(convs)
    n_turns = sum(len(c.get("turns", [])) for c in convs)
    n_spans = sum(len(t.get("span_annotations") or []) for c in convs for t in c.get("turns", []))
    outcomes = {}
    for c in convs:
        o = c.get("conversation_meta", {}).get("outcome", "UNKNOWN")
        outcomes[o] = outcomes.get(o, 0) + 1

    lines = [
        "# ViScamDial-Bench Dataset Summary",
        "",
        f"- **Total conversations:** {n}",
        f"- **Total turns:** {n_turns}",
        f"- **Total span annotations:** {n_spans}",
        "",
        "## Outcome Distribution",
    ]
    for o, cnt in sorted(outcomes.items()):
        lines.append(f"- {o}: {cnt} ({cnt/n:.0%})")

    lines += [
        "",
        "## Domain Distribution",
    ]
    domains = {}
    for c in convs:
        d = c.get("scenario", {}).get("domain_l1", "UNKNOWN")
        domains[d] = domains.get(d, 0) + 1
    for d, cnt in sorted(domains.items()):
        lines.append(f"- {d}: {cnt}")

    lines += [
        "",
        "*Generated by ViScamDial Visualization Tool v2*",
    ]
    return "\n".join(lines)
