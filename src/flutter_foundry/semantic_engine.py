from __future__ import annotations

import ast
import hashlib
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .platform_adapters import detect_project_surfaces
from .lsp_semantics import authoritative_semantic_snapshot
from .flutter_intelligence import flutter_specialist_snapshot

IGNORE_DIRS = {".git", ".factory", ".dart_tool", ".next", ".venv", "venv", "node_modules", "build", "dist", "target", "bin", "obj"}
MAX_SOURCE_FILES = 5000


@dataclass(frozen=True)
class SemanticNode:
    id: str
    kind: str
    language: str
    name: str
    path: str
    line: int | None = None
    confidence: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticEdge:
    source: str
    target: str
    kind: str
    confidence: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _id(kind: str, language: str, path: str, name: str) -> str:
    digest = hashlib.sha256(f"{kind}:{language}:{path}:{name}".encode()).hexdigest()[:16]
    return f"sem:{kind}:{digest}"


def _iter_files(base: Path, suffixes: set[str]) -> Iterable[Path]:
    count = 0
    for p in sorted(base.rglob("*")):
        if count >= MAX_SOURCE_FILES:
            break
        if not p.is_file() or p.suffix.lower() not in suffixes:
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        count += 1
        yield p


def _python_symbols(path: Path, root: Path) -> tuple[list[SemanticNode], list[SemanticEdge]]:
    rel = path.relative_to(root).as_posix()
    fid = _id("file", "python", rel, rel)
    nodes = [SemanticNode(fid, "file", "python", rel, rel, confidence="parser")]
    edges: list[SemanticEdge] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
    except SyntaxError:
        return nodes, edges
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(n, ast.ClassDef) else "function"
            sid = _id(kind, "python", rel, n.name)
            nodes.append(SemanticNode(sid, kind, "python", n.name, rel, getattr(n, "lineno", None), "parser"))
            edges.append(SemanticEdge(fid, sid, "declares", "parser"))
        elif isinstance(n, ast.Import):
            for alias in n.names:
                tid = _id("module", "python", "", alias.name)
                nodes.append(SemanticNode(tid, "module", "python", alias.name, "", confidence="parser"))
                edges.append(SemanticEdge(fid, tid, "imports", "parser"))
        elif isinstance(n, ast.ImportFrom):
            module = n.module or ""
            if module:
                tid = _id("module", "python", "", module)
                nodes.append(SemanticNode(tid, "module", "python", module, "", confidence="parser"))
                edges.append(SemanticEdge(fid, tid, "imports", "parser"))
    return nodes, edges


_IMPORT_PATTERNS = {
    "typescript": re.compile(r"(?:import\s+(?:[^;]+?\s+from\s+)?|require\s*\()?[\"']([^\"']+)[\"']"),
    "dart": re.compile(r"^\s*(?:import|export|part)\s+[\"']([^\"']+)[\"']", re.M),
    "csharp": re.compile(r"^\s*using\s+([A-Za-z0-9_.]+)\s*;", re.M),
    "java": re.compile(r"^\s*import\s+([A-Za-z0-9_.*]+)\s*;", re.M),
    "rust": re.compile(r"^\s*use\s+([^;]+);", re.M),
}

_SYMBOL_PATTERNS = {
    "typescript": re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(class|interface|type|enum|function)\s+([A-Za-z_$][\w$]*)", re.M),
    "dart": re.compile(r"^\s*(class|mixin|enum|extension|typedef)\s+([A-Za-z_]\w*)", re.M),
    "csharp": re.compile(r"^\s*(?:(?:public|private|internal|protected|sealed|abstract|static|partial)\s+)*(class|interface|record|enum|struct)\s+([A-Za-z_]\w*)", re.M),
    "java": re.compile(r"^\s*(?:(?:public|private|protected|abstract|final|static)\s+)*(class|interface|record|enum)\s+([A-Za-z_]\w*)", re.M),
    "rust": re.compile(r"^\s*(?:pub\s+)?(fn|struct|enum|trait|type)\s+([A-Za-z_]\w*)", re.M),
    "go": re.compile(r"^\s*(func|type)\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", re.M),
}


def _regex_symbols(path: Path, root: Path, language: str) -> tuple[list[SemanticNode], list[SemanticEdge]]:
    rel = path.relative_to(root).as_posix()
    fid = _id("file", language, rel, rel)
    nodes = [SemanticNode(fid, "file", language, rel, rel)]
    edges: list[SemanticEdge] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    sp = _SYMBOL_PATTERNS.get(language)
    if sp:
        for m in sp.finditer(text):
            kind, name = m.group(1), m.group(2)
            line = text.count("\n", 0, m.start()) + 1
            sid = _id(kind, language, rel, name)
            nodes.append(SemanticNode(sid, kind, language, name, rel, line))
            edges.append(SemanticEdge(fid, sid, "declares"))
    ip = _IMPORT_PATTERNS.get(language)
    if ip:
        for m in ip.finditer(text):
            name = m.group(1).strip()
            tid = _id("module", language, "", name)
            nodes.append(SemanticNode(tid, "module", language, name, ""))
            edges.append(SemanticEdge(fid, tid, "imports"))
    if language == "go":
        for name in re.findall(r'[\"`]([^\"`]+)[\"`]', text):
            tid = _id("module", language, "", name)
            nodes.append(SemanticNode(tid, "module", language, name, ""))
            edges.append(SemanticEdge(fid, tid, "imports"))
    return nodes, edges


