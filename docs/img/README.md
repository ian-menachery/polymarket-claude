# Screenshots

The root `README.md` embeds three images from this folder. To (re)generate them:

1. `make run` and open <http://localhost:5000>.
2. Capture each view at a window width of ~1200px and save as PNG here:

   | File | View (tab) | Needs | What it shows |
   | --- | --- | --- | --- |
   | `markets.png` | **Markets** | existing analyzed markets (no LLM call) | each estimate vs. the live price + divergence badge |
   | `scanner.png` | **Scan (EV)** | one live scan (calls the LLM) | the results table ranked by annualized EV |

   The two views below populate only once analyzed markets **resolve** — add them when you have data:

   | File | View (tab) | Needs |
   | --- | --- | --- |
   | `leaderboard.png` | **Leaderboard** | ≥1 resolved market (per-model Brier / log-loss / Brier skill) |
   | `performance.png` | **Performance** | ≥1 settled signal (the cumulative-P&L equity curve) |

Optional: a short `demo.gif` of a scan run makes the README hero even stronger.

Keep images reasonably small (< ~300 KB each); they're committed to the repo.
