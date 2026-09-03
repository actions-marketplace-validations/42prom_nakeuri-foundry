from __future__ import annotations

import json
import re
import sys
from typing import Any

DENY_PATTERNS = [
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\bgit\s+push\s+[^\n]*\bmain\b.*--force",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\n]*[xX]",
    r"\bchmod\s+-R\s+777\b",
]
FORCE_ASK_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+tag\b",
    r"\bflutter\s+build\b.*--release",
    r"\bfastlane\b",
    r"\bfirebase\s+deploy\b",
    r"\b(?:npm|dart|flutter)\s+publish\b",
    r"\bgh\s+release\b",
    r"\bflutter-foundry\s+lifecycle-approve\b",
    r"\bflutter-foundry\s+store-delivery-execute\b",
    r"\b(?:cat|type|Get-Content)\b[^\n]*(?:\.env|key\.properties|keystore|\.p12|\.pem)\b",
]


def _command_from(payload: dict[str, Any]) -> str:
    args = payload.get("toolCall", {}).get("args", {}) or {}
    for key in ["CommandLine","command","cmd","script"]:
        if key in args and isinstance(args[key], str):
            return args[key]
    return json.dumps(args, sort_keys=True)


def pretool(payload: dict[str, Any]) -> dict[str, Any]:
    tool = payload.get("toolCall", {}).get("name", "")
    if tool != "run_command":
        return {"decision":"allow"}
    command = _command_from(payload)
    for pattern in DENY_PATTERNS:
        if re.search(pattern, command, re.I):
            return {"decision":"deny","reason":"Nakeuri Flutter Foundry blocked a destructive command. Use a reversible, scoped alternative."}
    for pattern in FORCE_ASK_PATTERNS:
        if re.search(pattern, command, re.I):
            return {"decision":"force_ask","reason":"Nakeuri Flutter Foundry requires explicit user approval for release/push/secret-sensitive commands."}
    return {"decision":"allow"}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pretool"
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if mode == "pretool":
        out = pretool(payload)
    elif mode == "posttool":
        out = {}
    else:
        out = {}
    sys.stdout.write(json.dumps(out))

if __name__ == "__main__":
    main()
