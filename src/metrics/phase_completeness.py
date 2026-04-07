"""
phase_completeness.py — Phase Completeness Score (PCS) metric.

Dim1: Phase coverage ratio (P5 ≥ 40%)
Dim2: Phase sequence validity (non-decreasing sequence)
"""
from typing import Dict, Any, List

from src.constants import PCS_P5_MIN_RATIO, PCS_MIN_PHASES_PER_CONV
from src.schema import PHASE_ORDER


def compute_pcs(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính Phase Completeness Score cho toàn dataset.
    
    Returns:
        {
          phase_coverage_ratio: dict {P1..P6: float},
          stopped_at_phase: dict,
          invalid_sequences: list,
          p5_ok: bool,
          pcs_score: float,
          warnings: list,
        }
    """
    warnings: List[str] = []
    n = len(dataset)
    if n == 0:
        return {"pcs_score": 0.0, "warnings": ["Empty dataset"]}

    # Phase coverage
    phase_counts: Dict[str, int] = {f"P{i}": 0 for i in range(1, 7)}
    stopped_at: Dict[str, int] = {f"P{i}": 0 for i in range(1, 7)}
    invalid_sequences: List[Dict[str, Any]] = []

    for conv in dataset:
        phases = _get_conv_phases(conv)

        # Count phase presence
        for ph in set(phases):
            if ph in phase_counts:
                phase_counts[ph] += 1

        # Phase stopped at (last phase in conversation)
        if phases:
            last_ph = phases[-1]
            if last_ph in stopped_at:
                stopped_at[last_ph] += 1

        # Sequence validity (non-decreasing)
        phase_nums = [PHASE_ORDER.get(ph, 0) for ph in phases if ph in PHASE_ORDER]
        invalid_turns = []
        for i in range(1, len(phase_nums)):
            if phase_nums[i] < phase_nums[i - 1]:
                invalid_turns.append({
                    "position": i,
                    "from": phases[i - 1],
                    "to": phases[i],
                })
        if invalid_turns:
            invalid_sequences.append({
                "conversation_id": conv.get("conversation_id", ""),
                "violations": invalid_turns,
            })

        # Min phases check
        if len(set(phases)) < PCS_MIN_PHASES_PER_CONV:
            warnings.append(
                f"[{conv.get('conversation_id','')}] Only {len(set(phases))} phase(s) present (min {PCS_MIN_PHASES_PER_CONV})"
            )

    phase_coverage_ratio = {ph: round(cnt / n, 4) for ph, cnt in phase_counts.items()}
    stopped_pct = {ph: round(cnt / n, 4) for ph, cnt in stopped_at.items()}

    p5_ratio = phase_coverage_ratio.get("P5", 0.0)
    p5_ok = p5_ratio >= PCS_P5_MIN_RATIO
    if not p5_ok:
        warnings.append(f"P5 coverage {p5_ratio:.1%} < target {PCS_P5_MIN_RATIO:.0%}")

    if invalid_sequences:
        warnings.append(f"{len(invalid_sequences)} conversations have invalid phase sequences")

    # PCS score: coverage score × validity score
    coverage_score = sum(phase_coverage_ratio.values()) / 6.0
    validity_score = 1.0 - len(invalid_sequences) / n
    pcs_score = round(coverage_score * validity_score, 4)

    return {
        "phase_coverage_ratio": phase_coverage_ratio,
        "stopped_at_phase": stopped_pct,
        "invalid_sequences": invalid_sequences,
        "p5_ok": p5_ok,
        "p5_ratio": p5_ratio,
        "pcs_score": pcs_score,
        "invalid_seq_count": len(invalid_sequences),
        "warnings": warnings,
    }


def _get_conv_phases(conv: Dict[str, Any]) -> List[str]:
    """Extract ordered phase list from a conversation (turn-level)."""
    phases = []
    for t in conv.get("turns", []):
        ph = t.get("phase")
        if ph:
            phases.append(ph)
    # Fallback: conversation_meta.phases_present
    if not phases:
        phases = conv.get("conversation_meta", {}).get("phases_present", [])
    return phases
