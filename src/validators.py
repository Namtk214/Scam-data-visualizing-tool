"""
validators.py — Schema + logic validation for ViScamDial v2.
Backward compatible with legacy v1 schema.
"""
from typing import Dict, Any, List, Tuple

from src.schema import (
    VALID_OUTCOMES, VALID_PHASES, VALID_SSAT, VALID_VRT, VALID_VCS,
    VALID_SPAN_LABELS, VALID_DOMAIN_L1, PHASE_ORDER,
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

        # speech_acts must be list
        sa = t.get("speech_acts")
        if sa is not None and not isinstance(sa, list):
            errors.append(f"[{cid}] Turn {turn_id}: speech_acts must be a list")
        if isinstance(sa, list):
            for act in sa:
                if act not in VALID_SSAT:
                    warnings.append(f"[{cid}] Turn {turn_id}: unknown speech_act '{act}'")

        # manipulation_intensity range
        mi = t.get("manipulation_intensity")
        if mi is not None:
            try:
                mi_val = int(mi)
                if not (1 <= mi_val <= 5):
                    errors.append(f"[{cid}] Turn {turn_id}: manipulation_intensity {mi} not in [1,5]")
            except (TypeError, ValueError):
                errors.append(f"[{cid}] Turn {turn_id}: manipulation_intensity must be int 1-5")

        # VCS validity
        vcs = t.get("cognitive_state")
        if vcs and vcs not in VALID_VCS:
            warnings.append(f"[{cid}] Turn {turn_id}: unknown cognitive_state '{vcs}'")

        # VRT validity
        vrt = t.get("response_type")
        if vrt and vrt not in VALID_VRT:
            warnings.append(f"[{cid}] Turn {turn_id}: unknown response_type '{vrt}'")

    # Logic validation: phase sequence non-decreasing
    phases = [t.get("phase") for t in conv.get("turns", []) if t.get("phase")]
    phase_nums = [PHASE_ORDER.get(p, 0) for p in phases]
    for i in range(1, len(phase_nums)):
        if phase_nums[i] < phase_nums[i - 1]:
            warnings.append(
                f"[{cid}] Phase sequence decreasing at turn {i+1}: {phases[i-1]} → {phases[i]}"
            )
            break  # Only report first violation

    # Logic: SA_DEFLECT should follow victim suspicion
    turns_list = conv.get("turns", [])
    for i, t in enumerate(turns_list):
        if t.get("speaker") == "scammer" and "SA_DEFLECT" in (t.get("speech_acts") or []):
            # Check if previous victim turn had suspicion signal
            prev_victim = next(
                (turns_list[j] for j in range(i - 1, -1, -1) if turns_list[j].get("speaker") == "victim"),
                None
            )
            if prev_victim:
                vcs = prev_victim.get("cognitive_state", "")
                vrt = prev_victim.get("response_type", "")
                if vcs not in {"SUSPICIOUS", "RESISTANT", "REFUSING"} and vrt not in {"VR_QUESTION", "VR_RESIST", "VR_REFUSE"}:
                    warnings.append(
                        f"[{cid}] Turn {t.get('turn_id','?')}: SA_DEFLECT without preceding victim suspicion signal"
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
    victim_turns = [t for t in turns if t.get("speaker") == "victim"]
    cm = conv.get("conversation_meta", {})

    has_speech_acts = any(t.get("speech_acts") for t in scammer_turns)
    has_manipulation = any(t.get("manipulation_intensity") is not None for t in scammer_turns)
    has_vcs = any(t.get("cognitive_state") for t in victim_turns)
    has_vrt = any(t.get("response_type") for t in victim_turns)
    has_phases = bool(cm.get("phases_present") or any(t.get("phase") for t in turns))
    has_personas = bool(conv.get("personas"))
    has_quality = bool(conv.get("quality"))
    has_spans = any(t.get("span_annotations") for t in turns)
    has_text = any(t.get("text") for t in turns)

    return {
        "AI": {
            "ready": has_speech_acts,
            "missing": ([] if has_speech_acts else ["speech_acts"])
                       + ([] if has_manipulation else ["manipulation_intensity"])
                       + ([] if has_vcs else ["cognitive_state"]),
        },
        "DS": {
            "ready": has_speech_acts and has_text,
            "missing": ([] if has_speech_acts else ["speech_acts"])
                       + ([] if has_text else ["text"]),
        },
        "TCS": {"ready": has_speech_acts, "missing": [] if has_speech_acts else ["speech_acts"]},
        "LDS": {"ready": has_text, "missing": [] if has_text else ["text"]},
        "PCS": {"ready": has_phases, "missing": [] if has_phases else ["phases/phase labels"]},
        "VSVS": {"ready": has_vcs, "missing": [] if has_vcs else ["cognitive_state"]},
        "AQS": {"ready": True, "missing": ([] if has_spans else ["span_annotations (partial)"])},
        "DBR": {"ready": True, "missing": []},
    }
