# Changelog

## [1.1.0] — Production ready

### Fixed
- calculate_metrics() signature mismatch in app/pipeline.py (P0)
- Tool dispatch passing only query string instead of full kwargs in fallback_chains.py (P0)
- Agent never reaching "done" state — now enforced via STOPPING RULES in system prompt
- generate_conflict_narrative missing import in synthesis/engine.py
- Optional import missing in agents/prompts.py
- PII phone number redaction regex pattern
- TF-IDF embedder not initializing correctly on fresh deployment

### Added
- app/job_store.py — Redis-backed job store with in-memory fallback
- app/auth.py — Optional JWT authentication via REQUIRE_AUTH env var
- app/db_health.py — Database health check endpoint
- app/logging_config.py — Structured JSON logging
- app/metrics_tracker.py — Prometheus metrics (no-op if library absent)
- Prometheus /metrics endpoint via prometheus-fastapi-instrumentator
- Sentry error tracking via SENTRY_DSN env var
- Dockerfile + docker-compose.yml for local and production deployment
- GitHub Actions CI pipeline (.github/workflows/ci.yml)
- Full test suite: test_synthesis.py, test_helpers.py, test_pipeline_integration.py
- pytest.ini and conftest.py
- FinancialChart.tsx component in frontend
- frontend/.env.local.example for developer setup
- Multi-backend memory embedder (TF-IDF / sentence-transformers / OpenAI)
- Web search and vector_db_search aliases in TOOL_REGISTRY
- Groq max_tokens capped at 512 to prevent JSON generation failures
- .gitignore entries for all generated/committed artifacts

### Infrastructure
- Redis rate limiting via slowapi storage_uri
- /health/db endpoint
- Pydantic field validators on ResearchRequest
- prompt injection shield expanded with jailbreak patterns
