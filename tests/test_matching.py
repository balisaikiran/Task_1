from src.utils.matching import match_keyword, build_query_terms_v2


def test_match_keyword_exact():
    terms = ["github copilot", "claude"]
    m = match_keyword("I like using GitHub Copilot", terms, 85)
    assert m and m[0] == "github copilot"


def test_build_query_terms_v2():
    q = build_query_terms_v2(["github copilot", "claude"])
    assert "\"github copilot\"" in q and "claude" in q

