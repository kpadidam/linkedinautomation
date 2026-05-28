"""Tests for the LLM-fallback module — label normalization + cache."""

from __future__ import annotations

from services.ats.llm_fallback import (
    _normalize_label,
    cached_answer,
    write_cache,
)


def test_normalize_label_collapses_whitespace():
    assert _normalize_label("Why are    you interested?") == "why are you interested"


def test_normalize_label_lowercases():
    assert _normalize_label("WHY ARE YOU INTERESTED?") == "why are you interested"


def test_normalize_label_strips_punctuation():
    # Two questions phrased differently should hash to the same key.
    a = _normalize_label("Why are you interested in this role?")
    b = _normalize_label("Why are you interested in this role!")
    assert a == b


def test_cache_write_then_read(temp_db_session):
    write_cache(temp_db_session, "greenhouse", "Why are you interested?", "I love it.")
    hit = cached_answer(temp_db_session, "greenhouse", "Why are you interested?")
    assert hit == "I love it."


def test_cache_miss_returns_none(temp_db_session):
    assert cached_answer(temp_db_session, "greenhouse", "Unseen question?") is None


def test_cache_keyed_by_ats(temp_db_session):
    # Same label across different ATSes should be cacheable separately —
    # phrasing means different things on different platforms.
    write_cache(temp_db_session, "greenhouse", "Tell us about you", "GH answer")
    write_cache(temp_db_session, "easy_apply", "Tell us about you", "LI answer")
    assert cached_answer(temp_db_session, "greenhouse", "Tell us about you") == "GH answer"
    assert cached_answer(temp_db_session, "easy_apply", "Tell us about you") == "LI answer"


def test_cache_returns_latest_on_duplicate_key(temp_db_session):
    # If the operator answered the same question twice (manual override),
    # the latest write wins — cached_answer orders by created_at DESC.
    write_cache(temp_db_session, "greenhouse", "Why?", "v1")
    write_cache(temp_db_session, "greenhouse", "Why?", "v2", source="operator")
    assert cached_answer(temp_db_session, "greenhouse", "Why?") == "v2"
