# Screenshots

The root `README.md` embeds three images from this folder. To (re)generate them:

1. `make run` and open <http://localhost:5000>.
2. Capture each view at a window width of ~1200px and save as PNG here:

   | File | View (tab) | Needs | What it shows |
   | --- | --- | --- | --- |
   | `markets.png` | **Markets** | existing analyzed markets (no LLM call) | each estimate vs. the live price + divergence badge |
   | `scanner.png` | **Scan (EV)** | one live scan (calls the LLM) | the results table ranked by annualized EV |

   The two views below need *resolved* data. Rather than wait, seed a **throwaway demo DB** with
   synthetic (clearly-labeled `[DEMO]`) data — no API spend — and screenshot against that:

   ```bash
   RESEARCH_DB_PATH=data/demo.db PYTHONPATH=src python scripts/seed_demo.py
   RESEARCH_DB_PATH=data/demo.db make run     # Leaderboard + Performance + Calibration now populate
   # capture the shots, then delete data/demo.db (it must never feed real calibration)
   ```

   | File | View (tab) | Needs |
   | --- | --- | --- |
   | `leaderboard.png` | **Leaderboard** | resolved markets (synthetic via `seed_demo`, or real) |
   | `performance.png` | **Performance** | settled signals (synthetic via `seed_demo`, or real) |

Optional: a short `demo.gif` of a scan run makes the README hero even stronger.

Keep images reasonably small (< ~300 KB each); they're committed to the repo.
