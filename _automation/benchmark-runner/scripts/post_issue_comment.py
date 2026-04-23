import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_REPO = os.environ.get("PHARMA_SKILLS_GITHUB_REPO", "RConsortium/pharma-skills")

BENCHMARK_MARKER = "Automated Benchmark Results"


def get_github_token() -> Optional[str]:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _api_request(url: str, method: str = "GET", payload: Optional[dict] = None) -> dict:
    token = get_github_token()
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pharma-skills-benchmark-runner",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def find_existing_comment(repo: str, issue_number: str, model: str) -> Optional[int]:
    """Return the comment ID of an existing benchmark result for this model, or None."""
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
            f"?per_page=100&page={page}"
        )
        comments = _api_request(url)
        for c in comments:
            body = c.get("body", "")
            if BENCHMARK_MARKER in body and model in body:
                return c["id"]
        if len(comments) < 100:
            break
        page += 1
    return None


def post_issue_comment(repo: str, issue_number: str, body: str) -> str:
    data = _api_request(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        method="POST",
        payload={"body": body},
    )
    return data.get("html_url", "")


def update_issue_comment(repo: str, comment_id: int, body: str) -> str:
    data = _api_request(
        f"https://api.github.com/repos/{repo}/issues/comments/{comment_id}",
        method="PATCH",
        payload={"body": body},
    )
    return data.get("html_url", "")


def upsert_issue_comment(repo: str, issue_number: str, body: str, model: str) -> tuple[str, str]:
    """Post a new comment or update the existing one for this model. Returns (url, action)."""
    comment_id = find_existing_comment(repo, issue_number, model)
    if comment_id is not None:
        url = update_issue_comment(repo, comment_id, body)
        return url, "updated"
    url = post_issue_comment(repo, issue_number, body)
    return url, "created"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post or update a GitHub issue comment through REST API without gh."
    )
    parser.add_argument("issue_number", help="GitHub issue number to comment on")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Repository in owner/name form")
    parser.add_argument("--body-file", required=True, help="Markdown file to post")
    parser.add_argument(
        "--model",
        help=(
            "Model name as it appears in the comment body. When provided, an existing "
            "benchmark comment for this model is updated instead of creating a new one."
        ),
    )
    args = parser.parse_args()

    try:
        body = Path(args.body_file).read_text()
        if args.model:
            url, action = upsert_issue_comment(args.repo, args.issue_number, body, args.model)
        else:
            url = post_issue_comment(args.repo, args.issue_number, body)
            action = "created"
    except (OSError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"Error posting issue comment: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Comment {action}: {url or '(no URL returned)'}")


if __name__ == "__main__":
    main()
