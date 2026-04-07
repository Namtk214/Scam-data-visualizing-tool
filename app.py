"""
app.py — ViScamDial-Bench Visualization Tool v2
Chạy: streamlit run app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd

from src.normalize.normalize_input import normalize_dataset as normalize_dataset_v2
from src.validators import validate_dataset
from src.stats import build_conversation_df, flatten_to_turn_df, flatten_to_span_df
from src.schema import (
    VALID_OUTCOMES, VALID_DOMAIN_L1, VALID_AMBIGUITY_LEVELS,
    VALID_PHASES, VALID_SSAT, VALID_SPAN_LABELS, VCS_LEGACY_MAP_DEFAULT,
)
from src.constants import DS_TIER_THRESHOLDS

# Keep old normalize for backward compat (if exists)
try:
    from src.normalize import normalize_conversation as _old_normalize
except Exception:
    _old_normalize = None

from src.ui import page_input, page_browser, page_overview, page_quality, page_benchmark, page_export

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ViScamDial Benchmark Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Sidebar ───────────────────────────────── */
    [data-testid="stSidebar"] {background: #0f172a;}
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption {color: #cbd5e1 !important; font-size: 12px !important;}
    [data-testid="stSidebar"] h1 {color: #f1f5f9 !important; font-size: 17px !important;}
    [data-testid="stSidebar"] h2 {color: #f1f5f9 !important; font-size: 14px !important;}
    [data-testid="stSidebar"] h3 {color: #e2e8f0 !important; font-size: 12px !important;}

    /* ── Global font — comfortable reading size ───── */
    .main .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    h1 {font-size: 1.6rem !important; font-weight: 700 !important;}
    h2 {font-size: 1.25rem !important; font-weight: 600 !important;}
    h3 {font-size: 1.05rem !important; font-weight: 600 !important;}
    p, li, .stMarkdown {font-size: 14px !important;}
    .stCaption {font-size: 12px !important; color: #6b7280 !important;}

    /* ── Metric cards ──────────────────────────── */
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
    }
    div[data-testid="metric-container"] label {font-size: 11px !important; color: #6b7280 !important;}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 18px !important; font-weight: 700 !important;
    }

    /* ── Tabs ──────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {gap: 0.3rem;}
    .stTabs [data-baseweb="tab"] {
        padding: 7px 14px;
        border-radius: 6px 6px 0 0;
        font-size: 13px !important;
    }

    /* ── Expanders ─────────────────────────────── */
    .streamlit-expanderHeader {font-size: 13px !important;}

    /* ── Selectbox / multiselect ───────────────── */
    .stSelectbox label, .stMultiSelect label {font-size: 13px !important;}

    /* ── Dataframe ─────────────────────────────── */
    [data-testid="stDataFrame"] {font-size: 12px !important;}

    /* ── Alerts / info boxes ───────────────────── */
    .stAlert {font-size: 12px !important; padding: 8px 12px !important;}
</style>
""", unsafe_allow_html=True)



# ─── Session state class ───────────────────────────────────────────────────────
class AppSession:
    """Wrapper around st.session_state for clean access."""
    def __init__(self):
        if "conversations" not in st.session_state:
            st.session_state.conversations = []
        if "df_conv" not in st.session_state:
            st.session_state.df_conv = pd.DataFrame()
        if "df_turn" not in st.session_state:
            st.session_state.df_turn = pd.DataFrame()
        if "df_span" not in st.session_state:
            st.session_state.df_span = pd.DataFrame()
        if "gold_set" not in st.session_state:
            st.session_state.gold_set = None
        if "vcs_map" not in st.session_state:
            st.session_state.vcs_map = dict(VCS_LEGACY_MAP_DEFAULT)
        # Sidebar filter state
        if "_f_outcome" not in st.session_state:
            st.session_state._f_outcome = []
        if "_f_domain" not in st.session_state:
            st.session_state._f_domain = []
        if "_f_ambig" not in st.session_state:
            st.session_state._f_ambig = []
        if "_f_diff_tier" not in st.session_state:
            st.session_state._f_diff_tier = []
        if "_f_is_gold" not in st.session_state:
            st.session_state._f_is_gold = False
        if "_f_min_turns" not in st.session_state:
            st.session_state._f_min_turns = 1
        if "_f_max_turns" not in st.session_state:
            st.session_state._f_max_turns = 100

    @property
    def conversations(self):
        return st.session_state.conversations

    @conversations.setter
    def conversations(self, val):
        st.session_state.conversations = val

    @property
    def df_conv(self):
        return st.session_state.df_conv

    @property
    def gold_set(self):
        return st.session_state.gold_set

    @gold_set.setter
    def gold_set(self, val):
        st.session_state.gold_set = val

    @property
    def vcs_map(self):
        return st.session_state.vcs_map

    def refresh(self):
        convs = self.conversations
        st.session_state.df_conv = build_conversation_df(convs)
        st.session_state.df_turn = flatten_to_turn_df(convs)
        st.session_state.df_span = flatten_to_span_df(convs)

    def get_filtered(self):
        convs = self.conversations
        df = st.session_state.df_conv
        if df.empty or not convs:
            return convs

        f_outcome = st.session_state._f_outcome
        f_domain = st.session_state._f_domain
        f_ambig = st.session_state._f_ambig
        f_diff_tier = st.session_state._f_diff_tier
        f_is_gold = st.session_state._f_is_gold
        f_min = st.session_state._f_min_turns
        f_max = st.session_state._f_max_turns

        filtered = list(convs)
        if f_outcome:
            filtered = [c for c in filtered if c.get("conversation_meta", {}).get("outcome") in f_outcome
                        or c.get("conversation_labels", {}).get("outcome") in f_outcome]
        if f_domain:
            filtered = [c for c in filtered if c.get("scenario", {}).get("domain_l1") in f_domain]
        if f_ambig:
            filtered = [c for c in filtered if c.get("conversation_meta", {}).get("ambiguity_level") in f_ambig]
        if f_diff_tier:
            filtered = [c for c in filtered if c.get("conversation_meta", {}).get("difficulty_tier") in f_diff_tier]
        if f_is_gold:
            filtered = [c for c in filtered if c.get("quality", {}) and c["quality"].get("is_gold")]
        filtered = [c for c in filtered
                    if f_min <= len(c.get("turns", [])) <= f_max]
        return filtered


