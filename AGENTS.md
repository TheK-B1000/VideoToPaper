# Agent / contributor notes

## LLM usage (mandatory flow)

Pipeline code must **not** call OpenAI, Anthropic, or other model APIs directly.

**Required order:**

1. **`safe_llm_call()`** (`src/ops/llm_client.py`) — the only supported entry point from feature/pipeline code.
2. **`assert_llm_call_allowed()`** (`src/ops/cost_guard.py`) — run **before** any HTTP/SDK request (budget, dry-run, per-call and per-run caps).
3. **Vendor API** — implement **only** inside `llm_client`, never scattered across `src/`.
4. **`record_llm_usage()`** — run **after** a successful response; pass **usage reported by the API** (actual input/output tokens and actual cost) whenever the provider returns them.

Bypassing `safe_llm_call` breaks cost and safety guarantees.

**Estimates:** Pre-flight checks use `estimate_tokens()` (rough chars÷4). That is an acceptable first safety net; for tighter budgets, switch pre-flight counting to the **model’s tokenizer**. Post-call accounting should still use **actual** usage from the response.

Cursor rule: `.cursor/rules/llm-gateway.mdc`.
