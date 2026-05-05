# This directory stores the local benchmark run manifest (runs.json).
# The manifest is used for fast local deduplication before hitting the GitHub API,
# and as an audit log of all dispatched benchmark runs.
#
# runs.json is gitignored to avoid merge conflicts. Each entry has the shape:
# {
#   "eval_id": "github-issue-21",
#   "skill_name": "group-sequential-design",
#   "skill_sha": "<git sha>",
#   "model": "claude-sonnet-4-6",
#   "run_date": "<ISO 8601 UTC>",
#   "status": "dispatched"
# }
