from typing import List, Tuple, Optional
from rapidfuzz import fuzz, process


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def build_query_terms_v2(terms: List[str]) -> str:
    parts = []
    for t in terms:
        qt = t.strip()
        if " " in qt:
            parts.append(f'"{qt}"')
        else:
            parts.append(qt)
    return "(" + " OR ".join(parts) + ") -is:retweet lang:en"


def match_keyword(text: str, terms: List[str], threshold: int = 85) -> Optional[Tuple[str, float]]:
    n = normalize_text(text)
    exact_hits = [t for t in terms if t in n]
    if exact_hits:
        return exact_hits[0], 100.0
    res = process.extractOne(n, terms, scorer=fuzz.partial_ratio)
    if res and res[1] >= threshold:
        return res[0], float(res[1])
    return None

