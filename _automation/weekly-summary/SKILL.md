---
name: weekly-summary
description: Generate a concise weekly progress summary for the pharma_skills repository. Use this to summarize recent commits, PRs, and issues, then post the update to Slack and save it as a markdown file.
---

# Weekly Summary Skill

This skill automates the generation of a developer-focused weekly summary for the `RConsortium/pharma_skills` repository.

## Steps

1. **Research Recent Activity**
   - Run the following command to retrieve structured data for the last 7 days:
     ```bash
     python3 _automation/weekly-summary/scripts/get_weekly_data.py
     ```
   - Use the JSON output to identify the number of commits, open/closed issues, and merged/open PRs.

2. **Generate Summary**
   - Write a developer-focused summary under 150 words in Slack mrkdwn format.
   - Use the following structure:
     *📊 pharma_skills — week of [DATE]*
     • *Commits:* [count + one-line highlight]
     • *PRs:* [merged/open count + key change or discussion]
     • *Issues:* [opened/closed count + notable item]
     • *TL;DR:* [1-2 sentences on overall momentum and what to watch next week]
   - Skip any section with no activity.
   - Be direct and terse.

3. **Slack Output**
   - Post the summary to Slack channel **C0AR7L8GR5Z** using the `slack_send_message` tool.

4. **File Output**
   - Save the summary as a markdown file: `/sessions/[session-dir]/mnt/outputs/pharma-skills-weekly-summary-[YYYY-MM-DD].md`.
   - Present the file using the `present_files` tool.
