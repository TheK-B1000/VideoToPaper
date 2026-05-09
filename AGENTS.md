# Agent / contributor notes

## LLM usage (mandatory flow)

Pipeline code must **not** call OpenAI, Anthropic, or other model APIs directly.

**Required order:**

1. **`safe_llm_call()`** (`src/ops/llm_client.py`) — the only supported entry point from feature/pipeline code. Requires **`expected_output_tokens > 0`**. Retries (**`max_llm_retries_per_call`**) wrap **only** the injected `llm_callable`, never the guard or accounting.
2. **`assert_llm_call_allowed()`** (`src/ops/cost_guard.py`) — run **before** any HTTP/SDK request (kill switch, enabled/dry-run, prompt checks, per-call and per-run estimates, **daily/month persisted spend**, model allowlist, explicit env arming).
3. **Vendor API** — implement **only** inside `llm_client`, never scattered across `src/`.
4. **`record_llm_usage()`** — after a successful response; pass **usage reported by the API** (actual input/output tokens and actual cost) whenever the provider returns them.
5. **`record_spend_usd()`** (`src/ops/budget_persistence.py`) — after success, updates daily/month JSON totals under **`budget_persistence_dir`** (see below).

Bypassing `safe_llm_call` breaks cost and safety guarantees.

### Fail-closed defaults

Prefer **`llm_enabled`: false** and **`dry_run`: true** in config. **`fail_closed`** must stay **`true`**. Missing or invalid budget keys → **`ValueError`** before any vendor I/O. Treat “no config / bad config” as **no real calls**.

### Real calls require two switches

- **`llm_enabled`** true and **`dry_run`** false in **`budget`** (see `configs/*.json`).
- Environment **`ALLOW_REAL_LLM_CALLS=true`** (checked in **`assert_real_llm_armed()`** after dry-run and **`allowed_models`** checks). Without this, tests, scripts, and cron jobs cannot accidentally spend.

### Budget config (required keys)

The guard expects a full **`budget`** dict including at least: **`max_estimated_cost_usd_per_day`**, **`max_estimated_cost_usd_per_month`**, **`max_estimated_cost_usd_per_call`**, **`allowed_models`**, **`max_prompt_chars`**, **`max_llm_retries_per_call`**, **`budget_persistence_dir`**, plus the existing run-level caps. Example layout: **`configs/argument_config.json`** → **`budget`**.

**Daily/month caps are global (cost_guard):** **`max_estimated_cost_usd_per_day`** / **`max_estimated_cost_usd_per_month`** apply to all guarded LLM traffic that shares that **`budget`** block and persistence dir. Do **not** duplicate them under **`speaker_perspective`** (or other stage blocks) unless you introduce real per-stage overrides with explicit precedence rules and validation in **`cost_guard`**—until then, stage JSON only carries stage knobs (e.g. **`use_llm`**, **`max_claims_per_call`**) and inherits the top-level **`budget`**.

### Persistent spend (cross-run)

Under **`budget_persistence_dir`** (default in repo config: **`logs/budget`**):

- **`daily_usage_YYYY-MM-DD.json`** — UTC calendar day total **`total_cost_usd`**.
- **`monthly_usage_YYYY-MM.json`** — UTC month total.

Pre-flight blocks if **`persisted_daily + estimated_call_cost`** or **`persisted_monthly + estimated_call_cost`** would exceed the caps. **`record_spend_usd`** runs only after a **successful** vendor response (when **`budget_persistence_dir`** is set).

### Ledger (audit trail)

Append-only **`ledger_YYYY-MM-DD.jsonl`** in the same directory as persistence. Each attempted call (allowed or blocked) should log context passed via **`ledger_context`** on **`safe_llm_call`** (`run_id`, `pipeline_name`, …) plus estimates, **`allowed`**, reason when blocked, and actual usage when available.

### Kill switch

If **`.llm_kill_switch`** exists under **`kill_switch_root`** (default: current working directory when not overridden), all LLM calls are **`PermissionError`**. Drop an empty file at the repo root to halt spending immediately.

### Prompt checks

Before estimation, **`validate_prompt_for_llm`** can reject: prompts over **`max_prompt_chars`**, lines that look like **`sk-…`** API keys (unless disabled), very long base64-like lines, and optional **`reject_prompt_substrings`**. Keep chunk-sized prompts; do not paste whole transcripts by mistake.

### Estimates vs reality

Pre-flight uses **`estimate_tokens()`** (rough chars÷4). For tighter caps, prefer the **target model’s tokenizer** in call sites that can supply accurate counts. Post-call accounting must use **actual** usage from the API when available.

### Gemini steelman smoke (optional, local)

Shipped **`configs/argument_config.json`** keeps **`speaker_perspective.use_llm`: false**. For a **real** Gemini call through **`safe_llm_call`**, copy **`configs/argument_config.gemini_smoke.example.json`** to **`configs/argument_config.gemini_smoke.local.json`** (pattern **`configs/*.local.json`** is gitignored). Set **`GEMINI_API_KEY`** or **`GOOGLE_API_KEY`**, and **`ALLOW_REAL_LLM_CALLS=true`**. Ensure **`data/outputs/argument_map.json`** and **`data/processed/claim_inventory.json`** exist (Week 2/3 outputs from your usual argument-structure / claim-inventory entrypoints — `main.py` does not expose a separate `--stage argument` switch). Then:

`python main.py --stage steelman --config-path configs/argument_config.gemini_smoke.local.json`

Inspect **`logs/runs`**, **`logs/budget`** ledger lines (**`guard_reason_code`** absent on success, present on guard refusal), and **`data/processed/speaker_perspective.json`**. Do not commit API keys, **`*.local.json`**, or generated logs unless intentional.

### Evidence retrieval (real bibliography vs DryRun placeholders)

Shipped **`configs/argument_config.json`** sets **`evidence_retrieval.dry_run`: true**, which emits synthetic **DryRun** rows so Week 6–8 artifacts keep their shape without calling providers.

For **live** OpenAlex + Semantic Scholar retrieval:

1. Turn off retrieval dry-run: use **`configs/argument_config.retrieval_live.example.json`** as a template (same layout as the default config with **`evidence_retrieval.dry_run`: false** and a slightly higher **`per_query_limit`**), copy it to a **`configs/*.local.json`** file if you prefer not to edit the committed default, **or** run **`python main.py --stage evidence_retrieval --no-dry-run --config-path configs/argument_config.json`** so CLI overrides config for that stage only.
2. Optional: set **`SEMANTIC_SCHOLAR_API_KEY`** in the environment ([Semantic Scholar API](https://www.semanticscholar.org/product/api)) for higher rate limits. OpenAlex does not require a key; the client already throttles requests.
3. Re-run **Week 7** integration and downstream (**`build_paper_spec`**, **`assemble_paper`**, or the **`youtube_paper`** orchestrator) so **`evidence_integration.json`**, **`paper_spec.json`**, and **`inquiry_paper.html`** ingest real **`evidence_records`** (titles/URLs from providers instead of placeholder links).

Quick check: **`python scripts/smoke_evidence_retrieval.py`** expects **`dry_run`: false** and makes real HTTP calls.

Cursor rule: `.cursor/rules/llm-gateway.mdc`.
