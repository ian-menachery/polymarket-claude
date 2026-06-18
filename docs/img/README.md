# Screenshots

The root `README.md` embeds three images from this folder. To (re)generate them:

1. `make run` and open <http://localhost:5000>.
2. Make sure there's data to show: run a scan with logging on
   (`POST /api/scan` with `{"log_signals": true}`, or let the background scheduler run), and
   refresh so some markets resolve. The leaderboard and track record populate as forecasts resolve.
3. Capture each view at a window width of ~1200px and save as PNG here:

   | File | View (tab) | What it shows |
   | --- | --- | --- |
   | `scanner.png` | **Scan (EV)** | the results table ranked by annualized EV |
   | `leaderboard.png` | **Leaderboard** | per-model Brier / log-loss / accuracy / Brier skill |
   | `performance.png` | **Performance** | the cumulative-P&L equity curve + summary stats |

Optional: a short `demo.gif` of a scan run makes the README hero even stronger.

Keep images reasonably small (< ~300 KB each); they're committed to the repo.
