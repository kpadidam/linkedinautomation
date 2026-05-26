"""Local semantic matcher for the auto-apply pipeline (slice 1).

Replaces the LLM-based scorer at services/resume_matcher.py for the apply
gate specifically. Pipeline:

  1. Hard filters (years, title family) reject obvious mismatches early.
  2. Chunked per-requirement embedding match — for each requirement in the
     JD, take the max cosine against any resume bullet. Mean of those is
     the semantic component.
  3. Keyword overlap on known skills (must-haves found / total).
  4. Composite = 0.5 * semantic + 0.5 * keyword.
  5. Gating happens elsewhere (a percentile cut against the last N scores
     — call ``gate()``). Absolute thresholds drift with corpus; percentile
     self-calibrates.

The model (all-MiniLM-L6-v2) is loaded lazily on first use to avoid the
~80MB download blocking app startup. Encoding is CPU-only; ~50ms/text.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

import numpy as np

from services.jd_parser import (
    extract_must_have_skills,
    extract_requirements,
    extract_title_family,
    extract_years_required,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Model loader (lazy + singleton)
# ---------------------------------------------------------------------------

_MODEL = None
_MODEL_NAME = None


def get_model(name: str = DEFAULT_MODEL):
    """Lazy-load the SentenceTransformer model. Singleton per process."""

    global _MODEL, _MODEL_NAME
    if _MODEL is not None and _MODEL_NAME == name:
        return _MODEL
    from sentence_transformers import SentenceTransformer  # local import: heavy
    logger.info(f"Loading embedding model: {name}")
    _MODEL = SentenceTransformer(name)
    _MODEL_NAME = name
    return _MODEL


def encode(texts: Sequence[str], name: str = DEFAULT_MODEL) -> np.ndarray:
    """Encode a list of strings into a (n, dim) float32 matrix."""

    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = get_model(name)
    vecs = model.encode(
        list(texts),
        normalize_embeddings=True,  # so cosine = dot product
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vecs.astype(np.float32, copy=False)


# ---------------------------------------------------------------------------
# Serialization (numpy <-> bytes)
# ---------------------------------------------------------------------------


def to_bytes(arr: np.ndarray) -> bytes:
    """Serialize an ndarray to bytes via ``np.save`` (preserves shape+dtype)."""
    buf = io.BytesIO()
    np.save(buf, arr, allow_pickle=False)
    return buf.getvalue()


def from_bytes(blob: bytes) -> np.ndarray:
    """Inverse of ``to_bytes``."""
    return np.load(io.BytesIO(blob), allow_pickle=False)


# ---------------------------------------------------------------------------
# Profile shape
# ---------------------------------------------------------------------------


@dataclass
class CandidateProfile:
    """Everything the matcher needs about the user.

    ``resume_bullets`` is a list of short text spans (one role/project per
    line ideally). If only a free-form resume is available, sentence-split
    it before passing in. ``skills`` drives the keyword-overlap signal.
    ``years_experience`` is used as a hard gate against the JD's
    "N years required" extraction.
    """

    resume_bullets: List[str]
    skills: List[str]
    years_experience: Optional[int] = None
    target_title_families: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Match result
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    """Output of ``score()``.

    ``raw_score`` is the composite signal in [0, 1]. ``rejected_by`` is set
    to the name of the hard filter that killed the job (or ``None`` if the
    score is meaningful). ``reasons`` carries human-readable explainability
    bits that the dashboard surfaces.
    """

    raw_score: float
    rejected_by: Optional[str]
    semantic: float
    keyword: float
    must_haves_found: List[str]
    must_haves_missing: List[str]
    extracted_requirements: List[str]
    years_required: Optional[int]
    title_family: Optional[str]
    reasons: dict

    def to_dict(self) -> dict:
        return {
            "raw_score": self.raw_score,
            "rejected_by": self.rejected_by,
            "semantic": self.semantic,
            "keyword": self.keyword,
            "must_haves_found": self.must_haves_found,
            "must_haves_missing": self.must_haves_missing,
            "extracted_requirements": self.extracted_requirements,
            "years_required": self.years_required,
            "title_family": self.title_family,
            "reasons": self.reasons,
        }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _reject(name: str, **extra) -> MatchResult:
    return MatchResult(
        raw_score=0.0,
        rejected_by=name,
        semantic=0.0,
        keyword=0.0,
        must_haves_found=[],
        must_haves_missing=[],
        extracted_requirements=[],
        years_required=None,
        title_family=None,
        reasons={"rejected": name, **extra},
    )


def score(
    jd_text: str,
    jd_title: str,
    profile: CandidateProfile,
    model_name: str = DEFAULT_MODEL,
) -> MatchResult:
    """Score a single job against a candidate profile.

    Returns a ``MatchResult`` whose ``raw_score`` is the composite in
    [0, 1]. ``rejected_by`` is set when a hard filter killed the job and
    ``raw_score`` is 0 in that case.
    """

    # ------------------------------------------------------------------
    # Hard filter: title family
    # ------------------------------------------------------------------
    title_family = extract_title_family(jd_title or "")
    if profile.target_title_families:
        if title_family not in profile.target_title_families:
            return _reject(
                "title_family",
                detected=title_family,
                wanted=profile.target_title_families,
            )

    # ------------------------------------------------------------------
    # Hard filter: years of experience
    # ------------------------------------------------------------------
    years_required = extract_years_required(jd_text or "")
    if (
        profile.years_experience is not None
        and years_required is not None
        and years_required > profile.years_experience
    ):
        return _reject(
            "years",
            required=years_required,
            have=profile.years_experience,
        )

    # ------------------------------------------------------------------
    # Requirement extraction + per-requirement semantic match
    # ------------------------------------------------------------------
    requirements = extract_requirements(jd_text or "")
    if not requirements:
        # Fall back to scoring the whole description as a single chunk so
        # we still get *some* signal. Don't reject — JDs without parseable
        # requirements sections are common.
        requirements = [jd_text[:1500]] if jd_text else []

    if requirements and profile.resume_bullets:
        req_vecs = encode(requirements, name=model_name)
        bullet_vecs = encode(profile.resume_bullets, name=model_name)
        # Cosine matrix: (n_reqs, n_bullets). Normalized vectors -> dot.
        sims = req_vecs @ bullet_vecs.T
        per_req_max = sims.max(axis=1)
        semantic = float(per_req_max.mean())
        # Clamp to [0, 1] — cosine on normalized vectors is technically
        # [-1, 1] but for embedding-space text it sits in ~[0, 1] anyway.
        semantic = max(0.0, min(1.0, semantic))
    else:
        semantic = 0.0

    # ------------------------------------------------------------------
    # Keyword overlap on must-haves
    # ------------------------------------------------------------------
    found = extract_must_have_skills(jd_text or "", profile.skills)
    # Use the JD's mentioned-skills as the denominator: how many of the
    # skills mentioned in this JD does the candidate have? More fair than
    # dividing by total profile skills.
    jd_mentioned_skills = extract_must_have_skills(
        jd_text or "", _ALL_COMMON_SKILLS | set(profile.skills)
    )
    if jd_mentioned_skills:
        keyword = len(found) / len(jd_mentioned_skills)
        missing = sorted(jd_mentioned_skills - found)
    else:
        keyword = 0.0
        missing = []

    # ------------------------------------------------------------------
    # Composite
    # ------------------------------------------------------------------
    composite = 0.5 * semantic + 0.5 * keyword

    return MatchResult(
        raw_score=composite,
        rejected_by=None,
        semantic=semantic,
        keyword=keyword,
        must_haves_found=sorted(found),
        must_haves_missing=missing,
        extracted_requirements=requirements,
        years_required=years_required,
        title_family=title_family,
        reasons={
            "weights": {"semantic": 0.5, "keyword": 0.5},
            "n_requirements": len(requirements),
            "n_jd_skills_mentioned": len(jd_mentioned_skills),
        },
    )


# ---------------------------------------------------------------------------
# Percentile gate
# ---------------------------------------------------------------------------


def gate(
    raw_score: float,
    recent_scores: Sequence[float],
    percentile: int = 90,
) -> bool:
    """True if ``raw_score`` clears the Nth percentile of ``recent_scores``.

    Empty corpus → always False (we want at least one batch's worth of
    history before we trust the gate). When there are fewer than 20 prior
    scores the gate falls back to a hardcoded floor of 0.5 so a cold start
    doesn't approve everything in the first few hours.
    """

    if not recent_scores or len(recent_scores) < 20:
        return raw_score >= 0.5
    cutoff = float(np.percentile(recent_scores, percentile))
    return raw_score >= cutoff


# ---------------------------------------------------------------------------
# Common-skills lexicon (denominator for keyword score)
# ---------------------------------------------------------------------------

# Used to estimate "how many skills did this JD mention" without requiring
# the candidate to enumerate every possible tech. Intentionally short —
# this is a denominator-stabilizer, not a comprehensive taxonomy. Append
# user-specific tech via profile.skills.
_ALL_COMMON_SKILLS = {
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "SQL", "NoSQL",
    "Postgres", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
    "React", "Vue", "Angular", "Next.js", "Node.js", "Django", "Flask",
    "FastAPI", "Spring", "Rails", "Express", "GraphQL", "REST", "gRPC",
    "Kafka", "Spark", "Hadoop", "Airflow", "dbt", "Snowflake", "Databricks",
    "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy",
    "Linux", "Git", "CI/CD", "Jenkins", "GitHub Actions",
}


# ---------------------------------------------------------------------------
# Convenience: build a CandidateProfile from a DB UserProfile row
# ---------------------------------------------------------------------------


def profile_from_user_row(user_profile, resume_text: Optional[str] = None) -> CandidateProfile:
    """Build a CandidateProfile from a database UserProfile row.

    Pulls resume text from the row (or the passed-in override), splits it
    into bullets on newlines, and unions skill lists. ``search_roles`` /
    target families are not on UserProfile today — caller can populate
    ``target_title_families`` explicitly when known.
    """

    text = resume_text or (getattr(user_profile, "resume_text", "") or "")
    # Sentence-split if no obvious bullets; otherwise keep one bullet per line.
    if "\n" in text and len(text.splitlines()) >= 5:
        bullets = [ln.strip(" -*\u2022\t") for ln in text.splitlines() if ln.strip()]
    else:
        import re as _re
        bullets = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    bullets = [b for b in bullets if len(b.split()) >= 3][:200]

    skills = getattr(user_profile, "skills", None) or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    return CandidateProfile(
        resume_bullets=bullets,
        skills=list(skills),
        years_experience=None,  # not stored on UserProfile yet
        target_title_families=[],
    )
