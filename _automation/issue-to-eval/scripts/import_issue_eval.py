import json
import subprocess
import argparse
import sys
import os
import re

# Headers the parser expects — must stay in sync with .github/ISSUE_TEMPLATE/benchmark.md
EXPECTED_HEADERS = {
    "skill": "## Skills",
    "prompt": "## Query",
    "expected_output": "## Expected Output",
    "files": "## Attached Files / Input Context (Optional)",
    "assertions": "## Rubric Criteria (Assertions)",
}


def clean_value(val: str) -> str:
    """Strip leading bullets, hyphens, and whitespace."""
    if not val:
        return ""
    return re.sub(r"^[\s\-\*•]+", "", val.strip()).strip()


def parse_issue_markdown(body: str) -> dict:
    """
    Extract fields from a GitHub issue body using the standard benchmark template headers.
    Emits a WARNING to stderr for any expected header that produces an empty result (fix 1.5).
    """
    sections = {
        "skill":           r"## Skills\n(.*?)(?=\n##|$)",
        "prompt":          r"## Query\n(.*?)(?=\n##|$)",
        "expected_output": r"## Expected Output\n(.*?)(?=\n##|$)",
        "files":           r"## Attached Files / Input Context \(Optional\)\n(.*?)(?=\n##|$)",
        "assertions":      r"## Rubric Criteria \(Assertions\)\n(.*?)(?=\n##|$)",
    }

    data: dict = {}
    for key, pattern in sections.items():
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        content = match.group(1).strip() if match else ""

        if key == "skill":
            data["skill_name"] = clean_value(content).lower().replace(" ", "-")
        elif key == "files":
            data["files"] = [clean_value(f) for f in content.split("\n") if clean_value(f)]
        elif key == "assertions":
            data["assertions"] = [clean_value(a) for a in content.split("\n") if clean_value(a)]
        else:
            data[key] = clean_value(content)

        # Warn on empty results so silent parse failures surface immediately (fix 1.5)
        result_value = data.get("skill_name" if key == "skill" else key, "")
        is_empty = (
            not result_value
            if not isinstance(result_value, list)
            else len(result_value) == 0
        )
        if is_empty:
            print(
                f"WARNING: '{EXPECTED_HEADERS[key]}' section is empty or missing. "
                "Ensure the issue follows the benchmark template.",
                file=sys.stderr,
            )

    return data


def save_to_evals(eval_entry: dict, skill_name: str) -> str:
    if not skill_name or skill_name == "unknown-skill":
        return "Error: Could not determine target skill name from issue."

    target_dir = os.path.join(skill_name, "evals")
    os.makedirs(target_dir, exist_ok=True)
    eval_file = os.path.join(target_dir, "evals.json")

    if os.path.exists(eval_file):
        with open(eval_file) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"skill_name": skill_name, "evals": []}
    else:
        data = {"skill_name": skill_name, "evals": []}

    found_idx = -1
    for i, existing in enumerate(data["evals"]):
        if existing.get("id") == eval_entry["id"]:
            found_idx = i
            break

    if found_idx != -1:
        existing = data["evals"][found_idx]
        changed = any(
            existing.get(field) != eval_entry.get(field)
            for field in ("prompt", "expected_output", "files", "assertions")
        )
        if not changed:
            return f"Skipped: {eval_entry['id']} in {skill_name} is up to date."
        data["evals"][found_idx] = eval_entry
        status = f"Updated: {eval_entry['id']} in {skill_name}/evals/evals.json (content changed)"
    else:
        data["evals"].append(eval_entry)
        status = f"Success: Added {eval_entry['id']} to {skill_name}/evals/evals.json"

    with open(eval_file, "w") as f:
        json.dump(data, f, indent=2)

    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True, help="GitHub Issue number or URL")
    args = parser.parse_args()

    issue_match = re.search(r"(\d+)$", args.issue)
    if not issue_match:
        print(f"Error: Could not parse issue number from '{args.issue}'", file=sys.stderr)
        sys.exit(1)

    issue_id = issue_match.group(1)

    try:
        result = subprocess.run(
            ["gh", "issue", "view", issue_id, "--json", "number,body,title"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: gh failed fetching issue {issue_id}: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    issue_data = json.loads(result.stdout)
    parsed = parse_issue_markdown(issue_data["body"])

    eval_entry = {
        "id": f"github-issue-{issue_data['number']}",
        "prompt": parsed.get("prompt", ""),
        "expected_output": parsed.get("expected_output", ""),
        "files": parsed.get("files", []),
        "assertions": parsed.get("assertions", []),
    }

    status = save_to_evals(eval_entry, parsed.get("skill_name", ""))
    print(status)


if __name__ == "__main__":
    main()
