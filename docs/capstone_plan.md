# Capstone Plan

## Goal

Build a production-minded Video-to-Research AI Assistant that turns a video transcript into a structured, evidence-grounded research brief.

## Roadmap

1. Transcript ingestion and cleaning
2. Transcript chunking
3. LLM summarization pipeline
4. Structured claim extraction
5. Relational data modeling
6. FastAPI backend
7. Vector search and retrieval-augmented generation
8. Research brief generation
9. Evaluation and quality assurance
10. Streamlit demo and portfolio polish

## Architectural Pattern

```text
messy input -> clean structured data -> AI processing -> evidence-grounded output -> usable product
```

## Early Milestones

Week 1 establishes a canonical transcript segment:

```json
{
  "text": "Reinforcement learning is useful for sequential decision making.",
  "start_time": 12.4,
  "end_time": 18.9
}
```

Week 2 groups timestamped segments into traceable chunks:

```json
{
  "chunk_id": "chunk_001",
  "text": "...",
  "start_time": 12.4,
  "end_time": 145.2,
  "word_count": 650
}
```

## Completion Standard

A feature is complete only when you can explain how it works, why the design was chosen, and how it would be extended without referring to the code.
