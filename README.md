# VideoToPaper

Minimal project scaffold. Build features incrementally from here.

## Layout

```text
VideoToPaper/
├── README.md
├── requirements.txt
├── main.py
├── configs/
│   └── default_config.json
├── data/
│   ├── raw/
│   ├── processed/
│   └── outputs/
├── logs/
│   └── runs/
├── src/
│   ├── infrastructure/
│   ├── data/
│   ├── core/
│   ├── ml/
│   ├── ops/
│   └── output/
└── tests/
```

## Quick start

Create a virtual environment, install dependencies when you add them, then run:

```powershell
python main.py
```
# Transcript Research Engine

## Problem

Video To Paper is a small AI/data pipeline that takes raw transcript data, cleans and validates it, converts it into canonical timestamped segments, chunks those segments for later AI processing, summarizes the chunks, preserves timestamp citations, and generates structured research notes.

The first milestone is to build the transcript ingestion foundation: load raw transcript JSON, clean the text, validate each segment, and save a clean canonical JSON file.

## System Layers

### Infrastructure Layer
Owns configuration, paths, logging setup, and environment-level concerns.

### Data Layer
Owns schemas, validation rules, and JSON loading/saving.

### Core Logic Layer
Owns transcript cleaning, transcript processing, chunking, and citation construction.

### ML/AI Layer
Owns summarization, prompt templates, model clients, and evaluation.

### Ops Layer
Owns run tracking, metrics, audit logs, and reproducibility metadata.

### Output Layer
Owns markdown reports, research notes, and paper-style output.

## Initial Data Contract

A canonical transcript segment must have this shape:

```json
{
  "text": "Reinforcement learning is useful for sequential decision making.",
  "start_time": 12.4,
  "end_time": 18.9
}