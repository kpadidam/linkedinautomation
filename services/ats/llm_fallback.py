"""LLM fallback for unknown / free-text ATS form fields.

When an adapter encounters a field whose label doesn't match any
``field_map.yaml`` pattern, it calls ``answer_field()`` here. We use
the operator's already-configured OpenAI or Groq key (slice 1 settings)
— no new dependency.

Cache strategy: ``(ats_kind, normalized_label)`` → answer. Once we've
answered "Why are you interested in this role?" once for Greenhouse,
every subsequent Greenhouse application gets the cached answer without
another LLM call. The cache lives in ``analysis_cache`` (already used
by the legacy resume matcher) — single table, two new ``analysis_type``
values: ``ats_field_answer`` and ``ats_field_skip``.

Cost model:
- One-time LLM call per (ats, label) pair, then free forever
- Typical Greenhouse form has 2-5 free-text questions → ~$0.02-$0.05 on
  the operator's very first Greenhouse application, ~$0 thereafter
- Different companies asking the same question reuse the same cached
  answer — the operator can review/edit via the cache table if needed

This module is NOT used in slice 4's dry-run path. The adapter logs
``source='skipped'`` for unknown fields during dry-run so the operator
sees what would have been LLM'd. Real LLM calls start in slice 5+ once
the operator opts into real submits.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from config import settings
from database.models import AnalysisCache

logger = logging.getLogger(__name__)


def _normalize_label(label: str) -> str:
    """Collapse a form label to its dedup-friendly form.

    "Why are you interested in this role?" vs "Why are you interested in
    this position?" → same cached answer. We lowercase + strip
    punctuation + collapse whitespace. Trade-off: too aggressive
    normalization conflates unrelated questions; too loose loses cache
    hits. Current rule favors hits since the cache value is operator-
    reviewable.
    """

    cleaned = re.sub(r"[^\w\s]+", " ", label.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def cached_answer(
    db: Session,
    ats_kind: str,
    label: str,
) -> Optional[str]:
    """Return a previously-LLM'd answer for this (ats, label), or None."""

    key = f"{ats_kind}|{_normalize_label(label)}"
    row = (
        db.query(AnalysisCache)
        .filter(AnalysisCache.job_id == key)
        .filter(AnalysisCache.analysis_type == "ats_field_answer")
        .order_by(AnalysisCache.created_at.desc())
        .first()
    )
    if row and isinstance(row.analysis_result, dict):
        return row.analysis_result.get("answer")
    return None


def write_cache(
    db: Session,
    ats_kind: str,
    label: str,
    answer: str,
    source: str = "llm",
) -> None:
    """Persist an answer for future reuse. ``source`` lets us mark
    operator-supplied answers as authoritative."""

    key = f"{ats_kind}|{_normalize_label(label)}"
    row = AnalysisCache(
        job_id=key,
        analysis_type="ats_field_answer",
        analysis_result={
            "answer": answer,
            "source": source,
            "label_raw": label,
        },
        expires_at=datetime.utcnow() + timedelta(days=365),
    )
    db.add(row)
    db.commit()


async def answer_field(
    db: Session,
    ats_kind: str,
    label: str,
    jd_snippet: str,
    profile_resume_text: str,
) -> Optional[str]:
    """Produce an answer for a free-text form field.

    Returns ``None`` if neither LLM provider is configured — the adapter
    then logs the field as skipped and the operator gets an audit-log
    entry showing what couldn't be filled.

    Slice 5 wires this in. Slice 4 calls only ``cached_answer`` and
    skips when the cache misses, to keep the first ATS slice fully
    deterministic during initial calibration.
    """

    # Cache hit short-circuits.
    hit = cached_answer(db, ats_kind, label)
    if hit:
        return hit

    if not (settings.openai_api_key or settings.groq_api_key):
        logger.info(
            f"[llm_fallback] no LLM key — skipping field '{label[:60]}'"
        )
        return None

    prompt = _build_prompt(label, jd_snippet, profile_resume_text)

    try:
        answer = await _call_llm(prompt)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[llm_fallback] call failed: {e}")
        return None

    if answer:
        write_cache(db, ats_kind, label, answer, source="llm")
    return answer


def _build_prompt(label: str, jd_snippet: str, resume_text: str) -> str:
    """Tight prompt — we want one paragraph max, no hallucinated facts
    about projects/companies that aren't in the resume."""

    return (
        "You are filling out a job application on behalf of the candidate "
        "described below. Answer the question concisely (1-2 sentences "
        "unless the question explicitly asks for a paragraph). Use ONLY "
        "facts from the resume text — do not invent projects, dates, or "
        "achievements. If the question asks for an opinion, write one in "
        "first person, professional tone.\n\n"
        f"QUESTION: {label}\n\n"
        f"JOB DESCRIPTION (excerpt):\n{jd_snippet[:1200]}\n\n"
        f"CANDIDATE RESUME:\n{resume_text[:3000]}\n\n"
        "ANSWER:"
    )


async def _call_llm(prompt: str) -> str:
    """Call whichever LLM the operator has configured. Groq first (free
    tier), OpenAI second."""

    if settings.groq_api_key:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)
        resp = await client.chat.completions.create(
            model=settings.groq_model or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.6,
        )
        return (resp.choices[0].message.content or "").strip()

    if settings.openai_api_key:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.6,
        )
        return (resp.choices[0].message.content or "").strip()

    return ""
