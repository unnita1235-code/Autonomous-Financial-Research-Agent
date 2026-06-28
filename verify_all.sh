#!/bin/bash
# Save as verify_all.sh and run: bash verify_all.sh

PASS=0; FAIL=0; WARN=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  PASS${NC}  $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}  FAIL${NC}  $1"; FAIL=$((FAIL+1)); }
warn() { echo -e "${YELLOW}  WARN${NC}  $1"; WARN=$((WARN+1)); }

echo ""; echo "=== PHASE 1: Critical Bug Fixes ==="; echo ""
grep -q 'run_data = {' app/pipeline.py             && ok  "P1.1  pipeline.py calculate_metrics fixed"         || fail "P1.1  pipeline.py calculate_metrics NOT fixed"
grep -q 'statement_type' agent/fallback_chains.py && ok "P1.2  fallback_chains tool kwargs passing"    || fail "P1.2  fallback_chains still passes only query string"
grep -q 'generate_conflict_narrative' synthesis/narrative.py && ok "P1.3  narrative.py has generate_conflict_narrative" || fail "P1.3  generate_conflict_narrative missing"
grep -q 'from typing import.*Optional' agents/prompts.py    && ok "P1.4  prompts.py Optional import present"  || fail "P1.4  prompts.py missing Optional import"
[ -f app/db_health.py ]                            && ok  "P1.5  app/db_health.py exists"                    || fail "P1.5  app/db_health.py missing"
python3 -c "from app.database import get_db_engine; print()" 2>/dev/null && ok "P1.5b database module imports" || fail "P1.5b database module import error"

echo ""; echo "=== PHASE 2: Infrastructure ==="; echo ""
[ -f app/job_store.py ]                            && ok  "P2.1  app/job_store.py exists"                    || fail "P2.1  app/job_store.py missing"
grep -q 'redis' requirements.txt                   && ok  "P2.2  redis in requirements.txt"                  || warn "P2.2  redis not in requirements.txt"
grep -q 'REDIS_URL' .env.example                   && ok  "P2.3  REDIS_URL in .env.example"                  || warn "P2.3  REDIS_URL missing from .env.example"
grep -q 'storage_uri' app/limiter.py               && ok  "P2.4  limiter uses Redis storage_uri"             || warn "P2.4  limiter still in-memory only"

echo ""; echo "=== PHASE 3: Agent Intelligence ==="; echo ""
python3 -c "from agents.react_loop import run_agent, _parse_llm_json, _validate_action" 2>/dev/null && ok "P3.1  react_loop imports OK with helpers" || fail "P3.1  react_loop import FAILED"
grep -q '_parse_llm_json' agents/react_loop.py     && ok  "P3.2  _parse_llm_json in react_loop.py"          || fail "P3.2  _parse_llm_json missing"
grep -q '_validate_action' agents/react_loop.py    && ok  "P3.3  _validate_action in react_loop.py"          || fail "P3.3  _validate_action missing"
grep -q 'STOPPING RULES' agents/prompts.py         && ok  "P3.4  improved SYSTEM_PROMPT with stopping rules" || fail "P3.4  SYSTEM_PROMPT not updated"
grep -q 'web_search.*fetch_web' tools/__init__.py  && ok  "P3.5  web_search alias in TOOL_REGISTRY"          || warn "P3.5  web_search alias missing"
grep -q 'vector_db_search' tools/__init__.py       && ok  "P3.6  vector_db_search alias in TOOL_REGISTRY"    || warn "P3.6  vector_db_search alias missing"
grep -q 'max_tokens.*512' agents/llm_client.py     && ok  "P3.7  Groq max_tokens reduced to 512"             || warn "P3.7  Groq token limit not adjusted"

echo ""; echo "=== PHASE 4: Memory System ==="; echo ""
grep -q '_init_backend' memory/embedder.py         && ok  "P4.1  embedder has multi-backend support"         || fail "P4.1  embedder not upgraded"
grep -q 'sentence_transformers' memory/embedder.py && ok  "P4.2  sentence-transformers backend present"       || warn "P4.2  sentence-transformers backend missing"
python3 -c "from memory.embedder import embed, EMBEDDING_DIM; print(EMBEDDING_DIM)" 2>/dev/null && ok "P4.3  embedder imports OK" || fail "P4.3  embedder import FAILED"

