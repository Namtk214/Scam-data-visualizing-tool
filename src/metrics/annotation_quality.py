"""
annotation_quality.py — Annotation Quality Score (AQS) metric. Span-only version.

Dimensions:
  1. Cohen's Kappa vs Gold Set — so sánh span tags per turn (if available)
  2. Annotator Entropy — phân phối span tags per annotator (lazy detection)
  3. Span Completeness — tỷ lệ scammer turns có ít nhất 1 span annotation
"""
import math
from collections import Counter
from typing import Dict, Any, List, Optional

from src.constants import (
    AQS_KAPPA_MIN, AQS_KAPPA_ERROR,
    AQS_SPAN_COMPLETENESS_MIN, AQS_LAZY_ENTROPY_RATIO,
    AQS_MIN_TURNS_FOR_ENTROPY,
)
from src.schema import get_turn_span_tags


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
    # Tỷ lệ scammer turns có ít nhất 1 span annotation
    span_comp = _compute_span_completeness(dataset)
    if span_comp["completeness_ratio"] < AQS_SPAN_COMPLETENESS_MIN:
        warnings.append(
            f"Span annotation completeness {span_comp['completeness_ratio']:.1%} < {AQS_SPAN_COMPLETENESS_MIN:.0%}"
        )

    # ── Annotator entropy (span tag distribution per annotator) ────
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
    """Span completeness: tỷ lệ scammer turns có ít nhất 1 span annotation."""
    total_scammer_turns = 0
    turns_with_spans = 0

    for conv in dataset:
        for turn in conv.get("turns", []):
            if turn.get("speaker") != "scammer":
                continue
            total_scammer_turns += 1
            spans = turn.get("span_annotations") or []
            if spans:
                turns_with_spans += 1

    ratio = round(turns_with_spans / total_scammer_turns, 4) if total_scammer_turns > 0 else 1.0
    return {
        "total_scammer_turns": total_scammer_turns,
        "turns_with_spans": turns_with_spans,
        "completeness_ratio": ratio,
        "ok": ratio >= AQS_SPAN_COMPLETENESS_MIN,
    }


def _compute_annotator_entropy(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per-annotator span tag entropy để detect lazy annotation."""
    annotator_labels: Dict[str, List[str]] = {}

    for conv in dataset:
        qa = conv.get("quality") or {}
        writer_id = qa.get("writer_id", "unknown")
        for turn in conv.get("turns", []):
            if turn.get("speaker") == "scammer":
                for tag in get_turn_span_tags(turn):
                    annotator_labels.setdefault(writer_id, []).append(tag)

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
    """Cohen's Kappa per span tag: presence (1/0) per scammer turn vs gold."""
    gold_by_id = {c["conversation_id"]: c for c in gold_set}

    from src.schema import ALL_SPAN_TAGS
    pred_lists: Dict[str, List[int]] = {tag: [] for tag in ALL_SPAN_TAGS}
    gold_lists: Dict[str, List[int]] = {tag: [] for tag in ALL_SPAN_TAGS}

    for conv in dataset:
        cid = conv.get("conversation_id", "")
        gold_conv = gold_by_id.get(cid)
        if not gold_conv:
            continue

        pred_turns = [t for t in conv.get("turns", []) if t.get("speaker") == "scammer"]
        gold_turns = [t for t in gold_conv.get("turns", []) if t.get("speaker") == "scammer"]

        for p_turn, g_turn in zip(pred_turns, gold_turns):
            p_tags = get_turn_span_tags(p_turn)
            g_tags = get_turn_span_tags(g_turn)
            for tag in ALL_SPAN_TAGS:
                pred_lists[tag].append(1 if tag in p_tags else 0)
                gold_lists[tag].append(1 if tag in g_tags else 0)

    kappa_per_label: Dict[str, float] = {}
    for tag in ALL_SPAN_TAGS:
        preds = pred_lists.get(tag, [])
        golds = gold_lists.get(tag, [])
        if len(preds) < 2:
            continue
        kappa_per_label[tag] = round(_cohen_kappa(preds, golds), 4)

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
    p_counts = Counter(pred)
    g_counts = Counter(gold)
    all_labels = set(p_counts) | set(g_counts)
    pe = sum((p_counts.get(l, 0) / n) * (g_counts.get(l, 0) / n) for l in all_labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)
