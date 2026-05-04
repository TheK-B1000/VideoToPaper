# Agent / contributor notes

## LLM usage

Do **not** call an LLM directly from arbitrary modules.

- **Avoid:** `client.responses.create(...)`, raw OpenAI/other SDK calls scattered in `src/`.
- **Prefer:** `safe_llm_call(...)` from the shared ops layer.

**Target architecture:** `cost_guard` → `safe_llm_call` → vendor API, ideally centralized in `src/ops/llm_client.py` so there is only one defensive gate.

Cursor encodes this as a project rule: `.cursor/rules/llm-gateway.mdc`.
