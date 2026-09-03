from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import queue
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote


@dataclass(frozen=True)
class LSPBackend:
    language: str
    command: tuple[str, ...]
    suffixes: tuple[str, ...]
    tool: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BACKENDS: tuple[LSPBackend, ...] = (
    LSPBackend("dart", ("dart", "language-server", "--protocol=lsp"), (".dart",), "dart"),
    LSPBackend("typescript", ("typescript-language-server", "--stdio"), (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"), "typescript-language-server"),
    LSPBackend("python", ("pyright-langserver", "--stdio"), (".py",), "pyright-langserver"),
    LSPBackend("csharp", ("csharp-ls",), (".cs",), "csharp-ls"),
    LSPBackend("go", ("gopls", "serve"), (".go",), "gopls"),
    LSPBackend("rust", ("rust-analyzer",), (".rs",), "rust-analyzer"),
    LSPBackend("java", ("jdtls",), (".java",), "jdtls"),
)


def backend_status() -> dict[str, Any]:
    rows = []
    for b in BACKENDS:
        rows.append({**b.to_dict(), "available": shutil.which(b.tool) is not None})
    return {"status": "pass", "schema": "nakeuri/lsp-backends/v1", "backends": rows}


def _uri(path: Path) -> str:
    p = path.resolve().as_posix()
    if os.name == "nt" and not p.startswith("/"):
        p = "/" + p
    return "file://" + quote(p, safe="/:@")


class LSPClient:
    """Minimal synchronous stdio JSON-RPC client for semantic queries.

    It intentionally implements only the portable LSP methods Foundry needs. Servers
    that cannot answer these standard methods are reported as unavailable for the
    authoritative semantic layer rather than silently treated as successful.
    """

    def __init__(self, command: list[str] | tuple[str, ...], root: Path, *, timeout: float = 8.0):
        self.command = list(command)
        self.root = root.resolve()
        self.timeout = timeout
        self.proc: subprocess.Popen[bytes] | None = None
        self._next_id = 1

    def __enter__(self) -> "LSPClient":
        self.proc = subprocess.Popen(self.command, cwd=self.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.request("initialize", {
            "processId": None,
            "rootUri": _uri(self.root),
            "capabilities": {"textDocument": {"documentSymbol": {}, "references": {}}},
            "workspaceFolders": [{"uri": _uri(self.root), "name": self.root.name}],
        })
        self.notify("initialized", {})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.proc:
            try:
                self.request("shutdown", None)
            except Exception:
                pass
            try:
                self.notify("exit", None)
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            for stream in (self.proc.stdin, self.proc.stdout):
                try:
                    if stream: stream.close()
                except Exception:
                    pass

    def _send(self, obj: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("LSP process is not running")
        body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
        self.proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        if not self.proc or not self.proc.stdout:
            raise RuntimeError("LSP process is not running")
        out: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
        stream = self.proc.stdout
        def blocking_read() -> None:
            try:
                headers: dict[str, str] = {}
                while True:
                    line = stream.readline()
                    if not line:
                        raise RuntimeError("LSP server exited")
                    if line in {b"\r\n", b"\n"}:
                        break
                    text = line.decode("ascii", errors="replace").strip()
                    if ":" in text:
                        k, v = text.split(":", 1); headers[k.lower().strip()] = v.strip()
                size = int(headers.get("content-length", "0"))
                if size <= 0:
                    raise RuntimeError("LSP response missing Content-Length")
                body = stream.read(size)
                out.put((True, json.loads(body.decode("utf-8"))))
            except Exception as exc:
                out.put((False, exc))
        thread = threading.Thread(target=blocking_read, name="nakeuri-lsp-read", daemon=True); thread.start()
        try:
            ok, value = out.get(timeout=self.timeout)
        except queue.Empty:
            try: self.proc.terminate()
            except Exception: pass
            raise TimeoutError("LSP response timeout")
        if not ok: raise value
        return value

    def request(self, method: str, params: Any) -> Any:
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() <= deadline:
            msg = self._read()
            if msg.get("id") != request_id:
                continue
            if "error" in msg:
                raise RuntimeError(f"LSP {method} error: {msg['error']}")
            return msg.get("result")
        raise TimeoutError(f"LSP request timeout: {method}")

    def notify(self, method: str, params: Any) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def document_symbols(self, path: Path, language_id: str) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        uri = _uri(path)
        self.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": language_id, "version": 1, "text": text}})
        result = self.request("textDocument/documentSymbol", {"textDocument": {"uri": uri}}) or []
        self.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
        return result if isinstance(result, list) else []

    def document_semantics(self, path: Path, language_id: str, *, max_reference_symbols: int = 24) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="replace"); uri = _uri(path)
        self.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": language_id, "version": 1, "text": text}})
        raw = self.request("textDocument/documentSymbol", {"textDocument": {"uri": uri}}) or []
        raw = raw if isinstance(raw, list) else []
        flat = _flatten_symbols(raw, path=path, root=self.root, language=language_id)
        refs=[]
        for sym in flat[:max_reference_symbols]:
            try:
                found = self.request("textDocument/references", {"textDocument": {"uri": uri}, "position": {"line": max(0, int(sym["line"])-1), "character": int(sym.get("character",0))}, "context": {"includeDeclaration": False}}) or []
                for loc in found if isinstance(found, list) else []:
                    if not isinstance(loc, dict): continue
                    target_uri=str(loc.get("uri", ""));target_range=loc.get("range") or {};start=target_range.get("start") or {}
                    refs.append({"symbol":sym["name"],"source":sym["path"],"target_uri":target_uri,"line":int(start.get("line",0))+1,"character":int(start.get("character",0))})
            except Exception:
                continue
        self.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
        return {"symbols": raw, "references": refs}


def _flatten_symbols(rows: list[dict[str, Any]], *, path: Path, root: Path, language: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rel = path.relative_to(root).as_posix()
    def visit(item: dict[str, Any], parent: str | None = None) -> None:
        name = str(item.get("name", "")).strip()
        if not name:
            return
        rng = item.get("selectionRange") or item.get("range") or {}
        start = rng.get("start") or {}
        row = {
            "name": name,
            "path": rel,
            "line": int(start.get("line", 0)) + 1,
            "character": int(start.get("character", 0) or 0),
            "kind": int(item.get("kind", 0) or 0),
            "language": language,
            "parent": parent,
            "confidence": "authoritative-lsp",
        }
        out.append(row)
        for child in item.get("children") or []:
            if isinstance(child, dict):
                visit(child, name)
    for item in rows:
        if isinstance(item, dict):
            visit(item)
    return out


def authoritative_semantic_snapshot(root: Path, *, max_files_per_language: int = 24, timeout: float = 8.0) -> dict[str, Any]:
    root = root.resolve()
    results: dict[str, Any] = {}
    total_symbols = 0
    for backend in BACKENDS:
        if shutil.which(backend.tool) is None:
            results[backend.language] = {"status": "unavailable", "tool": backend.tool, "symbols": []}
            continue
        files = [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() in backend.suffixes and ".git" not in p.parts and "node_modules" not in p.parts][:max_files_per_language]
        if not files:
            results[backend.language] = {"status": "not_applicable", "tool": backend.tool, "symbols": []}
            continue
        symbols: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        errors: list[str] = []
        try:
            with LSPClient(backend.command, root, timeout=timeout) as client:
                for path in files:
                    try:
                        sem = client.document_semantics(path, backend.language)
                        symbols.extend(_flatten_symbols(sem["symbols"], path=path, root=root, language=backend.language))
                        references.extend(sem["references"])
                    except Exception as exc:
                        errors.append(f"{path.relative_to(root).as_posix()}: {exc}")
        except Exception as exc:
            errors.append(str(exc))
        status = "pass" if symbols and not errors else "partial" if symbols else "fail"
        results[backend.language] = {"status": status, "tool": backend.tool, "files_queried": len(files), "symbols": symbols, "references": references, "errors": errors[:12]}
        total_symbols += len(symbols)
    return {
        "status": "pass" if total_symbols else "degraded",
        "schema": "nakeuri/authoritative-semantics/v1",
        "total_symbols": total_symbols,
        "languages": results,
        "rule": "Authoritative LSP symbols override heuristic declarations when available; fallback parsing remains explicit when they are unavailable.",
    }
