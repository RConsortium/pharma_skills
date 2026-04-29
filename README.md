# Pharma Skills

A collection of agent skills for pharmaceutical R&D.

## Skills

| Skill | Description |
|-------|-------------|
| [group-sequential-design](group-sequential-design/) | Design group sequential clinical trials for survival endpoints (OS, PFS, DFS) with interim analyses, spending functions, multiplicity, and event/enrollment prediction |
| [clinical-trial-simulation](clinical-trial-simulation/) | Design and simulate clinical trials using the TrialSimulator R package and produce a QC-ready build-order-spine report. Design-agnostic: composes from independent building blocks (endpoints, arms, milestones, regimens) rather than following a fixed catalog of design templates. |

## Usage

**Option 1: Conversational / CLI**
Ask your agent to directly enable a skill from this repo:
> enable "group-sequential-design" skill from https://github.com/RConsortium/pharma_skills

**Option 2: Local IDE (Cursor, Windsurf, Copilot, etc.)**
1. Clone this repository locally or as a git submodule.
2. Symlink the skill you want into your project, or manually reference it in your configuration files (like `.cursorrules` or `llms.txt`):
   `Please refer to /path/to/pharma_skills/group-sequential-design/SKILL.md for the trial design workflow.`

## Contributing

### New Skills 

Contributions of new skills are welcome. Each skill should:

1. Live in its own folder at the repo root
2. Include a `SKILL.md` with frontmatter (`name`, `description`) and instructions
3. Include a `README.md` describing what the skill does, requirements, and usage
4. Include an MIT `LICENSE`
5. Follow the [Agent Skill Development Lifecycle](LIFECYCLE.md)

### New Benchmark data 

You can add new benchmark data by creating new github issues following the `benchmark` templates.

### Evaluate Benchmark data 

If you're interested in contributing to the skill evaluation using your Claude Code account, following this [video](https://github.com/user-attachments/assets/05d24707-36b8-49fc-86ea-beb6365e288e) to set it up.

## License

All skills in this repository are required to be licensed under the MIT License to ensure maximum permissiveness and rapid adoption within pharmaceutical research.


## Join Us

This effort is the part B of R consortium Submissions Working Group [Pilot 7](https://github.com/RConsortium/submissions-pilot7-synthetic-data). The pilot 7 aims at developing modern, realistic synthetic clinical trial benchmark datasets and test cases to evaluate open-source clinical data science tools and pharma AI “skills,” starting with group sequential design.

Pilot 7 holds weekly standups three times a month on Fridays from 8–9 AM PST. We also host monthly Submissions Working Group meetings with FDA staff, bringing together participants across different pilot subgroups.

[Pilot 7 Meeting minutes](https://github.com/RConsortium/submissions-pilot7-synthetic-data/wiki/Meeting-Minutes)

Everyone is welcome to join. To access our calendar and join the Slack workspace, please see 
[here](https://rconsortium.github.io/submissions-wg/join.html)

To learn more about the R consortium Submissions Working Group, visit [here](https://rconsortium.github.io/submissions-wg/)
