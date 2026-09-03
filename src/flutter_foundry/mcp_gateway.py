from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .trust_boundary import wrap_untrusted_text

CURRENT_SPEC = "2026-07-28"
DEPRECATED_CAPABILITIES = {"roots", "sampling", "logging", "legacy-http-sse"}
TOOL_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
TASKS_EXTENSION = "io.modelcontextprotocol/tasks"
_TOOL_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,160}$")
_METHOD_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,160}$")


@dataclass(frozen=True)
class MCPServerPolicy:
    server_id: str
    trust: str
    allowed_tools: tuple[str, ...] = ()
    max_output_bytes: int = 1_000_000
    allow_network: bool = False
    auth_issuer: str | None = None
    allowed_methods: tuple[str, ...] = ()
    require_auth: bool = False
    max_cache_ttl_ms: int = 300_000

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_policy(policy: MCPServerPolicy) -> dict[str, Any]:
    findings = []
    if policy.trust not in {"official", "pinned", "untrusted"}:
        findings.append("invalid trust tier")
    if policy.max_output_bytes <= 0 or policy.max_output_bytes > 10_000_000:
        findings.append("max_output_bytes outside allowed range")
    if any(not _TOOL_RE.match(t) for t in policy.allowed_tools):
        findings.append("invalid tool name in allowlist")
    if any(not _METHOD_RE.match(m) for m in policy.allowed_methods):
        findings.append("invalid method in allowlist")
    if policy.require_auth and not policy.auth_issuer:
        findings.append("require_auth needs a pinned auth_issuer")
    if policy.max_cache_ttl_ms < 0 or policy.max_cache_ttl_ms > 3_600_000:
        findings.append("max_cache_ttl_ms outside allowed range")
    return {"status": "fail" if findings else "pass", "findings": findings, "policy": policy.to_dict()}


def authorize_tool(policy: MCPServerPolicy, tool: str) -> dict[str, Any]:
    if not _TOOL_RE.match(tool):
        return {"status": "blocked", "reason": "invalid tool name"}
    if policy.allowed_tools and tool not in policy.allowed_tools:
        return {"status": "blocked", "reason": "tool not allowlisted"}
    return {"status": "pass", "server_id": policy.server_id, "tool": tool}


def authorize_request(
    policy: MCPServerPolicy,
    *,
    method: str,
    name: str | None = None,
    headers: dict[str, str] | None = None,
    auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Policy decision for the stateless 2026-07-28 remote MCP model.

    Mcp-Method/Mcp-Name header routing is treated as routing metadata only; it
    does not create trust. Issuer validation is required when auth is enabled.
    """
    headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    if not _METHOD_RE.match(method):
        return {"status": "blocked", "reason": "invalid MCP method"}
    if policy.allowed_methods and method not in policy.allowed_methods:
        return {"status": "blocked", "reason": "MCP method not allowlisted"}
    header_method = headers.get("mcp-method")
    if header_method is not None and header_method != method:
        return {"status": "blocked", "reason": "Mcp-Method header/body mismatch"}
    if name is not None:
        if not _TOOL_RE.match(name):
            return {"status": "blocked", "reason": "invalid MCP name"}
        header_name = headers.get("mcp-name")
        if header_name is not None and header_name != name:
            return {"status": "blocked", "reason": "Mcp-Name header/body mismatch"}
    if policy.require_auth:
        issuer = str((auth or {}).get("issuer", ""))
        if not issuer or issuer != policy.auth_issuer:
            return {"status": "blocked", "reason": "authorization issuer validation failed"}
    return {
        "status": "pass",
        "server_id": policy.server_id,
        "method": method,
        "name": name,
        "stateless": True,
        "routing_headers_validated": True,
    }


def inspect_tool_output(policy: MCPServerPolicy, tool: str, output: str | bytes) -> dict[str, Any]:
    auth = authorize_tool(policy, tool)
    if auth["status"] != "pass":
        return auth
    raw = output.encode("utf-8", errors="replace") if isinstance(output, str) else bytes(output)
    if len(raw) > policy.max_output_bytes:
        return {"status": "blocked", "reason": "MCP output exceeds configured maximum", "bytes": len(raw)}
    text = raw.decode("utf-8", errors="replace")
    wrapped = wrap_untrusted_text(text, f"mcp:{policy.server_id}:{tool}", max_chars=policy.max_output_bytes)
    return {
        "status": "warn" if wrapped["inspection"]["suspicious"] else "pass",
        "classification": "UNTRUSTED_CONTENT",
        "instruction_authority": False,
        "output": wrapped,
    }


def validate_list_cache(policy: MCPServerPolicy, ttl_ms: int, *, deterministic_order: bool) -> dict[str, Any]:
    findings = []
    if ttl_ms < 0 or ttl_ms > policy.max_cache_ttl_ms:
        findings.append("cache TTL exceeds policy")
    if not deterministic_order:
        findings.append("list response order is not deterministic")
    return {"status": "fail" if findings else "pass", "findings": findings, "ttl_ms": ttl_ms, "deterministic_order": deterministic_order}


def spec_compatibility(client_spec: str, capabilities: list[str] | None = None) -> dict[str, Any]:
    capabilities = capabilities or []
    deprecated = sorted(set(capabilities) & DEPRECATED_CAPABILITIES)
    return {
        "status": "warn" if deprecated or client_spec != CURRENT_SPEC else "pass",
        "current_spec": CURRENT_SPEC,
        "client_spec": client_spec,
        "stateless_core_expected": True,
        "header_routing": {"method": "Mcp-Method", "name": "Mcp-Name"},
        "cacheable_list_results": True,
        "tool_schema_dialect": TOOL_SCHEMA_DIALECT,
        "tasks_extension": TASKS_EXTENSION,
        "extensions_framework": True,
        "deprecated_used": deprecated,
        "authorization": {"issuer_validation_required": True, "dynamic_client_registration": "deprecated", "client_metadata_documents": "preferred"},
        "deprecation_window": "minimum 12 months per current specification policy",
    }
