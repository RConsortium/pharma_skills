# GSDBench Intake Guide

This document describes the standard mechanism for contributing benchmark case
proposals to **GSDBench**, the group sequential design benchmark used by the
community-authored research paper on AI agent skills for clinical trial design.

The main charter defines the authorship, recognition, and incentive model.
This document focuses on the practical intake workflow: how contributors prepare
benchmark cases, what information is required, and how maintainers can parse and
review submissions.

## Purpose

GSDBench evaluates AI agents on realistic group sequential design tasks,
especially survival endpoint designs relevant to late-stage pharmaceutical
development.

To build a high-quality benchmark dataset, contributors need a consistent way to
submit cases that are:

- Realistic enough to represent actual statistical design work.
- Structured enough for scientific review.
- Machine-readable enough for downstream benchmark construction.
- Safe for public sharing.
- Detailed enough to support reproducible scoring.

[GSDBench Intake](https://rconsortium.github.io/pharma-skills/gsdbench-intake/)
is the standard preparation mechanism for these submissions.

## What the intake app does

GSDBench Intake is a static web application that helps contributors prepare one
benchmark case proposal at a time.

The app generates:

1.  A GitHub issue title.
2.  A GitHub-flavored Markdown issue body.
3.  Human-readable benchmark sections.
4.  A machine-readable JSON block for downstream parsing.
5.  Optional downloadable Markdown and JSON output.

The app does **not** submit anything to GitHub directly. It makes no GitHub API
calls, stores no secrets, sends no telemetry, and requires no backend.

Drafts are saved only in the contributor's browser through `localStorage`.

## Standard contributor workflow

The expected workflow is:

1.  Open the GSDBench Intake app.
2.  Complete the intake form for one benchmark case.
3.  Resolve validation warnings shown in the generated issue panel.
4.  Copy the generated GitHub issue title.
5.  Copy the generated GitHub issue body.
6.  Paste both into a new GitHub issue in the benchmark repository.
7.  Respond to maintainer review comments as needed.
8.  Once accepted, the issue will be tagged `accepted-benchmark`.

The accepted GitHub issue is the canonical benchmark record. The intake app is
the standard preparation tool, but acceptance is determined through maintainer
review.

## AI-assisted form filling from a draft case

Some contributors may first draft a benchmark case in free-text form, including
cases drafted with help from an AI assistant. This is an acceptable workflow,
provided the final GitHub issue still passes through the GSDBench Intake
structure and the contributor verifies the content before submission.

In practice, a contributor can:

1.  Draft the benchmark case locally in Markdown or plain text.
2.  Before sharing any draft with an AI coding agent or browser-capable
    assistant, redact or sanitize confidential, proprietary, and
    patient-identifiable information; for non-public information, prefer a
    local or on-device agent where feasible. Then ask the agent to open the
    GSDBench Intake app.
3.  Use agentic browser automation (such as
    [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp),
    [Codex browser use](https://developers.openai.com/codex/app/browser),
    [Claude Code Chrome integration](https://code.claude.com/docs/en/chrome))
    to fill the intake form based on the sanitized draft.
4.  Conduct human review of all populated fields.
5.  Resolve validation warnings (if any).
6.  Copy the generated issue title and body into a GitHub issue.

This workflow can reduce manual data entry while conforming to the structured
intake format. The contributor remains responsible for confirming scientific
accuracy, public-sharing safety, rubric quality, and the absence of confidential
or patient-identifiable information.

AI-assisted drafting or form filling does not replace maintainer review.
The accepted GitHub issue remains the authoritative benchmark case record.

## One benchmark case per issue

Each GitHub issue should describe exactly one benchmark case.

A case may involve a complex trial design scenario, but it should correspond to
a single AI agent task with a single prompt, one coherent expected output, and
one set of associated rubrics.

Closely related variants should be submitted as separate issues only when they
test meaningfully different design features, assumptions, edge cases, or known
AI failure modes.

## Validation rules

The intake app validates structure before allowing the generated issue to be
copied or downloaded. Validation confirms that the submission is structurally
complete. It does not guarantee scientific validity or acceptance.

The app includes a synthetic example that contributors can load to inspect the
expected level of detail and verify that the generated issue output is valid.

Maintainers may still request revisions, reject cases, merge duplicates, adjust
tags, or ask for stronger reference truth and rubric criteria.

## Public sharing and confidentiality

All benchmark submissions are intended to become public GitHub issues.

Do not submit:

- PHI.
- Patient-level data.
- Confidential protocol text.
- Proprietary company information.
- Trade secrets.
- Internal decision records.
- Confidential regulatory correspondence.
- Identifiable sponsor, product, site, investigator, or patient information
  unless already public and appropriate to cite.

When adapting from real work, contributors should generalize the design
scenario, alter nonessential details, and ensure that the resulting case is safe
for public release.

Synthetic, literature inspired, and public protocol inspired examples are
strongly encouraged.

## Relationship to authorship credit

Using the intake app does **not** by itself create authorship credit.

Credit toward the community-authored paper is based on accepted benchmark
contributions, substantive review, and/or reported evaluation runs, as defined
in the main charter document.

For benchmark authors, a case contributes toward recognition only after it is
reviewed and tagged as `accepted-benchmark`.
