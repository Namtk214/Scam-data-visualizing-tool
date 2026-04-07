"""
normalize_input.py — Normalize conversation sang unified v2 internal schema.

Sau khi normalize, mọi conversation phải có:
  - conversation_id
  - scenario.id, scenario.name, scenario.domain_l1
  - conversation_meta.outcome, conversation_meta.phases_present
  - turns[]
  - quality

Mỗi turn phải có:
  - turn_id, speaker, text, phase, speech_acts (list), 
    response_type (or null), cognitive_state (or null),
    manipulation_intensity (or null), span_annotations (list)
"""
from typing import Dict, Any, List, Optional

from src.normalize.legacy_adapter import is_legacy_schema, adapt_legacy
from src.schema import VALID_PHASES, VALID_SSAT, VALID_VRT, VALID_VCS_V2
from src.constants import classify_length


def normalize_conversation(
    conv: Dict[str, Any],
    vcs_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Normalize một conversation sang unified v2 schema.
    Tự detect legacy vs v2 schema.
    
    Args:
        conv: raw conversation dict
        vcs_map: custom VCS legacy mapping
    
    Returns:
        Normalized conversation dict
    """
    if is_legacy_schema(conv):
        conv = adapt_legacy(conv, vcs_map)
    else:
        # v2 schema: fill in missing derived fields
        conv = _fill_derived_fields(conv)

    # Ensure all mandatory fields exist
    conv = _ensure_mandatory_fields(conv)
    # Normalize all turns
    conv["turns"] = [_normalize_turn(t, i + 1) for i, t in enumerate(conv.get("turns", []))]
    return conv


def normalize_dataset(
    raw: List[Dict[str, Any]],
    vcs_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Normalize toàn bộ dataset."""
    return [normalize_conversation(c, vcs_map) for c in raw]


def _fill_derived_fields(conv: Dict[str, Any]) -> Dict[str, Any]:
    """Fill các fields có thể derive từ data v2 nếu chưa có."""
    turns = conv.get("turns", [])
    cm = conv.setdefault("conversation_meta", {})

    # total_turns
    if not cm.get("total_turns"):
        cm["total_turns"] = len(turns)

    # phases_present
    if not cm.get("phases_present"):
        seen = set()
        phases = []
        for t in turns:
            ph = t.get("phase")
            if ph and ph not in seen:
                seen.add(ph)
                phases.append(ph)
        cm["phases_present"] = phases

    # primary_tactics
    if not cm.get("primary_tactics"):
        tactic_counter: Dict[str, int] = {}
        for t in turns:
            if t.get("speaker") == "scammer":
                for s in (t.get("speech_acts") or []):
                    tactic_counter[s] = tactic_counter.get(s, 0) + 1
        cm["primary_tactics"] = sorted(tactic_counter, key=lambda k: -tactic_counter[k])[:3]

    # length_class
    if not cm.get("length_class"):
        cm["length_class"] = classify_length(len(turns))

    return conv


def _ensure_mandatory_fields(conv: Dict[str, Any]) -> Dict[str, Any]:
    """Đảm bảo tất cả mandatory fields tồn tại (fill None/empty nếu cần)."""
    conv.setdefault("conversation_id", "UNKNOWN")

    scenario = conv.setdefault("scenario", {})
    scenario.setdefault("id", "UNKNOWN")
    scenario.setdefault("name", "")
    scenario.setdefault("domain_l1", "UNKNOWN")

    cm = conv.setdefault("conversation_meta", {})
    cm.setdefault("outcome", "")
    cm.setdefault("phases_present", [])
    cm.setdefault("length_class", "")
    cm.setdefault("total_turns", len(conv.get("turns", [])))
    cm.setdefault("primary_tactics", [])
    cm.setdefault("ambiguity_score", None)
    cm.setdefault("difficulty_score", None)
    cm.setdefault("ambiguity_level", "")
    cm.setdefault("difficulty_tier", "")

    conv.setdefault("turns", [])
    conv.setdefault("quality", {
        "writer_id": "",
        "expert_reviewer_id": "",
        "annotation_method": "unknown",
        "iaa_score": None,
        "expert_authenticity_score": None,
        "is_gold": False,
    })

    return conv


def _normalize_turn(turn: Dict[str, Any], fallback_id: int) -> Dict[str, Any]:
    """Normalize một turn: fill các required fields."""
    result = dict(turn)

    result.setdefault("turn_id", fallback_id)
    result.setdefault("speaker", "")
    result.setdefault("text", "")
    result.setdefault("phase", None)

    # speech_acts must be a list
    sa = result.get("speech_acts")
    if sa is None:
        result["speech_acts"] = []
    elif isinstance(sa, str):
        result["speech_acts"] = [sa] if sa else []

    result.setdefault("response_type", None)
    result.setdefault("cognitive_state", None)
    result.setdefault("manipulation_intensity", None)

    # span_annotations must be a list
    spans = result.get("span_annotations")
    if spans is None:
        # Try legacy spans field
        legacy_spans = result.get("spans", [])
        from src.normalize.legacy_adapter import _adapt_legacy_span
        result["span_annotations"] = [_adapt_legacy_span(s) for s in legacy_spans]
    
    return result
