"""
dataset_balance.py — Dataset Balance Report (DBR) metric.

8 dimensions: scenario, outcome, length_class, speech_acts,
              victim_state, domain_l1, difficulty_tier, ambiguity_level

Mỗi dimension: normalized entropy [0,1].
Mean balance score ≥ 0.65 = acceptable.
"""
import math
from collections import Counter
from typing import Dict, Any, List

from src.constants import DBR_MEAN_BALANCE_MIN, DBR_DIMENSIONS
from src.schema import VALID_SSAT, VALID_VCS_V2


def compute_dbr(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính Dataset Balance Report.
    
    Returns:
        {
          normalized_entropy: dict {dim: float},
          mean_balance_score: float,
          dimension_counts: dict {dim: Counter},
          warnings: list,
        }
    """
    warnings: List[str] = []
    n = len(dataset)
    if n == 0:
        return {"mean_balance_score": 0.0, "warnings": ["Empty dataset"]}

    # Collect per-dimension values
    dim_counters: Dict[str, Counter] = {d: Counter() for d in DBR_DIMENSIONS}

    for conv in dataset:
        cm = conv.get("conversation_meta", {})
        scenario = conv.get("scenario", {})

        dim_counters["scenario"][scenario.get("id", "UNKNOWN")] += 1
        dim_counters["outcome"][cm.get("outcome", "UNKNOWN")] += 1
        dim_counters["length_class"][cm.get("length_class", "unknown")] += 1
        dim_counters["domain_l1"][scenario.get("domain_l1", "UNKNOWN")] += 1
        dim_counters["difficulty_tier"][cm.get("difficulty_tier", "unknown")] += 1
        dim_counters["ambiguity_level"][cm.get("ambiguity_level", "unknown")] += 1

        # speech_acts: each unique tactic used as a category
        all_acts = set()
        for t in conv.get("turns", []):
            all_acts.update(t.get("speech_acts") or [])
        for act in all_acts:
            dim_counters["speech_acts"][act] += 1

        # victim_state: dominant state in conversation
        states = [t.get("cognitive_state") for t in conv.get("turns", [])
                  if t.get("speaker") == "victim" and t.get("cognitive_state")]
        if states:
            dominant = Counter(states).most_common(1)[0][0]
            dim_counters["victim_state"][dominant] += 1

    # Normalized entropy per dimension
    normalized_entropy: Dict[str, float] = {}
    for dim, counter in dim_counters.items():
        if not counter:
            normalized_entropy[dim] = 0.0
            warnings.append(f"Dimension '{dim}' has no data")
            continue
        normalized_entropy[dim] = round(_normalized_entropy(counter), 4)

    mean_score = round(sum(normalized_entropy.values()) / len(normalized_entropy), 4) if normalized_entropy else 0.0

    if mean_score < DBR_MEAN_BALANCE_MIN:
        warnings.append(f"Mean balance score {mean_score:.3f} < target {DBR_MEAN_BALANCE_MIN}")

    # Per-dimension warnings
    for dim, ent in normalized_entropy.items():
        if ent < 0.5:
            warnings.append(f"Dimension '{dim}' is heavily imbalanced (entropy={ent:.3f})")

    # Specific guardrails
    scenario_counts = dim_counters["scenario"]
    underrepresented = [s for s, c in scenario_counts.items() if c < 80]
    if underrepresented:
        warnings.append(f"Scenarios with < 80 examples: {underrepresented}")

    outcome_counts = dim_counters["outcome"]
    total_outcomes = sum(outcome_counts.values())
    if total_outcomes > 0:
        comply_ratio = (outcome_counts.get("FULL_COMPLIANCE", 0) + outline_count(outcome_counts)) / total_outcomes
        if comply_ratio > 0.60:
            warnings.append(f"FULL_COMPLIANCE ratio {comply_ratio:.1%} > 60% (positive bias warning)")

    return {
        "normalized_entropy": normalized_entropy,
        "mean_balance_score": mean_score,
        "balance_ok": mean_score >= DBR_MEAN_BALANCE_MIN,
        "dimension_counts": {d: dict(c) for d, c in dim_counters.items()},
        "warnings": warnings,
    }


def outline_count(counter: Counter) -> int:
    # Count legacy SCAM outcome
    return counter.get("SCAM", 0)


def _normalized_entropy(counter: Counter) -> float:
    """Normalized Shannon entropy [0,1]."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    n_classes = len(counter)
    if n_classes <= 1:
        return 0.0
    entropy = -sum((c / total) * math.log2(c / total) for c in counter.values() if c > 0)
    max_entropy = math.log2(n_classes)
    return entropy / max_entropy if max_entropy > 0 else 0.0
