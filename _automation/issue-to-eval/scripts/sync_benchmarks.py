import json
import subprocess
import sys
import argparse
from import_issue_eval import parse_issue_markdown, save_to_evals

DEFAULT_REPO = "RConsortium/pharma-skills"


def fetch_benchmark_issues(repo: str) -> list[dict]:
    """Fetch all issues labeled 'benchmark' with pagination (fix 2.4)."""
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--repo", repo,
                "--label", "benchmark",
                "--json", "number,body,title",
                "--limit", "1000",
            ],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: gh failed listing benchmark issues: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    return json.loads(result.stdout)


def sync_all_benchmarks(repo: str) -> None:
    issues = fetch_benchmark_issues(repo)

    if not issues:
        print("No issues found with 'benchmark' label.")
        return

    total = len(issues)
    print(f"Found {total} benchmark issue(s). Syncing...")

    synced = 0
    skipped = 0
    errors = 0

    for issue in issues:
        try:
            parsed = parse_issue_markdown(issue["body"])

            if not parsed.get("skill_name") or not parsed.get("prompt"):
                print(
                    f"Skipping Issue #{issue['number']}: Missing Skill Name or Query.",
                    file=sys.stderr,
                )
                skipped += 1
                continue

            eval_entry = {
                "id": f"github-issue-{issue['number']}",
                "prompt": parsed.get("prompt", ""),
                "expected_output": parsed.get("expected_output", ""),
                "files": parsed.get("files", []),
                "assertions": parsed.get("assertions", []),
            }
            if parsed.get("language"):
                eval_entry["language"] = parsed["language"]

            status = save_to_evals(eval_entry, parsed.get("target_skills", []))
            print(f"Issue #{issue['number']}: {status}")
            synced += 1

        except Exception as e:
            print(f"Error processing Issue #{issue['number']}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nSynced {synced}/{total} issues. Skipped: {skipped}. Errors: {errors}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync all GitHub issues labeled 'benchmark' into local _automation/evals/ directory."
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repository in owner/name format (default: {DEFAULT_REPO})",
    )
    args = parser.parse_args()
    sync_all_benchmarks(args.repo)


if __name__ == "__main__":
    main()
