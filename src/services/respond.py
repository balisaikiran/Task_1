import os
import logging
import re
from typing import Dict
from src.clients.blackbox import BlackboxClient
from src.utils.links import add_utm_params
from src.utils.matching import match_keyword


def sanitize_text(text: str) -> str:
    t = re.sub(r"https?://\S+", "", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def build_prompt(tweet_text: str, author_handle: str, keyword: str, referral_url: str) -> list:
    sys = (
        "You are a helpful coding assistant representing blackbox.ai. "
        "Reply to a tweet mentioning a competing AI coding tool. Be concise, polite, and contextual. "
        "Highlight blackbox.ai's value: fast code autocomplete, multi-IDE/browser support, explain & search code, and integrations. "
        "Do not disparage competitors. Avoid spam. Include the provided link naturally. "
        "Keep to one short paragraph."
    )
    user = (
        f"Tweet by @{author_handle}: {tweet_text}\n"
        f"Detected keyword: {keyword}\n"
        f"Referral link: {referral_url}"
    )
    return [{"role": "system", "content": sys}, {"role": "user", "content": user}]


def generate_reply(blackbox: BlackboxClient, tweet_text: str, author_handle: str, keyword: str, base_referral: str) -> str:
    url = add_utm_params(
        base_referral,
        {
            "utm_source": "twitter",
            "utm_medium": "bot",
            "utm_campaign": "competitor_mentions",
            "utm_content": "reply",
            "utm_term": keyword,
        },
    )
    messages = build_prompt(tweet_text, author_handle, keyword, url)
    reply = blackbox.chat(messages)
    reply = reply.strip()
    if len(reply) > 270:
        reply = reply[:267] + "..."
    return reply


def should_reply(text: str, terms: list, threshold: int) -> Dict:
    s = sanitize_text(text.lower())
    m = match_keyword(s, terms, threshold)
    if not m:
        return {"ok": False}
    k, c = m
    return {"ok": True, "keyword": k, "confidence": c}

