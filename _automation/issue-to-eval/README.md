# GitHub Issue to Benchmark Converter

A skill to effortlessly translate structured GitHub issues into `agentskills.io` compliant benchmark evaluation JSON.

## Motivation

To support autonomous AI agent iteration, tests must be reliably quantified. By capturing benchmark data directly in GitHub issues alongside bugs or feature requests, teams can build up rigorous test suites organically over time. This skill automates the chore of extracting testing logic into machine-readable JSON formats so AI agents can jump straight to running `evals` and iterating on their performance.

## Usage

When a new issue is logged following the standard benchmark template, you can simply ask the LLM:

> "Curate this github issue into an eval: <paste text or link>"

This skill will trigger and intelligently extract the necessary components (`target_skills`, optional `language`, `prompt`, `expected_output`, `files`, `assertions`) and construct the JSON spec expected by standard benchmark graders.

## Example

**User**: 
> "Parse this issue text into a benchmark:
> \## Skills 
> group-sequential-design
> \## Language
> R
> \## Query 
> Please output an interim bounds analysis..."

**Agent**: 
> "Here is the extracted evaluation data:"
> \`\`\`json
> {
>   "target_skills": ["group-sequential-design"],
>   "language": "R",
>   "evals": [ ... ]
> }
> \`\`\`