def semantic_project_graph(root: Path, *, include_authoritative: bool = True) -> dict[str, Any]:
    root = root.resolve()
    nodes: dict[str, SemanticNode] = {}
    edges: dict[tuple[str, str, str], SemanticEdge] = {}
    surfaces = detect_project_surfaces(root)
    language_counts: dict[str, int] = {}
    for surface in surfaces:
        base = root if surface["root"] == "." else root / surface["root"]
        sid = surface["id"]
        if sid == "python":
            specs = [("python", {".py"}, _python_symbols)]
        elif sid in {"node", "nextjs"}:
            specs = [("typescript", {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}, None)]
        elif sid == "flutter":
            specs = [("dart", {".dart"}, None)]
        elif sid == "dotnet":
            specs = [("csharp", {".cs"}, None)]
        elif sid == "go":
            specs = [("go", {".go"}, None)]
        elif sid == "rust":
            specs = [("rust", {".rs"}, None)]
        elif sid == "java":
            specs = [("java", {".java"}, None)]
        else:
            specs = []
        for language, suffixes, parser in specs:
            for path in _iter_files(base, suffixes):
                ns, es = parser(path, root) if parser else _regex_symbols(path, root, language)
                language_counts[language] = language_counts.get(language, 0) + 1
                for n in ns:
                    nodes[n.id] = n
                for e in es:
                    edges[(e.source, e.target, e.kind)] = e
    authoritative = {
        "dart_mcp_available": shutil.which("dart") is not None,
        "typescript_language_service_available": shutil.which("tsserver") is not None or shutil.which("typescript-language-server") is not None,
        "pyright_available": shutil.which("pyright") is not None or shutil.which("pyright-langserver") is not None,
        "roslyn_dotnet_available": shutil.which("dotnet") is not None or shutil.which("csharp-ls") is not None,
        "gopls_available": shutil.which("gopls") is not None,
        "rust_analyzer_available": shutil.which("rust-analyzer") is not None,
        "jdtls_available": shutil.which("jdtls") is not None,
    }
    live = authoritative_semantic_snapshot(root) if include_authoritative and any(authoritative.values()) else {"status":"degraded","total_symbols":0,"languages":{},"rule":"No authoritative LSP backend available on this host."}
    for language, payload in live.get("languages", {}).items():
        symbol_ids: dict[tuple[str,str], str] = {}
        for sym in payload.get("symbols", []):
            rel=str(sym.get("path", ""));name=str(sym.get("name", ""));sid=_id("symbol",language,rel,name)
            nodes[sid]=SemanticNode(sid,"symbol",language,name,rel,int(sym.get("line",1) or 1),"authoritative-lsp");symbol_ids[(rel,name)]=sid
        for ref in payload.get("references", []):
            src=symbol_ids.get((str(ref.get("source", "")),str(ref.get("symbol", ""))))
            uri=str(ref.get("target_uri", ""))
            if not src or not uri.startswith("file://"): continue
            try:
                from urllib.parse import unquote, urlparse
                target_path=Path(unquote(urlparse(uri).path))
                rel=target_path.resolve().relative_to(root).as_posix()
            except Exception:
                continue
            fid=_id("file",language,rel,rel);nodes.setdefault(fid,SemanticNode(fid,"file",language,rel,rel,confidence="authoritative-lsp"));edges[(src,fid,"referenced-by")]=SemanticEdge(src,fid,"referenced-by","authoritative-lsp")
    flutter = flutter_specialist_snapshot(root)
    return {
        "schema": "nakeuri/semantic-project-graph/v1",
        "status": "pass",
        "nodes": [n.to_dict() for n in sorted(nodes.values(), key=lambda x: x.id)],
        "edges": [e.to_dict() for e in sorted(edges.values(), key=lambda x: (x.source, x.target, x.kind))],
        "language_file_counts": language_counts,
        "authoritative_tools": authoritative,
        "authoritative_semantics": live,
        "flutter_specialist": flutter,
        "semantic_authority": "authoritative-lsp" if live.get("total_symbols",0) else "heuristic-fallback",
        "rule": "Heuristic parsers provide portable fallback only; official language analyzers/MCP/LSP remain authoritative when available, and live LSP/MCP/analyzer results are queried and marked authoritative when available.",
    }


def symbol_impact(root: Path, symbol: str) -> dict[str, Any]:
    graph = semantic_project_graph(root)
    matched = [n for n in graph["nodes"] if n.get("name") == symbol or symbol.lower() in str(n.get("name", "")).lower()]
    ids = {n["id"] for n in matched}
    incoming = [e for e in graph["edges"] if e["target"] in ids]
    outgoing = [e for e in graph["edges"] if e["source"] in ids]
    return {
        "status": "pass" if matched else "warn",
        "symbol": symbol,
        "matches": matched,
        "incoming": incoming,
        "outgoing": outgoing,
        "confidence": "mixed-authoritative-and-heuristic" if any(graph["authoritative_tools"].values()) else "heuristic-fallback",
    }
