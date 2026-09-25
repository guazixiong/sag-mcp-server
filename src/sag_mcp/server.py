"""SAG Knowledge Base MCP Server — Read-Write Edition.

A Model Context Protocol (MCP) server that exposes the full SAG knowledge base
API capabilities (18 tools) over Streamable HTTP transport. Works with Claude
Desktop, Cursor, VS Code, and any MCP-compatible client.

GitHub: https://github.com/Zleap-AI/sag-mcp-server
License: MIT
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.parse
import warnings
from pathlib import Path
from typing import Annotated

# ---------------------------------------------------------------------------
# Suppress noisy warnings before third-party imports
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", message=".*IncompleteFieldDefinition.*")
warnings.filterwarnings("ignore", message=".*lifespan.*")
logging.disable(logging.INFO)
for _name in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(_name).setLevel(logging.WARNING)

import httpx  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import Field  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration (all via environment variables)
# ---------------------------------------------------------------------------

API_URL = os.getenv("SAG_API_URL", "http://localhost:9002").rstrip("/")
TOKEN = os.getenv("SAG_TOKEN", "")
LOGIN_NAME = os.getenv("SAG_LOGIN_NAME", "Admin")


def _get_token() -> str:
    """Return a valid JWT token: use env var, or auto-login."""
    global TOKEN
    if TOKEN:
        return TOKEN
    with httpx.Client(timeout=15) as c:
        r = c.post(f"{API_URL}/api/v1/auth/login", json={"name": LOGIN_NAME})
        r.raise_for_status()
        TOKEN = r.json()["access_token"]
        return TOKEN


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


def _api(method: str, path: str, **kw) -> dict:
    """Call SAG API and return JSON."""
    url = f"{API_URL}{path}"
    timeout = kw.pop("timeout", 120)
    with httpx.Client(timeout=timeout) as c:
        r = c.request(method, url, headers=_headers(), **kw)
        r.raise_for_status()
        return r.json()


def _upload_api(path: str, *, files: dict, data: dict | None = None) -> dict:
    """Multipart file upload."""
    url = f"{API_URL}{path}"
    with httpx.Client(timeout=300) as c:
        r = c.post(url, headers=_headers(), files=files, data=data)
        r.raise_for_status()
        return r.json()


def _guess_ct(suffix: str) -> str:
    """Guess content-type from file extension."""
    mapping = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "SAG Knowledge Base (Read-Write)",
    instructions=(
        "SAG knowledge base read-write MCP server. "
        "Supports source/document management, semantic retrieval, and model configuration."
    ),
)

# Tool annotations: every tool talks to the external SAG API, so openWorldHint is
# always true; the other hints reflect whether the handler mutates server state.
_READONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
_WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
)
_IDEMPOTENT_WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
_DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True
)
_TRIGGER = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True
)

# ========================= Source Management ===============================


@mcp.tool(annotations=_READONLY)
def list_sources() -> str:
    """List all knowledge base sources (name, document count, chunk count)."""
    sources = _api("GET", "/api/v1/sources")
    if not sources:
        return "No sources in the knowledge base."
    lines = []
    for s in sources:
        lines.append(
            f"- {s['name']} (id: {s['id']}) | "
            f"{s.get('document_count', 0)} docs | {s.get('chunk_count', 0)} chunks"
        )
    return "\n".join(lines)


@mcp.tool(annotations=_WRITE)
def create_source(
    name: Annotated[str, Field(description="Source name")],
    description: Annotated[str, Field(description="Source description")] = "",
) -> str:
    """Create a new source for uploading documents or ingesting text."""
    result = _api("POST", "/api/v1/sources", json={"name": name, "description": description})
    return f"Source created: {result['name']} (id: {result['id']})"


@mcp.tool(annotations=_DESTRUCTIVE)
def delete_source(
    source_id: Annotated[str, Field(description="Source ID from list_sources")],
) -> str:
    """Delete a source and all its documents/vectors (irreversible)."""
    result = _api("DELETE", f"/api/v1/sources/{source_id}")
    return result.get("detail", "Deleted")


# ========================= Document Management =============================


@mcp.tool(annotations=_READONLY)
def list_documents(
    source_id: Annotated[str, Field(description="Source ID")],
) -> str:
    """List all documents under a source (filename, status, chunk/event counts)."""
    docs = _api("GET", f"/api/v1/sources/{source_id}/documents")
    if not docs:
        return "No documents in this source."
    lines = []
    for d in docs:
        lines.append(
            f"- {d['filename']} (id: {d['id']}) | {d['status']} | "
            f"{d.get('chunk_count', 0)} chunks | {d.get('event_count', 0)} events"
        )
    return "\n".join(lines)


@mcp.tool(annotations=_WRITE)
def upload_document(
    source_id: Annotated[str, Field(description="Source ID")],
    file_path: Annotated[str, Field(description="Local file absolute path")],
) -> str:
    """Upload a local file to a source (auto-parses and extracts)."""
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"
    ct = _guess_ct(p.suffix)
    with open(p, "rb") as f:
        result = _upload_api(
            f"/api/v1/sources/{source_id}/documents",
            files={"file": (p.name, f, ct)},
        )
    return (
        f"Uploaded: {result['filename']} (id: {result['id']}) | {result['status']}\n"
        f"Parsing and extraction will run in the background."
    )


@mcp.tool(annotations=_WRITE)
def ingest_text(
    source_id: Annotated[str, Field(description="Source ID")],
    text: Annotated[str, Field(description="Text content to write")],
    title: Annotated[str, Field(description="Document title")] = "",
) -> str:
    """Write text directly into a source (no file upload needed)."""
    body: dict = {"text": text}
    if title:
        body["title"] = title
    result = _api("POST", f"/api/v1/sources/{source_id}/documents/ingest", json=body)
    return f"Ingested: {result['filename']} (id: {result['id']}) | {result['status']}"


@mcp.tool(annotations=_WRITE)
def reprocess_document(
    source_id: Annotated[str, Field(description="Source ID")],
    document_id: Annotated[str, Field(description="Document ID")],
) -> str:
    """Re-process a document (re-parse and re-extract)."""
    result = _api("POST", f"/api/v1/sources/{source_id}/documents/{document_id}/reprocess")
    return f"Reprocess triggered, job: {result.get('id', '?')}"


@mcp.tool(annotations=_IDEMPOTENT_WRITE)
def pause_document(
    source_id: Annotated[str, Field(description="Source ID")],
    document_id: Annotated[str, Field(description="Document ID")],
) -> str:
    """Pause document processing."""
    result = _api("POST", f"/api/v1/sources/{source_id}/documents/{document_id}/pause")
    return f"Paused, job: {result.get('id', '?')}"


@mcp.tool(annotations=_IDEMPOTENT_WRITE)
def resume_document(
    source_id: Annotated[str, Field(description="Source ID")],
    document_id: Annotated[str, Field(description="Document ID")],
) -> str:
    """Resume document processing."""
    result = _api("POST", f"/api/v1/sources/{source_id}/documents/{document_id}/resume")
    return f"Resumed, job: {result.get('id', '?')}"


@mcp.tool(annotations=_DESTRUCTIVE)
def delete_document(
    source_id: Annotated[str, Field(description="Source ID")],
    document_id: Annotated[str, Field(description="Document ID")],
) -> str:
    """Delete a document and its vectors (irreversible)."""
    result = _api("DELETE", f"/api/v1/sources/{source_id}/documents/{document_id}")
    return result.get("detail", "Deleted")


# ========================= Retrieval (Read-Only) ===========================


@mcp.tool(annotations=_READONLY)
def search(
    query: Annotated[str, Field(description="Search query")],
    top_k: Annotated[int, Field(description="Max results (1-50, default 8)")] = 8,
    source_id: Annotated[str, Field(description="Limit to source ID (empty = all)")] = "",
) -> str:
    """Semantic search the knowledge base (returns LLM-synthesized summary + chunks)."""
    body: dict = {"query": query, "top_k": top_k}
    if source_id:
        body["source_ids"] = [source_id]
    result = _api("POST", "/api/v1/search", json=body, timeout=180)
    sections = result.get("sections", [])
    answer = result.get("answer", "")
    if not sections and not answer:
        return "No relevant content found."
    lines = []
    if answer:
        lines.append(f"Summary: {answer}")
    for i, s in enumerate(sections, 1):
        src = s.get("source_title", "")
        fname = s.get("document_filename", s.get("filename", ""))
        content = s.get("content", "")[:300]
        score = s.get("score", 0)
        lines.append(f"[{i}] {src}/{fname} (score: {score:.2f})\n{content}")
    return "\n\n".join(lines)


@mcp.tool(annotations=_READONLY)
def get_entity(
    source_id: Annotated[str, Field(description="Source ID")],
    entity_name: Annotated[str, Field(description="Entity name")],
) -> str:
    """Query entity details from the knowledge graph."""
    encoded = urllib.parse.quote(entity_name, safe="")
    result = _api("GET", f"/api/v1/sources/{source_id}/entities/{encoded}/context")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READONLY)
def outline(
    source_id: Annotated[str, Field(description="Source ID")],
) -> str:
    """Get document outline (hierarchical heading structure) for a source."""
    result = _api("GET", f"/api/v1/sources/{source_id}/outline")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READONLY)
def grep(
    source_id: Annotated[str, Field(description="Source ID")],
    keyword: Annotated[str, Field(description="Keyword or regex pattern")],
) -> str:
    """Keyword/regex search within a source."""
    encoded = urllib.parse.quote(keyword, safe="")
    result = _api("GET", f"/api/v1/sources/{source_id}/grep?keyword={encoded}")
    items = result.get("items", result.get("matches", []))
    if not items:
        return "No matches found."
    lines = []
    for i, m in enumerate(items[:10], 1):
        content = m.get("content", m.get("text", ""))[:200]
        lines.append(f"[{i}] {content}")
    return "\n\n".join(lines)


@mcp.tool(annotations=_READONLY)
def read_document(
    source_id: Annotated[str, Field(description="Source ID")],
    document_id: Annotated[str, Field(description="Document ID")],
) -> str:
    """Read the full text content of a document."""
    result = _api("GET", f"/api/v1/sources/{source_id}/documents/{document_id}/read")
    return result.get("content", json.dumps(result, ensure_ascii=False))


# ========================= Model Configuration =============================


@mcp.tool(annotations=_READONLY)
def get_model_config() -> str:
    """View current LLM / Embedding model configuration."""
    result = _api("GET", "/api/v1/system/model-config")
    config = result.get("config", result)
    lines = [f"  {k}: {v}" for k, v in config.items()]
    return "Current model config:\n" + "\n".join(lines)


@mcp.tool(annotations=_IDEMPOTENT_WRITE)
def update_model_config(
    llm_model: Annotated[str, Field(description="LLM model name")] = "",
    llm_base_url: Annotated[str, Field(description="LLM API base URL")] = "",
    llm_api_key: Annotated[str, Field(description="LLM API key")] = "",
    embedding_model: Annotated[str, Field(description="Embedding model name")] = "",
    embedding_base_url: Annotated[str, Field(description="Embedding API base URL")] = "",
    embedding_api_key: Annotated[str, Field(description="Embedding API key")] = "",
) -> str:
    """Update model configuration (only non-empty fields are applied)."""
    updates = {}
    for k, v in [
        ("llm_model", llm_model),
        ("llm_base_url", llm_base_url),
        ("llm_api_key", llm_api_key),
        ("embedding_model", embedding_model),
        ("embedding_base_url", embedding_base_url),
        ("embedding_api_key", embedding_api_key),
    ]:
        if v:
            updates[k] = v
    if not updates:
        return "No changes provided."
    result = _api("PUT", "/api/v1/system/model-config", json=updates)
    return f"Config updated: {json.dumps(updates, ensure_ascii=False)}"


@mcp.tool(annotations=_TRIGGER)
def test_model_config() -> str:
    """Test current model configuration (send a test request)."""
    result = _api("POST", "/api/v1/system/model-config/test")
    status = result.get("status", "unknown")
    detail = result.get("detail", "")
    return f"Test result: {status} — {detail}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """CLI entry point: sag-mcp-server [stdio|http] [port]"""
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    if mode == "http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.getenv("SAG_MCP_PORT", "9003"))
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        mcp.settings.streamable_http_path = "/mcp/"
        print(f"SAG MCP HTTP server on 0.0.0.0:{port}/mcp/", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
