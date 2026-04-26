# VideoToPaper

VideoToPaper is a capstone AI engineering project that turns long-form video transcripts into structured, timestamp-grounded research briefs.

This repository is scaffolded for the roadmap in `AI_Engineer_Capstone_Roadmap.docx`. The first milestone is intentionally small: build the transcript data structure and chunking algorithm by hand before adding LLMs, YouTube ingestion, databases, APIs, retrieval, or UI.

## Current Status

The repo is set up for Week 1 and Week 2 work:

- Canonical mock transcript data in `data/mock_transcript.json`
- Python package skeleton in `src/videotopaper`
- Starter stubs for transcript cleaning, validation, persistence, and chunking
- Smoke tests in `tests`
- Windows setup and test scripts in `scripts`
- Development log template in `docs/development_log.md`

The core feature functions currently raise `NotImplementedError` on purpose. Implement them manually as you work through the curriculum.

## Project Layout

```text
VideoToPaper/
  data/
    mock_transcript.json
  docs/
    capstone_plan.md
    development_log.md
  scripts/
    setup.ps1
    test.ps1
  src/
    videotopaper/
      __init__.py
      chunking.py
      transcripts.py
  tests/
    test_scaffold.py
  pyproject.toml
```

## Local Setup

Install Python 3.11 or newer, then run:

```powershell
.\scripts\setup.ps1
```

If Python is not on your PATH, pass the interpreter explicitly:

```powershell
.\scripts\setup.ps1 -Python "C:\Path\To\python.exe"
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run tests:

```powershell
.\scripts\test.ps1
```

If PowerShell blocks local scripts because they are unsigned, run the same command with a one-time bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

The starter scaffold has no third-party Python dependencies. Later roadmap weeks will add optional dependency groups from `pyproject.toml`.

## Week 1 Starting Point

Implement these functions in `src/videotopaper/transcripts.py`:

- `clean_text`
- `validate_segment`
- `load_transcript`
- `save_transcript`

Use the canonical segment shape:

```json
{
  "text": "Reinforcement learning is useful for sequential decision making.",
  "start_time": 12.4,
  "end_time": 18.9
}
```

## Week 2 Starting Point

Implement `chunk_transcript` in `src/videotopaper/chunking.py`.

Expected output shape:

```json
{
  "chunk_id": "chunk_001",
  "text": "...",
  "start_time": 12.4,
  "end_time": 145.2,
  "word_count": 650
}
```

## Manual-First Rule

For each feature:

1. Specify the behavior in plain language.
2. Define the input and output contract.
3. Attempt the implementation manually first.
4. Use AI for review, debugging, edge cases, and refactoring after the first draft exists.
5. Add tests.
6. Write a short development log entry explaining the design.
