# The Inquiry Engine Plan

## Goal

Build a video-to-paper pipeline that ingests a YouTube video, charitably reconstructs the speaker's argument, verifies empirical claims against authoritative literature, and produces an educational research paper for further inquiry.

## Output Standard

The output should read like a thoughtful editor took the speaker seriously, checked the literature, and wrote for a reader who wants to understand. If it reads like a takedown or an endorsement, the system has failed.

## Core Posture

- Charitable reconstruction of the speaker's perspective
- Evidence-balanced retrieval rather than confirmation seeking
- Reader-centered paper structure with explicit limits and further reading
- Verifiable citations that resolve to real sources

## Weekly Roadmap

1. Source and speaker ingestion with provenance plus transcript offset preservation
2. Chunking plus argument-structure extraction
3. Claim classification and verification-strategy routing
4. Steelmanning the speaker's perspective
5. Tiered external evidence retrieval with balance scoring
6. Relational schema design plus a FastAPI backend
7. Evidence integration and per-claim adjudication
8. Educational paper generation
9. Three-axis evaluation: steelman fidelity, evidence balance, educational quality
10. Frontend, demo, and portfolio packaging

## Failure Modes To Guard Against

- `Strawmanning`: the paper describes a version of the speaker's argument the speaker would not recognize.
- `Cherry-picking`: the evidence review represents only the literature that supports a preferred verdict.

## Current Repository Focus

This scaffold is intentionally limited to the first two weeks of the plan:

- `data/mock_video.json` captures source provenance and speaker context.
- `data/mock_transcript.json` captures transcript text plus character-offset-preserving segments.
- `src/videotopaper/sources.py` and `src/videotopaper/transcripts.py` cover week 1 starter work.
- `src/videotopaper/chunking.py` and `src/videotopaper/arguments.py` cover the week 2 handoff.

## Completion Standard

A component is complete when you can explain:

1. How it works
2. Why this design was chosen
3. How it would be extended

Do that without referring to the code.
