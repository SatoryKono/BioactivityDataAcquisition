"""Sanitized shared failures for MCP diagnostic transports."""


class ProbeError(RuntimeError):
    """A category and uncertainty flag, without raw server errors or secrets."""

    def __init__(self, category: str, *, uncertain: bool = False) -> None:
        super().__init__(category)
        self.category = category
        self.uncertain = uncertain


def rpc_result(value: dict) -> dict:
    """Project a response without retaining untrusted remote exception text."""
    error = value.get("error")
    if isinstance(error, dict):
        data = error.get("data")
        reason = data.get("reason") if isinstance(data, dict) else None
        if reason == "WORKSPACE_POLICY_DENIED":
            raise ProbeError("WORKSPACE_POLICY_DENIED")
        raise ProbeError("RPC_ERROR")
    result = value.get("result")
    if not isinstance(result, dict):
        raise ProbeError("INVALID_RESPONSE")
    return result
