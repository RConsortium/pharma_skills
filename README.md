# Group Sequential Design Skill

A Claude Code skill for designing group sequential clinical trials for survival endpoints (OS, PFS, DFS) with interim analyses, spending functions, multiplicity, and event/enrollment prediction.

## What It Does

- Collects design inputs through a structured Q&A
- Computes boundaries, events, sample size, and power for single-endpoint, co-primary, and multi-population designs
- Generates multiplicity diagrams (Maurer-Bretz graphical method)
- Verifies designs via `lrstat::lrsim()` simulation
- Produces a formatted Word report

## Supported Design Patterns

| Pattern | Description |
|---------|-------------|
| Single endpoint | OS, PFS, or DFS with group sequential boundaries |
| Co-primary endpoints | PFS + OS with alpha splitting and cross-endpoint triggers |
| Multi-population | Nested subgroups (e.g., biomarker+ and ITT) with step-down or alpha-split |
| Non-proportional hazards | Design under PH, evaluate under NPH |

## Requirements

### R packages
- `gsDesign` -- group sequential boundaries and sample size
- `gsDesign2` -- non-proportional hazards evaluation (AHR, analytical power)
- `lrstat` -- log-rank simulation for verification
- `graphicalMCP` -- multiplicity diagrams
- `jsonlite` -- JSON output

### Python packages
- `python-docx` -- Word report generation

## Installation

1. Copy the `group_sequential_design/` folder into your project's `.claude/skills/` directory
2. Ensure R and Python are installed with the required packages
3. Set the Rscript path in your project's `CLAUDE.md`:
   ```
   **Rscript path**: `/path/to/Rscript`
   ```

## Usage

Invoke with `/group_sequential_design` in Claude Code, or describe a trial design task (e.g., "Design a Phase 3 trial for 1L NSCLC with co-primary PFS and OS").

## Skill Structure

```
group_sequential_design/
├── SKILL.md            # Main skill instructions and Q&A workflow
├── reference.md        # Design guidance, rules, failure modes
├── examples.md         # R code examples by design pattern
├── post_design.md      # IA timing checks and verification procedure
├── README.md           # This file
├── LICENSE
└── references/         # Bundled PDFs and protocol text references
    ├── gsDesign.pdf
    ├── gsDesign2.pdf
    ├── lrstat.pdf
    ├── eventPred.pdf
    ├── gMCPLite.pdf
    ├── gsd-tech-manual-text.txt
    ├── kn048-text.txt
    ├── kn407-text.txt
    ├── kn426-text.txt
    └── kn564-text.txt
```

## Output

Each design produces a subfolder under `output/` containing:
- `gsd_design.R` -- R design script
- `gsd_results.json` -- design results
- `multiplicity_diagram.png` -- graphical testing diagram
- `gsd_verification.R` -- simulation verification script
- `gsd_verification_log.md` -- pass/fail results
- `gsd_report.py` -- Python report generator
- `gsd_report.docx` -- Word report
