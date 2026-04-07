"""
legacy_adapter.py — Chuyển đổi schema v1 cũ sang unified v2 schema.

Mapping rules:
  conversation_labels.scenario_group (A/B/C/D) → scenario.domain_l1
  conversation_labels.ambiguity_level (L1-L4)  → conversation_meta.ambiguity_level + ambiguity_score
  turn_labels.ssat     → speech_acts (list)
  turn_labels.vrt      → response_type
  turn_labels.vcs      → cognitive_state
  turn_labels.phase    → phase
  spans[{label,start,end,text}] → span_annotations[{tag,span_text,start,end}]
"""
from typing import Dict, Any, List, Optional

from src.schema import (
    SCENARIO_GROUP_TO_DOMAIN,
    AMBIGUITY_LEGACY_TO_V2,
    AMBIGUITY_LEGACY_TO_SCORE,
    OUTCOME_LEGACY_MAP,
    VCS_LEGACY_MAP_DEFAULT,
)


def is_legacy_schema(conv: Dict[str, Any]) -> bool:
    """Detect nếu conversation dùng schema v1 cũ."""
    return (
        "conversation_labels" in conv
        or "turn_labels" in conv.get("turns", [{}])[0] if conv.get("turns") else False
        or "scenario_group" in conv.get("conversation_labels", {})
    )


