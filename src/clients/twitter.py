import time
import requests
from requests_oauthlib import OAuth1Session


class TwitterClient:
    def __init__(self, bearer_token: str, consumer_key: str, consumer_secret: str, access_token: str, access_token_secret: str):
        self.bearer_token = bearer_token
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.base_url = "https://api.twitter.com/2"

    def search_recent(self, query: str, since_id: str | None = None, max_results: int = 50):
        url = f"{self.base_url}/tweets/search/recent"
        params = {
            "query": query,
            "tweet.fields": "author_id,lang,created_at",
            "expansions": "author_id",
            "user.fields": "username",
            "max_results": str(max_results),
        }
        if since_id:
            params["since_id"] = since_id
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 429:
            return None, r.headers
        r.raise_for_status()
        return r.json(), r.headers

    def post_reply(self, text: str, in_reply_to_tweet_id: str):
        url = f"{self.base_url}/tweets"
        json_data = {"text": text, "reply": {"in_reply_to_tweet_id": in_reply_to_tweet_id}}
        oauth = OAuth1Session(self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret)
        r = oauth.post(url, json=json_data)
        if r.status_code >= 400:
            r.raise_for_status()
        return r.json(), r.headers
