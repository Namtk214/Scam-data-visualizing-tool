"""
ambiguity_index.py — Ambiguity Index (AI) metric.

AI Score [0.0 - 1.0] đo độ tinh vi / nhập nhằng của kịch bản lừa đảo.

Factors:
  F1 (0.25): Absence of explicit SA_REQUEST
  F2 (0.20): Low manipulation intensity (avg < 2.5)
  F3 (0.20): Professional/neutral register without SA_THREAT
  F4 (0.15): Victim confusion (VR_QUESTION with NEUTRAL/CURIOUS state)
  F5 (0.10): Scammer deflection (SA_DEFLECT count)
  F6 (0.10): Outcome is PARTIAL_COMPLIANCE
"""
from typing import Dict, Any, List, Optional

from src.constants import AI_FACTOR_WEIGHTS, AI_LEVEL_THRESHOLDS


def compute_ai(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính Ambiguity Index cho một conversation.
    
    Args:
        conv: normalized conversation dict
    
    Returns:
        {
          ambiguity_score: float,
          ambiguity_level: str,
          contributing_factors: list of {factor, score, max_score},
          recommendation: str,
          warnings: list[str],
        }
    """
    warnings: List[str] = []
    turns = conv.get("turns", [])
    outcome = conv.get("conversation_meta", {}).get("outcome", "")

    scammer_turns = [t for t in turns if t.get("speaker") == "scammer"]
    victim_turns = [t for t in turns if t.get("speaker") == "victim"]

    if not scammer_turns:
        return _ai_fallback("No scammer turns found")

    factors: List[Dict[str, Any]] = []

    # ── F1: Absence of explicit SA_REQUEST ─────────────────────────
    all_ssat = []
    for t in scammer_turns:
        all_ssat.extend(t.get("speech_acts", []) or [])

    has_request = "SA_REQUEST" in all_ssat
    f1 = 0.0 if has_request else AI_FACTOR_WEIGHTS["f1_no_explicit_request"]
    factors.append({"factor": "F1: Absence of Explicit Request", "score": round(f1, 3), "max_score": 0.25})

    # ── F2: Low manipulation intensity ──────────────────────────────
    intensities = [
        t["manipulation_intensity"]
        for t in scammer_turns
        if t.get("manipulation_intensity") is not None
    ]
    f2 = 0.0
    if intensities:
        avg_intensity = sum(intensities) / len(intensities)
        if avg_intensity < 2.5:
            f2 = ((2.5 - avg_intensity) / 2.5) * AI_FACTOR_WEIGHTS["f2_low_manipulation"]
    else:
        warnings.append("manipulation_intensity missing → F2 set to 0")
    factors.append({"factor": "F2: Low Manipulation Intensity", "score": round(f2, 3), "max_score": 0.20})

    # ── F3: Professional/neutral register without threat ────────────
    from src.schema import FORMAL_REGISTERS
    formal_no_threat = 0
    has_register_data = False
    for t in scammer_turns:
        reg = (t.get("personas", {}) or {}).get("scammer", {}).get("speaking_register", "")
        # Try top-level conversation personas
        if not reg:
            personas = conv.get("personas") or {}
            scm = personas.get("scammer") or {}
            reg = scm.get("speaking_register", "")
        if reg:
            has_register_data = True
        is_formal = reg in FORMAL_REGISTERS
        has_threat = "SA_THREAT" in (t.get("speech_acts") or [])
        if is_formal and not has_threat:
            formal_no_threat += 1
    total_scammer = len(scammer_turns)
    f3 = 0.0
    if has_register_data and total_scammer > 0:
        f3 = (formal_no_threat / total_scammer) * AI_FACTOR_WEIGHTS["f3_professional_register"]
    else:
        warnings.append("speaking_register missing → F3 set to 0")
    factors.append({"factor": "F3: Professional Register (no threat)", "score": round(f3, 3), "max_score": 0.20})

    # ── F4: Victim confusion turns ──────────────────────────────────
    confused_turns = 0
    for t in victim_turns:
        vrt = t.get("response_type") or ""
        vcs = t.get("cognitive_state") or ""
        if vrt == "VR_QUESTION" and vcs in {"NEUTRAL", "CURIOUS", "CONCERNED"}:
            confused_turns += 1
    f4 = min(confused_turns * 0.03, AI_FACTOR_WEIGHTS["f4_victim_confusion"])
    factors.append({"factor": "F4: Victim Confusion", "score": round(f4, 3), "max_score": 0.15})

    # ── F5: Deflection count ────────────────────────────────────────
    deflect_count = all_ssat.count("SA_DEFLECT")
    f5 = min(deflect_count * 0.03, AI_FACTOR_WEIGHTS["f5_deflection"])
    factors.append({"factor": "F5: Scammer Deflection", "score": round(f5, 3), "max_score": 0.10})

    # ── F6: Partial compliance outcome ──────────────────────────────
    f6 = AI_FACTOR_WEIGHTS["f6_partial_outcome"] if outcome == "PARTIAL_COMPLIANCE" else 0.0
    factors.append({"factor": "F6: Partial Compliance Outcome", "score": round(f6, 3), "max_score": 0.10})

    # ── Total ────────────────────────────────────────────────────────
    score = round(f1 + f2 + f3 + f4 + f5 + f6, 4)
    level = _score_to_level(score)
    recommendation = _ai_recommendation(score, level)

    return {
        "ambiguity_score": score,
        "ambiguity_level": level,
        "contributing_factors": factors,
        "recommendation": recommendation,
        "warnings": warnings,
    }


def dataset_ai_report(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate AI metric trên toàn dataset.
    
    Returns:
        {
          per_conversation: list,
          mean_score: float,
          level_distribution: {low, medium, high},
          target_check: {low_ok, medium_ok, high_ok},
          warnings: list,
        }
    """
    results = []
    for conv in dataset:
        r = compute_ai(conv)
        r["conversation_id"] = conv.get("conversation_id", "")
        results.append(r)

    if not results:
        return {"per_conversation": [], "mean_score": 0.0, "warnings": ["Empty dataset"]}

    scores = [r["ambiguity_score"] for r in results]
    mean_score = round(sum(scores) / len(scores), 4)

    level_dist = {"low": 0, "medium": 0, "high": 0}
    for r in results:
        lv = r["ambiguity_level"]
        if lv in level_dist:
            level_dist[lv] += 1

    n = len(results)
    pct = {k: v / n for k, v in level_dist.items()}
    target_check = {
        "low_ok":    0.25 <= pct.get("low", 0) <= 0.35,
        "medium_ok": 0.40 <= pct.get("medium", 0) <= 0.50,
        "high_ok":   0.20 <= pct.get("high", 0) <= 0.30,
    }

    warnings = []
    if not target_check["low_ok"]:
        warnings.append(f"Low ambiguity ratio {pct['low']:.1%} outside target 25-35%")
    if not target_check["medium_ok"]:
        warnings.append(f"Medium ambiguity ratio {pct['medium']:.1%} outside target 40-50%")
    if not target_check["high_ok"]:
        warnings.append(f"High ambiguity ratio {pct['high']:.1%} outside target 20-30%")

    return {
        "per_conversation": results,
        "mean_score": mean_score,
        "level_distribution": level_dist,
        "level_pct": pct,
        "target_check": target_check,
        "warnings": warnings,
    }


def _score_to_level(score: float) -> str:
    for level, (lo, hi) in AI_LEVEL_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "high"


def _ai_recommendation(score: float, level: str) -> str:
    if level == "low":
        return "Kịch bản rõ ràng, dễ nhận diện. Xem xét thêm kịch bản nhập nhằng hơn."
    elif level == "medium":
        return "Độ nhập nhằng tốt. Kịch bản có khả năng đánh lừa đa số."
    else:
        return "Kịch bản rất tinh vi. Kiểm tra annotation để đảm bảo nhãn chính xác."


def _ai_fallback(reason: str) -> Dict[str, Any]:
    return {
        "ambiguity_score": 0.0,
        "ambiguity_level": "low",
        "contributing_factors": [],
        "recommendation": "Không thể tính AI: " + reason,
        "warnings": [reason],
    }