def adapt_legacy(conv: Dict[str, Any], vcs_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Convert legacy v1 conversation → v2 unified schema.
    Giữ lại tất cả fields gốc và chỉ thêm/map sang v2.
    
    Args:
        conv: conversation dict (có thể là v1 hoặc v2 partial)
        vcs_map: optional custom VCS legacy mapping
    
    Returns:
        conv dict đã được normalized sang v2 schema
    """
    if vcs_map is None:
        vcs_map = VCS_LEGACY_MAP_DEFAULT.copy()

    result = dict(conv)
    labels = conv.get("conversation_labels", {})

    # ── conversation_id ────────────────────────────────────────────
    if "conversation_id" not in result:
        result["conversation_id"] = conv.get("id", conv.get("title", "unknown"))

    # ── scenario block ─────────────────────────────────────────────
    if "scenario" not in result:
        sg = labels.get("scenario_group", "")
        domain_l1 = SCENARIO_GROUP_TO_DOMAIN.get(sg, "UNKNOWN")
        result["scenario"] = {
            "id": labels.get("scenario_id", sg or "UNKNOWN"),
            "name": labels.get("scenario_name", conv.get("title", "")),
            "domain_l1": domain_l1,
            "domain_l2": labels.get("domain_l2", ""),
            "fraud_goal": labels.get("fraud_goal", ""),
            "real_world_prevalence": "",
        }

    # ── conversation_meta block ────────────────────────────────────
    if "conversation_meta" not in result:
        legacy_ambig = labels.get("ambiguity_level", "")
        ambig_level_v2 = AMBIGUITY_LEGACY_TO_V2.get(legacy_ambig, legacy_ambig.lower() if legacy_ambig else "")
        ambig_score = AMBIGUITY_LEGACY_TO_SCORE.get(legacy_ambig, None)

        legacy_outcome = labels.get("outcome", "")
        outcome_v2 = OUTCOME_LEGACY_MAP.get(legacy_outcome, legacy_outcome)

        turns = conv.get("turns", [])
        phase_seq = labels.get("phase_sequence", [])

        # Derive phases_present from turns if not in labels
        if not phase_seq and turns:
            seen = set()
            phase_seq_derived = []
            for t in turns:
                ph = t.get("turn_labels", {}).get("phase") or t.get("phase")
                if ph and ph not in seen:
                    seen.add(ph)
                    phase_seq_derived.append(ph)
            phase_seq = phase_seq_derived

        # Derive primary_tactics from scammer turns
        tactic_counter: Dict[str, int] = {}
        for t in turns:
            if t.get("speaker") == "scammer":
                ssat = t.get("turn_labels", {}).get("ssat") or t.get("speech_acts", [])
                if isinstance(ssat, list):
                    for s in ssat:
                        tactic_counter[s] = tactic_counter.get(s, 0) + 1

        primary_tactics = [k for k, _ in sorted(tactic_counter.items(), key=lambda x: -x[1])][:3]

        n_turns = len(turns)
        from src.constants import classify_length
        length_class = labels.get("length_class") or classify_length(n_turns)

        result["conversation_meta"] = {
            "length_class": length_class,
            "total_turns": n_turns,
            "outcome": outcome_v2,
            "phases_present": phase_seq,
            "primary_tactics": primary_tactics,
            "cialdini_principles": labels.get("cialdini_principles", []),
            "cognitive_mechanisms": labels.get("cognitive_mechanisms", []),
            "ambiguity_score": ambig_score,
            "difficulty_score": None,
            "ambiguity_level": ambig_level_v2,
            "difficulty_tier": "",
        }
    else:
        # v2 schema but outcome might be missing
        cm = result["conversation_meta"]
        if not cm.get("outcome"):
            legacy_outcome = labels.get("outcome", "")
            cm["outcome"] = OUTCOME_LEGACY_MAP.get(legacy_outcome, legacy_outcome)

    # ── personas block ────────────────────────────────────────────
    if "personas" not in result:
        result["personas"] = None

    # ── quality block ─────────────────────────────────────────────
    if "quality" not in result:
        result["quality"] = {
            "writer_id": "",
            "expert_reviewer_id": "",
            "annotation_method": "unknown",
            "iaa_score": None,
            "expert_authenticity_score": None,
            "is_gold": False,
        }

    # ── turns ─────────────────────────────────────────────────────
    result["turns"] = [_adapt_legacy_turn(t, vcs_map) for t in conv.get("turns", [])]

    # ── meta block (v2) ───────────────────────────────────────────
    if "meta" not in result:
        result["meta"] = {
            "dataset_version": "1.0.0",
            "schema_version": "2.0.0",
            "language": "vi",
            "license": "CC BY-NC-SA 4.0",
            "_adapted_from_legacy": True,
        }

    return result


def _adapt_legacy_turn(turn: Dict[str, Any], vcs_map: Dict[str, str]) -> Dict[str, Any]:
    """Convert một turn từ v1 → v2 schema."""
    result = dict(turn)
    tl = turn.get("turn_labels", {}) or {}
    
    # speech_acts
    if "speech_acts" not in result:
        ssat = tl.get("ssat", [])
        result["speech_acts"] = ssat if isinstance(ssat, list) else ([ssat] if ssat else [])

    # response_type
    if "response_type" not in result:
        result["response_type"] = tl.get("vrt") or None

    # cognitive_state (with legacy mapping)
    if "cognitive_state" not in result:
        raw_vcs = tl.get("vcs") or None
        if raw_vcs:
            result["cognitive_state"] = vcs_map.get(raw_vcs, raw_vcs)
        else:
            result["cognitive_state"] = None

    # phase
    if "phase" not in result:
        result["phase"] = tl.get("phase") or None

    # manipulation_intensity
    if "manipulation_intensity" not in result:
        result["manipulation_intensity"] = tl.get("manipulation_intensity") or None

    # span_annotations
    if "span_annotations" not in result:
        spans = turn.get("spans", [])
        result["span_annotations"] = [_adapt_legacy_span(s) for s in spans]

    # cialdini_trigger, cognitive_mechanism, expected_victim_reaction, debrief_note
    for field in ["cialdini_trigger", "cognitive_mechanism", "expected_victim_reaction", "debrief_note"]:
        if field not in result:
            result[field] = None

    return result


def _adapt_legacy_span(span: Dict[str, Any]) -> Dict[str, Any]:
    """Convert span v1 {label, start, end, text} → v2 {tag, span_text, start, end}."""
    return {
        "tag": span.get("label") or span.get("tag", ""),
        "span_text": span.get("text") or span.get("span", ""),
        "start": span.get("start"),
        "end": span.get("end"),
    }
