# Clinical Trial Simulation Skill

An agent skill for designing and simulating clinical trials using the
[TrialSimulator](https://github.com/zhangh12/TrialSimulator) R package.
The skill walks a biostatistician through the design in plain language,
assembles a TrialSimulator script from building blocks, runs it, and
produces a QC-ready report that pairs each block of code with rationale,
parameters, and operating characteristics.

## What it does

- Listens to the user's brief (exploration mode) or maps a structured
  spec (implementation mode) to TrialSimulator's building blocks
  (`endpoint`, `arm`, `trial`, `milestone`, `listener`, `controller`,
  `regimen`).
- Asks plain-language questions to fill in argument values, in the
  package's standard build order, and confirms a parameter table and
  a save plan before writing any code.
- Generates a runnable R script split by purpose (`main.R`,
  `actions.R`, `generators.R`, `helpers.R`, `boundaries.R`) inside a
  per-trial output folder.
- Validates iteratively (sanity → calibration → production) and runs
  the simulation single-process by default; uses parallelism only
  when runtime warrants it.
- Writes a build-order-spine report — Markdown plus rendered HTML —
  with one bundled section per arm, full action-function bodies
  shown verbatim, operating characteristics mapped back to the
  user's research questions, and caveats inline.

## Scope

The skill is design-agnostic by construction: TrialSimulator
decouples a trial into a small set of independent building blocks
(endpoints, arms, the trial object, milestones, listeners,
controllers, regimens), and any trial design — fixed, adaptive,
seamless, platform, anything in between — is a particular
composition of those blocks. The skill teaches the agent to compose
them, not to follow a fixed catalog of recognized designs. If the
user can describe a design in clinical terms, the agent can usually
build it from the blocks.

## Requirements

- **R** ≥ 4.1
- **R packages** (CRAN unless noted):
  - [TrialSimulator](https://github.com/zhangh12/TrialSimulator)
    (the simulation engine; install from GitHub for the latest)
  - `survival`
  - `rpact` *or* `gsDesign` (for group-sequential boundary
    computation; either is fine)
  - `markdown` (for rendering the report to HTML)
  - `simdata` (only if NORTA correlated endpoints are used)
  - `DoseFinding` (only if MCPMod-style dose ranging is used)
- **Agent** capable of executing the
  [Agent Skills Specification](https://github.com/anthropics/skills)
  (Claude Code, or any compatible agent).

## How to use

### Claude Code

A slash command is bundled at `.claude/commands/simulate.md`. From a
session inside this repo:

```
/simulate
```

The agent loads `SKILL.md` and the cached references in
`references/` and starts the conversation.

### Other agents

Point your agent at `SKILL.md` as the entry document. It declares
the skill's `name` and `description` in YAML frontmatter and sources
the rest of the skill (`references/building_blocks.md`,
`references/helpers.md`, `references/report.md`).

## Output layout per simulation run

```
runs/<trial_name>/
  scripts/
    main.R          building blocks + listener + controller + run
    actions.R       action functions (if any)
    generators.R    custom generators (if any)
    helpers.R       helpers used by generators / actions (if any)
    boundaries.R    external boundary computation via rpact / gsDesign (if any)
  output.rds        saved per-replicate output
  report.md         Markdown report
  report.html       rendered with markdown::mark_html
  milestone_times.png
```

## Status

Pre-release; under active development. The skill is being iterated
against test simulations and feedback from the package author. See
the commit history for changes.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and pull requests welcome. The skill aims to be a thinking
framework, not a prescriptive script — contributions that simplify
the agent's path or correct package-specific behavior are especially
valued.
