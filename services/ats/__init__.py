"""ATS adapter package.

Each adapter implements ``ATSAdapter`` from ``base`` and registers itself
in ``DETECTORS`` so ``detect_ats(url, html)`` can dispatch. The apply
runner never instantiates concrete adapter classes — it calls
``acquire_adapter(job, page)`` and gets back the right one.
"""

from services.ats.base import (
    ATSAdapter,
    ApplyResult,
    ApplyStatus,
    ATSKind,
    FormField,
    UnknownATS,
    detect_ats,
)

__all__ = [
    "ATSAdapter",
    "ApplyResult",
    "ApplyStatus",
    "ATSKind",
    "FormField",
    "UnknownATS",
    "detect_ats",
]
