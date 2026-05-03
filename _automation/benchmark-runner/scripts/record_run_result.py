import json
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = REPO_ROOT / "_automation" / "benchmark-runner" / "runs"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--tokens-a", type=int, help="Tokens for Agent A")
    parser.add_argument("--tokens-b", type=int, help="Tokens for Agent B")
    args = parser.parse_args()

    manifest_path = RUNS_DIR / "runs.json"
    if not manifest_path.exists():
        print("Error: Manifest not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, "r") as f:
        records = json.load(f)

    # Find the most recent "dispatched" or "partial_a" record for this eval/model.
    # "partial_a" is written by Phase 1 when Agent A completes; Phase 2 updates it to "completed".
    found = False
    for record in reversed(records):
        if (record.get("eval_id") == args.eval_id
                and record.get("model") == args.model
                and record.get("status") in ("dispatched", "partial_a")):
            record["status"] = args.status
            record["end_timestamp"] = datetime.now(timezone.utc).timestamp()
            start = record.get("start_timestamp")
            if start:
                record["duration_sec"] = record["end_timestamp"] - start
                record["duration_min"] = round(record["duration_sec"] / 60, 1)
            if args.tokens_a is not None:
                record["tokens_a"] = args.tokens_a
            if args.tokens_b is not None:
                record["tokens_b"] = args.tokens_b
            found = True
            break

    if not found:
        print(f"Warning: No dispatched/partial_a record found for {args.eval_id} and {args.model}", file=sys.stderr)

    with open(manifest_path, "w") as f:
        json.dump(records, f, indent=2)

if __name__ == "__main__":
    main()
