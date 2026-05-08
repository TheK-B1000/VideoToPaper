from pathlib import Path

from src.docs.engineering_decisions import (
    EngineeringDecision,
    build_engineering_decisions_document,
    write_engineering_decisions_document,
)


def test_build_engineering_decisions_document_contains_default_decisions():
    document = build_engineering_decisions_document()

    assert document.title == "Engineering Decisions — The Inquiry Engine"
    assert "Interactive HTML instead of static PDF" in document.content
    assert "Embed-only video citation" in document.content
    assert "Balanced retrieval as a monitored property" in document.content
    assert len(document.decisions) >= 5


def test_build_engineering_decisions_document_renders_tradeoffs():
    decision = EngineeringDecision(
        title="Test Decision",
        decision="Use a testable design.",
        rationale="It improves confidence.",
        tradeoffs=[
            "Slightly more setup.",
            "Better maintainability.",
        ],
    )

    document = build_engineering_decisions_document([decision])

    assert "## 1. Test Decision" in document.content
    assert "Use a testable design." in document.content
    assert "It improves confidence." in document.content
    assert "- Slightly more setup." in document.content
    assert "- Better maintainability." in document.content


def test_engineering_decision_to_dict():
    decision = EngineeringDecision(
        title="Decision",
        decision="Do the thing.",
        rationale="Because it helps.",
        tradeoffs=["Tradeoff one."],
    )

    payload = decision.to_dict()

    assert payload == {
        "title": "Decision",
        "decision": "Do the thing.",
        "rationale": "Because it helps.",
        "tradeoffs": ["Tradeoff one."],
    }


def test_write_engineering_decisions_document_creates_file(tmp_path: Path):
    output_path = tmp_path / "docs" / "engineering_decisions.md"

    written_path = write_engineering_decisions_document(
        output_path=output_path,
    )

    assert written_path == output_path
    assert written_path.exists()

    content = written_path.read_text(encoding="utf-8")

    assert "# Engineering Decisions" in content
    assert "The Inquiry Engine" in content
    assert "Summary" in content
