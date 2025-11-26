import json
import os
import logging
from pathlib import Path
from typing import Any

from src.clients.twitter import TwitterClient
from src.clients.blackbox import BlackboxClient
from src.storage.state import LocalStateStore
from src.utils.matching import build_query_terms_v2
from src.services.respond import should_reply, generate_reply


logging.basicConfig(level=logging.INFO)


def load_keywords() -> tuple[list, int]:
    p = Path("config/keywords.json")
    d = json.loads(p.read_text())
    return d["terms"], int(d.get("threshold", 85))


def poll_mentions(_request: Any = None):
    bt = os.environ.get("TWITTER_BEARER_TOKEN", "")
    ck = os.environ.get("TWITTER_CONSUMER_KEY", "")
    cs = os.environ.get("TWITTER_CONSUMER_SECRET", "")
    at = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    ats = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
    bbkey = os.environ.get("BLACKBOX_API_KEY", "")

    if not all([bt, ck, cs, at, ats, bbkey]):
        logging.error("Missing required environment credentials")
        return {"status": "error", "message": "missing credentials"}

    twitter = TwitterClient(bt, ck, cs, at, ats)
    blackbox = BlackboxClient(bbkey)
    state = LocalStateStore()
    terms, threshold = load_keywords()
    query = build_query_terms_v2(terms)
    since_id = state.get_since_id()
    data, headers = twitter.search_recent(query, since_id)

    remaining = int(headers.get("x-rate-limit-remaining", "1"))
    if remaining <= 1:
        logging.warning("Near rate limit; skipping processing")
        return {"status": "ok", "skipped": True}

    tweets = data.get("data", [])
    users = {u["id"]: u.get("username") for u in data.get("includes", {}).get("users", [])}
    max_id = since_id
    count_replied = 0
    for t in tweets:
        tid = t["id"]
        txt = t["text"]
        lang = t.get("lang")
        if lang and lang != "en":
            continue
        if state.is_processed(tid):
            continue
        decision = should_reply(txt, terms, threshold)
        if not decision["ok"]:
            continue
        kw = decision["keyword"]
        rid = t.get("id")
        author_id = t.get("author_id", "")
        handle = users.get(author_id, author_id)
        base_url = "https://www.blackbox.ai/"
        try:
            reply = generate_reply(blackbox, txt, handle, kw, base_url)
            twitter.post_reply(reply, rid)
            state.mark_processed(tid)
            count_replied += 1
        except Exception as e:
            logging.error(f"Failed to reply: {e}")
        if not max_id or int(tid) > int(max_id or 0):
            max_id = tid
    if max_id and max_id != since_id:
        state.set_since_id(max_id)
    return {"status": "ok", "replied": count_replied}


def dev_run():
    bbkey = os.environ.get("BLACKBOX_API_KEY", "")
    if not bbkey:
        logging.error("Missing BLACKBOX_API_KEY for dev run")
        return
    blackbox = BlackboxClient(bbkey)
    base_url = "https://www.blackbox.ai/"
    samples = [
        {"text": "Thinking of switching from GitHub Copilot to something faster.", "author": "dev_alex"},
        {"text": "Does Claude Code work well in VSCode?", "author": "jane_codes"},
        {"text": "Tried tabnine for Python. Any alternatives?", "author": "py_guru"},
    ]
    terms, threshold = load_keywords()
    for s in samples:
        decision = should_reply(s["text"], terms, threshold)
        if not decision["ok"]:
            continue
        kw = decision["keyword"]
        reply = generate_reply(blackbox, s["text"], s["author"], kw, base_url)
        print(f"Reply to @{s['author']}: {reply}")


if __name__ == "__main__":
    if os.environ.get("DRY_RUN") == "1":
        dev_run()
    else:
        poll_mentions(None)
