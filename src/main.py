import json
import os
import logging
from pathlib import Path
import time
from typing import Any
from dotenv import load_dotenv

from src.clients.twitter import TwitterClient
from src.clients.blackbox import BlackboxClient
from src.storage.state import LocalStateStore
from src.utils.matching import build_query_terms_v2
from src.services.respond import should_reply, generate_reply


logging.basicConfig(level=logging.INFO)
load_dotenv()


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
    max_results = int(os.environ.get("MAX_RESULTS", "10"))
    data, headers = twitter.search_recent(query, since_id, max_results=max_results)
    if data is None:
        remaining = int(headers.get("x-rate-limit-remaining", "0"))
        reset = headers.get("x-rate-limit-reset")
        wait_s = int(os.environ.get("WAIT_ON_429_SECONDS", "0"))
        if wait_s > 0:
            time.sleep(wait_s)
            data, headers = twitter.search_recent(query, since_id, max_results=max_results)
        if data is None:
            auto_wait = os.environ.get("AUTO_WAIT_FOR_RESET", "0") == "1"
            max_auto_wait = int(os.environ.get("MAX_AUTO_WAIT_SECONDS", "0"))
            reset_epoch = int(reset or "0")
            now = int(time.time())
            delta = reset_epoch - now
            if auto_wait and delta > 0 and delta <= max_auto_wait:
                time.sleep(delta)
                data, headers = twitter.search_recent(query, since_id, max_results=max_results)
                if data is None:
                    logging.warning(f"Rate limited on search; skipping (remaining={remaining}, reset={reset})")
                    return {"status": "ok", "skipped": True, "remaining": remaining, "reset": reset}
            else:
                logging.warning(f"Rate limited on search; skipping (remaining={remaining}, reset={reset})")
                return {"status": "ok", "skipped": True, "remaining": remaining, "reset": reset}

    remaining = int(headers.get("x-rate-limit-remaining", "1"))
    reset = headers.get("x-rate-limit-reset")
    min_remain = int(os.environ.get("RATE_LIMIT_MIN_REMAINING", "0"))
    if remaining <= min_remain:
        logging.warning(f"Near rate limit; skipping processing (remaining={remaining}, reset={reset})")
        return {"status": "ok", "skipped": True, "remaining": remaining, "reset": reset}

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
