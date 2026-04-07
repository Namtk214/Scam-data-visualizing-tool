"""
tactic_coverage.py — Span Tag Coverage Score (TCS) metric. Span-only version.

TCS kiểm soát sự đa dạng span tags trong dataset.
Thay vì đếm speech_acts (turn-level), nay đếm span_annotations[].tag (token-level).

- Dim1: Span tag frequency (mỗi tag phải ≥ 50 examples)
- Dim2: Distribution balance (Gini coefficient ≤ 0.4)
- Top co-occurrences giữa các span tag pairs trong cùng turn
"""
from collections import Counter
from typing import Dict, Any, List, Tuple

from src.schema import ALL_SPAN_TAGS, get_turn_span_tags
from src.constants import TCS_MIN_COUNT_PER_TACTIC, TCS_GINI_TARGET, TCS_SATURATION


def compute_tcs(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính Span Tag Coverage Score cho toàn dataset.

    Returns:
        {
          span_tag_counts: dict,
          span_tag_frequency: dict,
          gini_coefficient: float,
          top_cooccurrences: list,
          uncovered_tags: list,
          tcs_score: float [0,1],
          warnings: list,
        }
    """
    warnings: List[str] = []

    # Aggregate all span tags from scammer turns
    tag_counts: Dict[str, int] = {t: 0 for t in ALL_SPAN_TAGS}
    cooc_counter: Counter = Counter()

    total_scammer_turns = 0
    for conv in dataset:
        for turn in conv.get("turns", []):
            if turn.get("speaker") == "scammer":
                total_scammer_turns += 1
                tags = list(get_turn_span_tags(turn))
                for tag in tags:
                    if tag in tag_counts:
                        tag_counts[tag] += 1
                # Co-occurrence pairs within same turn
                for i in range(len(tags)):
                    for j in range(i + 1, len(tags)):
                        pair = tuple(sorted([tags[i], tags[j]]))
                        cooc_counter[pair] += 1

    if total_scammer_turns == 0:
        return {"span_tag_counts": tag_counts, "warnings": ["No scammer turns found"]}

    # Span tag frequency (% of scammer turns)
    tag_frequency = {k: round(v / total_scammer_turns, 4) for k, v in tag_counts.items()}

    # Uncovered tags (< min threshold)
    uncovered = [t for t in ALL_SPAN_TAGS if tag_counts.get(t, 0) < TCS_MIN_COUNT_PER_TACTIC]
    if uncovered:
        warnings.append(f"Span tags with < {TCS_MIN_COUNT_PER_TACTIC} examples: {uncovered}")

    # Gini coefficient
    counts = sorted(tag_counts.values())
    gini = _compute_gini(counts)

    if gini > TCS_GINI_TARGET:
        warnings.append(f"Gini coefficient {gini:.3f} > target {TCS_GINI_TARGET} (label imbalance)")

    # Top co-occurrences
    top_cooc = [
        {"pair": list(pair), "count": cnt}
        for pair, cnt in cooc_counter.most_common(10)
    ]

    # TCS score: fraction of tags covered + gini penalty
    covered_ratio = (len(ALL_SPAN_TAGS) - len(uncovered)) / len(ALL_SPAN_TAGS)
    gini_penalty = max(0.0, gini - TCS_GINI_TARGET)
    tcs_score = round(max(0.0, covered_ratio * (1 - gini_penalty)), 4)

    return {
        "span_tag_counts": tag_counts,
        "span_tag_frequency": tag_frequency,
        "gini_coefficient": round(gini, 4),
        "top_cooccurrences": top_cooc,
        "uncovered_tags": uncovered,
        "tcs_score": tcs_score,
        "total_scammer_turns": total_scammer_turns,
        "warnings": warnings,
        # Legacy keys for chart compatibility
        "tactic_counts": tag_counts,
        "tactic_frequency": tag_frequency,
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
