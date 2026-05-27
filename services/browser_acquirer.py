"""Browser acquisition for the apply runner.

Three modes — the apply runner passes ``mode`` and gets back a ready
``Page`` plus a cleanup callable. The adapter layer (slice 4) never
knows or cares how the browser was launched.

  attached_chrome      — connect to a running Chrome via CDP on
                         ``--remote-debugging-port``. Best stealth (real
                         browser fingerprint) but requires the operator
                         to launch Chrome with the flag set. Per Chrome
                         136 (March 2025) this MUST use a dedicated
                         debug profile, not the operator's daily one —
                         the Settings UI surfaces a wizard for that.

  chromium_persistent  — Playwright launches its bundled chromium with a
                         persistent ``user_data_dir``. Cookies + storage
                         survive across runs; fingerprint still
                         Playwright-flavoured.

  chromium_ephemeral   — Fresh launch, no profile. Each run starts cold.
                         Slice 3's default — we're only navigating to
                         JD URLs and screenshotting, no need for
                         persistent state, and a fresh chromium can't
                         accidentally leak a real LinkedIn session.

Per paircode round 2: ``playwright-stealth`` is intentionally NOT
applied under ``attached_chrome`` — stealth patches on top of a real
Chrome create inconsistencies that detectors flag.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


VALID_MODES = ("attached_chrome", "chromium_persistent", "chromium_ephemeral")


@dataclass
class AcquiredBrowser:
    """Handle to a live browser the runner can drive.

    ``cleanup`` is async — call it in a ``finally`` block to free the
    browser (close ephemeral, close context for persistent, leave Chrome
    alone for attached).
    """

    page: object  # playwright.async_api.Page — kept loose to avoid import cost
    context: object  # BrowserContext
    cleanup: Callable[[], Awaitable[None]]
    mode: str


async def acquire(
    mode: str,
    *,
    user_data_dir: Optional[str] = None,
    attached_port: int = 9222,
    headless: bool = True,
    viewport: tuple[int, int] = (1366, 768),
) -> AcquiredBrowser:
    """Open a browser in the requested mode and return a usable Page.

    ``headless`` is honored only by the chromium_* modes (attached_chrome
    inherits whatever the operator's Chrome is doing). Slice 3 defaults
    to headless True for the ephemeral mode so the operator's desktop
    doesn't get flooded with windows during dry runs.
    """

    if mode not in VALID_MODES:
        raise ValueError(f"Unknown browser mode '{mode}'. Valid: {VALID_MODES}")

    # Local import: playwright pulls in ~50MB of JS and the import is slow
    # enough that we don't want it at module-load time for every API call.
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()

    if mode == "attached_chrome":
        browser = await pw.chromium.connect_over_cdp(
            f"http://127.0.0.1:{attached_port}"
        )
        # CDP attach gives us the existing default context — re-use it.
        contexts = browser.contexts
        context = contexts[0] if contexts else await browser.new_context()
        page = await context.new_page()

        async def cleanup():
            await page.close()
            # Don't close the context or browser — we don't own them.
            await pw.stop()

        return AcquiredBrowser(page=page, context=context, cleanup=cleanup, mode=mode)

    if mode == "chromium_persistent":
        if not user_data_dir:
            raise ValueError(
                "chromium_persistent requires user_data_dir; "
                "configure UserProfile.chromium_profile_dir_apply"
            )
        os.makedirs(user_data_dir, exist_ok=True)
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": viewport[0], "height": viewport[1]},
        )
        # NOTE: stealth should be applied here in slice 5 once we add the
        # dep. Persistent + stealth is the recommended chromium fallback
        # when attached-Chrome isn't available.
        page = context.pages[0] if context.pages else await context.new_page()

        async def cleanup():
            await context.close()
            await pw.stop()

        return AcquiredBrowser(page=page, context=context, cleanup=cleanup, mode=mode)

    # chromium_ephemeral
    browser = await pw.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": viewport[0], "height": viewport[1]}
    )
    page = await context.new_page()

    async def cleanup():
        await context.close()
        await browser.close()
        await pw.stop()

    return AcquiredBrowser(page=page, context=context, cleanup=cleanup, mode=mode)
