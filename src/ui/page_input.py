"""
page_input.py — Data Input page: upload, paste, demo loader.
"""
import json, os
import streamlit as st

from src.normalize.normalize_input import normalize_dataset
from src.validators import validate_dataset
from src.io_utils import parse_uploaded_file, parse_raw_json_text
from src.schema import VALID_OUTCOMES, VALID_DOMAIN_L1, VALID_AMBIGUITY_LEVELS
from src.demo_builders import build_demo_dataset


def render(session):
    st.header("📥 Data Input")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Upload File")
        uploaded = st.file_uploader(
            "Upload JSON / JSONL / CSV",
            type=["json", "jsonl", "csv"],
            key="upload_v2",
        )
        if uploaded is not None:
            _handle_upload(session, uploaded)

        st.markdown("---")
        st.subheader("Paste Raw JSON")
        raw_text = st.text_area(
            "Paste JSON array hoặc single object",
            height=200,
            placeholder='[{"conversation_id": "...", ...}]',
            key="paste_v2",
        )
        if st.button("Parse JSON Text", key="btn_parse"):
            if raw_text.strip():
                _handle_raw(session, raw_text)

    with col_right:
        st.subheader("Load Demo Data")
        st.info("Demo data v2 đầy đủ schema: personas, quality, metrics.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📂 Load demo_data.json", key="btn_demo_file"):
                _load_demo_file(session)
        with c2:
            if st.button("⚡ Generate in-memory", key="btn_gen_demo"):
                _gen_demo(session)

        st.markdown("---")
        if st.button("🗑 Clear All Data", type="secondary", key="btn_clear"):
            session.conversations = []
            session.refresh()
            st.success("Cleared.")

    # Preview
    st.markdown("---")
    n = len(session.conversations)
    st.subheader(f"Dataset Preview — {n} conversation(s)")

    if not session.df_conv.empty:
        cols = [c for c in [
            "conversation_id", "outcome", "domain_l1", "scenario_name",
            "ambiguity_level", "difficulty_tier", "n_turns", "n_spans", "is_gold"
        ] if c in session.df_conv.columns]
        st.dataframe(session.df_conv[cols], use_container_width=True)

        st.subheader("Preview single conversation (normalized JSON)")
        ids = [c["conversation_id"] for c in session.conversations]
        sel = st.selectbox("Select", ids, key="preview_sel")
        if sel:
            sample = next((c for c in session.conversations if c["conversation_id"] == sel), None)
            if sample:
                st.json(sample, expanded=False)
    else:
        st.info("Chưa có dữ liệu. Dùng các tùy chọn trên để load.")


def _handle_upload(session, uploaded):
    try:
        raw = parse_uploaded_file(uploaded)
        norm = normalize_dataset(raw, vcs_map=session.vcs_map)
        result = validate_dataset(norm)
        _show_result(result)
        if st.button("➕ Add valid samples", key="btn_add_upload"):
            _add_samples(session, result["valid_samples"])
    except Exception as e:
        st.error(f"Failed: {e}")


def _handle_raw(session, raw_text):
    try:
        raw = parse_raw_json_text(raw_text)
        norm = normalize_dataset(raw, vcs_map=session.vcs_map)
        result = validate_dataset(norm)
        _show_result(result)
        _add_samples(session, result["valid_samples"])
    except Exception as e:
        st.error(f"Parse error: {e}")


def _load_demo_file(session):
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "demo_data.json")
        path = os.path.normpath(path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        norm = normalize_dataset(raw if isinstance(raw, list) else [raw])
        result = validate_dataset(norm)
        session.conversations = result["valid_samples"]
        session.refresh()
        st.success(f"Loaded {len(session.conversations)} conversations.")
    except Exception as e:
        st.error(f"Error: {e}")


def _gen_demo(session):
    raw = build_demo_dataset()
    norm = normalize_dataset(raw)
    result = validate_dataset(norm)
    session.conversations = result["valid_samples"]
    session.refresh()
    st.success(f"Generated {len(session.conversations)} demo conversations.")


def _show_result(result):
    st.success(f"Parsed {result['n_valid'] + result['n_errors']} — Valid: {result['n_valid']}, Errors: {result['n_errors']}")
    if result["all_errors"]:
        with st.expander(f"Errors ({result['n_errors']})"):
            for e in result["all_errors"]:
                st.error(e)
    if result.get("all_warnings"):
        with st.expander(f"Warnings ({result.get('n_warnings', 0)})"):
            for w in result["all_warnings"]:
                st.warning(w)


def _add_samples(session, samples):
    existing = {c["conversation_id"] for c in session.conversations}
    added = 0
    for c in samples:
        if c["conversation_id"] not in existing:
            session.conversations.append(c)
            added += 1
    session.refresh()
    st.success(f"Added {added} conversations. Total: {len(session.conversations)}")
