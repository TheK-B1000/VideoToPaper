from typing import Any


def safe_llm_call(*args: Any, **kwargs: Any) -> Any:
    """
    Single approved entry point for LLM requests.

    Future wiring: cost_guard (budget checks) → this function → vendor API.
    Do not call vendor SDKs from other modules.

    Raises:
        NotImplementedError: Always, until a real implementation is added.
    """
    raise NotImplementedError(
        "safe_llm_call is not implemented yet. "
        "Add vendor integration here after cost_guard checks."
    )
