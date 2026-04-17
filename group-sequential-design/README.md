# Group Sequential Design Skill for Claude Code

A [Claude Code](https://claude.ai/code) skill that designs group sequential clinical trials for survival endpoints (OS, PFS, DFS). It collects trial parameters through a structured conversation, computes boundaries and sample sizes in R, verifies designs via simulation, and delivers a complete Word report — all within a single session.

## Video Demo

https://drive.google.com/file/d/1O9-SCJEoXGJv6J3YXuZZ1eiVB4Jk6Gao/view

## What It Does

Given a clinical trial scenario, this skill:

1. **Collects inputs** — Walks through 16 design questions (disease, endpoints, hazard ratios, enrollment, alpha spending, multiplicity strategy, etc.) one at a time
2. **Computes the design** — Writes and executes an R script using `gsDesign`/`gsSurv()` with the N-first approach: fix enrollment from a feasibility range, then derive events, timing, and power
3. **Handles multiplicity** — Builds a graphical testing strategy (Maurer-Bretz) with alpha recycling, step-down or alpha-split across populations and endpoints
4. **Checks timing constraints** — Validates IA/FA timing against minimum follow-up, minimum gap, and enrollment duration; warns and offers fixes if violated
5. **Evaluates NPH** — Optionally assesses power under non-proportional hazards (delayed effect, diminishing effect) using `gsDesign2` and `lrstat`
6. **Verifies via simulation** — Runs `lrstat::lrsim()` to confirm power (within +/-2pp), type I error (within +/-0.5pp), events (within +/-5%), and timing (within +/-1 month)
7. **Generates a Word report** — Produces a template-driven `.docx` with boundary tables, enrollment projections, sensitivity analyses, and verification results — zero hardcoded values

## Supported Design Patterns

**Endpoints:** OS, PFS, DFS, or any time-to-event endpoint

**Populations:** Single population, or nested subgroups (2-3 levels)

**Multiplicity strategies:**
- Alpha splitting with bidirectional recycling
- Fixed-sequence (gatekeeping) testing
- Step-down across populations
- Full graphical multiplicity (Maurer-Bretz) for any number of hypotheses

**Analysis structures:**
- Single-look, or 1-3 interim analyses per endpoint
- Cross-endpoint triggers (one endpoint's events drive another's analysis timing)
- Mixed: some endpoints tested once, others tested at multiple looks

**Hazard assumptions:**
- Proportional hazards (primary design basis)
- Non-proportional hazards evaluation (delayed effect, diminishing effect) as sensitivity analysis

## Output Structure

Each design produces a complete output folder:

```
output/gsd_{disease}_{endpoints}_{YYYYMMDD}/
├── gsd_design.R              # R design script (boundaries, events, timing)
├── gsd_results.json           # All results as structured JSON (drives the report)
├── multiplicity_diagram.png   # Graphical testing diagram (Maurer-Bretz)
├── gsd_verification.R         # lrstat simulation script
├── gsd_verification_log.md    # Pass/fail verification results
├── gsd_report.py              # Python report generator (reads from JSON)
└── gsd_report.docx            # Final Word report
```

## Requirements

### R (>= 4.0)
- [`gsDesign`](https://cran.r-project.org/package=gsDesign) — group sequential boundaries and sample size
- [`gsDesign2`](https://cran.r-project.org/package=gsDesign2) — non-proportional hazards (AHR, analytical power)
- [`lrstat`](https://cran.r-project.org/package=lrstat) — log-rank simulation for verification
- [`graphicalMCP`](https://cran.r-project.org/package=graphicalMCP) — multiplicity diagrams
- [`jsonlite`](https://cran.r-project.org/package=jsonlite) — JSON I/O

### Python (>= 3.8)
- [`python-docx`](https://pypi.org/project/python-docx/) — Word report generation

## Installation

1. Copy the `group-sequential-design/` folder into your project's `.claude/skills/` directory:
   ```
   your-project/
   └── .claude/
       └── skills/
           └── group-sequential-design/
               ├── SKILL.md
               ├── reference.md
               ├── examples.md
               ├── post_design.md
               ├── scripts/
               │   ├── compute_event_prob.R
               │   └── gsd_report_template.py
               └── evals/
                   └── evals.json
   ```

2. Install the required R packages:
   ```r
   install.packages(c("gsDesign", "gsDesign2", "lrstat", "graphicalMCP", "jsonlite"))
   ```

3. Install the required Python package:
   ```bash
   pip install python-docx
   ```

4. Set the Rscript path in your project's `CLAUDE.md`:
   ```markdown
   **Rscript path**: /path/to/Rscript
   ```

## Usage

Invoke the skill in Claude Code by either:

- Typing `/group-sequential-design`
- Describing a trial design task naturally, e.g.:

> "Design a Phase 3 trial for first-line metastatic NSCLC with co-primary PFS and OS, 1:1 randomization, target HR 0.70 for OS"

The skill will guide you through the remaining parameters interactively.

## Skill File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `SKILL.md` | 575 | Main entry point — Q&A workflow, 11-step design process, decision rules |
| `reference.md` | 1088 | Design guidance, parameter tables, spending functions, alpha recycling rules, failure modes, N-first algorithm |
| `examples.md` | 1753 | R code examples organized by design pattern |
| `post_design.md` | 169 | IA timing checks, verification simulation procedure, pass/fail criteria |
| `scripts/compute_event_prob.R` | — | Event probability computation helper |
| `scripts/gsd_report_template.py` | — | Template-driven Word report generator |
| `evals/evals.json` | — | Evaluation scenarios for testing skill correctness |

Files are read lazily during execution — only loaded when the workflow reaches the corresponding step.

## Key Design Principles

- **N-first approach**: Sample size (N) is a top-level parameter determined from feasibility, not derived by the optimizer. All timing, events, and power flow from fixed enrollment.
- **Event-driven timing**: IA/FA calendar times are determined by when target events accrue, with minimum follow-up and minimum gap as lower-bound constraints.
- **Simulation-verified**: Every design must pass `lrstat::lrsim()` verification before delivery.
- **Zero hardcoded reports**: The Word report reads every value from `gsd_results.json` — no numbers are typed into the report template.

## License

[MIT](LICENSE)
