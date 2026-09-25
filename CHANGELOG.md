# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MCP tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) on all 18 tools, matching each handler's actual behavior
- Unit test suite (`tests/test_server.py`): all 18 tools exercised against a mocked SAG API, plus annotation conformance checks

## [0.1.0] - 2026-08-21

### Added

- Initial release
- 18 MCP tools: source/document CRUD, semantic search, knowledge graph queries, model config
- Streamable HTTP transport with Bearer JWT authentication
- stdio transport for local integration
- Docker support
- Example configurations for Claude Desktop, Cursor, Dify
