import json
from pathlib import Path


class LocalStateStore:
    def __init__(self, path: str = "data/processed.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"processed": [], "since_id": None}))

    def _load(self):
        return json.loads(self.path.read_text())

    def _save(self, data):
        self.path.write_text(json.dumps(data))

    def get_since_id(self):
        return self._load().get("since_id")

    def set_since_id(self, since_id: str):
        d = self._load()
        d["since_id"] = since_id
        self._save(d)

    def is_processed(self, tweet_id: str) -> bool:
        return tweet_id in self._load().get("processed", [])

    def mark_processed(self, tweet_id: str):
        d = self._load()
        p = set(d.get("processed", []))
        p.add(tweet_id)
        d["processed"] = list(p)
        self._save(d)

