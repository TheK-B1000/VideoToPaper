"""
Load repository ``.env`` when ``python-dotenv`` is installed.

Safe no-op if the dependency is missing or no ``.env`` file exists.
"""

from __future__ import annotations


def try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()
