"""Download SEC Financial Statement Data Set archives.

One zip per calendar quarter, 50-100 MB each, at a stable URL. The client
respects SEC's fair-access policy (identifying User-Agent, well under
10 requests/second) and caches on disk: a quarter that is already present is
never re-downloaded unless asked.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

from efs import config

ARCHIVE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class FetchError(RuntimeError):
    """Unrecoverable response from sec.gov."""


@dataclass
class Fetcher:
    user_agent: str
    raw_dir: Path = config.RAW_DIR
    min_interval: float = 1.0        # seconds between requests; bulk files are large, be gentle
    timeout: float = 600.0
    max_attempts: int = 4
    session: requests.Session = field(default_factory=requests.Session)
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"})
        self._last_request = 0.0

    def archive_path(self, quarter: str) -> Path:
        return self.raw_dir / f"{quarter}.zip"

    def fetch(self, quarter: str, *, force: bool = False, log=print) -> Path:
        path = self.archive_path(quarter)
        if path.exists() and not force:
            log(f"[fetch] {quarter} cached ({path.stat().st_size // 1_000_000} MB)")
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        url = ARCHIVE_URL.format(quarter=quarter)
        log(f"[fetch] {quarter} downloading {url}")
        self._download(url, path)
        log(f"[fetch] {quarter} saved {path.stat().st_size // 1_000_000} MB")
        return path

    def _download(self, url: str, path: Path) -> None:
        tmp = path.with_suffix(".part")
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self._pace()
            try:
                with self.session.get(url, timeout=self.timeout, stream=True) as resp:
                    if resp.status_code == 200:
                        with tmp.open("wb") as fh:
                            for chunk in resp.iter_content(1 << 20):
                                fh.write(chunk)
                        tmp.replace(path)
                        return
                    if resp.status_code == 403:
                        hint = (
                            "it contains the substring 'github', which SEC's bot filter rejects "
                            "regardless of the rest of the string"
                            if "github" in self.user_agent.lower()
                            else "it must be of the form 'app-name contact@example.com'"
                        )
                        raise FetchError(
                            f"403 from {url}. SEC returns its 'Request Rate Threshold Exceeded' page "
                            f"for any User-Agent it dislikes, not only for real rate limits. "
                            f"Check the User-Agent (current: {self.user_agent!r}): {hint}."
                        )
                    if resp.status_code == 404:
                        raise FetchError(f"404: {url} (quarter not published yet?)")
                    if resp.status_code not in RETRY_STATUSES:
                        raise FetchError(f"HTTP {resp.status_code} from {url}")
                    last = FetchError(f"HTTP {resp.status_code} from {url}")
            except requests.RequestException as exc:
                last = exc
            if attempt < self.max_attempts:
                self.sleep(2 ** attempt)
        tmp.unlink(missing_ok=True)
        raise FetchError(f"giving up on {url} after {self.max_attempts} attempts") from last

    def _pace(self) -> None:
        now = time.monotonic()
        wait = self._last_request + self.min_interval - now
        if wait > 0:
            self.sleep(wait)
        self._last_request = time.monotonic()