session = AppSession()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🔍 ViScamDial")
    st.caption("Benchmark Visualization Tool v2")
    st.markdown("---")

    # Gold set upload
    st.subheader("Gold Set (Optional)")
    gold_upload = st.file_uploader("Upload gold JSON for AQS Kappa", type=["json"], key="gold_upload")
    if gold_upload:
        try:
            import json
            gold_raw = json.load(gold_upload)
            if isinstance(gold_raw, list):
                session.gold_set = normalize_dataset_v2(gold_raw)
                st.success(f"Gold set: {len(session.gold_set)} samples")
        except Exception as e:
            st.error(f"Gold set error: {e}")

    st.markdown("---")
    st.subheader("🔧 Filters")

    all_outcomes = sorted(set(
        c.get("conversation_meta", {}).get("outcome") or c.get("conversation_labels", {}).get("outcome", "")
        for c in session.conversations
    ) - {""})
    st.session_state._f_outcome = st.multiselect("Outcome", options=all_outcomes, default=[], key="f_outcome")

    all_domains = sorted(set(
        c.get("scenario", {}).get("domain_l1", "") for c in session.conversations
    ) - {""})
    st.session_state._f_domain = st.multiselect("Domain L1", options=all_domains or sorted(VALID_DOMAIN_L1), default=[], key="f_domain")

    all_ambig = sorted(set(
        c.get("conversation_meta", {}).get("ambiguity_level", "") for c in session.conversations
    ) - {""})
    st.session_state._f_ambig = st.multiselect("Ambiguity Level", options=all_ambig or ["low", "medium", "high"], default=[], key="f_ambig")

    tiers = ["easy", "medium", "hard", "expert"]
    st.session_state._f_diff_tier = st.multiselect("Difficulty Tier", options=tiers, default=[], key="f_diff")

    st.session_state._f_is_gold = st.checkbox("Gold only ⭐", value=False, key="f_gold")

    max_turns = max((len(c.get("turns", [])) for c in session.conversations), default=50)
    min_t, max_t = st.slider("Turn range", 1, max(max_turns, 50), (1, max(max_turns, 50)), key="f_turns")
    st.session_state._f_min_turns = min_t
    st.session_state._f_max_turns = max_t

    st.markdown("---")
    st.subheader("⚙️ VCS Legacy Mapping")
    st.caption("How to map old VCS labels (CONFUSED/ANXIOUS)")
    confused_map = st.selectbox("CONFUSED →", ["CURIOUS", "CONCERNED"], key="vcs_confused")
    anxious_map = st.selectbox("ANXIOUS →", ["CONCERNED", "FEARFUL"], key="vcs_anxious")
    st.session_state.vcs_map = {"CONFUSED": confused_map, "ANXIOUS": anxious_map}

    st.markdown("---")
    n_total = len(session.conversations)
    n_filtered = len(session.get_filtered())
    st.caption(f"**{n_total}** loaded · **{n_filtered}** filtered")


# ─── Main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📥 Data Input",
    "🔎 Data Browser",
    "📊 Dataset Overview",
    "📈 Quality Metrics",
    "🏆 Benchmark Readiness",
    "💾 Export",
])

with tab1:
    page_input.render(session)

with tab2:
    page_browser.render(session)

with tab3:
    page_overview.render(session)

with tab4:
    page_quality.render(session)

with tab5:
    page_benchmark.render(session)

with tab6:
    page_export.render(session)
