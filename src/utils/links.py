from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse


def add_utm_params(base_url: str, params: dict) -> str:
    u = urlparse(base_url)
    q = dict(parse_qsl(u.query))
    q.update(params)
    new_q = urlencode(q)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))

