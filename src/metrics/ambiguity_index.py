"""
ambiguity_index.py — Ambiguity Index (AI) metric. Span-only version.

AI Score [0.0 - 1.0] đo độ tinh vi / nhập nhằng của kịch bản lừa đảo.
Tính hoàn toàn từ span_annotations thay vì turn-level labels.

Factors (5 factors, tổng = 1.0):
  F1 (0.28): Absence of explicit REQUEST_INFO span
  F2 (0.22): Low span density (avg spans/scammer-turn < 1.5)
  F3 (0.22): Identity/org impersonation without THREAT_PHRASE (formal, non-threatening)
  F4 (0.14): Scammer turns immediately preceding victim turns have URGENCY/THREAT spans
             (gián tiếp: victim bị ép → ambiguity cao khi nạn nhân vẫn chưa nhận ra)
             Lưu ý: đây là nghịch đảo — nhiều ép buộc tường minh → AI thấp (ít tinh vi)
  F5 (0.14): DEFLECT_PHRASE span count (scammer né tránh)
"""
from typing import Dict, Any, List

from src.constants import AI_LEVEL_THRESHOLDS
from src.schema import get_turn_span_tags, ESCALATION_SPANS


# Updated weights — 5 factors, tổng = 1.0
_AI_WEIGHTS = {
    "f1_no_explicit_request": 0.28,
    "f2_low_span_density":    0.22,
    "f3_formal_no_threat":    0.22,
    "f5_deflection":          0.14,
    "f6_partial_outcome":     0.14,
}


def compute_ai(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính Ambiguity Index cho một conversation từ span_annotations.

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
    if not scammer_turns:
        return _ai_fallback("No scammer turns found")

    factors: List[Dict[str, Any]] = []

    # ── F1: Absence of REQUEST_INFO span ───────────────────────────
    # Nếu không tìm thấy REQUEST_INFO span nào → kịch bản tinh vi (không hỏi thẳng)
    has_request = any(
        "REQUEST_INFO" in get_turn_span_tags(t)
        for t in scammer_turns
    )
    f1 = 0.0 if has_request else _AI_WEIGHTS["f1_no_explicit_request"]
    factors.append({"factor": "F1: No Explicit Request Span", "score": round(f1, 3), "max_score": 0.28})

    # ── F2: Low span density per scammer turn ───────────────────────
    # Ít span → ít thao túng tường minh → kịch bản mờ ám hơn
    span_counts = [len(t.get("span_annotations") or []) for t in scammer_turns]
    avg_spans = sum(span_counts) / len(span_counts) if span_counts else 0
    DENSITY_THRESHOLD = 1.5
    if avg_spans < DENSITY_THRESHOLD:
        f2 = ((DENSITY_THRESHOLD - avg_spans) / DENSITY_THRESHOLD) * _AI_WEIGHTS["f2_low_span_density"]
    else:
        f2 = 0.0
    factors.append({"factor": "F2: Low Span Density", "score": round(f2, 3), "max_score": 0.22})

    # ── F3: FAKE_ID/FAKE_ORG without THREAT_PHRASE ──────────────────
    # Giả mạo danh tính một cách lịch sự, không đe doạ → tinh vi nhất
    formal_impersonation_count = 0
    has_identity_span = False
    for t in scammer_turns:
        tags = get_turn_span_tags(t)
        if tags & {"FAKE_ID", "FAKE_ORG"}:
            has_identity_span = True
            if "THREAT_PHRASE" not in tags:
                formal_impersonation_count += 1
    if has_identity_span and len(scammer_turns) > 0:
        f3 = (formal_impersonation_count / len(scammer_turns)) * _AI_WEIGHTS["f3_formal_no_threat"]
    else:
        f3 = 0.0
        if not has_identity_span:
            warnings.append("No FAKE_ID/FAKE_ORG spans found → F3 set to 0")
    factors.append({"factor": "F3: Formal Impersonation (no Threat)", "score": round(f3, 3), "max_score": 0.22})

    # ── F5: DEFLECT_PHRASE span count ──────────────────────────────
    deflect_count = sum(
        1 for t in scammer_turns if "DEFLECT_PHRASE" in get_turn_span_tags(t)
    )
    f5 = min(deflect_count * 0.04, _AI_WEIGHTS["f5_deflection"])
    factors.append({"factor": "F5: Deflection Spans", "score": round(f5, 3), "max_score": 0.14})

    # ── F6: Partial compliance outcome ──────────────────────────────
    f6 = _AI_WEIGHTS["f6_partial_outcome"] if outcome == "PARTIAL_COMPLIANCE" else 0.0
    factors.append({"factor": "F6: Partial Compliance Outcome", "score": round(f6, 3), "max_score": 0.14})

    # ── Total ────────────────────────────────────────────────────────
    score = round(f1 + f2 + f3 + f5 + f6, 4)
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
