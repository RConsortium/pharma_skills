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
