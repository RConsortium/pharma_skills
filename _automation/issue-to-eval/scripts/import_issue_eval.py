import json
import subprocess
import argparse
import sys
import os
import re
from typing import Sequence, Union

# Headers the parser expects — must stay in sync with .github/ISSUE_TEMPLATE/benchmark.md
EXPECTED_HEADERS = {
    "skill": "## Skills",
    "language": "## Language (Optional)",
    "prompt": "## Query",
    "expected_output": "## Expected Output",
    "files": "## Attached Files / Input Context (Optional)",
    "assertions": "## Rubric Criteria (Assertions)",
}
OPTIONAL_KEYS = {"language", "files"}


def clean_value(val: str) -> str:
    """Strip template comments, leading bullets, hyphens, and whitespace."""
    if not val:
        return ""
    val = re.sub(r"<!--.*?-->", "", val, flags=re.DOTALL)
    return re.sub(r"^[\s\-\*•]+", "", val.strip()).strip()


def normalize_skill_name(name: str) -> str:
    return clean_value(name).lower().replace(" ", "-").replace("_", "-")


def parse_list_items(content: str, split_commas: bool = False) -> list[str]:
    """Parse newline/comma separated issue-template values."""
    cleaned = re.sub(r"<!--.*?-->", "", content or "", flags=re.DOTALL)
    items: list[str] = []
    for line in cleaned.splitlines():
        parts = line.split(",") if split_commas else [line]
        for part in parts:
            value = clean_value(part)
            if value:
                items.append(value)
    return items


def parse_issue_markdown(body: str) -> dict:
    """
    Extract fields from a GitHub issue body using the standard benchmark template headers.
    Emits a WARNING to stderr for any expected header that produces an empty result (fix 1.5).
    """
    sections = {
        "skill":           r"## Skills[ \t]*\n(.*?)(?=\n##|$)",
        "language":        r"## Language(?: \(Optional\))?[ \t]*\n(.*?)(?=\n##|$)",
        "prompt":          r"## Query[ \t]*\n(.*?)(?=\n##|$)",
        "expected_output": r"## Expected Output[ \t]*\n(.*?)(?=\n##|$)",
        "files":           r"## Attached Files / Input Context \(Optional\)[ \t]*\n(.*?)(?=\n##|$)",
        "assertions":      r"## Rubric Criteria \(Assertions\)[ \t]*\n(.*?)(?=\n##|$)",
    }


    data: dict = {}
    for key, pattern in sections.items():
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        content = match.group(1).strip() if match else ""

        if key == "skill":
            target_skills = [
                normalize_skill_name(skill)
                for skill in parse_list_items(content, split_commas=True)
                if normalize_skill_name(skill)
            ]
            data["target_skills"] = target_skills
            data["skill_name"] = target_skills[0] if target_skills else ""
        elif key == "language":
            data["language"] = clean_value(content)
        elif key == "files":
            data["files"] = parse_list_items(content, split_commas=True)
        elif key == "assertions":
            data["assertions"] = parse_list_items(content)
        else:
            data[key] = clean_value(content)

    # Heuristic fallback for language if not explicitly provided in the header
    if not data.get("language"):
        combined_text = (data.get("expected_output", "") + " " + " ".join(data.get("assertions", []))).lower()
        if ".r" in combined_text or " r " in combined_text or " rscript" in combined_text or "gsdesign" in combined_text:
            data["language"] = "R"
        elif ".py" in combined_text or "python" in combined_text:
            data["language"] = "Python"

    for key in sections.keys():
        # Warn on empty results so silent parse failures surface immediately (fix 1.5)
        result_value = data.get("skill_name" if key == "skill" else key, "")
        is_empty = (
            not result_value
            if not isinstance(result_value, list)
            else len(result_value) == 0
        )
        if is_empty:
            if key not in OPTIONAL_KEYS:
                print(
                    f"WARNING: '{EXPECTED_HEADERS[key]}' section is empty or missing. "
                    "Ensure the issue follows the benchmark template.",
                    file=sys.stderr,
                )

    return data


def save_to_evals(eval_entry: dict, skill_name: Union[str, Sequence[str]]) -> str:
    target_skills = (
        [normalize_skill_name(skill) for skill in skill_name if normalize_skill_name(skill)]
        if isinstance(skill_name, (list, tuple))
        else [normalize_skill_name(skill_name)] if normalize_skill_name(skill_name) else []
    )
    if not target_skills or target_skills == ["unknown-skill"]:
        return "Error: Could not determine target skill name from issue."

    target_dir = os.path.join("_automation", "evals")
    os.makedirs(target_dir, exist_ok=True)
    eval_file = os.path.join(target_dir, f"{eval_entry['id']}.json")

    eval_entry["target_skills"] = target_skills

    if os.path.exists(eval_file):
        with open(eval_file) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = {}

        changed = any(
            existing.get(field) != eval_entry.get(field)
            for field in ("prompt", "expected_output", "files", "assertions", "target_skills", "language")
        )
        if not changed:
            return f"Skipped: {eval_entry['id']} in _automation/evals/ is up to date."
        
        status = f"Updated: {eval_entry['id']} in _automation/evals/ (content changed)"
    else:
        status = f"Success: Added {eval_entry['id']} to _automation/evals/"

    with open(eval_file, "w") as f:
        json.dump(eval_entry, f, indent=2)

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
            capture_output=True, text=True, encoding="utf-8", check=True,
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
    if parsed.get("language"):
        eval_entry["language"] = parsed["language"]

    status = save_to_evals(eval_entry, parsed.get("target_skills", []))
    print(status)


if __name__ == "__main__":
    main()
