"""
stats.py — Tất cả hàm thống kê dạng pandas DataFrame.
Span-only version: không còn speech_acts, cognitive_state, response_type, manipulation_intensity.
"""
from typing import List, Dict, Any
from collections import Counter, defaultdict
import pandas as pd
import numpy as np


def build_conversation_df(conversations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Tạo DataFrame ở conversation-level. Hỗ trợ v1 + v2 schema."""
    rows = []
    for conv in conversations:
        labels = conv.get("conversation_labels", {})
        cm = conv.get("conversation_meta", {})
        scenario = conv.get("scenario", {})
        quality = conv.get("quality", {}) or {}
        turns = conv.get("turns", [])
        n_turns = len(turns)
        n_scammer = sum(1 for t in turns if t.get("speaker") == "scammer")
        n_victim = sum(1 for t in turns if t.get("speaker") == "victim")
        # v2: span_annotations, v1: spans
        n_spans = sum(len(t.get("span_annotations") or t.get("spans", [])) for t in turns)
        n_tokens = sum(len(t.get("text", "").split()) for t in turns)

        # outcome: v2 first, then v1
        outcome = cm.get("outcome") or labels.get("outcome", "")
        domain_l1 = scenario.get("domain_l1") or labels.get("domain_l1", "")
        scenario_name = scenario.get("name") or labels.get("scenario_name", "")
        ambiguity_level = cm.get("ambiguity_level") or labels.get("ambiguity_level", "")
        difficulty_tier = cm.get("difficulty_tier") or ""

        phases = list(cm.get("phases_present") or [])
        if not phases:
            seen = set()
            for t in turns:
                ph = t.get("phase") or (t.get("turn_labels") or {}).get("phase")
                if ph and ph not in seen:
                    seen.add(ph)
                    phases.append(ph)

        rows.append({
            "conversation_id": conv.get("conversation_id", ""),
            "title": conv.get("title") or scenario_name,
            "outcome": outcome,
            "scenario_group": labels.get("scenario_group", ""),
            "scenario_name": scenario_name,
            "domain_l1": domain_l1,
            "ambiguity_level": ambiguity_level,
            "difficulty_tier": difficulty_tier,
            "phase_sequence": " → ".join(phases),
            "n_turns": n_turns,
            "n_scammer_turns": n_scammer,
            "n_victim_turns": n_victim,
            "n_spans": n_spans,
            "n_tokens": n_tokens,
            "is_gold": quality.get("is_gold", False),
            "annotation_method": quality.get("annotation_method", ""),
            "writer_id": quality.get("writer_id", ""),
            "has_personas": bool(conv.get("personas")),
        })
    return pd.DataFrame(rows)


def flatten_to_turn_df(conversations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Tạo DataFrame ở turn-level. Span-only: chỉ giữ turn_id, speaker, phase, text, n_spans."""
    rows = []
    for conv in conversations:
        conv_id = conv.get("conversation_id", "")
        cm = conv.get("conversation_meta", {})
        outcome = cm.get("outcome") or conv.get("conversation_labels", {}).get("outcome", "")
        turns = conv.get("turns", [])
        for t in turns:
            phase = t.get("phase") or (t.get("turn_labels", {}) or {}).get("phase") or ""
            spans = t.get("span_annotations") or t.get("spans", [])
            n_spans = len(spans)
            span_tags = [sp.get("tag", "") for sp in spans if sp.get("tag")]

            rows.append({
                "conversation_id": conv_id,
                "outcome": outcome,
                "turn_id": t.get("turn_id", 0),
                "speaker": t.get("speaker", ""),
                "text": t.get("text", ""),
                "n_tokens": len(t.get("text", "").split()),
                "phase": phase,
                "n_spans": n_spans,
                "span_tags": span_tags,
                "span_tags_str": "|".join(span_tags),
            })
    return pd.DataFrame(rows)


def flatten_to_span_df(conversations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Tạo DataFrame ở span-level. Hỗ trợ v1 + v2 schema."""
    rows = []
    for conv in conversations:
        conv_id = conv.get("conversation_id", "")
        for t in conv.get("turns", []):
            # v2: span_annotations, v1: spans
            span_list = t.get("span_annotations") or t.get("spans", [])
            for sp in span_list:
                start = sp.get("start", 0)
                end = sp.get("end", 0)
                # v2: tag+span_text; v1: label+text
                label = sp.get("tag") or sp.get("label", "")
                text = sp.get("span_text") or sp.get("text", "")
                rows.append({
                    "conversation_id": conv_id,
                    "turn_id": t.get("turn_id", 0),
                    "speaker": t.get("speaker", ""),
                    "span_label": label,
                    "span_text": text,
                    "start": start,
                    "end": end,
                    "char_length": (end - start) if (start and end) else len(text),
                    "token_length": len(text.split()),
                })
    return pd.DataFrame(rows)


def compute_stats(conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tính thống kê tổng quan."""
    df_conv = build_conversation_df(conversations)
    df_turn = flatten_to_turn_df(conversations)
    df_span = flatten_to_span_df(conversations)

    n_conv = len(df_conv)
    n_turns = len(df_turn)
    n_scammer = len(df_turn[df_turn["speaker"] == "scammer"]) if not df_turn.empty else 0
    n_victim = len(df_turn[df_turn["speaker"] == "victim"]) if not df_turn.empty else 0
    n_spans = len(df_span)
    avg_turns = df_conv["n_turns"].mean() if n_conv > 0 else 0
    avg_tokens_conv = df_conv["n_tokens"].mean() if n_conv > 0 else 0
    avg_tokens_turn = df_turn["n_tokens"].mean() if n_turns > 0 else 0

    return {
        "n_conversations": n_conv,
        "n_turns": n_turns,
        "n_scammer_turns": n_scammer,
        "n_victim_turns": n_victim,
        "n_spans": n_spans,
        "avg_turns_per_conv": round(float(avg_turns), 2),
        "avg_tokens_per_conv": round(float(avg_tokens_conv), 2),
        "avg_tokens_per_turn": round(float(avg_tokens_turn), 2),
        # v2 outcomes
        "n_full_compliance": len(df_conv[df_conv["outcome"] == "FULL_COMPLIANCE"]) if not df_conv.empty else 0,
        "n_partial_compliance": len(df_conv[df_conv["outcome"] == "PARTIAL_COMPLIANCE"]) if not df_conv.empty else 0,
        "n_refusal": len(df_conv[df_conv["outcome"] == "REFUSAL"]) if not df_conv.empty else 0,
        # v1 legacy
        "n_scam": len(df_conv[df_conv["outcome"] == "SCAM"]) if not df_conv.empty else 0,
        "n_ambiguous": len(df_conv[df_conv["outcome"] == "AMBIGUOUS"]) if not df_conv.empty else 0,
        "n_legit": len(df_conv[df_conv["outcome"] == "LEGIT"]) if not df_conv.empty else 0,
    }


def compute_phase_transitions(df_turn: pd.DataFrame) -> pd.DataFrame:
    """
    Tính ma trận chuyển phase giữa turn i -> turn i+1.
    Returns pivot DataFrame (from_phase x to_phase).
    """
    transitions = []
    for conv_id, group in df_turn.groupby("conversation_id"):
        phases = group.sort_values("turn_id")["phase"].tolist()
        for i in range(len(phases) - 1):
            p_from = phases[i]
            p_to = phases[i + 1]
            if p_from and p_to:
                transitions.append((p_from, p_to))

    if not transitions:
        return pd.DataFrame()

    df_trans = pd.DataFrame(transitions, columns=["from_phase", "to_phase"])
    pivot = df_trans.groupby(["from_phase", "to_phase"]).size().reset_index(name="count")
    matrix = pivot.pivot(index="from_phase", columns="to_phase", values="count").fillna(0)
    return matrix


def compute_vcs_transitions(df_turn: pd.DataFrame) -> pd.DataFrame:
    """
    Tính ma trận chuyển VCS giữa các victim turn liên tiếp.
    """
    transitions = []
    victim_turns = df_turn[df_turn["speaker"] == "victim"].copy()

    for conv_id, group in victim_turns.groupby("conversation_id"):
        vcs_list = group.sort_values("turn_id")["vcs"].tolist()
        for i in range(len(vcs_list) - 1):
            v_from = vcs_list[i]
            v_to = vcs_list[i + 1]
            if v_from and v_to:
                transitions.append((v_from, v_to))

    if not transitions:
        return pd.DataFrame()

    df_trans = pd.DataFrame(transitions, columns=["from_vcs", "to_vcs"])
    pivot = df_trans.groupby(["from_vcs", "to_vcs"]).size().reset_index(name="count")
    matrix = pivot.pivot(index="from_vcs", columns="to_vcs", values="count").fillna(0)
    return matrix


def compute_span_tag_cooccurrence(df_turn: pd.DataFrame) -> pd.DataFrame:
    """
    Tính co-occurrence matrix của Span Tags.
    """
    scammer_turns = df_turn[df_turn["speaker"] == "scammer"]
    all_tag_lists = []
    for tag_list in scammer_turns.get("span_tags", pd.Series(dtype=object)):
        if isinstance(tag_list, list):
            all_tag_lists.append(tag_list)

    all_labels = sorted({s for row in all_tag_lists for s in row})
    if not all_labels:
        return pd.DataFrame()

    matrix = pd.DataFrame(0, index=all_labels, columns=all_labels)
    for row in all_tag_lists:
        for a in row:
            for b in row:
                if a in matrix.index and b in matrix.columns:
                    matrix.loc[a, b] += 1

    return matrix


def compute_span_tag_phase_matrix(df_turn: pd.DataFrame) -> pd.DataFrame:
    """
    Tính Span Tag x Phase: rows = phase, cols = span tags.
    Thay thế compute_tactic_phase_matrix.
    """
    scammer = df_turn[df_turn["speaker"] == "scammer"].copy()
    rows = []
    for _, row in scammer.iterrows():
        phase = row.get("phase", "")
        for tag in (row.get("span_tags") or []):
            rows.append({"phase": phase, "span_tag": tag})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    matrix = df.groupby(["phase", "span_tag"]).size().reset_index(name="count")
    pivot = matrix.pivot(index="phase", columns="span_tag", values="count").fillna(0)
    return pivot


def compute_prefix_signals(
    conversations: List[Dict[str, Any]],
    signal_spans: set = None,
) -> pd.DataFrame:
    """
    Tính tín hiệu scam xuất hiện tại mỗi prefix (25%, 50%, 75%, 100%).
    Span-only: chỉ dùng span tags, không cần speech_acts nữa.
    """
    from src.schema import SCAM_SIGNAL_SPANS
    if signal_spans is None:
        signal_spans = SCAM_SIGNAL_SPANS

    rows = []
    for conv in conversations:
        turns = conv.get("turns", [])
        n = len(turns)
        if n == 0:
            continue
        conv_id = conv.get("conversation_id", "")
        cm = conv.get("conversation_meta", {})
        outcome = cm.get("outcome") or conv.get("conversation_labels", {}).get("outcome", "")

        for pct in [0.25, 0.5, 0.75, 1.0]:
            cutoff = max(1, int(np.ceil(pct * n)))
            prefix_turns = turns[:cutoff]
            n_signals = 0
            for t in prefix_turns:
                for sp in (t.get("span_annotations") or t.get("spans", [])):
                    tag = sp.get("tag") or sp.get("label", "")
                    if tag in signal_spans:
                        n_signals += 1
            rows.append({
                "conversation_id": conv_id,
                "outcome": outcome,
                "prefix_pct": pct,
                "n_signals": n_signals,
            })

    return pd.DataFrame(rows)
