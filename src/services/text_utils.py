from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower()))


def tokenize(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def token_overlap(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def is_near_duplicate(left: str, right: str, threshold: float = 0.82) -> bool:
    if normalize_text(left) == normalize_text(right):
        return True
    return token_overlap(left, right) >= threshold


def relevance_score(query: str, content: str) -> float:
    if not query.strip():
        return 0.15
    overlap = token_overlap(query, content)
    query_tokens = tokenize(query)
    content_tokens = tokenize(content)
    if not query_tokens:
        return 0.15
    coverage = len(query_tokens & content_tokens) / len(query_tokens)
    return (0.65 * overlap) + (0.35 * coverage)


def memory_key(content: str) -> str | None:
    lowered = content.lower()
    if "weight" in lowered or "weigh" in lowered:
        return "weight"
    if "height" in lowered:
        return "height"
    if re.search(r"\bage\b|\byears old\b", lowered):
        return "age"
    if "name is" in lowered or "call me" in lowered:
        return "name"
    return None
