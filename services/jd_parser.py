"""Heuristic job-description parser.

Pure regex / string operations. No external NLP deps. The signals here feed
the embedding matcher (services/embed_matcher.py) so it can score against
extracted requirements instead of full-text noise.

Everything is best-effort: real JDs are messy, and a parse miss should
degrade gracefully (the matcher falls back to scoring against the whole
description). Determinism + explainability matter more than recall.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Requirements section extraction
# ---------------------------------------------------------------------------

# Section headings we treat as "this is the requirements list."
# Matched case-insensitively at line start, optionally with markdown / colons.
_REQ_HEADINGS = (
    r"requirements?",
    r"qualifications?",
    r"what you[''’]ll bring",
    r"what we[''’]re looking for",
    r"who you are",
    r"must[\s-]*haves?",
    r"basic qualifications?",
    r"minimum qualifications?",
    r"required skills?",
    r"key skills?",
)

# Headings that signal the *end* of a requirements block.
_END_HEADINGS = (
    r"nice to have",
    r"bonus",
    r"preferred",
    r"benefits?",
    r"perks?",
    r"about (us|the team|the role|the company)",
    r"responsibilities",
    r"what you[''’]ll do",
    r"compensation",
    r"equal opportunity",
    r"eeo",
)

_HEADING_PREFIX = r"^\s*[#*•\-\u2022]?\s*"
_HEADING_SUFFIX = r"\s*:?\s*$"

_REQ_HEAD_RE = re.compile(
    _HEADING_PREFIX + r"(?:" + "|".join(_REQ_HEADINGS) + ")" + _HEADING_SUFFIX,
    re.IGNORECASE,
)
_END_HEAD_RE = re.compile(
    _HEADING_PREFIX + r"(?:" + "|".join(_END_HEADINGS) + ")" + _HEADING_SUFFIX,
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r"^\s*[-•*\u2022]\s+(.*\S)\s*$")


def extract_requirements(jd_text: str) -> List[str]:
    """Return the bulleted requirements list from a JD.

    Strategy:
      1. Find the first ``Requirements:``-style heading.
      2. Read lines until an end-section heading or blank-line gap.
      3. Keep only lines that look like bullets; strip the bullet character.
      4. If no heading match, fall back to *every* bullet in the whole text
         (typical JDs have one bulleted block — this catches the common case
         where the heading was rendered as bold instead of a separate line).
      5. If still nothing, sentence-split the whole JD and keep medium-length
         sentences (>= 5 words). Last-resort signal.
    """

    if not jd_text or not jd_text.strip():
        return []

    lines = jd_text.splitlines()
    bullets: List[str] = []

    # --- pass 1: find a section heading ---
    start_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if _REQ_HEAD_RE.match(line):
            start_idx = i + 1
            break

    if start_idx is not None:
        blank_streak = 0
        for line in lines[start_idx:]:
            if _END_HEAD_RE.match(line):
                break
            if not line.strip():
                blank_streak += 1
                # Two blank lines in a row ends the section.
                if blank_streak >= 2 and bullets:
                    break
                continue
            blank_streak = 0
            m = _BULLET_RE.match(line)
            if m:
                bullets.append(m.group(1).strip())

    # --- pass 2: every bullet in the text ---
    if not bullets:
        for line in lines:
            m = _BULLET_RE.match(line)
            if m:
                bullets.append(m.group(1).strip())

    # --- pass 3: sentence split ---
    if not bullets:
        # Split on sentence boundaries; keep substantive sentences only.
        sentences = re.split(r"(?<=[.!?])\s+", jd_text)
        bullets = [
            s.strip()
            for s in sentences
            if 5 <= len(s.split()) <= 60
        ]

    # Cap. Past ~25 bullets a JD is usually pasting boilerplate.
    return bullets[:25]


# ---------------------------------------------------------------------------
# Years of experience
# ---------------------------------------------------------------------------

# Match "5+ years", "3-5 years of experience", "five years of", etc.
# We only handle digits — spelled-out numbers ("five") are noise-prone.
_YEARS_RE = re.compile(
    r"\b(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?"
    r"(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp|professional|industry)?",
    re.IGNORECASE,
)


def extract_years_required(jd_text: str) -> Optional[int]:
    """Smallest integer N such that the JD asks for "N years of experience".

    Returns the *minimum* matched value, since postings usually list "5+ years"
    or "3-5 years" — the lower bound is the gating one. ``None`` when no
    years-of-experience phrase is found.
    """

    if not jd_text:
        return None
    candidates: List[int] = []
    for m in _YEARS_RE.finditer(jd_text):
        try:
            n = int(m.group(1))
            if 0 < n <= 30:  # sanity clamp; "100 years" is noise
                candidates.append(n)
        except ValueError:  # noqa: PERF203
            continue
    return min(candidates) if candidates else None


# ---------------------------------------------------------------------------
# Title family
# ---------------------------------------------------------------------------

# Seniority adjectives we strip before bucketing.
_SENIORITY_WORDS = {
    "senior", "sr", "staff", "principal", "lead", "junior", "jr",
    "associate", "entry", "intermediate", "mid", "level",
    "i", "ii", "iii", "iv",
    "1", "2", "3", "4",
}

# Coarse buckets. Order matters — first match wins. Keep small; the goal is
# a hard pre-filter, not taxonomy.
_TITLE_FAMILIES: List[tuple[str, tuple[str, ...]]] = [
    ("data-engineer",     ("data engineer", "analytics engineer", "etl engineer")),
    ("data-scientist",    ("data scientist", "ml scientist", "research scientist")),
    ("ml-engineer",       ("ml engineer", "machine learning engineer", "ai engineer", "mlops")),
    ("data-analyst",      ("data analyst", "business analyst", "bi analyst", "analyst")),
    ("backend-engineer",  ("backend engineer", "back-end engineer", "backend developer", "api engineer", "server engineer")),
    ("frontend-engineer", ("frontend engineer", "front-end engineer", "frontend developer", "ui engineer", "react engineer")),
    ("fullstack-engineer",("full stack engineer", "fullstack engineer", "full-stack developer", "fullstack developer")),
    ("mobile-engineer",   ("ios engineer", "android engineer", "mobile engineer", "mobile developer")),
    ("devops-engineer",   ("devops", "site reliability", "sre", "platform engineer", "infrastructure engineer", "cloud engineer")),
    ("security-engineer", ("security engineer", "appsec", "infosec", "security analyst")),
    ("qa-engineer",       ("qa engineer", "test engineer", "sdet", "quality engineer")),
    ("product-manager",   ("product manager", "product owner", "pm")),
    ("designer",          ("designer", "ux", "ui designer")),
    ("software-engineer", ("software engineer", "software developer", "developer", "programmer", "engineer")),
]


def extract_title_family(title: str) -> Optional[str]:
    """Bucket a job title into a coarse family for hard filtering.

    Returns a canonical slug like ``"data-engineer"`` or ``None`` if the
    title doesn't match any known family. The fallback bucket
    ``"software-engineer"`` is intentionally last so more specific families
    win first.
    """

    if not title:
        return None
    t = title.lower()
    # Drop seniority words to normalize "Sr. Data Engineer III" ->
    # "data engineer". Keep punctuation simple.
    tokens = re.split(r"[^a-z]+", t)
    tokens = [tok for tok in tokens if tok and tok not in _SENIORITY_WORDS]
    normalized = " ".join(tokens)
    for family, keywords in _TITLE_FAMILIES:
        if any(kw in normalized for kw in keywords):
            return family
    return None


# ---------------------------------------------------------------------------
# Must-have skills (string-overlap)
# ---------------------------------------------------------------------------


def extract_must_have_skills(
    jd_text: str, known_skills: Iterable[str]
) -> Set[str]:
    """Return the subset of ``known_skills`` that appear in the JD text.

    Case-insensitive whole-word match. ``known_skills`` is typically the
    user's resume skill list — the matcher uses the overlap ratio as one
    half of the composite score.

    Multi-word skills ("React Native", "Apache Spark") are matched as
    phrases. Single-token skills require word boundaries so "go" doesn't
    match inside "google".
    """

    if not jd_text or not known_skills:
        return set()
    text_lower = jd_text.lower()
    found: Set[str] = set()
    for skill in known_skills:
        skill = (skill or "").strip()
        if not skill:
            continue
        s_lower = skill.lower()
        if " " in s_lower:
            # Phrase match — simple substring is fine for multi-word skills.
            if s_lower in text_lower:
                found.add(skill)
        else:
            # Single token — enforce word boundaries.
            if re.search(rf"\b{re.escape(s_lower)}\b", text_lower):
                found.add(skill)
    return found
