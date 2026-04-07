"""
schema.py — Label enums, taxonomy, và helpers cho ViScamDial-Bench v2.
Span-only schema: chỉ dùng SpanLabel làm nhãn per-turn.
Backward compatible với schema v1 cũ (Outcome SCAM/AMBIGUOUS/LEGIT).
"""
from enum import Enum
from typing import List, Dict, Set


# ─────────────────────────────────────────────────────────────────
# OUTCOME (v2 — extended)
# ─────────────────────────────────────────────────────────────────
class Outcome(str, Enum):
    FULL_COMPLIANCE = "FULL_COMPLIANCE"
    PARTIAL_COMPLIANCE = "PARTIAL_COMPLIANCE"
    REFUSAL = "REFUSAL"
    INTERRUPTED = "INTERRUPTED"
    # Legacy v1 aliases (kept for backward compat)
    SCAM = "SCAM"
    AMBIGUOUS = "AMBIGUOUS"
    LEGIT = "LEGIT"


VALID_OUTCOMES = {e.value for e in Outcome}

# Legacy → v2 mapping
OUTCOME_LEGACY_MAP: Dict[str, str] = {
    "SCAM": "FULL_COMPLIANCE",
    "AMBIGUOUS": "PARTIAL_COMPLIANCE",
    "LEGIT": "REFUSAL",
}


# ─────────────────────────────────────────────────────────────────
# DOMAIN / SCENARIO (v2)
# ─────────────────────────────────────────────────────────────────
class DomainL1(str, Enum):
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    COMMERCIAL_FRAUD = "COMMERCIAL_FRAUD"
    INVESTMENT_FRAUD = "INVESTMENT_FRAUD"
    ROMANCE_FRAUD = "ROMANCE_FRAUD"
    TECHNICAL_FRAUD = "TECHNICAL_FRAUD"
    UNKNOWN = "UNKNOWN"


VALID_DOMAIN_L1 = {e.value for e in DomainL1}

# Legacy ScenarioGroup A/B/C/D → domain_l1
SCENARIO_GROUP_TO_DOMAIN: Dict[str, str] = {
    "A": "AUTHORITY_IMPERSONATION",
    "B": "COMMERCIAL_FRAUD",
    "C": "INVESTMENT_FRAUD",
    "D": "ROMANCE_FRAUD",
}

