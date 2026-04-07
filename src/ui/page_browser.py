"""
page_browser.py — Data Browser page: filter, view conversation cards.
"""
from typing import List, Dict, Any
import streamlit as st

from src.schema import SPAN_COLORS, VALID_DOMAIN_L1
from src.viz.charts_detail import plot_ds_radar_single


def render(session):
    st.header("🔎 Data Browser")

    convs = session.get_filtered()
    if not convs:
        st.info("No conversations match the current filters. Load data in Data Input tab.")
        return

    # Search
    kw = st.text_input("Search (title, text, ID)", placeholder="công an, OTP, Shopee...", key="browser_search")
    if kw:
        kw_lower = kw.lower()
        convs = [
            c for c in convs
            if kw_lower in c.get("conversation_id", "").lower()
            or kw_lower in (c.get("scenario", {}) or {}).get("name", "").lower()
            or any(kw_lower in t.get("text", "").lower() for t in c.get("turns", []))
        ]

    st.caption(f"Showing **{len(convs)}** conversations after filters.")

    if not convs:
        st.warning("No results for this search.")
        return

    # Conversation selector
    conv_opts = {c["conversation_id"]: f"{c['conversation_id']} — {(c.get('scenario') or {}).get('name', '')}" for c in convs}
    sel_id = st.selectbox("Select conversation", list(conv_opts.keys()),
                          format_func=lambda x: conv_opts[x], key="browser_sel")
    conv = next((c for c in convs if c["conversation_id"] == sel_id), None)
    if not conv:
        return

    _render_conv_card(conv)


def _render_conv_card(conv: Dict[str, Any]):
    cm = conv.get("conversation_meta", {})
    scenario = conv.get("scenario", {})
    quality = conv.get("quality", {})
    personas = conv.get("personas", {}) or {}

    # ── Header KPIs ───────────────────────────────────────────────
    st.markdown(f"## {conv.get('conversation_id')}")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Outcome", cm.get("outcome", "—"))
    c2.metric("Domain", scenario.get("domain_l1", "—"))
    c3.metric("Ambiguity", cm.get("ambiguity_level", "—"))
    c4.metric("Difficulty", cm.get("difficulty_tier", "—"))
    c5.metric("# Turns", cm.get("total_turns", len(conv.get("turns", []))))
    c6.metric("Gold", "⭐" if quality.get("is_gold") else "—")

    # ── Scenario & Meta ────────────────────────────────────────────
    with st.expander("📋 Scenario & Meta", expanded=False):
        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown(f"**Scenario:** {scenario.get('name', '—')}")
            st.markdown(f"**Domain L1:** {scenario.get('domain_l1', '—')}")
            st.markdown(f"**Fraud goal:** {scenario.get('fraud_goal', '—')}")
            phases = cm.get("phases_present", [])
            st.markdown(f"**Phases:** {' → '.join(phases) if phases else '—'}")
            primary_tags = cm.get("primary_span_tags") or cm.get("primary_tactics") or []
            st.markdown(f"**Primary span tags:** {', '.join(primary_tags) or '—'}")
        with mc2:
            st.markdown(f"**Ambiguity score:** {cm.get('ambiguity_score')}")
            st.markdown(f"**Difficulty score:** {cm.get('difficulty_score')}")
            st.markdown(f"**Cialdini:** {', '.join(cm.get('cialdini_principles', []) or [])}")
            st.markdown(f"**Cognitive mechanisms:** {', '.join(cm.get('cognitive_mechanisms', []) or [])}")

    # ── Personas ──────────────────────────────────────────────────
    if personas:
        with st.expander("👥 Personas", expanded=False):
            pc1, pc2 = st.columns(2)
            with pc1:
                scm = personas.get("scammer") or {}
                st.markdown("**Scammer**")
                st.markdown(f"- Claimed identity: {scm.get('claimed_identity', '—')}")
                st.markdown(f"- Register: {scm.get('speaking_register', '—')}")
                st.markdown(f"- Gender presented: {scm.get('gender_presented', '—')}")
            with pc2:
                vic = personas.get("victim") or {}
                st.markdown("**Victim**")
                st.markdown(f"- Age range: {vic.get('age_range', '—')}")
                st.markdown(f"- Gender: {vic.get('gender', '—')}")
                st.markdown(f"- Vulnerability: {vic.get('vulnerability_profile', '—')}")
                st.markdown(f"- Prior scam knowledge: {vic.get('prior_scam_knowledge', '—')}")

    # ── Quality block ─────────────────────────────────────────────
    if quality:
        with st.expander("🏆 Quality", expanded=False):
            qc1, qc2, qc3 = st.columns(3)
            qc1.metric("IAA Score", quality.get("iaa_score", "—"))
            qc2.metric("Authenticity", quality.get("expert_authenticity_score", "—"))
            qc3.metric("Method", quality.get("annotation_method", "—"))

    # Span density timeline (replaces manipulation_intensity timeline)
    from src.viz.charts_detail import plot_ds_radar_single
    from src.metrics.difficulty_score import compute_ds
    ds_result = compute_ds(conv)
    if ds_result.get("sub_scores"):
        st.plotly_chart(plot_ds_radar_single(ds_result["sub_scores"]), use_container_width=True)

    # ── Turns ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Turns")
    for turn in conv.get("turns", []):
        _render_turn(turn)


