"""
constants.py — Tập trung toàn bộ thresholds, targets, và config cho ViScamDial-Bench v2.
Không hardcode giá trị rải rác trong code; đưa tất cả vào đây.
"""
from typing import Dict, Any


# ─────────────────────────────────────────────────────────────────
# METRIC THRESHOLDS — MER PASS CONDITIONS
# ─────────────────────────────────────────────────────────────────

MER_PASS_CONDITIONS: Dict[str, Any] = {
    "mean_ambiguity_min": 0.30,
    "mean_ambiguity_max": 0.55,
    "mean_difficulty_min": 0.45,
    "mean_difficulty_max": 0.70,
    "mean_iaa_kappa_min": 0.75,
    "near_duplicate_ratio_max": 0.05,   # < 5%
    "balance_score_min": 0.65,
    "min_conversations_per_scenario": 80,  # configurable
    "p5_coverage_min": 0.40,            # >= 40%
    "span_completeness_min": 0.80,      # >= 80%
    "max_warnings_for_ready": 3,
}

# ─────────────────────────────────────────────────────────────────
# AI — Ambiguity Index
# ─────────────────────────────────────────────────────────────────
AI_TARGET = {
    "low_min": 0.25,
    "low_max": 0.35,
    "medium_min": 0.40,
    "medium_max": 0.50,
    "high_min": 0.20,
    "high_max": 0.30,
}

AI_FACTOR_WEIGHTS = {
    "f1_no_explicit_request": 0.25,
    "f2_low_manipulation": 0.20,
    "f3_professional_register": 0.20,
    "f4_victim_confusion": 0.15,
    "f5_deflection": 0.10,
    "f6_partial_outcome": 0.10,
}

AI_LEVEL_THRESHOLDS = {
    "low": (0.0, 0.35),
    "medium": (0.35, 0.65),
    "high": (0.65, 1.01),
}

# ─────────────────────────────────────────────────────────────────
# DS — Difficulty Score
# ─────────────────────────────────────────────────────────────────
DS_TARGET = {
    "easy_pct_min": 0.15,
    "easy_pct_max": 0.20,
    "medium_pct_min": 0.35,
    "medium_pct_max": 0.45,
    "hard_pct_min": 0.25,
    "hard_pct_max": 0.35,
    "expert_pct_min": 0.10,
    "expert_pct_max": 0.20,
}

DS_TIER_THRESHOLDS = {
    "easy":   (0.00, 0.30),
    "medium": (0.30, 0.55),
    "hard":   (0.55, 0.75),
    "expert": (0.75, 1.01),
}

DS_FACTOR_WEIGHTS = {
    "ambiguity":           0.25,
    "tactic_density":      0.20,
    "phase_complexity":    0.15,
    "linguistic":          0.20,
    "victim_confusion":    0.10,
    "scammer_adaptability":0.10,
}

# ─────────────────────────────────────────────────────────────────
# TCS — Tactic Coverage Score
# ─────────────────────────────────────────────────────────────────
TCS_MIN_COUNT_PER_TACTIC = 50
TCS_GINI_TARGET = 0.40       # Gini <= 0.40 is acceptable
TCS_SATURATION = 8           # unique tactics saturation point

# ─────────────────────────────────────────────────────────────────
# LDS — Linguistic Diversity Score
# ─────────────────────────────────────────────────────────────────
LDS_TTR_MIN = 0.30
LDS_MEAN_COSINE_MAX = 0.35
LDS_NEAR_DUP_THRESHOLD = 0.70  # cosine sim > 0.70 → near duplicate
LDS_MAX_SAMPLE_SIZE = 500       # sample for cosine matrix

# ─────────────────────────────────────────────────────────────────
# PCS — Phase Completeness Score
# ─────────────────────────────────────────────────────────────────
PCS_P5_MIN_RATIO = 0.40
PCS_MIN_PHASES_PER_CONV = 2

# ─────────────────────────────────────────────────────────────────
# VSVS — Victim State Validity Score
# ─────────────────────────────────────────────────────────────────
VSVS_VALIDITY_THRESHOLD = 0.85  # is_valid if ratio > 0.85

# ─────────────────────────────────────────────────────────────────
# AQS — Annotation Quality Score
# ─────────────────────────────────────────────────────────────────
AQS_KAPPA_MIN = 0.75
AQS_KAPPA_ERROR = 0.65       # below this → ERROR
AQS_SPAN_COMPLETENESS_MIN = 0.80
AQS_LAZY_ENTROPY_RATIO = 0.60   # < 60% of team mean → lazy flag
AQS_MIN_TURNS_FOR_ENTROPY = 50

# ─────────────────────────────────────────────────────────────────
# DBR — Dataset Balance Report
# ─────────────────────────────────────────────────────────────────
DBR_MEAN_BALANCE_MIN = 0.65
DBR_DIMENSIONS = [
    "scenario", "outcome", "length_class", "speech_acts",
    "victim_state", "domain_l1", "difficulty_tier", "ambiguity_level"
]

# ─────────────────────────────────────────────────────────────────
# CONVERSATION LENGTH CLASSES
# ─────────────────────────────────────────────────────────────────
LENGTH_CLASS_THRESHOLDS = {
    "short":  (0, 8),
    "medium": (8, 20),
    "long":   (20, 9999),
}

def classify_length(n_turns: int) -> str:
    if n_turns < 8:
        return "short"
    elif n_turns < 20:
        return "medium"
    return "long"


# ─────────────────────────────────────────────────────────────────
# BENCHMARK TASKS
# ─────────────────────────────────────────────────────────────────
BENCHMARK_TASKS = {
    "T1": {
        "name": "Scam Detection",
        "input": "full conversation",
        "output": "binary scam/not",
        "label_field": "outcome",
    },
    "T2": {
        "name": "Scenario Classification",
        "input": "full conversation",
        "output": "scenario id",
        "label_field": "scenario.id",
    },
    "T3": {
        "name": "Phase Segmentation",
        "input": "full conversation",
        "output": "phase sequence",
        "label_field": "turns[].phase",
    },
    "T4": {
        "name": "Tactic Classification",
        "input": "single scammer turn",
        "output": "SSAT multi-label",
        "label_field": "turns[].speech_acts",
    },
    "T5": {
        "name": "Outcome Prediction",
        "input": "partial conversation P1-P3",
        "output": "outcome class",
        "label_field": "outcome",
    },
    "T6": {
        "name": "Victim State Tracking",
        "input": "victim turn sequence",
        "output": "VCS sequence",
        "label_field": "turns[].cognitive_state",
    },
    "T7": {
        "name": "Ambiguity-Stratified Evaluation",
        "input": "full conversation grouped by ambiguity tier",
        "output": "T1 performance per tier",
        "label_field": "ambiguity_level",
    },
}
