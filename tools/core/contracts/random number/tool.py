from __future__ import annotations

import json
from typing import Any, Mapping


def run(input: Any, tools: Mapping[str, Any], tool_path) -> str:
    def _payload(value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            nested = value.get("input")
            if isinstance(nested, Mapping):
                return nested
            if isinstance(nested, str):
                return _payload(nested)
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            if text.startswith("{"):
                try:
                    decoded = json.loads(text)
                except json.JSONDecodeError:
                    decoded = None
                if isinstance(decoded, Mapping):
                    return decoded
            parts = [part for part in text.replace(",", " ").split() if part]
            if len(parts) == 2:
                return {"min": parts[0], "max": parts[1]}
            raise ValueError(
                "input string must be '<min> <max>' or a JSON object with min and max"
            )
        if value is None:
            return {}
        raise ValueError("input must be an object or string")

    def _parse_int(value: Any, label: str) -> int:
        text = str(value).strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"{label} must be an integer, got {value!r}") from exc

    payload = _payload(input)
    min_value = _parse_int(payload.get("min"), "min")
    max_value = _parse_int(payload.get("max"), "max")
    if min_value > max_value:
        raise ValueError(f"min must be <= max, got min={min_value}, max={max_value}")
    script = (
        f"let min = {min_value}; let max = {max_value}; "
        "random int $min..$max | to nuon | str replace -a \"\\n\" \"\" | "
        "str replace -a \"\\r\" \"\""
    )
    return tools["nushell"](script)
