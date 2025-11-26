import os
import json
from typing import Dict
from dotenv import load_dotenv


REQUIRED_KEYS = [
    "BLACKBOX_API_KEY",
    "TWITTER_BEARER_TOKEN",
    "TWITTER_CONSUMER_KEY",
    "TWITTER_CONSUMER_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
]


def load_env() -> Dict[str, str]:
    load_dotenv()
    return {k: os.getenv(k, "") for k in REQUIRED_KEYS}


def mask(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 6:
        return "***"
    return v[:3] + "***" + v[-3:]


def env_details() -> Dict:
    vals = load_env()
    return {
        "present": {k: bool(vals[k]) for k in REQUIRED_KEYS},
        "masked": {k: mask(vals[k]) for k in REQUIRED_KEYS},
    }


if __name__ == "__main__":
    print(json.dumps(env_details(), indent=2))

