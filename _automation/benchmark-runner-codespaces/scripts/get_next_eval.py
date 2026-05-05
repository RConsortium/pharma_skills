import hashlib
import json
import subprocess
import argparse
import sys
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Derive repo root from this file's location — no CWD dependency (fix 1.4)
REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_SIZE_LIMIT_BYTES = 100 * 1024  # 100 KB (fix 2.3)
RUNS_DIR = REPO_ROOT / "_automation" / "benchmark-runner" / "runs"
GITHUB_REPO = os.environ.get("PHARMA_SKILLS_GITHUB_REPO", "RConsortium/pharma-skills")
TEXT_EXTENSIONS = {
    ".csv", ".tsv", ".txt", ".md", ".r", ".py", ".json",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".sql",
}


def normalize_model_name(name: str) -> str:
    """Lowercase + strip all punctuation/spaces for robust deduplication (fix 1.3)."""
    return re.sub(r"[\s\-_\.]", "", name.lower())


def get_github_token() -> Optional[str]:
    """Return the GitHub token used for REST API fallbacks, if configured."""
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def fetch_issue_comments_via_api(issue_number: str, repo: str = GITHUB_REPO) -> list[dict]:
    """Fetch issue comments through GitHub REST without requiring the gh CLI."""
    token = get_github_token()
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")

    comments: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
            f"?per_page=100&page={page}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "pharma-skills-benchmark-runner",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            page_comments = json.loads(response.read().decode("utf-8"))
        if not page_comments:
            break
        comments.extend(page_comments)
        if len(page_comments) < 100:
            break
        page += 1
    return comments


def has_matching_benchmark_comment(comments: list[dict], target_sha: str, target_model: str) -> bool:
    """Return True when comments contain a benchmark result for this SHA/model."""
    norm_target = normalize_model_name(target_model)

    for comment in comments:
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


def get_issue_num(eval_id: str) -> int:
    match = re.search(r"(\d+)$", eval_id)
    return int(match.group(1)) if match else 0


def get_default_runner_id() -> str:
    for env_name in ("PHARMA_SKILLS_RUNNER_ID", "GITHUB_ACTOR", "USER", "USERNAME"):
        value = os.environ.get(env_name)
        if value:
            return value
    try:
        return os.uname().nodename
    except AttributeError:
        return "default-runner"


def get_default_selection_salt(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%MZ")


def distributed_selection_score(eval_case: dict, model: str, runner_id: str, salt: str) -> int:
    key = "|".join([
        normalize_model_name(model),
        runner_id,
        salt,
        eval_case.get("id", ""),
        eval_case.get("_skill_sha", ""),
    ])
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)


def select_eval(
    eligible_evals: list[dict],
    model: str,
    selection_mode: str,
    runner_id: str,
    selection_salt: str,
    now: datetime,
) -> dict:
    if selection_mode == "daily":
        today_last_digit = int(str(now.day)[-1])
        return min(
            eligible_evals,
            key=lambda e: (
                abs((get_issue_num(e["id"]) % 10) - today_last_digit),
                get_issue_num(e["id"])
            )
        )

    if selection_mode == "distributed":
        return min(
            eligible_evals,
            key=lambda e: (
                distributed_selection_score(e, model, runner_id, selection_salt),
                get_issue_num(e["id"]),
            )
        )

    raise ValueError(f"Unsupported selection mode: {selection_mode}")


def get_skill_content_sha(skill_path: Path) -> str:
    """SHA256 over the actual content of bundled skill files (.md, .py), excluding evals/.

    Using content rather than git-commit SHA avoids false "new version" signals when
    surrounding commits (e.g. moving eval files out of the skill directory) touch the
    path without changing any skill file.  The hash is stable as long as the files
    the agents actually receive are unchanged.
    """
    h = hashlib.sha256()
    for root, dirs, files in os.walk(skill_path):
        root_path = Path(root)
        if root_path.name == "evals":
            dirs.clear()
            continue
        dirs.sort()
        for fname in sorted(files):
            if not (fname.endswith(".md") or fname.endswith(".py")):
                continue
            fpath = root_path / fname
            rel = str(fpath.relative_to(skill_path))
            try:
                content = fpath.read_bytes()
                h.update(rel.encode())
                h.update(content)
            except OSError:
                pass
    return h.hexdigest()


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
                "--repo", GITHUB_REPO,
                "--json", "comments",
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        return has_matching_benchmark_comment(data.get("comments", []), target_sha, target_model)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # If gh is unavailable or unauthenticated, try the REST API fallback.
        err_msg = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
        print(
            f"Warning: gh failed checking comments for issue {issue_id} — "
            f"trying GitHub REST API fallback: {err_msg}",
            file=sys.stderr,
        )
    except json.JSONDecodeError as e:
        print(
            f"Warning: gh returned invalid JSON checking comments for issue {issue_id} — "
            f"trying GitHub REST API fallback: {e}",
            file=sys.stderr,
        )

    try:
        comments = fetch_issue_comments_via_api(issue_number)
    except (RuntimeError, OSError, urllib.error.URLError, urllib.error.HTTPError) as e:
        print(
            f"Warning: GitHub REST API fallback failed checking comments for issue "
            f"{issue_id} — treating as pending (may cause a duplicate if transient): {e}",
            file=sys.stderr,
        )
        return False
    return has_matching_benchmark_comment(comments, target_sha, target_model)