echo ""; echo "=== PHASE 5: Security & Auth ==="; echo ""
[ -f app/auth.py ]                                 && ok  "P5.1  app/auth.py exists"                         || fail "P5.1  app/auth.py missing"
python3 -c "from app.auth import verify_token, create_access_token" 2>/dev/null && ok "P5.2  auth module imports OK" || fail "P5.2  auth module import FAILED"
grep -q '555.0199\|[0-9]{3}.[0-9]{4}' security/pii_redactor.py && ok "P5.3  PII phone pattern updated"       || warn "P5.3  PII phone regex may not catch all patterns"
grep -q 'jailbreak\|DAN mode\|im_start' security/prompt_injection_shield.py && ok "P5.4  injection shield expanded" || warn "P5.4  injection patterns not expanded"
grep -q 'field_validator' app/models.py            && ok  "P5.5  Pydantic field validators added"             || fail "P5.5  field validators missing"

echo ""; echo "=== PHASE 6: Frontend ==="; echo ""
[ -f frontend/.env.local.example ]                 && ok  "P6.1  frontend/.env.local.example exists"         || fail "P6.1  frontend/.env.local.example missing"
[ -f frontend/components/FinancialChart.tsx ]      && ok  "P6.2  FinancialChart component exists"             || fail "P6.2  FinancialChart.tsx missing"
grep -q 'isProdWithLocalhost' frontend/app/page.tsx && ok "P6.3  localhost warning in frontend"               || warn "P6.3  no localhost warning in frontend"

echo ""; echo "=== PHASE 7: Tests ==="; echo ""
python3 -c "import ast; ast.parse(open('tests/test_synthesis.py').read()); print('ok')" 2>/dev/null && ok "P7.1  test_synthesis.py is valid Python" || fail "P7.1  test_synthesis.py is binary/broken"
[ -f tests/test_helpers.py ]                       && ok  "P7.2  tests/test_helpers.py exists"               || fail "P7.2  tests/test_helpers.py missing"
[ -f tests/test_pipeline_integration.py ]          && ok  "P7.3  integration tests exist"                    || fail "P7.3  integration tests missing"
[ -f pytest.ini ] || [ -f setup.cfg ]              && ok  "P7.4  pytest.ini exists"                          || warn "P7.4  pytest.ini missing"

echo ""; echo "=== PHASE 8: Observability ==="; echo ""
[ -f app/logging_config.py ]                       && ok  "P8.1  app/logging_config.py exists"               || fail "P8.1  logging_config.py missing"
[ -f app/metrics_tracker.py ]                      && ok  "P8.2  app/metrics_tracker.py exists"              || fail "P8.2  metrics_tracker.py missing"
grep -q 'Instrumentator' app/main.py               && ok  "P8.3  Prometheus instrumentation in main.py"      || warn "P8.3  Prometheus not added to main.py"
grep -q 'configure_logging' app/main.py            && ok  "P8.4  configure_logging called in main.py"        || warn "P8.4  configure_logging not in main.py"

echo ""; echo "=== PHASE 9: Docker & CI/CD ==="; echo ""
[ -f Dockerfile ]                                  && ok  "P9.1  Dockerfile exists"                          || fail "P9.1  Dockerfile missing"
[ -f docker-compose.yml ]                          && ok  "P9.2  docker-compose.yml exists"                  || fail "P9.2  docker-compose.yml missing"
[ -f .github/workflows/ci.yml ]                    && ok  "P9.3  GitHub Actions CI workflow exists"          || fail "P9.3  .github/workflows/ci.yml missing"
[ -f .github/workflows/deploy.yml ]                && ok  "P9.4  GitHub Actions deploy workflow exists"      || fail "P9.4  .github/workflows/deploy.yml missing"
grep -q 'agent_run_output.json' .gitignore         && ok  "P9.5  committed artifacts in .gitignore"          || fail "P9.5  committed artifacts not in .gitignore"

echo ""; echo "=== PHASE 10: Docs & Cleanup ==="; echo ""
grep -q 'Quick Start\|quick start' README.md       && ok  "P10.1 README has Quick Start section"             || fail "P10.1 README not updated"
[ -f CHANGELOG.md ]                                && ok  "P10.2 CHANGELOG.md exists"                        || fail "P10.2 CHANGELOG.md missing"

echo ""; echo "=== PYTHON IMPORT VALIDATION ==="; echo ""
PYTHONPATH=. python3 scripts/verify_imports.py 2>/dev/null && ok "IMPORTS all core imports pass" || fail "IMPORTS core import errors found"

echo ""; echo "=== TEST SUITE ==="; echo ""
PYTHONPATH=. python3 -m pytest tests/ -q --tb=no 2>/dev/null
[ $? -eq 0 ] && ok "TESTS all tests pass" || fail "TESTS some tests failing"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${GREEN}PASS: $PASS${NC}   ${RED}FAIL: $FAIL${NC}   ${YELLOW}WARN: $WARN${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
[ $FAIL -eq 0 ] && echo -e "${GREEN}  All critical checks passed!${NC}" || echo -e "${RED}  $FAIL critical items need fixing. See FAIL lines above.${NC}"
echo ""
