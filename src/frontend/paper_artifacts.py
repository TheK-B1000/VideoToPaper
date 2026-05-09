from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TITLE_PATTERN = re.compile(
    r"<title[^>]*>(.*?)</title>",
    re.IGNORECASE | re.DOTALL,
)

H1_PATTERN = re.compile(
    r"<h1[^>]*>(.*?)</h1>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class PaperArtifact:
    path: str
    exists: bool
    title: str | None
    size_bytes: int | None
    modified_at: float | None

    @property
    def is_openable(self) -> bool:
        return self.exists and self.path.endswith(".html")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "title": self.title,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "is_openable": self.is_openable,
        }


def inspect_paper_artifact(path: str | Path | None) -> PaperArtifact:
    if path is None:
        return PaperArtifact(
            path="",
            exists=False,
            title=None,
            size_bytes=None,
            modified_at=None,
        )

    paper_path = Path(path)

    if not paper_path.exists() or not paper_path.is_file():
        return PaperArtifact(
            path=paper_path.as_posix(),
            exists=False,
            title=None,
            size_bytes=None,
            modified_at=None,
        )

    stat = paper_path.stat()

    return PaperArtifact(
        path=paper_path.as_posix(),
        exists=True,
        title=extract_html_title(paper_path),
        size_bytes=stat.st_size,
        modified_at=stat.st_mtime,
    )


def extract_html_title(path: str | Path) -> str | None:
    html_path = Path(path)

    if html_path.suffix.lower() != ".html":
        return None

    text = html_path.read_text(encoding="utf-8", errors="ignore")

    title = _first_clean_match(TITLE_PATTERN, text)

    if title:
        return title

    return _first_clean_match(H1_PATTERN, text)


def build_file_url(path: str | Path) -> str:
    """
    Convert a local path into a ``file://`` URI.

    Note: Browsers usually **block** following ``file://`` links from an ``http://``
    origin (e.g. Streamlit on localhost), so prefer :func:`open_local_html_in_default_app`.
    """
    return Path(path).resolve().as_uri()


def open_local_html_in_default_app(path: str | Path) -> bool:
    """
    Open a local HTML file using the OS default handler (browser).

    Used from Inquiry Studio because ``st.link_button(..., file://...)`` is blocked
    by browser security when the app is served over HTTP.

    On Windows, ``cmd /c start`` is preferred—some setups ignore ``os.startfile``
    for HTML associations.
    """
    resolved = Path(path).resolve()

    if not resolved.is_file():
        return False

    if sys.platform == "win32":
        try:
            subprocess.run(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    str(resolved),
                ],
                check=False,
                timeout=60,
                cwd=str(resolved.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            return True
        except (OSError, subprocess.TimeoutExpired):
            os.startfile(str(resolved))  # type: ignore[attr-defined]
            return True

    import webbrowser

    return bool(webbrowser.open(resolved.as_uri()))


def reveal_file_in_os_file_manager(path: str | Path) -> bool:
    """
    Focus the file in Explorer (Windows), Finder reveal (macOS), or open parent folder (Linux).
    """
    resolved = Path(path).resolve()

    if not resolved.is_file():
        return False

    if sys.platform == "win32":
        subprocess.run(
            ["explorer", "/select,", str(resolved)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return True

    if sys.platform == "darwin":
        subprocess.run(
            ["open", "-R", str(resolved)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return True

    subprocess.run(
        ["xdg-open", str(resolved.parent)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    return True


def collect_paper_artifacts(paths: list[str | Path | None]) -> list[PaperArtifact]:
    return [inspect_paper_artifact(path) for path in paths]


def filter_openable_papers(artifacts: list[PaperArtifact]) -> list[PaperArtifact]:
    return [artifact for artifact in artifacts if artifact.is_openable]


def _first_clean_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)

    if not match:
        return None

    raw = match.group(1)
    cleaned = re.sub(r"<[^>]+>", "", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned or None