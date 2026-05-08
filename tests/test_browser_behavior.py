from pathlib import Path

import pytest

from src.html.paper_assembler import write_html_paper
from tools.generate_sample_paper import build_sample_document


pytestmark = pytest.mark.browser


@pytest.fixture()
def sample_html(tmp_path: Path) -> Path:
    output_path = tmp_path / "sample_interactive_paper.html"
    write_html_paper(build_sample_document(), output_path)
    return output_path


def test_claim_card_expands_and_collapses(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    first_claim = page.locator("[data-component='claim-card']").first()
    details = first_claim.locator("[data-claim-details]")
    toggle = first_claim.locator("[data-action='toggle-claim']")

    assert details.is_hidden()

    toggle.click()
    assert details.is_visible()
    assert toggle.get_attribute("aria-expanded") == "true"

    toggle.click()
    assert details.is_hidden()
    assert toggle.get_attribute("aria-expanded") == "false"


def test_claim_card_toggles_between_quote_and_adjudication(
    page,
    sample_html: Path,
):
    page.goto(sample_html.as_uri())

    first_claim = page.locator("[data-component='claim-card']").first()
    quote = first_claim.locator("[data-claim-quote]")
    adjudication = first_claim.locator("[data-claim-adjudication]")
    mode_button = first_claim.locator("[data-action='toggle-claim-mode']")

    assert quote.is_visible()
    assert adjudication.is_hidden()

    mode_button.click()

    assert quote.is_hidden()
    assert adjudication.is_visible()
    assert mode_button.get_attribute("aria-pressed") == "true"
    assert mode_button.inner_text() == "Show speaker quote"

    mode_button.click()

    assert quote.is_visible()
    assert adjudication.is_hidden()
    assert mode_button.get_attribute("aria-pressed") == "false"
    assert mode_button.inner_text() == "Show adjudication"


def test_evidence_panel_filters_by_stance(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    first_panel = page.locator("[data-component='evidence-panel']").first()
    stance_filter = first_panel.locator("[data-filter='evidence-stance']")
    records = first_panel.locator("[data-evidence-record]")

    assert records.count() == 3
    assert first_panel.locator("[data-evidence-record]:visible").count() == 3

    stance_filter.select_option("supports")

    visible_records = first_panel.locator("[data-evidence-record]:visible")
    assert visible_records.count() == 1
    assert visible_records.first().get_attribute("data-stance") == "supports"

    stance_filter.select_option("qualifies")

    visible_records = first_panel.locator("[data-evidence-record]:visible")
    assert visible_records.count() == 1
    assert visible_records.first().get_attribute("data-stance") == "qualifies"

    stance_filter.select_option("all")

    assert first_panel.locator("[data-evidence-record]:visible").count() == 3


def test_evidence_panel_filters_by_tier(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    first_panel = page.locator("[data-component='evidence-panel']").first()
    tier_filter = first_panel.locator("[data-filter='evidence-tier']")

    tier_filter.select_option("1")

    visible_records = first_panel.locator("[data-evidence-record]:visible")
    assert visible_records.count() == 2

    for index in range(visible_records.count()):
        assert visible_records.nth(index).get_attribute("data-tier") == "1"

    tier_filter.select_option("2")

    visible_records = first_panel.locator("[data-evidence-record]:visible")
    assert visible_records.count() == 1
    assert visible_records.first().get_attribute("data-tier") == "2"

    tier_filter.select_option("all")

    assert first_panel.locator("[data-evidence-record]:visible").count() == 3


def test_source_key_finding_expands_and_collapses(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    first_panel = page.locator("[data-component='evidence-panel']").first()
    first_record = first_panel.locator("[data-evidence-record]").first()

    toggle = first_record.locator("[data-action='toggle-source-detail']")
    detail = first_record.locator(".source-detail")

    assert detail.is_hidden()

    toggle.click()

    assert detail.is_visible()
    assert toggle.get_attribute("aria-expanded") == "true"

    toggle.click()

    assert detail.is_hidden()
    assert toggle.get_attribute("aria-expanded") == "false"


def test_reading_list_filters_by_topic(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    reading_list = page.locator("[data-component='reading-list']")
    topic_filter = reading_list.locator("[data-filter='reading-topic']")

    assert reading_list.locator("[data-reading-item]:visible").count() == 4

    topic_filter.select_option("opponent_modeling")

    visible_items = reading_list.locator("[data-reading-item]:visible")
    assert visible_items.count() == 1
    assert visible_items.first().get_attribute("data-topic") == "opponent_modeling"

    topic_filter.select_option("all")

    assert reading_list.locator("[data-reading-item]:visible").count() == 4


def test_reading_list_filters_by_tier(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    reading_list = page.locator("[data-component='reading-list']")
    tier_filter = reading_list.locator("[data-filter='reading-tier']")

    tier_filter.select_option("3")

    visible_items = reading_list.locator("[data-reading-item]:visible")
    assert visible_items.count() == 1
    assert visible_items.first().get_attribute("data-tier") == "3"

    tier_filter.select_option("1")

    visible_items = reading_list.locator("[data-reading-item]:visible")
    assert visible_items.count() == 3

    for index in range(visible_items.count()):
        assert visible_items.nth(index).get_attribute("data-tier") == "1"


def test_reading_list_sorts_open_access_first(page, sample_html: Path):
    page.goto(sample_html.as_uri())

    reading_list = page.locator("[data-component='reading-list']")
    sort_filter = reading_list.locator("[data-sort='reading-accessibility']")

    sort_filter.select_option("open-access-first")

    items = reading_list.locator("[data-reading-item]")
    first_item = items.first()

    assert first_item.get_attribute("data-open-access") == "true"