## 1. Create a codespace from Github 
open https://github.com/codespaces and create a codespace under main from pharma-skills

![alt text](image/image.png)

Then you will see clouds-based VS code. While selecting 2 core, you can use 60 hours per month.

Select the main branch. As you have notified that a folder of .devcontainer/ is created. This pre-build the environment with R and required R packages. This will help save the session time from Claude Code.

We previously experience a hard time in Claude Code in Claude.ai for routine, where it didnt perform as expected (not starting up, installation failed, etc.)

## 2. Download Claude Code onto this machine

Find Terminal and run below
```
curl -fsSL https://claude.ai/install.sh | bash
```
## 3. login to Github Through CLI; This will ensure you can push your automated report to Github Issues

```
unset GITHUB_TOKEN
gh auth login
```
Login using token or authorization 

## 4. Start Claude Code using dangerous mode. 

Note that we are in the sandbox mode and can utilize this mode to enable agent to do most of things, so that we don't confirm manually 

```
claude --dangerously-skip-permissions
```
Then login your claude account


## Prompt 

```
Read the skill instructions from the file at the path below, then execute them exactly:
File: ./_automation/benchmark-runner-codespaces/SKILL.md

```

Your task is, by reading "./_automation/benchmark-runner-codespaces/SKILL.md", complete the task, and find corresponding delayed process of installating R environment, and parallel agent A and B tasks. Known issues including too many replicated turns in each tasks, and also always recognize old github issues instead of new github issues. Please propose solutions under this structure after you complete. I might expect this whole flow to be completed within 30 minutes. If you  experience longer, please stop, help digest and propose improvment
