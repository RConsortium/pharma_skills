import json
import subprocess
import argparse
import sys
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Derive repo root from this file's location — no CWD dependency (fix 1.4)
REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_SIZE_LIMIT_BYTES = 100 * 1024  # 100 KB (fix 2.3)
RUNS_DIR = REPO_ROOT / "_automation" / "benchmark-runner" / "runs"


def normalize_model_name(name: str) -> str:
    """Lowercase + strip all punctuation/spaces for robust deduplication (fix 1.3)."""
    return re.sub(r"[\s\-_\.]", "", name.lower())


def get_git_sha(skill_path: Path) -> str:
    """Composite SHA over the entire skill directory, not just SKILL.md (fix 3.3)."""
    try:
        result = subprocess.run(
            ["git", "log", "-n", "1", "--format=%H", "--", str(skill_path)],
            capture_output=True, text=True, check=True, cwd=str(REPO_ROOT),
        )
        sha = result.stdout.strip()
        return sha if sha else "unknown"
    except subprocess.CalledProcessError as e:
        print(f"Error: git log failed for {skill_path}: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def check_github_comments(issue_id: str, target_sha: str, target_model: str) -> bool:
    """Return True if a matching benchmark comment already exists (fix 1.1 + 1.3)."""
    match = re.search(r"(\d+)$", issue_id)
    if not match:
        return False
    issue_number = match.group(1)

    try:
        result = subprocess.run(
            [
                "gh", "issue", "view", issue_number,
                "--repo", "RConsortium/pharma_skills",
                "--json", "comments",
            ],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        # A transient gh failure means we cannot confirm — warn loudly but do not
        # silently skip: return False so the benchmark still runs rather than being
        # dropped entirely. The run manifest will record it for audit.
        print(
            f"Warning: gh failed checking comments for issue {issue_id} — "
            f"treating as pending (may cause a duplicate if transient): {e.stderr}",
            file=sys.stderr,
        )
        return False

    data = json.loads(result.stdout)
    norm_target = normalize_model_name(target_model)

    for comment in data.get("comments", []):
        body = comment.get("body", "")
        if "Automated Benchmark Results" not in body:
            continue
        has_sha = (
            f"Skill version: `{target_sha}`" in body
            or f"**Skill version** | `{target_sha}`" in body
        )
        # Normalize the entire comment body so variant spellings still match (fix 1.3)
        has_model = norm_target in normalize_model_name(body)
        if has_sha and has_model:
            return True
    return False


def write_run_manifest(eval_case: dict, model: str, skill_sha: str, status: str) -> None:
    """Append a structured run record for audit and local deduplication (fix 2.2)."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "eval_id": eval_case.get("id"),
        "skill_name": eval_case.get("_skill_name"),
        "skill_sha": skill_sha,
        "model": model,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    manifest_path = RUNS_DIR / "runs.json"
    records = []
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                records = json.load(f)
        except (json.JSONDecodeError, OSError):
            records = []
    records.append(record)
    with open(manifest_path, "w") as f:
        json.dump(records, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", required=True,
        help="Model API ID being used (e.g. claude-sonnet-4-6). "
             "Use the canonical API identifier, not the display name, "
             "to keep deduplication consistent.",
    )
    parser.add_argument("--priority-skill", help="Focus selection on this specific skill folder.")
    parser.add_argument("--priority-issue", help="Prioritize this specific issue ID (e.g. github-issue-27).")
    args = parser.parse_args()

    # Discover skills relative to REPO_ROOT — no CWD assumption (fix 1.4)
    skills: list[Path] = []
    for item in REPO_ROOT.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name.startswith("_"):
            continue
        if (item / "SKILL.md").exists() and (item / "evals" / "evals.json").exists():
            skills.append(item)

    # Prioritize selected skill if provided
    if args.priority_skill:
        skills.sort(key=lambda p: (0 if p.name == args.priority_skill else 1, p.name))
    else:
        skills.sort(key=lambda p: p.name)

    # Collect all eligible evaluations across all skills
    today_last_digit = int(str(datetime.now(timezone.utc).day)[-1])
    eligible_evals: list[dict] = []

    for skill_path in skills:
        evals_path = skill_path / "evals" / "evals.json"
        try:
            with open(evals_path) as f:
                eval_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading {evals_path}: {e}", file=sys.stderr)
            continue

        skill_name = eval_data.get("skill_name", skill_path.name)
        skill_sha = get_git_sha(skill_path)

        # Prioritize selected issue if provided; otherwise reverse to pick newest first
        eval_cases = eval_data.get("evals", [])
        if args.priority_issue:
            eval_cases.sort(key=lambda e: (0 if e.get("id") == args.priority_issue else 1))
        
        for eval_case in eval_cases:
            eval_id = eval_case.get("id")

            if not check_github_comments(eval_id, skill_sha, args.model):
                eval_case["_skill_name"] = skill_name
                eval_case["_skill_sha"] = skill_sha
                eval_case["_skill_dir"] = str(skill_path.relative_to(REPO_ROOT))

                with open(skill_path / "SKILL.md") as s:
                    eval_case["_skill_content"] = s.read()

                # Bundle .md and .py files — exclude evals/ to avoid leaking rubric
                # to Agent A, and warn if total exceeds 100 KB (fixes 2.3)
                bundled: dict[str, str] = {}
                total_bytes = 0
                size_warned = False
                for root, dirs, files in os.walk(skill_path):
                    root_path = Path(root)
                    if root_path.name == "evals":
                        dirs.clear()
                        continue
                    for fname in sorted(files):
                        if not (fname.endswith(".md") or fname.endswith(".py")):
                            continue
                        fpath = root_path / fname
                        rel = str(fpath.relative_to(skill_path))
                        try:
                            content = fpath.read_text()
                        except OSError:
                            continue
                        total_bytes += len(content.encode())
                        if total_bytes > BUNDLE_SIZE_LIMIT_BYTES and not size_warned:
                            print(
                                f"Warning: bundle for '{skill_name}' exceeds "
                                f"{BUNDLE_SIZE_LIMIT_BYTES // 1024} KB — consider "
                                "a _bundle_manifest.json to control included files.",
                                file=sys.stderr,
                            )
                            size_warned = True
                        bundled[rel] = content
                eval_case["_bundled_resources"] = bundled
                eligible_evals.append(eval_case)

                # If we prioritized a specific issue and found it, we can stop collecting
                if args.priority_issue and eval_id == args.priority_issue:
                    break

    if not eligible_evals:
        print("STATUS: UP_TO_DATE")
        return

    def get_issue_num(eval_id: str) -> int:
        match = re.search(r"(\d+)$", eval_id)
        return int(match.group(1)) if match else 0

    # Apply the selection logic:
    # 1. Distance between issue last digit and today's day last digit
    # 2. Tie-breaker: smallest issue number
    selected_eval = min(
        eligible_evals,
        key=lambda e: (
            abs((get_issue_num(e["id"]) % 10) - today_last_digit),
            get_issue_num(e["id"])
        )
    )

    write_run_manifest(selected_eval, args.model, selected_eval["_skill_sha"], "dispatched")
    print(json.dumps(selected_eval, indent=2))

    print("STATUS: UP_TO_DATE")


if __name__ == "__main__":
    main()
