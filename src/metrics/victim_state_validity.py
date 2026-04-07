"""
victim_state_validity.py — Span Tag Transition Score (VSVS). Span-only version (Option B).

Thay vì theo dõi cognitive_state transitions, nay theo dõi sự thay đổi
span tag-set giữa các scammer turns liên tiếp.

Logic: Kiểm tra xem kịch bản có leo thang đúng thứ tự không:
  - Phase sớm (P1/P2): chủ yếu FAKE_ID, FAKE_ORG, FAKE_VALIDATION, SOCIAL_PROOF
  - Phase giữa (P3/P4): xuất hiện thêm URGENCY_PHRASE, THREAT_PHRASE
  - Phase cuối (P5): có REQUEST_INFO

Nếu REQUEST_INFO xuất hiện ở P1 ngay từ đầu mà chưa có FAKE_ID → bất hợp lý.
Nếu DEFLECT_PHRASE xuất hiện mà trước đó không có phase leo thang → bất hợp lý.
"""
from typing import Dict, Any, List

from src.schema import get_turn_span_tags, PHASE_ORDER
from src.constants import VSVS_VALIDITY_THRESHOLD


# Span tags phù hợp theo phase
_PHASE_EXPECTED_SPANS = {
    "P1": {"FAKE_ID", "FAKE_ORG", "FAKE_VALIDATION"},
    "P2": {"FAKE_ID", "FAKE_ORG", "FAKE_VALIDATION", "SOCIAL_PROOF"},
    "P3": {"FAKE_VALIDATION", "URGENCY_PHRASE", "THREAT_PHRASE", "SOCIAL_PROOF"},
    "P4": {"URGENCY_PHRASE", "THREAT_PHRASE", "REQUEST_INFO", "DEFLECT_PHRASE", "FAKE_VALIDATION"},
    "P5": {"REQUEST_INFO", "URGENCY_PHRASE", "DEFLECT_PHRASE"},
    "P6": set(),
}

_ALL_SPAN_TAGS = set(_tag for tags in _PHASE_EXPECTED_SPANS.values() for _tag in tags)


def compute_vsvs(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính Span Transition Validity Score cho một conversation.

    Kiểm tra 2 loại vi phạm:
    1. Span tag xuất hiện ở phase không phù hợp
    2. REQUEST_INFO không được setup bằng ít nhất 1 identity span hoặc urgency span trước đó

    Returns:
        {validity_ratio, invalid_transitions, is_valid, recommendation, warnings}
    """
    warnings: List[str] = []
    turns = conv.get("turns", [])
    scammer_turns = [t for t in turns if t.get("speaker") == "scammer"]

    if len(scammer_turns) < 2:
        return {
            "validity_ratio": 1.0,
            "invalid_transitions": [],
            "is_valid": True,
            "recommendation": "Quá ít scammer turns để đánh giá span transition (mặc định valid).",
            "warnings": [],
        }

    invalid_trans = []
    seen_identity = False  # đã thấy FAKE_ID/FAKE_ORG chưa
    seen_urgency = False   # đã thấy URGENCY_PHRASE/THREAT_PHRASE chưa

    for i, t in enumerate(scammer_turns):
        tags = get_turn_span_tags(t)
        phase = t.get("phase", "")
        expected = _PHASE_EXPECTED_SPANS.get(phase, _ALL_SPAN_TAGS)

        # Update seen flags
        if tags & {"FAKE_ID", "FAKE_ORG"}:
            seen_identity = True
        if tags & {"URGENCY_PHRASE", "THREAT_PHRASE"}:
            seen_urgency = True

        # Vi phạm 1: span xuất hiện ngoài phase bình thường
        if phase and expected is not _ALL_SPAN_TAGS:
            unexpected = tags - expected - {""}
            if unexpected:
                invalid_trans.append({
                    "position": i,
                    "phase": phase,
                    "violation": "unexpected_spans_for_phase",
                    "spans": list(unexpected),
                })

        # Vi phạm 2: REQUEST_INFO xuất hiện mà chưa có identity hoặc urgency setup
        if "REQUEST_INFO" in tags and not seen_identity and not seen_urgency:
            invalid_trans.append({
                "position": i,
                "phase": phase,
                "violation": "request_without_setup",
                "spans": ["REQUEST_INFO"],
            })

    total_checks = len(scammer_turns)
    invalid_count = len(invalid_trans)
    validity_ratio = round(1.0 - invalid_count / total_checks, 4)
    is_valid = validity_ratio >= VSVS_VALIDITY_THRESHOLD

    if invalid_trans:
        warnings.append(f"{invalid_count} invalid span transitions found")

    recommendation = (
        "Chuỗi span annotation hợp lệ theo thứ tự phase."
        if is_valid
        else f"Cần kiểm tra lại {invalid_count} turns có span annotation bất hợp lý theo phase."
    )

    return {
        "validity_ratio": validity_ratio,
        "invalid_transitions": invalid_trans,
        "is_valid": is_valid,
        "recommendation": recommendation,
        "total_checks": total_checks,
        "invalid_count": invalid_count,
        "warnings": warnings,
    }


def dataset_vsvs_report(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate VSVS cho toàn dataset."""
    results = []
    for conv in dataset:
        r = compute_vsvs(conv)
        r["conversation_id"] = conv.get("conversation_id", "")
        results.append(r)

    if not results:
        return {"per_conversation": [], "warnings": ["Empty dataset"]}

    ratios = [r["validity_ratio"] for r in results]
    mean_ratio = round(sum(ratios) / len(ratios), 4)
    n_valid = sum(1 for r in results if r["is_valid"])

    all_invalid = []
    for r in results:
        for inv in r.get("invalid_transitions", []):
            all_invalid.append({
                "conversation_id": r["conversation_id"],
                **inv,
            })

    warnings = []
    invalid_count_ratio = (len(results) - n_valid) / len(results)
    if invalid_count_ratio > 0.15:
        warnings.append(f"{invalid_count_ratio:.0%} of conversations have invalid span transitions")

    # Build span tag transition matrix (tag-set → most common next tag-set)
    trans_matrix: Dict[str, Dict[str, int]] = {}
    for conv in dataset:
        scammer_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "scammer"]
        tag_sets = [
            ",".join(sorted(get_turn_span_tags(t))) or "(none)"
            for t in scammer_turns
        ]
        for i in range(1, len(tag_sets)):
            fr, to = tag_sets[i - 1], tag_sets[i]
            trans_matrix.setdefault(fr, {})
            trans_matrix[fr][to] = trans_matrix[fr].get(to, 0) + 1

    return {
        "per_conversation": results,
        "mean_validity_ratio": mean_ratio,
        "n_valid": n_valid,
        "n_invalid": len(results) - n_valid,
        "all_invalid_transitions": all_invalid,
        "transition_matrix": trans_matrix,
        "warnings": warnings,
    }