def build_agent_prompts(eval_case: dict) -> None:
    """Build matched A/B prompts from one neutral task payload."""
    task_parts: list[str] = []
    if eval_case.get("language"):
        task_parts.append(f"Use {eval_case['language']} for this task.")
    task_parts.append(eval_case["prompt"])

    input_files: list[dict[str, str]] = []
    for idx, fpath_str in enumerate(eval_case.get("files") or [], start=1):
        source_path = REPO_ROOT / fpath_str
        ext = Path(fpath_str).suffix.lower()
        alias = f"input_{idx:03d}{ext or '.dat'}"
        kind = "text" if ext in TEXT_EXTENSIONS else "binary"
        input_files.append({
            "alias": alias,
            "source": str(source_path),
            "kind": kind,
        })

        if kind == "text":
            try:
                content = source_path.read_text(encoding="utf-8")
            except OSError as e:
                print(
                    f"Warning: could not read input file {fpath_str}: {e}",
                    file=sys.stderr,
                )
                continue
            task_parts.append(f"--- {alias} ---\n{content}")

    if input_files:
        aliases = ", ".join(f"`{item['alias']}`" for item in input_files)
        task_parts.append(f"Input file(s) are staged in the `input/` directory: {aliases}")

    usage_suffix = (
        "At the very end of your response, state your best estimate of the "
        "total tokens used in this turn (input + output) using the format: "
        "`[USAGE: {total_tokens}]`"
    )
    common_task_prompt = "\n\n".join(task_parts)
    eval_case["_input_files"] = input_files
    eval_case["_common_task_prompt"] = common_task_prompt
    eval_case["_prompt_a"] = (
        "Follow the provided skill workflow to complete this task. "
        "Save all generated files into a directory named `output_A/`. "
        "Produce all expected outputs.\n\n"
        f"{common_task_prompt}\n\n"
        f"{usage_suffix}"
    )
    eval_case["_prompt_b"] = (
        "Complete this task using only your base knowledge and tools. "
        "Do NOT use any SKILL.md, skill instructions, bundled skill resources, "
        "or repository skill files. "
        "Save all generated files into a directory named `output_B/`. "
        "Produce all expected outputs.\n\n"
        f"{common_task_prompt}\n\n"
        f"{usage_suffix}"
    )
    eval_case["_scoring_prompt"] = (
        "Score two anonymized benchmark candidates against the rubric below. "
        "Do not infer which candidate used a skill. Score only the artifacts "
        "available under `candidate_1/` and `candidate_2/`.\n\n"
        f"Task prompt:\n{eval_case['prompt']}\n\n"
        f"Expected output:\n{eval_case.get('expected_output', '')}\n\n"
        "Assertions:\n"
        + "\n".join(f"- {assertion}" for assertion in eval_case.get("assertions", []))
        + "\n\nReturn a concise score table with Pass, Partial, or Fail for each "
        "assertion and each candidate. Do not mention or infer treatment labels."
    )

    blind_seed = hashlib.sha256(
        f"{eval_case.get('id', '')}:{eval_case.get('_skill_sha', '')}".encode()
    ).hexdigest()
    if int(blind_seed[:2], 16) % 2 == 0:
        eval_case["_blinded_scoring_map"] = {
            "candidate_1": "output_A",
            "candidate_2": "output_B",
        }
    else:
        eval_case["_blinded_scoring_map"] = {
            "candidate_1": "output_B",
            "candidate_2": "output_A",
        }


