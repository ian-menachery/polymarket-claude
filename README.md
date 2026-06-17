# Polymarket Research Copilot

[![CI](https://github.com/ian-menachery/polymarket-claude/actions/workflows/ci.yml/badge.svg)](https://github.com/ian-menachery/polymarket-claude/actions/workflows/ci.yml)

A local research tool that fetches live **Polymarket** and **Kalshi** prediction markets, asks an
LLM (OpenAI or Anthropic, with web search) for a calibrated probability estimate, and surfaces the
markets where the model's estimate diverges most from the current market price.

It's a *research aid* — a structured way to find "where to look," not a trading bot. It is read-only
against the exchanges and never places orders.

> **Disclaimer:** Estimates come from an LLM and are not financial advice. EV figures are directional.

## What it does

- **Dual exchange** — normalizes Polymarket (Gamma API) and Kalshi markets into one model; scan
  either or both (`EXCHANGE=polymarket|kalshi|both`).
- **Dual LLM provider** — `LLM_PROVIDER=openai|anthropic`, switchable via `.env`. Each analysis
  records the model that produced it, so calibration stays per-model across a provider switch.
- **EV divergence scanner** — ranks markets by annualized expected value using the model's
  *calibrated* estimate vs. the **executable** order-book price (depth-aware VWAP fill), not just the
  mid. Falls back to the mid when no two-sided book is available.
- **Adversarial refutation** — a skeptical second pass (optionally cross-model) re-checks the
  top-ranked edges before they're trusted.
- **Calibration tracking** — temperature-scaling recalibration per model, reliability curves,
  Brier/log-loss, and a CSV export (with forecast horizon) for the companion calibration tracker.
- **Forward signals & P&L** — logs actionable edges at scan time and scores realized P&L once the
  market resolves (the real calibration flywheel).
- **Background automation** — stdlib scheduler (no APScheduler) for periodic scans, resolution
  sweeps, and optional stale re-analysis; high-divergence alerts to a JSONL log + optional webhook.
- **Single-file web UI** — Flask serves a React (CDN) frontend at `/`: markets, scanner, signals,
  alerts, and calibration views.

## Stack

Python 3.12 · Flask · httpx (sync) · Pydantic · SQLite (stdlib) · OpenAI / Anthropic SDKs.
No asyncio, no build pipeline, no Docker — it's a deliberately small local tool.

## Quick start

```bash
make install
cp .env.example .env      # set LLM_PROVIDER + the matching API key
make run                  # → http://localhost:5000
```

## Make targets

| Target | What it does |
| --- | --- |
| `make install` / `make install-dev` | runtime deps / dev deps (pytest, ruff, pip-tools) |
| `make run` | start the Flask app on :5000 |
| `make test` | run the test suite (100+ unit/integration tests) |
| `make lint` | ruff over `src` + `tests` |
| `make lock` | regenerate pinned `requirements*.lock` |

## Project layout

```
src/research/      models · db · polymarket · kalshi · analyzer · scanner · calibration · scheduler · app
frontend/          single-file React UI served by Flask
scripts/           portfolio sim + crowd-calibration backtest (CLI)
tests/             pure-logic, DB round-trip, route, and resilience tests
```

Deeper docs: [`ARCHITECTURE.md`](ARCHITECTURE.md) (data flow + schema),
[`ROADMAP.md`](ROADMAP.md) (phased plan), [`API_REFERENCE.md`](API_REFERENCE.md) (Polymarket /
Kalshi / LLM APIs), [`CALIBRATION_NOTES.md`](CALIBRATION_NOTES.md).

## Configuration

All runtime knobs are environment variables (see [`.env.example`](.env.example) for the full set):
provider/model, exchange selection, volume/liquidity/divergence gates, target position size,
scan & resolution & stale-reanalysis cadences, and alert thresholds/webhook. API keys are read from
the environment only and never committed (`.env` is gitignored).

## License

[MIT](LICENSE) © Ian Menachery
