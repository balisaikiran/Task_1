import requests


class BlackboxClient:
    def __init__(self, api_key: str, base_url: str = "https://api.blackbox.ai"):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, messages, model: str = "blackboxai/openai/gpt-4") -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model,
            "messages": messages,
        }
        r = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=30)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]