def write_run_manifest(eval_case: dict, model: str, skill_sha: str, status: str) -> None:
    """Append a structured run record for audit and local deduplication (fix 2.2)."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "eval_id": eval_case.get("id"),
        "skill_name": eval_case.get("_skill_name"),
        "skill_sha": skill_sha,
        "model": model,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "start_timestamp": datetime.now(timezone.utc).timestamp(),
        "status": status,
        "selection_mode": eval_case.get("_selection_mode"),
        "selection_runner_id": eval_case.get("_selection_runner_id"),
        "selection_salt": eval_case.get("_selection_salt"),
    }
    manifest_path = RUNS_DIR / "runs.json"
    records = []
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, OSError):
            records = []
    records.append(record)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", required=True,
        help="Model API ID being used (e.g. gemini-2.0-flash, gpt-4o, claude-3-7-sonnet). "
             "Use the canonical API identifier, not the display name, "
             "to keep deduplication consistent.",
    )
    parser.add_argument("--priority-skill", help="Focus selection on this specific skill folder.")
    parser.add_argument("--priority-issue", help="Prioritize this specific issue ID (e.g. github-issue-27).")
    parser.add_argument(
        "--selection-mode",
        choices=("distributed", "daily"),
        default=os.environ.get("PHARMA_SKILLS_SELECTION_MODE", "distributed"),
        help=(
            "How to choose among pending evals. 'distributed' hashes model, runner id, "
            "selection salt, and eval id so multiple runners spread out. 'daily' preserves "
            "the previous day-last-digit ordering."
        ),
    )
    parser.add_argument(
        "--runner-id",
        default=get_default_runner_id(),
        help=(
            "Stable id for this worker/person. Defaults to PHARMA_SKILLS_RUNNER_ID, "
            "GITHUB_ACTOR, USER, USERNAME, or hostname."
        ),
    )
    parser.add_argument(
        "--selection-salt",
        default=os.environ.get("PHARMA_SKILLS_SELECTION_SALT"),
        help=(
            "Salt for distributed selection. Defaults to the current UTC minute. "
            "Set explicitly to reproduce a prior dispatch order."
        ),
    )
    args = parser.parse_args()

    # Discover evals from the centralized evals directory
    evals_dir = REPO_ROOT / "_automation" / "evals"
    if not evals_dir.exists():
        print("STATUS: UP_TO_DATE")
        return

    # Collect all eligible evaluations across all skills
    dispatch_now = datetime.now(timezone.utc)
    selection_salt = args.selection_salt or get_default_selection_salt(dispatch_now)
    eligible_evals: list[dict] = []

    for eval_file in sorted(evals_dir.glob("*.json")):
        try:
            with open(eval_file, encoding="utf-8") as f:
                eval_case = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error reading {eval_file}: {e}", file=sys.stderr)
            continue

        eval_id = eval_case.get("id")
        if args.priority_issue and eval_id != args.priority_issue:
            continue

        target_skills = eval_case.get("target_skills", [])
        if not target_skills:
            continue

        primary_skill_name = target_skills[0]
        if args.priority_skill and primary_skill_name != args.priority_skill:
            continue

        skill_path = REPO_ROOT / primary_skill_name
        if not (skill_path / "SKILL.md").exists():
            continue

        skill_sha = get_skill_content_sha(skill_path)

        if not check_github_comments(eval_id, skill_sha, args.model):
            eval_case["_skill_name"] = primary_skill_name
            eval_case["_skill_sha"] = skill_sha
            eval_case["_skill_dir"] = str(skill_path.relative_to(REPO_ROOT))

            with open(skill_path / "SKILL.md", encoding="utf-8") as s:
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
                        content = fpath.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    total_bytes += len(content.encode())
                    if total_bytes > BUNDLE_SIZE_LIMIT_BYTES and not size_warned:
                        print(
                            f"Warning: bundle for '{primary_skill_name}' exceeds "
                            f"{BUNDLE_SIZE_LIMIT_BYTES // 1024} KB — consider "
                            "a _bundle_manifest.json to control included files.",
                            file=sys.stderr,
                        )
                        size_warned = True
                    bundled[rel] = content
            eval_case["_bundled_resources"] = bundled

            build_agent_prompts(eval_case)

            eligible_evals.append(eval_case)

            # If we prioritized a specific issue and found it, we can stop collecting
            if args.priority_issue and eval_id == args.priority_issue:
                break

    if not eligible_evals:
        print("STATUS: UP_TO_DATE")
        return

    selected_eval = select_eval(
        eligible_evals,
        args.model,
        args.selection_mode,
        args.runner_id,
        selection_salt,
        dispatch_now,
    )
    selected_eval["_selection_mode"] = args.selection_mode
    selected_eval["_selection_runner_id"] = args.runner_id
    selected_eval["_selection_salt"] = selection_salt

    write_run_manifest(selected_eval, args.model, selected_eval["_skill_sha"], "dispatched")
    print(json.dumps(selected_eval, indent=2))

    print("STATUS: UP_TO_DATE")


if __name__ == "__main__":
    main()