# (Kept for backward compat display)
class ScenarioGroup(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

VALID_SCENARIO_GROUPS = {e.value for e in ScenarioGroup}

SCENARIO_GROUP_DESC = {
    "A": "Mạo danh cơ quan / công an / ngân hàng / thuế",
    "B": "Mạo danh dịch vụ thương mại / TMĐT / giao hàng / Shopee",
    "C": "Lừa đảo tài chính / kỹ thuật số / crypto / đầu tư",
    "D": "Lừa đảo xã hội / cảm xúc / người thân / tai nạn",
}


# ─────────────────────────────────────────────────────────────────
# AMBIGUITY (v1 levels kept, v2 uses float score + level string)
# ─────────────────────────────────────────────────────────────────
class AmbiguityLevel(str, Enum):
    # v1 legacy
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    # v2 string levels
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

VALID_AMBIGUITY_LEVELS = {e.value for e in AmbiguityLevel}

AMBIGUITY_LEGACY_TO_V2: Dict[str, str] = {
    "L1": "low",
    "L2": "low",
    "L3": "medium",
    "L4": "high",
}

AMBIGUITY_LEGACY_TO_SCORE: Dict[str, float] = {
    "L1": 0.15,
    "L2": 0.30,
    "L3": 0.50,
    "L4": 0.75,
}


# ─────────────────────────────────────────────────────────────────
# PHASE
# ─────────────────────────────────────────────────────────────────
class Phase(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"
    P6 = "P6"

VALID_PHASES = {e.value for e in Phase}

PHASE_DESC = {
    "P1": "Identity Establish",
    "P2": "Rapport Build",
    "P3": "Problem Inject",
    "P4": "Solution Offer",
    "P5": "Compliance Extract",
    "P6": "Disengage",
}

PHASE_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6}


# ─────────────────────────────────────────────────────────────────
# SPAN LABELS — nhãn duy nhất ở turn level (token/span-level)
# ─────────────────────────────────────────────────────────────────
class SpanLabel(str, Enum):
    FAKE_ID = "FAKE_ID"
    FAKE_ORG = "FAKE_ORG"
    URGENCY_PHRASE = "URGENCY_PHRASE"
    THREAT_PHRASE = "THREAT_PHRASE"
    FAKE_VALIDATION = "FAKE_VALIDATION"
    REQUEST_INFO = "REQUEST_INFO"
    DEFLECT_PHRASE = "DEFLECT_PHRASE"
    SOCIAL_PROOF = "SOCIAL_PROOF"

VALID_SPAN_LABELS = {e.value for e in SpanLabel}
ALL_SPAN_TAGS = list(VALID_SPAN_LABELS)

# Nhóm span theo "cường độ thao túng" để suy luận intensity
HIGH_INTENSITY_SPANS = {"THREAT_PHRASE", "URGENCY_PHRASE", "REQUEST_INFO"}
MEDIUM_INTENSITY_SPANS = {"FAKE_VALIDATION", "SOCIAL_PROOF", "DEFLECT_PHRASE"}
LOW_INTENSITY_SPANS = {"FAKE_ID", "FAKE_ORG"}

# Span báo hiệu leo thang chiến thuật (dùng cho VSVS span-transition)
ESCALATION_SPANS = {"THREAT_PHRASE", "REQUEST_INFO", "URGENCY_PHRASE"}

# Tín hiệu scam (dùng cho prefix signal analysis)
SCAM_SIGNAL_SPANS = {"THREAT_PHRASE", "REQUEST_INFO", "URGENCY_PHRASE", "FAKE_VALIDATION", "SOCIAL_PROOF"}


# ─────────────────────────────────────────────────────────────────
# CIALDINI PRINCIPLES & COGNITIVE MECHANISMS
# ─────────────────────────────────────────────────────────────────
VALID_CIALDINI = {
    "authority", "scarcity", "social_proof", "reciprocity", "liking", "commitment"
}

VALID_COGNITIVE_MECHANISMS = {
    "fear_injection", "fear_then_relief", "cognitive_overload",
    "false_authority", "manufactured_urgency", "identity_anchoring",
}


# ─────────────────────────────────────────────────────────────────
# SPEAKING REGISTER
# ─────────────────────────────────────────────────────────────────
VALID_REGISTERS = {
    "formal_professional", "semi_formal", "casual", "authoritative", "intimate"
}
FORMAL_REGISTERS = {"formal_professional", "authoritative"}


# ─────────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────────
OUTCOME_COLORS = {
    "FULL_COMPLIANCE": "#e74c3c",
    "PARTIAL_COMPLIANCE": "#f39c12",
    "REFUSAL": "#27ae60",
    "INTERRUPTED": "#95a5a6",
    # Legacy
    "SCAM": "#e74c3c",
    "AMBIGUOUS": "#f39c12",
    "LEGIT": "#27ae60",
}

SPEAKER_COLORS = {
    "scammer": "#e74c3c",
    "victim": "#3498db",
}

SPAN_COLORS = {
    "FAKE_ID": "#e74c3c",
    "FAKE_ORG": "#e67e22",
    "URGENCY_PHRASE": "#f39c12",
    "THREAT_PHRASE": "#c0392b",
    "FAKE_VALIDATION": "#9b59b6",
    "REQUEST_INFO": "#2980b9",
    "DEFLECT_PHRASE": "#7f8c8d",
    "SOCIAL_PROOF": "#27ae60",
}

DOMAIN_COLORS = {
    "AUTHORITY_IMPERSONATION": "#e74c3c",
    "COMMERCIAL_FRAUD": "#f39c12",
    "INVESTMENT_FRAUD": "#9b59b6",
    "ROMANCE_FRAUD": "#e91e63",
    "TECHNICAL_FRAUD": "#2980b9",
    "UNKNOWN": "#95a5a6",
}

# Legacy color maps (kept for backward compat with charts that may reference them)
SSAT_COLORS: Dict[str, str] = {}   # Deprecated — tactics removed
VCS_COLORS: Dict[str, str] = {}    # Deprecated — cognitive states removed


# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────
def is_valid_outcome(val: str) -> bool:
    return val in VALID_OUTCOMES

def is_valid_domain_l1(val: str) -> bool:
    return val in VALID_DOMAIN_L1

def is_valid_scenario_group(val: str) -> bool:
    return val in VALID_SCENARIO_GROUPS

def is_valid_ambiguity_level(val: str) -> bool:
    return val in VALID_AMBIGUITY_LEVELS

def is_valid_phase(val: str) -> bool:
    return val in VALID_PHASES

def is_valid_span_label(val: str) -> bool:
    return val in VALID_SPAN_LABELS


def get_turn_span_tags(turn: Dict) -> Set[str]:
    """Trả về tập các span tag có trong một turn."""
    return {
        sp.get("tag", "") for sp in (turn.get("span_annotations") or [])
        if sp.get("tag")
    }


def get_conv_span_tags(conv: Dict) -> Set[str]:
    """Trả về tập các span tag có trong toàn bộ conversation (scammer turns)."""
    tags: Set[str] = set()
    for t in conv.get("turns", []):
        if t.get("speaker") == "scammer":
            tags.update(get_turn_span_tags(t))
    return tags
