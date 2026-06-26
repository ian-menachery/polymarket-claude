# Polymarket Research Copilot — CLAUDE.md

## Working agreement on planning

Plan-first is **relaxed** (owner's call, 2026-06-13): commit changes directly to `main`
and make code edits without stating a plan or waiting for confirmation first.

Still state a brief plan when a change is large, risky, ambiguous, or hard to reverse —
otherwise just implement. Surface contradictions and unexpected findings as before.

## What this is
A local research tool that fetches live Polymarket markets, analyzes them with an LLM (web search enabled), and surfaces markets where the model's probability estimate diverges significantly from the current price. Companion project to the calibration tracker (separate repo).

## Stack (locked)
- `flask`, `httpx` (sync), `anthropic`, `openai`, `pydantic`, `sqlite3` (stdlib), `python-dotenv`
- No `asyncio`. No `aiosqlite`. No React build pipeline. No Docker. No Postgres.
- New dependencies require asking first.

## LLM provider (dual-provider)
The analysis engine (`analyzer.py`) supports **both OpenAI and Anthropic**, selected at
runtime by the `LLM_PROVIDER` env var (`openai` or `anthropic`). Each `Analysis` records the
`model` that produced it, so calibration stays per-model across a provider switch.

- **Currently primary: Anthropic** — `.env` sets `LLM_PROVIDER=anthropic` and
  `ANALYSIS_MODEL=claude-sonnet-4-6` (also the code default). The Anthropic path uses the
  server-side `web_search` tool (confirm web_search is enabled for the org in the Claude Console).
- **OpenAI is the reversible fallback** — set `LLM_PROVIDER=openai` (+ `OPENAI_MODEL`, default
  `gpt-5.5`) and restart to switch back. No code change needed; the path is kept intact.
- Switch providers by changing `LLM_PROVIDER` in `.env` (then restart).
- Each `Analysis` records its `model`, so calibration stays **per-model** across a switch — a
  provider change starts a fresh per-model calibration history (uncalibrated until `CALIBRATION_MIN_N`
  resolved pairs); don't size real positions on a new model until its outcomes confirm calibration.
- No silent fallback: if OpenAI credits are exhausted (`insufficient_quota`), the engine latches
  `openai_exhausted` and returns an explicit error — it does not quietly switch providers.

## Quick start
```bash
make install
cp .env.example .env    # set LLM_PROVIDER + the matching API key
                        # (OpenAI: OPENAI_API_KEY; Anthropic: ANTHROPIC_API_KEY)
make run                # → http://localhost:5000
```

## Project structure
```
polymarket-research/
├── CLAUDE.md                 ← you are here
├── ARCHITECTURE.md           ← data flow, DB schema, component specs
├── ROADMAP.md                ← phased feature plan
├── API_REFERENCE.md          ← Polymarket + Anthropic API reference
├── CALIBRATION_NOTES.md      ← integration with calibration tracker
├── src/
│   └── research/
│       ├── models.py         ← Pydantic models
│       ├── db.py             ← sqlite3 access layer (sync only)
│       ├── polymarket.py     ← Polymarket API client (httpx sync)
│       ├── analyzer.py       ← LLM analysis engine (OpenAI or Anthropic, via LLM_PROVIDER)
│       ├── scanner.py        ← batch divergence scanner
│       └── app.py            ← Flask app + all routes
├── frontend/
│   └── index.html            ← single file served by Flask at /
├── data/                     ← SQLite DB, gitignored
├── requirements.txt
├── .env.example
└── Makefile
```

## Module boundaries (enforce these)
- All Polymarket API calls live in `polymarket.py`. No `httpx` imports anywhere else.
- All DB operations live in `db.py`. No raw SQL outside that module.
- No business logic in `db.py`. It only reads and writes.
- Flask routes in `app.py` call the modules — they don't contain logic.

## Code conventions
- Type hints on every function in Python
- All probabilities stored as float 0–1 in DB; displayed as % in frontend
- Market IDs are always strings
- Never delete or overwrite analysis records — only append

## Things you should not do
- Do not add infrastructure speculatively (no FastAPI upgrade, no Redis, no Celery)
- Do not "clean up" code I didn't ask you to clean up — mention it, don't fix it silently
- Do not invent data. If an API call fails, surface the error — never fill with zeros
- Do not use `asyncio` anywhere. Use `time.sleep()` for rate limiting.
- Do not hardcode API keys (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) — read them from env

## Things you should do
- After each substantive change, suggest a commit message (short, imperative)
- When you finish a piece of work, summarize what changed in 2–3 sentences
- If a request seems like Phase 2+ work, say so and ask whether to skip ahead

## Phase awareness
Phases are in ROADMAP.md. Always know which phase we're in.
Current phase: **Phase 5 — Advanced** (in progress). Phases 1–4 are complete (EV scanner,
persistence/history, calibration + resolution sweep). Phase 5 is mostly built: scheduled background
scanning (stdlib threading.Timer, not APScheduler), portfolio simulator, crowd backtesting,
multi-model comparison (cross-model adversarial refutation), and webhook/forward-signal alerting
(forward signal log + high-divergence alerts). Note: the scanner is a Flask/httpx-sync stack, not the
FastAPI/`main.py` named in ROADMAP.md's early checklists.

## Relationship to calibration tracker
This is a separate project. The `polymarket.py` module here borrows patterns from the calibration tracker's `polymarket/` module (API normalization, gotchas) but does not import from it directly. The shared data contract is documented in CALIBRATION_NOTES.md.
