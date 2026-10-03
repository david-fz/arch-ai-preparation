import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

from openai import OpenAI

from arch_ai_preparation.main import missing_env, resolve_api_key

RUNS_FILE = Path("runs/day1.jsonl")


@dataclass(frozen=True)
class CallRecord:
    """Una llamada al LLM = una línea de runs/day1.jsonl (esquema de agent_steps)."""

    ts: str
    experiment: str
    model: str
    prompt_hash: str
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    latency_ms: float
    cost_usd: float | None
    finish_reason: str | None
    max_tokens: int
    temperature: float


@cache
def _client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=resolve_api_key(),
        timeout=30.0,
        max_retries=1,
    )


def _price(name: str) -> float | None:
    """Precio en USD por 1M de tokens desde el entorno; None si no está definido."""
    raw = os.environ.get(name)
    return float(raw) if raw else None


def compute_cost(tokens_in: int, tokens_cached: int, tokens_out: int) -> float | None:
    """costo = no_cacheados × p_in + cacheados × p_in_cacheado + output × p_out.

    Devuelve None si faltan LLM_PRICE_INPUT o LLM_PRICE_OUTPUT. Si falta
    LLM_PRICE_CACHED_INPUT se cobra el input cacheado a la tarifa normal.
    """
    p_in = _price("LLM_PRICE_INPUT")
    p_out = _price("LLM_PRICE_OUTPUT")
    if p_in is None or p_out is None:
        return None
    p_cached = _price("LLM_PRICE_CACHED_INPUT")
    if p_cached is None:
        p_cached = p_in
    uncached = tokens_in - tokens_cached
    return (uncached * p_in + tokens_cached * p_cached + tokens_out * p_out) / 1_000_000


def hash_prompt(messages: list[dict]) -> str:
    canonical = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def call_llm(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    experiment: str,
) -> CallRecord:
    if missing := missing_env():
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    client = _client()
    model = os.environ["LLM_MODEL"]

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    # Algunos servidores omiten usage o prompt_tokens_details: se asume 0.
    usage = response.usage
    tokens_in = getattr(usage, "prompt_tokens", None) or 0
    tokens_out = getattr(usage, "completion_tokens", None) or 0
    details = getattr(usage, "prompt_tokens_details", None)
    tokens_cached = getattr(details, "cached_tokens", None) or 0

    record = CallRecord(
        ts=datetime.now(UTC).isoformat(),
        experiment=experiment,
        model=response.model or model,
        prompt_hash=hash_prompt(messages),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tokens_cached=tokens_cached,
        latency_ms=round(latency_ms, 1),
        cost_usd=compute_cost(tokens_in, tokens_cached, tokens_out),
        finish_reason=response.choices[0].finish_reason,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    cost = "n/d" if record.cost_usd is None else f"${record.cost_usd:.6f}"
    print(
        f"[{experiment}] in={tokens_in} out={tokens_out} cached={tokens_cached} "
        f"| {record.latency_ms:.1f} ms | {cost}"
    )
    return record
