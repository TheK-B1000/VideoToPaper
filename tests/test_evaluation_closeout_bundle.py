from src.evaluation.evaluation_closeout_bundle import (
    EvaluationCloseoutBundle,
    write_evaluation_closeout_bundle,
)


def test_write_evaluation_closeout_bundle_creates_all_docs(tmp_path):
    bundle = write_evaluation_closeout_bundle(tmp_path)

    assert isinstance(bundle, EvaluationCloseoutBundle)

    assert bundle.readme_section_path.exists()
    assert bundle.architecture_doc_path.exists()
    assert bundle.dev_log_path.exists()
    assert bundle.checklist_path.exists()
    assert bundle.handoff_note_path.exists()

    assert bundle.readme_section_path.name == "evaluation_readme_section.md"
    assert bundle.architecture_doc_path.name == "evaluation_architecture.md"
    assert bundle.dev_log_path.name == "evaluation_dev_log.md"
    assert bundle.checklist_path.name == "evaluation_completion_checklist.md"
    assert bundle.handoff_note_path.name == "evaluation_handoff_note.md"


def test_write_evaluation_closeout_bundle_writes_expected_content(tmp_path):
    bundle = write_evaluation_closeout_bundle(tmp_path)

    readme = bundle.readme_section_path.read_text(encoding="utf-8")
    architecture = bundle.architecture_doc_path.read_text(encoding="utf-8")
    dev_log = bundle.dev_log_path.read_text(encoding="utf-8")
    checklist = bundle.checklist_path.read_text(encoding="utf-8")
    handoff = bundle.handoff_note_path.read_text(encoding="utf-8")

    assert "## Paper Evaluation System" in readme
    assert "# Evaluation System Architecture" in architecture
    assert "# Evaluation Harness Development Log" in dev_log
    assert "# Evaluation Module Completion Checklist" in checklist
    assert "# Evaluation Module Handoff Note" in handoff


def test_closeout_bundle_to_dict_returns_string_paths(tmp_path):
    bundle = write_evaluation_closeout_bundle(tmp_path)

    payload = bundle.to_dict()

    assert payload["readme_section_path"].endswith("evaluation_readme_section.md")
    assert payload["architecture_doc_path"].endswith("evaluation_architecture.md")
    assert payload["dev_log_path"].endswith("evaluation_dev_log.md")
    assert payload["checklist_path"].endswith("evaluation_completion_checklist.md")
    assert payload["handoff_note_path"].endswith("evaluation_handoff_note.md")
