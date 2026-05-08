from __future__ import annotations

import importlib.util

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if importlib.util.find_spec("pytest_playwright") is not None:
        return

    skip_browser = pytest.mark.skip(
        reason="browser tests require pytest-playwright and its page fixture"
    )

    for item in items:
        if item.get_closest_marker("browser") is not None:
            item.add_marker(skip_browser)
