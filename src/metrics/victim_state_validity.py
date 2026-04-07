"""
victim_state_validity.py — Victim State Validity Score (VSVS) metric.

Kiểm tra chuỗi cognitive_state của victim có hợp lý theo VALID_TRANSITIONS không.
"""
from typing import Dict, Any, List

from src.schema import VALID_TRANSITIONS
from src.constants import VSVS_VALIDITY_THRESHOLD


def compute_vsvs(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính VSVS cho một conversation.
    
    Returns:
        {validity_ratio, invalid_transitions, is_valid, recommendation, warnings}
    """
    warnings: List[str] = []
    victim_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "victim"]
    states = [t.get("cognitive_state") for t in victim_turns if t.get("cognitive_state")]

    if len(states) <= 1:
        return {
            "validity_ratio": 1.0,
            "invalid_transitions": [],
            "is_valid": True,
            "recommendation": "Quá ít victim turns để đánh giá (mặc định valid).",
            "warnings": [],
        }

    invalid_trans = []
    for i in range(1, len(states)):
        prev_state = states[i - 1]
        curr_state = states[i]
        allowed = VALID_TRANSITIONS.get(prev_state, set())
        if curr_state not in allowed:
            invalid_trans.append({
                "position": i,
                "from_state": prev_state,
                "to_state": curr_state,
            })

    total_transitions = len(states) - 1
    invalid_count = len(invalid_trans)
    validity_ratio = round(1.0 - invalid_count / total_transitions, 4)
    is_valid = validity_ratio >= VSVS_VALIDITY_THRESHOLD

    if invalid_trans:
        warnings.append(f"{invalid_count} invalid state transitions found")

    recommendation = (
        "Chuỗi tâm lý nạn nhân hợp lệ." if is_valid
        else f"Cần kiểm tra lại {invalid_count} bước nhảy trạng thái bất hợp lý."
    )

    return {
        "validity_ratio": validity_ratio,
        "invalid_transitions": invalid_trans,
        "is_valid": is_valid,
        "recommendation": recommendation,
        "total_transitions": total_transitions,
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
        warnings.append(f"{invalid_count_ratio:.0%} of conversations have invalid state transitions")

    # Build transition matrix across dataset
    trans_matrix: Dict[str, Dict[str, int]] = {}
    for conv in dataset:
        victim_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "victim"]
        states = [t.get("cognitive_state") for t in victim_turns if t.get("cognitive_state")]
        for i in range(1, len(states)):
            fr, to = states[i - 1], states[i]
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
