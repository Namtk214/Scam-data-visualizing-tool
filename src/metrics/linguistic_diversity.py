"""
linguistic_diversity.py — Linguistic Diversity Score (LDS) metric.

Dimensions:
  1. Type-Token Ratio (TTR > 0.3)
  2. Internal Semantic Similarity via TF-IDF cosine (mean cosine < 0.35)
  3. Near-duplicate pairs (cosine > 0.70)
  4. Bigram reuse ratio
  5. Overall diversity_score
"""
from typing import Dict, Any, List, Tuple
from collections import Counter
import math

from src.constants import (
    LDS_TTR_MIN, LDS_MEAN_COSINE_MAX,
    LDS_NEAR_DUP_THRESHOLD, LDS_MAX_SAMPLE_SIZE
)


def compute_lds(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính Linguistic Diversity Score cho toàn dataset.
    
    Returns:
        {ttr, mean_pairwise_sim, near_duplicate_pairs, 
         bigram_reuse_ratio, diversity_score, warnings}
    """
    warnings: List[str] = []

    # Build per-conversation scammer text blobs
    texts: List[str] = []
    conv_ids: List[str] = []
    for conv in dataset:
        blob = " ".join(
            t.get("text", "") for t in conv.get("turns", [])
            if t.get("speaker") == "scammer"
        ).strip().lower()
        if blob:
            texts.append(blob)
            conv_ids.append(conv.get("conversation_id", ""))

    if not texts:
        return {"diversity_score": 0.0, "warnings": ["No scammer text found"]}

    # ── Dim 1: TTR ────────────────────────────────────────────────
    all_tokens = " ".join(texts).split()
    ttr = len(set(all_tokens)) / len(all_tokens) if all_tokens else 0.0
    if ttr < LDS_TTR_MIN:
        warnings.append(f"TTR {ttr:.3f} < threshold {LDS_TTR_MIN}")

    # ── Dim 4: Bigram reuse ratio ──────────────────────────────────
    all_bigrams = _extract_bigrams(" ".join(texts))
    bigram_counts = Counter(all_bigrams)
    total_bigrams = len(all_bigrams)
    repeated_bigrams = sum(cnt for cnt in bigram_counts.values() if cnt > 1)
    bigram_reuse_ratio = round(repeated_bigrams / total_bigrams, 4) if total_bigrams > 0 else 0.0

    # ── Dim 2 & 3: TF-IDF cosine similarity ──────────────────────
    sample = texts[:LDS_MAX_SAMPLE_SIZE]
    sample_ids = conv_ids[:LDS_MAX_SAMPLE_SIZE]

    if len(sample) >= 2:
        tfidf_matrix = _simple_tfidf(sample)
        mean_sim, near_dup_pairs = _compute_pairwise_sim(tfidf_matrix, sample_ids)
    else:
        mean_sim = 0.0
        near_dup_pairs = []
        warnings.append("Too few conversations for similarity computation")

    if mean_sim > LDS_MEAN_COSINE_MAX:
        warnings.append(f"Mean cosine similarity {mean_sim:.3f} > threshold {LDS_MEAN_COSINE_MAX}")

    near_dup_ratio = len(near_dup_pairs) / max(len(sample), 1)
    if near_dup_ratio > 0.05:
        warnings.append(f"Near-duplicate ratio {near_dup_ratio:.1%} > 5%")

    # ── Overall diversity score ────────────────────────────────────
    ttr_score = min(ttr / 0.5, 1.0)  # normalize: TTR 0.5 = perfect
    sim_score = max(0.0, 1.0 - mean_sim / LDS_MEAN_COSINE_MAX) if mean_sim > 0 else 1.0
    bigram_score = max(0.0, 1.0 - bigram_reuse_ratio)
    diversity_score = round((ttr_score * 0.4 + sim_score * 0.4 + bigram_score * 0.2), 4)

    return {
        "ttr": round(ttr, 4),
        "ttr_ok": ttr >= LDS_TTR_MIN,
        "mean_pairwise_sim": round(mean_sim, 4),
        "sim_ok": mean_sim <= LDS_MEAN_COSINE_MAX,
        "near_duplicate_pairs": near_dup_pairs[:20],  # top 20
        "near_dup_count": len(near_dup_pairs),
        "near_dup_ratio": round(near_dup_ratio, 4),
        "bigram_reuse_ratio": bigram_reuse_ratio,
        "diversity_score": diversity_score,
        "vocabulary_size": len(set(all_tokens)),
        "total_tokens": len(all_tokens),
        "warnings": warnings,
    }


def _extract_bigrams(text: str) -> List[Tuple[str, str]]:
    tokens = text.split()
    return list(zip(tokens, tokens[1:]))


def _simple_tfidf(documents: List[str]) -> List[List[float]]:
    """Lightweight TF-IDF without sklearn dependency."""
    # Tokenize
    tokenized = [doc.split() for doc in documents]
    
    # Build vocabulary
    vocab = sorted(set(tok for doc in tokenized for tok in doc))
    vocab_idx = {w: i for i, w in enumerate(vocab)}
    n = len(documents)
    v = len(vocab)
    
    # TF
    tf = [[0.0] * v for _ in range(n)]
    for i, tokens in enumerate(tokenized):
        cnt = Counter(tokens)
        total = len(tokens)
        for tok, c in cnt.items():
            if tok in vocab_idx:
                tf[i][vocab_idx[tok]] = c / total

    # IDF
    idf = [0.0] * v
    for j in range(v):
        df = sum(1 for i in range(n) if tf[i][j] > 0)
        idf[j] = math.log((n + 1) / (df + 1)) + 1

    # TF-IDF
    tfidf = [[tf[i][j] * idf[j] for j in range(v)] for i in range(n)]
    
    # L2 normalize
    for i in range(n):
        norm = math.sqrt(sum(x * x for x in tfidf[i])) or 1.0
        tfidf[i] = [x / norm for x in tfidf[i]]
    
    return tfidf


def _compute_pairwise_sim(
    tfidf: List[List[float]],
    ids: List[str],
    threshold: float = LDS_NEAR_DUP_THRESHOLD
) -> Tuple[float, List[Dict[str, Any]]]:
    """Compute mean pairwise cosine similarity and find near-duplicates."""
    n = len(tfidf)
    if n < 2:
        return 0.0, []

    total_sim = 0.0
    count = 0
    near_dups = []

    for i in range(n):
        for j in range(i + 1, n):
            sim = sum(tfidf[i][k] * tfidf[j][k] for k in range(len(tfidf[i])))
            total_sim += sim
            count += 1
            if sim >= threshold:
                near_dups.append({
                    "conv_a": ids[i],
                    "conv_b": ids[j],
                    "similarity": round(sim, 4),
                })

    mean_sim = total_sim / count if count > 0 else 0.0
    return mean_sim, sorted(near_dups, key=lambda x: -x["similarity"])
