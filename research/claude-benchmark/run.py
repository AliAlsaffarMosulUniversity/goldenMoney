"""Send every task to every Claude model and log output, tokens, cost and latency.

Usage:
    python run.py --tasks tasks/pilot.json --reps 1
    python run.py --tasks tasks/pilot.json --models claude-haiku-5-5 --reps 1
    python run.py --tasks tasks/pilot.json --dry-run      # print the plan only

Requires ANTHROPIC_API_KEY in the environment. Finished runs are skipped,
so the script can be re-run safely after an interruption.
"""
import argparse
import json
import pathlib
import time

import anthropic

# USD per million tokens (input, output). Re-check on the run date.
PRICES = {
    "claude-fable-5-2": (8.00, 40.00),
    "claude-fable-5-1": (10.00, 50.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.00, 5.00),
}

SYSTEM = "You are a senior professional. Follow the brief exactly."
MAX_TOKENS = 32000
OUT_DIR = pathlib.Path(__file__).parent / "outputs"


def settings(model: str) -> dict:
    """Closest equivalent of 'adaptive thinking, high effort' for each model."""
    if model == "claude-haiku-4-5":  # no adaptive thinking or effort on this model
        return {"thinking": {"type": "enabled", "budget_tokens": 16000}}
    if model in {"claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"}:
        return {"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}}
    # Claude 5.x models: thinking is on by default
    return {"output_config": {"effort": "high"}}


def run_one(client, task: dict, model: str, rep: int) -> dict:
    stem = f"{task['id']}__{model}__r{rep}"
    meta_path = OUT_DIR / f"{stem}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())

    record = {"task": task["id"], "domain": task["domain"], "difficulty": task["difficulty"],
              "model": model, "rep": rep}
    t0 = time.perf_counter()
    try:
        # Refusal fallbacks are deliberately NOT enabled: a fallback would swap the model under test.
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": task["prompt"]}],
            **settings(model),
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.NotFoundError as e:
        record.update(error="model_not_available", detail=str(e))
        meta_path.write_text(json.dumps(record, indent=2))
        return record
    except anthropic.BadRequestError as e:
        record.update(error="bad_request", detail=str(e))
        meta_path.write_text(json.dumps(record, indent=2))
        return record

    latency = time.perf_counter() - t0
    text = "".join(b.text for b in msg.content if b.type == "text")
    p_in, p_out = PRICES[model]
    usage = msg.usage
    record.update(
        stop_reason=msg.stop_reason,
        refusal=msg.stop_reason == "refusal",
        refusal_category=getattr(msg.stop_details, "category", None) if msg.stop_details else None,
        served_model=msg.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=round((usage.input_tokens * p_in + usage.output_tokens * p_out) / 1e6, 6),
        latency_s=round(latency, 2),
        request_id=msg._request_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    (OUT_DIR / f"{stem}.md").write_text(text, encoding="utf-8")
    meta_path.write_text(json.dumps(record, indent=2))
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks/pilot.json")
    ap.add_argument("--models", nargs="*", default=list(PRICES))
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tasks = json.loads(pathlib.Path(args.tasks).read_text())
    plan = [(t, m, r) for t in tasks for m in args.models for r in range(args.reps)]
    print(f"{len(plan)} generations planned ({len(tasks)} tasks x {len(args.models)} models x {args.reps} reps)")
    if args.dry_run:
        return

    OUT_DIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic()
    total = 0.0
    for task, model, rep in plan:
        rec = run_one(client, task, model, rep)
        total += rec.get("cost_usd", 0.0)
        status = rec.get("error") or rec.get("stop_reason")
        print(f"{task['id']:8} {model:20} r{rep}  {status:16} "
              f"${rec.get('cost_usd', 0):.4f}  {rec.get('latency_s', '-')}s  (running total ${total:.2f})")


if __name__ == "__main__":
    main()
