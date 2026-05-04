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

Cursor rule: `.cursor/rules/llm-gateway.mdc`.
