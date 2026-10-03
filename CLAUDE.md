# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A smoke test (README and code comments are in Spanish) that validates connectivity to any OpenAI-compatible Chat Completions endpoint (Microsoft Foundry via Entra ID, Ollama, vLLM, OpenRouter, OpenAI…). Provider switching is done **only through environment variables** — the code must stay provider-agnostic.

## Commands

```bash
uv sync                                          # install deps (Python version pinned in .python-version)
cp .env.example .env                             # keep only one provider profile active
uv run --env-file .env arch-ai-preparation       # run the smoke test
echo $?                                          # check exit code
uv run ruff check .                              # lint (rules: E, F, I, UP, B)
uv run ruff format .                             # format
```

There is no test suite; the program itself is the test.

## Architecture

Everything lives in `src/arch_ai_preparation/main.py` (entry point `main`, registered as the `arch-ai-preparation` script in `pyproject.toml`). Flow: `missing_env()` validates config → `resolve_api_key()` picks auth → `OpenAI` client sends one chat completion → exceptions map to exit codes.

- **Auth switch (`LLM_AUTH`)**: `key` (default) passes `LLM_API_KEY` as a static string; `entra` passes a bearer-token *callable* from `azure.identity` (`DefaultAzureCredential`, scope from `LLM_TOKEN_SCOPE`, default `https://ai.azure.com/.default`). The OpenAI client accepts a callable as `api_key` and refreshes tokens itself. `azure.identity` is imported lazily so key-based profiles don't need it.
- **`missing_env()` must stay in sync with `resolve_api_key()`**: `LLM_API_KEY` is only required when `LLM_AUTH != entra`.
- **Exit codes** are part of the contract (documented in README): `0` OK, `1` auth/404/network error, `2` missing env vars. Add new failure paths to the matching code and update the README table if semantics change.
- Client is configured with `timeout=30.0, max_retries=1` so failures surface quickly.

`src/arch_ai_preparation/llm.py` holds `call_llm(...) -> CallRecord`: times only the API call with `perf_counter`, tolerates missing `usage`/`prompt_tokens_details`, computes `cost_usd` from `LLM_PRICE_*` env vars (USD per 1M tokens; `None` if input/output prices are unset), appends one JSON line to `runs/day1.jsonl` (gitignored) and prints a row. It reuses `resolve_api_key()`/`missing_env()` from `main.py` and lets OpenAI exceptions propagate.

Env var reference and provider profiles are in `README.md` and `.env.example`.
