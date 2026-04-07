"""
tactic_coverage.py — Tactic Coverage Score (TCS) metric.

TCS kiểm soát sự đa dạng tactics trong dataset.
- Dim1: Label frequency (mỗi tactic phải ≥ 50 examples)
- Dim2: Distribution balance (Gini coefficient ≤ 0.4)
- Top co-occurrences giữa các tactic pairs
"""
from collections import Counter
from typing import Dict, Any, List, Tuple

from src.schema import ALL_TACTICS
from src.constants import TCS_MIN_COUNT_PER_TACTIC, TCS_GINI_TARGET


def compute_tcs(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính Tactic Coverage Score cho toàn dataset.
    
    Returns:
        {
          tactic_counts: dict,
          tactic_frequency: dict,
          gini_coefficient: float,
          top_cooccurrences: list,
          uncovered_tactics: list,
          tcs_score: float [0,1],
          warnings: list,
        }
    """
    warnings: List[str] = []

    # Aggregate all speech_acts from scammer turns
    tactic_counts: Dict[str, int] = {t: 0 for t in ALL_TACTICS}
    cooc_counter: Counter = Counter()

    total_scammer_turns = 0
    for conv in dataset:
        for turn in conv.get("turns", []):
            if turn.get("speaker") == "scammer":
                total_scammer_turns += 1
                acts = list(set(turn.get("speech_acts") or []))  # unique per turn
                for a in acts:
                    if a in tactic_counts:
                        tactic_counts[a] += 1
                # Co-occurrence pairs
                for i in range(len(acts)):
                    for j in range(i + 1, len(acts)):
                        pair = tuple(sorted([acts[i], acts[j]]))
                        cooc_counter[pair] += 1

    if total_scammer_turns == 0:
        return {"tactic_counts": tactic_counts, "warnings": ["No scammer turns found"]}

    # Tactic frequency (% of scammer turns)
    tactic_frequency = {k: round(v / total_scammer_turns, 4) for k, v in tactic_counts.items()}

    # Uncovered tactics (< min threshold)
    uncovered = [t for t in ALL_TACTICS if tactic_counts.get(t, 0) < TCS_MIN_COUNT_PER_TACTIC]
    if uncovered:
        warnings.append(f"Tactics with < {TCS_MIN_COUNT_PER_TACTIC} examples: {uncovered}")

    # Gini coefficient
    counts = sorted(tactic_counts.values())
    gini = _compute_gini(counts)

    if gini > TCS_GINI_TARGET:
        warnings.append(f"Gini coefficient {gini:.3f} > target {TCS_GINI_TARGET} (label imbalance)")

    # Top co-occurrences
    top_cooc = [
        {"pair": list(pair), "count": cnt}
        for pair, cnt in cooc_counter.most_common(10)
    ]

    # TCS score: fraction of tactics covered + gini penalty
    covered_ratio = (len(ALL_TACTICS) - len(uncovered)) / len(ALL_TACTICS)
    gini_penalty = max(0.0, gini - TCS_GINI_TARGET)  # 0 if ok
    tcs_score = round(max(0.0, covered_ratio * (1 - gini_penalty)), 4)

    return {
        "tactic_counts": tactic_counts,
        "tactic_frequency": tactic_frequency,
        "gini_coefficient": round(gini, 4),
        "top_cooccurrences": top_cooc,
        "uncovered_tactics": uncovered,
        "tcs_score": tcs_score,
        "total_scammer_turns": total_scammer_turns,
        "warnings": warnings,
    }


def _compute_gini(values: List[int]) -> float:
    """Compute Gini coefficient for a list of counts."""
    if not values or sum(values) == 0:
        return 0.0
    n = len(values)
    sorted_vals = sorted(values)
    total = sum(sorted_vals)
    gini = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(sorted_vals))
    return gini / (n * total)
