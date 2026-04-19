---
name: weekly-summary
description: Generate a concise weekly progress summary for the pharma_skills repository. Use this to summarize recent commits, PRs, and issues, then post the update to Slack and save it as a markdown file.
---

# Weekly Summary Skill

This skill automates the generation of a developer-focused weekly summary for the `RConsortium/pharma_skills` repository.

## Configuration

Before running, read `_automation/weekly-summary/config.json` to load:
- `max_words` — word limit for the summary (default 150)
- `slack_channel` — Slack channel ID to post to (overridden by `PHARMA_SKILLS_SLACK_CHANNEL` env var)
- `lookback_days` — how many days of activity to include (default 7)

If `PHARMA_SKILLS_SLACK_CHANNEL` is set in the environment, it takes precedence over `config.json`.
If neither is set, **stop and report an error** — do not guess a channel ID.

## Steps

1. **Research Recent Activity**
   - Run the following command to retrieve structured data for the configured lookback period:
     ```bash
     python3 _automation/weekly-summary/scripts/get_weekly_data.py
     ```
   - Use the JSON output to identify the number of commits, open/closed issues, and merged/open PRs.

2. **Generate Summary**
   - Write a developer-focused summary under `max_words` words (from config) in Slack mrkdwn format.
   - Use the following structure:
     *📊 pharma_skills — week of [DATE]*
     • *Commits:* [count + one-line highlight]
     • *PRs:* [merged/open count + key change or discussion]
     • *Issues:* [opened/closed count + notable item]
     • *TL;DR:* [1-2 sentences on overall momentum and what to watch next week]
   - Skip any section with no activity.
   - Be direct and terse.

3. **Slack Output**
   - Read the Slack channel from the environment variable `PHARMA_SKILLS_SLACK_CHANNEL`, falling back to `slack_channel` in `config.json`.
   - Post the summary using the `slack_send_message` tool.

4. **File Output**
   - Save the summary as a markdown file: `/sessions/[session-dir]/mnt/outputs/pharma-skills-weekly-summary-[YYYY-MM-DD].md`.
   - Present the file using the `present_files` tool.
