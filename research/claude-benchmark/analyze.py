"""Score every output, then write results.csv, summary.md and a blinded rating sheet.

Usage: python analyze.py
"""
import csv
import json
import pathlib
import random
import statistics as st

from checks import score

HERE = pathlib.Path(__file__).parent
OUT = HERE / "outputs"
DOMAINS = ["report", "video", "image", "code"]


def main():
    rows = []
    for meta_path in sorted(OUT.glob("*.json")):
        rec = json.loads(meta_path.read_text())
        text_path = meta_path.with_suffix(".md")
        if rec.get("error") or not text_path.exists():
            rec["auto_score"], rec["checks"] = None, {}
        else:
            rec["auto_score"], rec["checks"] = score(rec["domain"], text_path.read_text(encoding="utf-8"))
        rows.append(rec)
    if not rows:
        print("No outputs yet. Run run.py first.")
        return

    # Per-generation results
    with open(HERE / "results.csv", "w", newline="") as f:
        cols = ["task", "domain", "difficulty", "model", "rep", "stop_reason", "error", "auto_score",
                "input_tokens", "output_tokens", "cost_usd", "latency_s", "request_id", "checks"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "checks": json.dumps(r["checks"])})

    # Per-model summary (Table 4 of the paper)
    models = sorted({r["model"] for r in rows}, key=lambda m: -max(
        (x.get("cost_usd") or 0) for x in rows if x["model"] == m))
    lines = ["| Model | " + " | ".join(f"Auto score: {d}" for d in DOMAINS)
             + " | Auto score: overall | Mean cost/task (USD) | Median latency (s) | Refusals | Errors |",
             "| --- " * (len(DOMAINS) + 6) + "|"]
    for m in models:
        mine = [r for r in rows if r["model"] == m]
        ok = [r for r in mine if r["auto_score"] is not None]

        def avg(xs):
            return f"{st.mean(xs):.2f}" if xs else "-"
        per_dom = [avg([r["auto_score"] for r in ok if r["domain"] == d]) for d in DOMAINS]
        cost = [r["cost_usd"] for r in ok if r.get("cost_usd") is not None]
        lat = [r["latency_s"] for r in ok if r.get("latency_s") is not None]
        cost_cols = f" | {st.mean(cost):.4f} | {st.median(lat):.1f}" if cost else " | - | -"
        lines.append(f"| {m} | " + " | ".join(per_dom)
                     + f" | {avg([r['auto_score'] for r in ok])}" + cost_cols)
        lines[-1] +=f" | {sum(bool(r.get('refusal')) for r in mine)} | {sum(bool(r.get('error')) for r in mine)} |"
    (HERE / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    # Blinded rating sheet for human experts + separate key
    rated = [r for r in rows if r["auto_score"] is not None]
    rng = random.Random(2026)
    rng.shuffle(rated)
    with open(HERE / "rating_sheet.csv", "w", newline="") as f, open(HERE / "rating_key.csv", "w", newline="") as k:
        ws, wk = csv.writer(f), csv.writer(k)
        ws.writerow(["item_id", "task", "output_file", "correctness_1_5", "completeness_1_5",
                     "usefulness_1_5", "craft_1_5", "rater_id", "guessed_model"])
        wk.writerow(["item_id", "model", "rep"])
        for i, r in enumerate(rated, 1):
            item = f"ITEM-{i:04d}"
            blind = HERE / "blind" / f"{item}.md"
            blind.parent.mkdir(exist_ok=True)
            blind.write_text((OUT / f"{r['task']}__{r['model']}__r{r['rep']}.md").read_text(encoding="utf-8"))
            ws.writerow([item, r["task"], f"blind/{item}.md", "", "", "", "", "", ""])
            wk.writerow([item, r["model"], r["rep"]])
    print(f"\nWrote results.csv, summary.md, rating_sheet.csv (+ rating_key.csv, keep it from raters).")


if __name__ == "__main__":
    main()
