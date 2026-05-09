import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.frontend.inquiry_library_manifest import (
    register_pipeline_outputs_for_studio,
    write_inquiry_library_manifest,
)
from src.frontend.inquiry_studio import InquiryRecord, discover_inquiries


def test_write_inquiry_library_manifest_round_trip(tmp_path: Path):
    lib = tmp_path / "inquiries"
    repo = tmp_path / "repo"
    paper = repo / "out" / "paper.html"
    paper.parent.mkdir(parents=True)
    paper.write_text("<html><title>T</title></html>", encoding="utf-8")

    mp = write_inquiry_library_manifest(
        library_dir=lib,
        inquiry_id="inquiry_ABC123xyz_9",
        title="Test Title",
        youtube_url="https://youtu.be/ABC123xyz_9",
        paper_path=paper,
        repo_root=repo,
        parameters={"retrieval_depth": 3, "source_tiers": [1, 2]},
    )

    record = InquiryRecord.from_manifest(mp)
    assert record.inquiry_id == "inquiry_ABC123xyz_9"
    assert record.title == "Test Title"
    assert record.status == "completed"
    assert record.paper_path.endswith("out/paper.html")


def test_register_pipeline_outputs_for_studio_requires_video_metadata(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data" / "outputs").mkdir(parents=True)
    (repo / "data" / "outputs" / "inquiry_paper.html").write_text(
        "<html><title>X</title></html>", encoding="utf-8"
    )

    with pytest.raises(ValueError):
        register_pipeline_outputs_for_studio(repo, library_dir=tmp_path / "inq")


def test_register_pipeline_outputs_for_studio_prefers_paper_spec_video(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data" / "outputs").mkdir(parents=True)
    (repo / "data" / "outputs" / "inquiry_paper.html").write_text(
        "<html><title>X</title></html>", encoding="utf-8"
    )
    (repo / "data" / "outputs" / "paper_spec.json").write_text(
        json.dumps(
            {
                "title": "Spec Title",
                "video": {
                    "video_id": "ZZZyyZZZZ10",
                    "url": "https://youtu.be/ZZZyyZZZZ10",
                },
            }
        ),
        encoding="utf-8",
    )
    lib = tmp_path / "inquiries"

    register_pipeline_outputs_for_studio(repo, library_dir=lib)

    records = discover_inquiries(lib)
    assert len(records) == 1
    assert records[0].inquiry_id == "inquiry_ZZZyyZZZZ10"
    assert records[0].youtube_url == "https://youtu.be/ZZZyyZZZZ10"


def test_register_pipeline_outputs_for_studio_writes_manifest(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data" / "processed").mkdir(parents=True)
    (repo / "data" / "outputs").mkdir(parents=True)
    (repo / "data" / "outputs" / "inquiry_paper.html").write_text(
        "<html><title>X</title></html>", encoding="utf-8"
    )
    (repo / "data" / "outputs" / "paper_spec.json").write_text(
        json.dumps({"title": "Paper From Spec"}),
        encoding="utf-8",
    )
    (repo / "data" / "processed" / "source_registry.json").write_text(
        json.dumps(
            {
                "video_id": "ABC123xyz_9",
                "url": "https://youtu.be/ABC123xyz_9",
            }
        ),
        encoding="utf-8",
    )
    lib = tmp_path / "inquiries"

    register_pipeline_outputs_for_studio(repo, library_dir=lib)

    records = discover_inquiries(lib)
    assert len(records) == 1
    assert records[0].title == "Paper From Spec"
    assert records[0].youtube_url == "https://youtu.be/ABC123xyz_9"
