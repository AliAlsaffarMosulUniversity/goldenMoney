# Claude model comparison: experiment code

Code for the paper *From Prose to Pixels to Programs: An Empirical Comparison of the Claude Model Family*.
It sends the same tasks to 13 Claude models, scores every output with automatic checks, and
prepares a blinded sheet for expert raters.

| File | Purpose |
| --- | --- |
| `tasks/pilot.json` | Pilot: 4 simple tasks, one per domain (report, video, image, code) |
| `run.py` | Calls the Claude API; saves each output (`outputs/*.md`) and its tokens, cost, latency (`outputs/*.json`) |
| `checks.py` | Automatic checks per domain (headings and totals; JSON/SRT validity and ffmpeg render; SVG validity and render; hidden unit tests) |
| `analyze.py` | Writes `results.csv`, `summary.md` and a blinded `rating_sheet.csv` (+ `rating_key.csv`, keep it away from raters) |
| `samples/` | Hand-written good and bad answers used only to test that the checks work; not results |

## Run it

1. Requirements: Python 3.10+, `ffmpeg`, and `pip install anthropic cairosvg jsonschema pillow`.
2. Set your key: `export ANTHROPIC_API_KEY=...` (in a Claude Code cloud session, add it as an environment variable in the environment settings, then start a new session).
3. Check the plan without spending anything: `python run.py --dry-run`
4. Pilot (52 generations): `python run.py --tasks tasks/pilot.json --reps 1`
5. Score and summarise: `python analyze.py`

Runs that already finished are skipped, so you can re-run after an interruption.

## Cost of the pilot

Worst case, if every call used all 32,000 output tokens: about USD 39. Real outputs for these
tasks are much shorter, so the actual cost should be a small fraction of that; `run.py` prints
a running total.

## Notes

- Refusal fallbacks are disabled on purpose, so every answer comes from the model under test.
- Models your account cannot access are recorded as `model_not_available` and skipped.
- Prices in `run.py` are list prices as of November 2026; re-check them on the run date.
