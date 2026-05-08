# Inquiry Studio

Inquiry Studio is the local operator surface for the Inquiry Engine. It lets an operator prepare inquiry runs, browse prior inquiries, inspect audit reports, open generated HTML papers, monitor run progress, and connect to the backend API when available.

## Run the Studio

```bash
streamlit run src/frontend/inquiry_studio.py
```

## Configured Paths

- Inquiry library: `data/inquiries`
- Run requests queue: `data/run_requests`
- Local runs directory: `logs/runs`
- Operator activity log: `logs/operator_activity.jsonl`
- Default audit report path: `not configured`
- Default progress log path: `logs/runs/latest_progress.json`
- Backend base URL: `http://127.0.0.1:8000`
- Backend timeout (seconds): `10.0`

## Operator workflow

1. Submit a YouTube URL from the sidebar.
2. Review created requests in **Run Requests**.
3. Launch locally or submit to backend.
4. Inspect reports in **Audit Inspector**.
5. Watch execution updates in **Run Progress**.
6. Review readiness in **Health Check**.

## Completion standard

A run is considered complete when:
- a manifest exists in the inquiry library,
- generated paper and audit artifacts are discoverable, and
- activity log captures major operator actions.