def _render_turn(turn: Dict[str, Any]):
    speaker = turn.get("speaker", "")
    is_scammer = speaker == "scammer"
    bg = "#fff1f0" if is_scammer else "#f0f7ff"
    border = "#ef4444" if is_scammer else "#3b82f6"

    text = turn.get("text", "")
    spans = turn.get("span_annotations") or []
    highlighted = _highlight_spans(text, spans)

    # Phase badge + Span tag badges
    badges_html = ""
    ph = turn.get("phase")
    if ph:
        badges_html += f'<span style="background:#1e293b;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">{ph}</span>'
    for sp in (turn.get("span_annotations") or []):
        tag = sp.get("tag", "")
        if tag:
            color = SPAN_COLORS.get(tag, "#6366f1")
            badges_html += f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:4px;">{tag}</span>'

    st.markdown(f"""
    <div style="border-left:4px solid {border};background:{bg};padding:12px 16px;margin-bottom:10px;border-radius:6px;">
        <div style="font-weight:700;color:{border};margin-bottom:6px;">
            [{turn.get('turn_id','?')}] {speaker.upper()}
        </div>
        <div style="margin-bottom:8px;line-height:1.7;">{highlighted}</div>
        <div>{badges_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Span annotation preview
    if spans:
        with st.expander(f"  📍 Spans ({len(spans)})", expanded=False):
            for sp in spans:
                tag = sp.get("tag", "")
                color = SPAN_COLORS.get(tag, "#6b7280")
                st.markdown(
                    f'<span style="background:{color}22;border:1px solid {color};border-radius:4px;padding:2px 8px;margin-right:6px;font-size:12px;">{tag}</span>'
                    f'<span style="font-size:13px;">„{sp.get("span_text", "")}"</span>',
                    unsafe_allow_html=True
                )


def _highlight_spans(text: str, spans: list) -> str:
    if not spans or not text:
        return text
    # Use span_text for {tag, span_text} format
    result = text
    for sp in spans:
        span_text = sp.get("span_text", "") or sp.get("span", "")
        tag = sp.get("tag", "")
        color = SPAN_COLORS.get(tag, "#f59e0b")
        if span_text and span_text in result:
            highlighted = (
                f'<mark style="background:{color}33;border-bottom:2px solid {color};'
                f'padding:0 2px;border-radius:2px;" title="{tag}">{span_text}</mark>'
            )
            result = result.replace(span_text, highlighted, 1)
    return result
