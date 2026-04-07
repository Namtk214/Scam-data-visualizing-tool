"""
annotation_quality.py — Annotation Quality Score (AQS) metric.

Dimensions:
  1. Cohen's Kappa vs Gold Set (if available)
  2. Annotator Entropy (lazy detection)
  3. Span Completeness (> 80%)
"""
import math
from collections import Counter
from typing import Dict, Any, List, Optional

from src.constants import (
    AQS_KAPPA_MIN, AQS_KAPPA_ERROR,
    AQS_SPAN_COMPLETENESS_MIN, AQS_LAZY_ENTROPY_RATIO,
    AQS_MIN_TURNS_FOR_ENTROPY,
)
from src.schema import TACTICS_REQUIRING_SPAN


def compute_aqs(
    dataset: List[Dict[str, Any]],
    gold_set: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Tính Annotation Quality Score.
    
    Args:
        dataset: normalized dataset
        gold_set: optional list of gold conversations (same schema)
    
    Returns:
        {cohen_kappa_per_label, mean_kappa, annotator_entropy,
         span_completeness, aqs_score, warnings}
    """
    warnings: List[str] = []
    note: List[str] = []

    # ── Span completeness ──────────────────────────────────────────
    span_comp = _compute_span_completeness(dataset)
    if span_comp["completeness_ratio"] < AQS_SPAN_COMPLETENESS_MIN:
        warnings.append(
            f"Span annotation completeness {span_comp['completeness_ratio']:.1%} < {AQS_SPAN_COMPLETENESS_MIN:.0%}"
        )

    # ── Annotator entropy ──────────────────────────────────────────
    entropy_result = _compute_annotator_entropy(dataset)

    # ── Cohen's Kappa vs Gold Set ──────────────────────────────────
    kappa_result: Dict[str, Any] = {}
    if gold_set:
        kappa_result = _compute_kappa_against_gold(dataset, gold_set)
        mean_kappa = kappa_result.get("mean_kappa", 0.0)
        if mean_kappa < AQS_KAPPA_ERROR:
            warnings.append(f"ERROR: Mean kappa {mean_kappa:.3f} < {AQS_KAPPA_ERROR} (critical)")
        elif mean_kappa < AQS_KAPPA_MIN:
            warnings.append(f"Mean kappa {mean_kappa:.3f} < target {AQS_KAPPA_MIN}")
    else:
        note.append("No gold set provided — Cohen's Kappa not computed. Upload gold set for full AQS.")
        kappa_result = {"mean_kappa": None, "cohen_kappa_per_label": {}}

    # ── AQS composite score ────────────────────────────────────────
    sc_score = span_comp["completeness_ratio"]
    if kappa_result.get("mean_kappa") is not None:
        kappa_score = kappa_result["mean_kappa"]
        aqs_score = round(0.5 * kappa_score + 0.5 * sc_score, 4)
    else:
        aqs_score = round(sc_score, 4)

    return {
        "span_completeness": span_comp,
        "annotator_entropy": entropy_result,
        "cohen_kappa_per_label": kappa_result.get("cohen_kappa_per_label", {}),
        "mean_kappa": kappa_result.get("mean_kappa"),
        "aqs_score": aqs_score,
        "notes": note,
        "warnings": warnings,
    }


def _compute_span_completeness(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Span completeness: turns with required span / turns requiring span."""
    turns_requiring = 0
    turns_with_spans = 0

    for conv in dataset:
        for turn in conv.get("turns", []):
            if turn.get("speaker") != "scammer":
                continue
            speech_acts = turn.get("speech_acts") or []
            has_required_tactic = any(sa in TACTICS_REQUIRING_SPAN for sa in speech_acts)
            if has_required_tactic:
                turns_requiring += 1
                spans = turn.get("span_annotations") or []
                if spans:
                    turns_with_spans += 1

    ratio = round(turns_with_spans / turns_requiring, 4) if turns_requiring > 0 else 1.0
    return {
        "turns_requiring_spans": turns_requiring,
        "turns_with_spans": turns_with_spans,
        "completeness_ratio": ratio,
        "ok": ratio >= AQS_SPAN_COMPLETENESS_MIN,
    }


def _compute_annotator_entropy(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-annotator entropy to detect lazy annotation."""
    annotator_labels: Dict[str, List[str]] = {}

    for conv in dataset:
        qa = conv.get("quality") or {}
        writer_id = qa.get("writer_id", "unknown")
        for turn in conv.get("turns", []):
            if turn.get("speaker") == "scammer":
                for sa in (turn.get("speech_acts") or []):
                    annotator_labels.setdefault(writer_id, []).append(sa)
            elif turn.get("speaker") == "victim":
                vcs = turn.get("cognitive_state")
                if vcs:
                    annotator_labels.setdefault(writer_id, []).append(vcs)

    entropy_per = {}
    for ann, labels in annotator_labels.items():
        if len(labels) >= AQS_MIN_TURNS_FOR_ENTROPY:
            entropy_per[ann] = _shannon_entropy(labels)

    if not entropy_per:
        return {"entropy_per_annotator": {}, "lazy_annotators": []}

    mean_entropy = sum(entropy_per.values()) / len(entropy_per)
    lazy_threshold = mean_entropy * AQS_LAZY_ENTROPY_RATIO
    lazy = [a for a, e in entropy_per.items() if e < lazy_threshold]

    return {
        "entropy_per_annotator": {a: round(e, 4) for a, e in entropy_per.items()},
        "mean_entropy": round(mean_entropy, 4),
        "lazy_threshold": round(lazy_threshold, 4),
        "lazy_annotators": lazy,
    }


def _compute_kappa_against_gold(
    dataset: List[Dict[str, Any]],
    gold_set: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Simple Cohen's Kappa per label type."""
    gold_by_id = {c["conversation_id"]: c for c in gold_set}

    all_labels = set()
    pred_lists: Dict[str, List[str]] = {}
    gold_lists: Dict[str, List[str]] = {}

    for conv in dataset:
        cid = conv.get("conversation_id", "")
        gold_conv = gold_by_id.get(cid)
        if not gold_conv:
            continue
        for p_turn, g_turn in zip(conv.get("turns", []), gold_conv.get("turns", [])):
            if p_turn.get("speaker") == "scammer":
                for sa in (p_turn.get("speech_acts") or []):
                    all_labels.add(sa)
                    pred_lists.setdefault(sa, []).append(1)
                    gold_val = 1 if sa in (g_turn.get("speech_acts") or []) else 0
                    gold_lists.setdefault(sa, []).append(gold_val)
            elif p_turn.get("speaker") == "victim":
                p_vcs = p_turn.get("cognitive_state") or "NONE"
                g_vcs = g_turn.get("cognitive_state") or "NONE"
                all_labels.add("vcs")
                pred_lists.setdefault("vcs", []).append(p_vcs)
                gold_lists.setdefault("vcs", []).append(g_vcs)

    kappa_per_label: Dict[str, float] = {}
    for label in all_labels:
        preds = pred_lists.get(label, [])
        golds = gold_lists.get(label, [])
        if len(preds) < 2:
            continue
        kappa_per_label[label] = round(_cohen_kappa(preds, golds), 4)

    mean_kappa = round(sum(kappa_per_label.values()) / len(kappa_per_label), 4) if kappa_per_label else 0.0

    return {
        "cohen_kappa_per_label": kappa_per_label,
        "mean_kappa": mean_kappa,
    }


def _shannon_entropy(labels: List[str]) -> float:
    counts = Counter(labels)
    total = len(labels)
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def _cohen_kappa(pred: List, gold: List) -> float:
    """Simple binary or categorical Cohen's kappa."""
    n = len(pred)
    if n == 0:
        return 0.0
    po = sum(1 for p, g in zip(pred, gold) if p == g) / n
    # Expected agreement
    p_counts = Counter(pred)
    g_counts = Counter(gold)
    all_labels = set(p_counts) | set(g_counts)
    pe = sum((p_counts.get(l, 0) / n) * (g_counts.get(l, 0) / n) for l in all_labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)
