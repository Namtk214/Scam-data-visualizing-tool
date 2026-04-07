"""
difficulty_score.py — Difficulty Score (DS) metric.

DS Score [0.0 - 1.0] đo độ khó tổng thể của conversation đối với NLP model.

Sub-scores (weighted sum):
  F1 (0.25): Ambiguity contribution (reuse AI score)
  F2 (0.20): Tactic density (unique tactics / 8)
  F3 (0.15): Phase complexity (phases_present / 6)
  F4 (0.20): Linguistic complexity (TTR of scammer text)
  F5 (0.10): Victim confusion (state changes)
  F6 (0.10): Scammer adaptability (SA_ESCALATE + SA_DEFLECT count)

Tiers: easy <0.30, medium <0.55, hard <0.75, expert ≥0.75
"""
from typing import Dict, Any, List

from src.constants import DS_FACTOR_WEIGHTS, DS_TIER_THRESHOLDS, DS_TARGET, TCS_SATURATION
from src.metrics.ambiguity_index import compute_ai


def compute_ds(conv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tính Difficulty Score cho một conversation.
    
    Returns:
        {difficulty_score, difficulty_tier, sub_scores, recommendation, warnings}
    """
    warnings: List[str] = []
    turns = conv.get("turns", [])
    scammer_turns = [t for t in turns if t.get("speaker") == "scammer"]
    victim_turns = [t for t in turns if t.get("speaker") == "victim"]

    sub_scores: Dict[str, float] = {}

    # ── F1: Ambiguity contribution ──────────────────────────────────
    ai_result = compute_ai(conv)
    f1 = ai_result["ambiguity_score"] * DS_FACTOR_WEIGHTS["ambiguity"]
    sub_scores["ambiguity"] = round(f1, 4)
    warnings.extend(ai_result.get("warnings", []))

    # ── F2: Tactic density ──────────────────────────────────────────
    unique_tactics = set()
    for t in scammer_turns:
        unique_tactics.update(t.get("speech_acts") or [])
    tactic_density = min(len(unique_tactics) / TCS_SATURATION, 1.0)
    f2 = tactic_density * DS_FACTOR_WEIGHTS["tactic_density"]
    sub_scores["tactic_density"] = round(f2, 4)

    # ── F3: Phase complexity ────────────────────────────────────────
    phases = conv.get("conversation_meta", {}).get("phases_present", [])
    if not phases:
        # derive from turns
        seen = set()
        for t in turns:
            ph = t.get("phase")
            if ph:
                seen.add(ph)
        phases = list(seen)
    phase_ratio = min(len(set(phases)) / 6.0, 1.0)
    f3 = phase_ratio * DS_FACTOR_WEIGHTS["phase_complexity"]
    sub_scores["phase_complexity"] = round(f3, 4)

    # ── F4: Linguistic complexity (TTR of scammer text) ─────────────
    scammer_text = " ".join(t.get("text", "") for t in scammer_turns).lower()
    tokens = scammer_text.split()
    if tokens:
        ttr = len(set(tokens)) / len(tokens)
        ling = min(ttr * 2, 1.0)  # cap at 0.5 TTR → 1.0 factor
    else:
        ling = 0.0
        warnings.append("No scammer text found → F4 set to 0")
    f4 = ling * DS_FACTOR_WEIGHTS["linguistic"]
    sub_scores["linguistic"] = round(f4, 4)

    # ── F5: Victim state changes ────────────────────────────────────
    victim_states = [t.get("cognitive_state") for t in victim_turns if t.get("cognitive_state")]
    state_changes = sum(1 for i in range(1, len(victim_states)) if victim_states[i] != victim_states[i - 1])
    victim_conf = min(state_changes / 5.0, 1.0)
    f5 = victim_conf * DS_FACTOR_WEIGHTS["victim_confusion"]
    sub_scores["victim_confusion"] = round(f5, 4)

    # ── F6: Scammer adaptability ────────────────────────────────────
    escalate = sum(1 for t in scammer_turns if "SA_ESCALATE" in (t.get("speech_acts") or []))
    deflect = sum(1 for t in scammer_turns if "SA_DEFLECT" in (t.get("speech_acts") or []))
    adapt = min((escalate + deflect) / 4.0, 1.0)
    f6 = adapt * DS_FACTOR_WEIGHTS["scammer_adaptability"]
    sub_scores["scammer_adaptability"] = round(f6, 4)

    # ── Total ────────────────────────────────────────────────────────
    score = round(f1 + f2 + f3 + f4 + f5 + f6, 4)
    tier = _score_to_tier(score)
    recommendation = _ds_recommendation(tier)

    return {
        "difficulty_score": score,
        "difficulty_tier": tier,
        "sub_scores": sub_scores,
        "recommendation": recommendation,
        "warnings": warnings,
    }


def dataset_ds_report(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate DS metric trên toàn dataset."""
    results = []
    for conv in dataset:
        r = compute_ds(conv)
        r["conversation_id"] = conv.get("conversation_id", "")
        results.append(r)

    if not results:
        return {"per_conversation": [], "mean_score": 0.0, "warnings": ["Empty dataset"]}

    scores = [r["difficulty_score"] for r in results]
    mean_score = round(sum(scores) / len(scores), 4)

    tier_dist = {"easy": 0, "medium": 0, "hard": 0, "expert": 0}
    for r in results:
        t = r["difficulty_tier"]
        if t in tier_dist:
            tier_dist[t] += 1

    n = len(results)
    pct = {k: v / n for k, v in tier_dist.items()}

    warnings = []
    if not (DS_TARGET["easy_pct_min"] <= pct.get("easy", 0) <= DS_TARGET["easy_pct_max"]):
        warnings.append(f"Easy tier {pct['easy']:.1%} outside target 15-20%")
    if not (DS_TARGET["medium_pct_min"] <= pct.get("medium", 0) <= DS_TARGET["medium_pct_max"]):
        warnings.append(f"Medium tier {pct['medium']:.1%} outside target 35-45%")
    if not (DS_TARGET["hard_pct_min"] <= pct.get("hard", 0) <= DS_TARGET["hard_pct_max"]):
        warnings.append(f"Hard tier {pct['hard']:.1%} outside target 25-35%")

    return {
        "per_conversation": results,
        "mean_score": mean_score,
        "tier_distribution": tier_dist,
        "tier_pct": pct,
        "warnings": warnings,
    }


def _score_to_tier(score: float) -> str:
    for tier, (lo, hi) in DS_TIER_THRESHOLDS.items():
        if lo <= score < hi:
            return tier
    return "expert"


def _ds_recommendation(tier: str) -> str:
    msgs = {
        "easy":   "Conversation quá dễ, cân nhắc bổ sung thêm chiến thuật phức tạp hơn.",
        "medium": "Độ khó vừa phải, phù hợp cho training set chính.",
        "hard":   "Conversation khó, phù hợp cho test set cao cấp.",
        "expert": "Rất phức tạp, suitable for adversarial evaluation.",
    }
    return msgs.get(tier, "")
