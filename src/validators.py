"""
validators.py — Schema + logic validation for ViScamDial v2 (Span-only).
Turn-level labels (speech_acts, cognitive_state, response_type, manipulation_intensity)
đã bị xóa. Chỉ validate span_annotations per turn.
"""
from typing import Dict, Any, List, Tuple

from src.schema import (
    VALID_OUTCOMES, VALID_PHASES, VALID_SPAN_LABELS,
    VALID_DOMAIN_L1, PHASE_ORDER, get_turn_span_tags,
)


def validate_basic_schema(conv: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Kiểm tra schema cơ bản cho một conversation.
    Returns (errors, warnings).
    """
    errors: List[str] = []
    warnings: List[str] = []
    cid = conv.get("conversation_id", "UNKNOWN")

    # Mandatory top-level fields
    if not conv.get("conversation_id"):
        errors.append(f"[{cid}] Missing conversation_id")

    if not conv.get("turns"):
        warnings.append(f"[{cid}] No turns found")

    # Scenario check
    scenario = conv.get("scenario") or {}
    if not scenario.get("id"):
        warnings.append(f"[{cid}] Missing scenario.id")
    domain = scenario.get("domain_l1", "")
    if domain and domain not in VALID_DOMAIN_L1:
        warnings.append(f"[{cid}] Unknown domain_l1: {domain}")

    # conversation_meta check
    cm = conv.get("conversation_meta") or {}
    outcome = cm.get("outcome") or conv.get("conversation_labels", {}).get("outcome", "")
    if outcome and outcome not in VALID_OUTCOMES:
        errors.append(f"[{cid}] Invalid outcome: {outcome}")

    # Turn-level validation
    for t in conv.get("turns", []):
        turn_id = t.get("turn_id", "?")
        speaker = t.get("speaker", "")

        if speaker not in {"scammer", "victim", ""}:
            errors.append(f"[{cid}] Turn {turn_id}: invalid speaker '{speaker}' (must be scammer/victim)")

        # phase validation
        phase = t.get("phase")
        if phase and phase not in VALID_PHASES:
            warnings.append(f"[{cid}] Turn {turn_id}: unknown phase '{phase}'")

        # span_annotations validation
        spans = t.get("span_annotations")
        if spans is not None and not isinstance(spans, list):
            errors.append(f"[{cid}] Turn {turn_id}: span_annotations must be a list")
        if isinstance(spans, list):
            for sp in spans:
                tag = sp.get("tag", "")
                if tag and tag not in VALID_SPAN_LABELS:
                    warnings.append(f"[{cid}] Turn {turn_id}: unknown span tag '{tag}'")
                if not sp.get("span_text"):
                    warnings.append(f"[{cid}] Turn {turn_id}: span annotation missing span_text for tag '{tag}'")

    # Logic validation: phase sequence non-decreasing
    phases = [t.get("phase") for t in conv.get("turns", []) if t.get("phase")]
    phase_nums = [PHASE_ORDER.get(p, 0) for p in phases]
    for i in range(1, len(phase_nums)):
        if phase_nums[i] < phase_nums[i - 1]:
            warnings.append(
                f"[{cid}] Phase sequence decreasing at turn {i+1}: {phases[i-1]} → {phases[i]}"
            )
            break

    # Logic validation: REQUEST_INFO span should not appear in P1 without prior identity span
    turns_list = conv.get("turns", [])
    seen_identity = False
    for t in turns_list:
        if t.get("speaker") != "scammer":
            continue
        tags = get_turn_span_tags(t)
        if tags & {"FAKE_ID", "FAKE_ORG"}:
            seen_identity = True
        if "REQUEST_INFO" in tags and not seen_identity:
            phase = t.get("phase", "?")
            if phase in {"P1", "P2"}:
                warnings.append(
                    f"[{cid}] Turn {t.get('turn_id','?')}: REQUEST_INFO span in {phase} without prior identity setup"
                )

    return errors, warnings


def validate_dataset(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate toàn bộ dataset. Returns validation summary.

    Returns:
        {n_valid, n_errors, valid_samples, all_errors, all_warnings, n_warnings}
    """
    valid_samples = []
    all_errors: List[str] = []
    all_warnings: List[str] = []

    for conv in dataset:
        errors, warnings = validate_basic_schema(conv)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        if not errors:
            valid_samples.append(conv)

    return {
        "n_valid": len(valid_samples),
        "n_errors": len(dataset) - len(valid_samples),
        "valid_samples": valid_samples,
        "all_errors": all_errors,
        "all_warnings": all_warnings,
        "n_warnings": len(all_warnings),
    }


def check_metric_readiness(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra data có đủ cho từng metric không.
    Returns {metric: {ready: bool, missing_fields: list}}
    """
    turns = conv.get("turns", [])
    scammer_turns = [t for t in turns if t.get("speaker") == "scammer"]
    cm = conv.get("conversation_meta", {})

    has_spans = any(t.get("span_annotations") for t in scammer_turns)
    has_phases = bool(cm.get("phases_present") or any(t.get("phase") for t in turns))
    has_text = any(t.get("text") for t in turns)
    has_quality = bool(conv.get("quality"))

    return {
        "AI": {
            "ready": has_spans,
            "missing": [] if has_spans else ["span_annotations"],
        },
        "DS": {
            "ready": has_spans and has_text,
            "missing": ([] if has_spans else ["span_annotations"])
                       + ([] if has_text else ["text"]),
        },
        "TCS": {
            "ready": has_spans,
            "missing": [] if has_spans else ["span_annotations"],
        },
        "LDS": {
            "ready": has_text,
            "missing": [] if has_text else ["text"],
        },
        "PCS": {
            "ready": has_phases,
            "missing": [] if has_phases else ["phase labels"],
        },
        "VSVS": {
            "ready": has_spans,
            "missing": [] if has_spans else ["span_annotations"],
        },
        "AQS": {
            "ready": True,
            "missing": [] if has_spans else ["span_annotations (partial)"],
        },
        "DBR": {
            "ready": True,
            "missing": [],
        },
    }
