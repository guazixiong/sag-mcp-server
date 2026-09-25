"""Unit tests for all 18 MCP tools (mocked SAG API, no network)."""

from __future__ import annotations

import asyncio

import pytest

from sag_mcp import server

HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")


class AnyDict(dict):
    """Fake API response: any missing key resolves to a printable placeholder."""

    def __missing__(self, key):
        return 0 if key.endswith("_count") else "x"


@pytest.fixture
def calls(monkeypatch):
    recorded: list[tuple[str, str]] = []

    def fake_api(method, path, **kw):
        recorded.append((method, path))
        return AnyDict()

    def fake_upload_api(path, *, files, data=None):
        recorded.append(("POST", path))
        return AnyDict()

    monkeypatch.setattr(server, "_api", fake_api)
    monkeypatch.setattr(server, "_upload_api", fake_upload_api)
    return recorded


# ---------------------------------------------------------------------------
# Tool invocations
# ---------------------------------------------------------------------------

def test_list_sources(calls):
    assert isinstance(server.list_sources(), str)
    assert calls == [("GET", "/api/v1/sources")]


def test_create_source(calls):
    out = server.create_source("kb", "desc")
    assert "Source created" in out
    assert calls == [("POST", "/api/v1/sources")]


def test_delete_source(calls):
    assert isinstance(server.delete_source("s1"), str)
    assert calls == [("DELETE", "/api/v1/sources/s1")]


def test_list_documents(calls):
    out = server.list_documents("s1")
    assert isinstance(out, str)
    assert calls == [("GET", "/api/v1/sources/s1/documents")]


def test_upload_document(calls, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# hi", encoding="utf-8")
    out = server.upload_document("s1", str(f))
    assert "Uploaded" in out
    assert calls == [("POST", "/api/v1/sources/s1/documents")]


def test_upload_document_missing_file(calls):
    out = server.upload_document("s1", "/nope/missing.pdf")
    assert "File not found" in out
    assert calls == []


def test_ingest_text(calls):
    out = server.ingest_text("s1", "content", "title")
    assert "Ingested" in out
    assert calls == [("POST", "/api/v1/sources/s1/documents/ingest")]


def test_reprocess_document(calls):
    out = server.reprocess_document("s1", "d1")
    assert "Reprocess triggered" in out
    assert calls == [("POST", "/api/v1/sources/s1/documents/d1/reprocess")]


def test_pause_document(calls):
    out = server.pause_document("s1", "d1")
    assert "Paused" in out
    assert calls == [("POST", "/api/v1/sources/s1/documents/d1/pause")]


def test_resume_document(calls):
    out = server.resume_document("s1", "d1")
    assert "Resumed" in out
    assert calls == [("POST", "/api/v1/sources/s1/documents/d1/resume")]


def test_delete_document(calls):
    assert isinstance(server.delete_document("s1", "d1"), str)
    assert calls == [("DELETE", "/api/v1/sources/s1/documents/d1")]


def test_search(calls):
    out = server.search("q", top_k=5, source_id="s1")
    assert out == "No relevant content found."
    assert calls == [("POST", "/api/v1/search")]


def test_get_entity(calls):
    out = server.get_entity("s1", "some entity")
    assert isinstance(out, str)
    assert calls == [("GET", "/api/v1/sources/s1/entities/some%20entity/context")]


def test_outline(calls):
    assert isinstance(server.outline("s1"), str)
    assert calls == [("GET", "/api/v1/sources/s1/outline")]


def test_grep(calls):
    out = server.grep("s1", "key word")
    assert out == "No matches found."
    assert calls == [("GET", "/api/v1/sources/s1/grep?keyword=key%20word")]


def test_read_document(calls):
    assert isinstance(server.read_document("s1", "d1"), str)
    assert calls == [("GET", "/api/v1/sources/s1/documents/d1/read")]


def test_get_model_config(calls):
    out = server.get_model_config()
    assert "Current model config" in out
    assert calls == [("GET", "/api/v1/system/model-config")]


def test_update_model_config(calls):
    out = server.update_model_config(llm_model="gpt-x")
    assert "Config updated" in out
    assert calls == [("PUT", "/api/v1/system/model-config")]


def test_update_model_config_noop(calls):
    assert server.update_model_config() == "No changes provided."
    assert calls == []


def test_test_model_config(calls):
    out = server.test_model_config()
    assert "Test result" in out
    assert calls == [("POST", "/api/v1/system/model-config/test")]


# ---------------------------------------------------------------------------
# Declaration-level checks (MCP spec conformance)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tools():
    return asyncio.run(server.mcp.list_tools())


def test_all_18_tools_registered(tools):
    assert len(tools) == 18


def test_every_tool_declares_all_four_hints(tools):
    for t in tools:
        assert t.annotations is not None, t.name
        for hint in HINTS:
            value = getattr(t.annotations, hint)
            assert isinstance(value, bool), f"{t.name}.{hint} = {value!r}"


def test_read_only_tools_never_mutate(tools):
    mutating = {
        "create_source", "delete_source", "upload_document", "ingest_text",
        "reprocess_document", "pause_document", "resume_document",
        "delete_document", "update_model_config",
    }
    for t in tools:
        assert t.annotations.readOnlyHint == (t.name not in mutating), t.name


def test_destructive_tools_flagged(tools):
    for t in tools:
        assert t.annotations.destructiveHint == t.name.startswith("delete_"), t.name
