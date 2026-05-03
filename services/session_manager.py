"""Subprocess-based scraper session manager with log capture."""

import asyncio
import logging
import os
import signal
import sys
from collections import deque
from datetime import datetime
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages a single scraper subprocess with live log broadcasting."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.process: Optional[asyncio.subprocess.Process] = None
        self.started_at: Optional[datetime] = None
        self.exit_code: Optional[int] = None
        self.log_buffer: deque[str] = deque(maxlen=2000)
        self.subscribers: list[asyncio.Queue[str]] = []
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def status(self) -> dict:
        return {
            "running": self.is_running,
            "pid": self.process.pid if self.process else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "exit_code": self.exit_code,
            "log_count": len(self.log_buffer),
        }

    async def start(self, script: str = "quick_search.py") -> dict:
        if self.is_running:
            return {"status": "already_running", **self.status()}

        # Clean any stale Chromium singleton locks from a previous unclean shutdown.
        # These prevent persistent_context from launching with the same profile.
        profile_dir = os.path.join(self.project_root, "data", "browser_profile")
        for fname in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                p = os.path.join(profile_dir, fname)
                if os.path.lexists(p):
                    os.unlink(p)
            except Exception as e:
                logger.warning(f"Could not remove {fname}: {e}")

        venv_python = os.path.join(self.project_root, "venv", "bin", "python")
        python = venv_python if os.path.exists(venv_python) else sys.executable

        self.process = await asyncio.create_subprocess_exec(
            python, "-u", script,
            cwd=self.project_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        self.started_at = datetime.utcnow()
        self.exit_code = None
        self.log_buffer.clear()
        self._reader_task = asyncio.create_task(self._read_output())
        self._broadcast(f"[session] started pid={self.process.pid} script={script}")
        return {"status": "started", **self.status()}

    async def stop(self) -> dict:
        if not self.is_running:
            return {"status": "not_running", **self.status()}
        try:
            self.process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass
        self.exit_code = self.process.returncode
        self._broadcast(f"[session] stopped exit_code={self.exit_code}")
        return {"status": "stopped", **self.status()}

    async def _read_output(self):
        assert self.process and self.process.stdout
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip()
                self._broadcast(text)
        finally:
            await self.process.wait()
            self.exit_code = self.process.returncode
            self._broadcast(f"[session] process exited code={self.exit_code}")

    def _broadcast(self, line: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        entry = f"{ts}  {line}"
        self.log_buffer.append(entry)
        for q in list(self.subscribers):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    async def stream(self) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self.subscribers.append(q)
        try:
            for line in list(self.log_buffer):
                yield line
            while True:
                line = await q.get()
                yield line
        finally:
            if q in self.subscribers:
                self.subscribers.remove(q)
