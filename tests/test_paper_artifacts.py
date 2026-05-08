from pathlib import Path

from src.frontend.paper_artifacts import (
    build_file_url,
    collect_paper_artifacts,
    extract_html_title,
    filter_openable_papers,
    inspect_paper_artifact,
)


def test_extract_html_title_prefers_title_tag(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text(
        """
        <html>
          <head>
            <title>Inquiry Paper Title</title>
          </head>
          <body>
            <h1>Fallback Heading</h1>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    assert extract_html_title(paper_path) == "Inquiry Paper Title"


def test_extract_html_title_falls_back_to_h1(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text(
        """
        <html>
          <body>
            <h1>The Speaker's Perspective</h1>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    assert extract_html_title(paper_path) == "The Speaker's Perspective"


def test_extract_html_title_strips_nested_tags(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text(
        """
        <html>
          <head>
            <title><span>Nested</span> Paper Title</title>
          </head>
        </html>
        """,
        encoding="utf-8",
    )

    assert extract_html_title(paper_path) == "Nested Paper Title"


def test_extract_html_title_returns_none_for_non_html(tmp_path: Path):
    text_path = tmp_path / "paper.txt"
    text_path.write_text("Not HTML", encoding="utf-8")

    assert extract_html_title(text_path) is None


def test_inspect_paper_artifact_for_existing_html(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text(
        "<html><head><title>Existing Paper</title></head></html>",
        encoding="utf-8",
    )

    artifact = inspect_paper_artifact(paper_path)

    assert artifact.exists is True
    assert artifact.is_openable is True
    assert artifact.title == "Existing Paper"
    assert artifact.size_bytes is not None
    assert artifact.size_bytes > 0
    assert artifact.modified_at is not None
    assert artifact.path == paper_path.as_posix()


def test_inspect_paper_artifact_for_missing_path(tmp_path: Path):
    missing_path = tmp_path / "missing.html"

    artifact = inspect_paper_artifact(missing_path)

    assert artifact.exists is False
    assert artifact.is_openable is False
    assert artifact.title is None
    assert artifact.size_bytes is None
    assert artifact.modified_at is None


def test_inspect_paper_artifact_for_none_path():
    artifact = inspect_paper_artifact(None)

    assert artifact.exists is False
    assert artifact.is_openable is False
    assert artifact.path == ""


def test_build_file_url_returns_file_uri(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    paper_path.write_text("<html></html>", encoding="utf-8")

    file_url = build_file_url(paper_path)

    assert file_url.startswith("file:")
    assert "paper.html" in file_url


def test_collect_and_filter_openable_papers(tmp_path: Path):
    html_path = tmp_path / "paper.html"
    txt_path = tmp_path / "notes.txt"
    missing_path = tmp_path / "missing.html"

    html_path.write_text("<html><title>Paper</title></html>", encoding="utf-8")
    txt_path.write_text("notes", encoding="utf-8")

    artifacts = collect_paper_artifacts([html_path, txt_path, missing_path, None])
    openable = filter_openable_papers(artifacts)

    assert len(artifacts) == 4
    assert len(openable) == 1
    assert openable[0].path == html_path.as_posix()