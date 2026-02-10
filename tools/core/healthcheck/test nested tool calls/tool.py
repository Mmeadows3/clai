from __future__ import annotations

from typing import Any, Mapping


def run(input: Mapping[str, Any], tools: Mapping[str, Any], tool_path) -> dict[str, int]:
    def _tool_value(response: Any) -> Any:
        if isinstance(response, dict):
            if "result" in response:
                return response["result"]
            for key in ("stdout", "text", "stderr"):
                value = response.get(key)
                if isinstance(value, str):
                    return value
        return response

    def _parse_int(value: Any, label: str) -> int:
        text = str(value).strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer, got {value!r}") from exc

    left_number = _parse_int(
        _tool_value(
            tools["call_tool"]("core.healthcheck.random_number", {"min": 1, "max": 10})
        ),
        "left_number",
    )
    right_number = _parse_int(
        _tool_value(
            tools["call_tool"]("core.healthcheck.random_number", {"min": 1, "max": 10})
        ),
        "right_number",
    )

    return {
        "left_number": left_number,
        "right_number": right_number,
        "product": left_number * right_number,
    }
