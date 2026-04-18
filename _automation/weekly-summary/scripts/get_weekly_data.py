import json
import subprocess
from datetime import datetime, timedelta
import os

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {command}: {e.stderr}", flush=True)
        return ""

def get_weekly_data():
    # Commits (last 7 days)
    commits_raw = run_command('git log --since="7 days ago" --oneline')
    commits_list = [line for line in commits_raw.split('\n') if line]
    commit_count = len(commits_list)
    commit_highlights = commits_list[:5] # Limit to top 5 highlights to save tokens

    # Issues (updated in last 7 days)
    # Using gh search to get all issues updated in the last 7 days
    issues_json = run_command('gh issue list --repo RConsortium/pharma_skills --state all --search "updated:>=$(date -v-7d +%Y-%m-%d)" --json number,title,state,updatedAt')
    issues_list = json.loads(issues_json) if issues_json else []
    
    issues_opened = [i for i in issues_list if i['state'] == 'OPEN' and i['updatedAt'] >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')]
    # Simpler filtering for summary purposes
    issues_summary = []
    for i in issues_list:
        issues_summary.append({
            "number": i['number'],
            "title": i['title'],
            "state": i['state']
        })

    # PRs (updated in last 7 days)
    prs_json = run_command('gh pr list --repo RConsortium/pharma_skills --state all --search "updated:>=$(date -v-7d +%Y-%m-%d)" --json number,title,state,updatedAt,mergedAt')
    prs_list = json.loads(prs_json) if prs_json else []
    
    prs_summary = []
    for pr in prs_list:
        prs_summary.append({
            "number": pr['number'],
            "title": pr['title'],
            "state": pr['state'],
            "merged": bool(pr.get('mergedAt'))
        })

    # Final structure
    result = {
        "week_starting": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        "week_ending": datetime.now().strftime('%Y-%m-%d'),
        "commits": {
            "total_count": commit_count,
            "highlights": commit_highlights
        },
        "issues": {
            "total_updated": len(issues_summary),
            "list": issues_summary
        },
        "pull_requests": {
            "total_updated": len(prs_summary),
            "list": prs_summary
        }
    }
    
    return result

if __name__ == "__main__":
    data = get_weekly_data()
    print(json.dumps(data, indent=2))
