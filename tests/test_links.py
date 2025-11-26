from src.utils.links import add_utm_params


def test_add_utm_params():
    base = "https://www.blackbox.ai/"
    u = add_utm_params(base, {"utm_source": "twitter", "utm_medium": "bot"})
    assert "utm_source=twitter" in u and "utm_medium=bot" in u

