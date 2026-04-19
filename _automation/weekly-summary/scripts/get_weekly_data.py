import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def run_command(command: str) -> str:
    """Run a shell command and return stdout. Exit with error on failure (fix 1.1)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: command failed: {command}\n{e.stderr}", file=sys.stderr)
        sys.exit(1)


def get_weekly_data() -> dict:
    config = load_config()
    lookback_days: int = config.get("lookback_days", 7)  # fix 2.5 — read from config
    since_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # Commits
    commits_raw = run_command(f'git log --since="{lookback_days} days ago" --oneline')
    commits_list = [line for line in commits_raw.split("\n") if line]

    # Issues updated in the lookback window
    issues_json = run_command(
        f'gh issue list --repo RConsortium/pharma_skills --state all '
        f'--search "updated:>={since_date}" --json number,title,state,updatedAt --limit 1000'
    )
    issues_list = json.loads(issues_json) if issues_json else []
    issues_summary = [
        {"number": i["number"], "title": i["title"], "state": i["state"]}
        for i in issues_list
    ]

    # PRs updated in the lookback window
    prs_json = run_command(
        f'gh pr list --repo RConsortium/pharma_skills --state all '
        f'--search "updated:>={since_date}" --json number,title,state,updatedAt,mergedAt --limit 1000'
    )
    prs_list = json.loads(prs_json) if prs_json else []
    prs_summary = [
        {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "merged": bool(pr.get("mergedAt")),
        }
        for pr in prs_list
    ]

    return {
        "week_starting": since_date,
        "week_ending": datetime.now().strftime("%Y-%m-%d"),
        "commits": {
            "total_count": len(commits_list),
            "highlights": commits_list[:5],
        },
        "issues": {
            "total_updated": len(issues_summary),
            "list": issues_summary,
        },
        "pull_requests": {
            "total_updated": len(prs_summary),
            "list": prs_summary,
        },
    }


if __name__ == "__main__":
    data = get_weekly_data()
    print(json.dumps(data, indent=2))
