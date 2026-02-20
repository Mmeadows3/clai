from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def run(input: Any, tools: Mapping[str, Any], tool_path) -> dict[str, Any]:
    payload = input if isinstance(input, dict) else {}
    value = str(payload.get("value") or "")
    probe_file = str(payload.get("probe_file") or "").strip()
    probe_token = str(payload.get("probe_token") or "").strip()

    probe_written = False
    if probe_file:
        target = Path(probe_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(probe_token, encoding="utf-8")
        probe_written = True

    return {
        "tool_type": "python",
        "echoed_value": value,
        "probe_written": probe_written,
        "probe_token": probe_token,
    }
