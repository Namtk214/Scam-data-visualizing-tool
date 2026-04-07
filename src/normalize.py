"""
normalize.py — Backward-compat wrapper. 
New code should use src.normalize.normalize_input directly.
"""
from src.normalize.normalize_input import normalize_conversation, normalize_dataset


def normalize_dataset(raw, vcs_map=None):
    """Backward-compat: normalize list of conversations."""
    from src.normalize.normalize_input import normalize_dataset as _norm
    return _norm(raw, vcs_map)


def normalize_conversation(conv, vcs_map=None):
    """Backward-compat: normalize single conversation."""
    from src.normalize.normalize_input import normalize_conversation as _norm
    return _norm(conv, vcs_map)
