---
name: github_issue_benchmark_converter
description: Converts a GitHub Issue describing a task, problem, or feature into a standardized benchmark data entry in JSON format mapping perfectly to agentskills.io schemas. Use when a user needs to curate benchmark data or parse an issue into an eval.
---

A skill to automatically extract benchmark data from a GitHub Issue and format it as an Agent Skills compliant evaluation JSON.

### Task Flow

1. **Verify the Input Format**:
   Examine the provided text, URL, or JSON content from the target GitHub Issue. Look for the expected markdown headers: `## Skills`, `## Query`, `## Expected Output`, `## Attached Files / Input Context`, and `## Rubric Criteria (Assertions)`.

2. **Extract Fields**:
   Parse the text to extract the values for each section:
   - **skill_name**: Extracted from under `## Skills`.
   - **prompt**: Extracted from under `## Query`.
   - **expected_output**: Extracted from under `## Expected Output`.
   - **files**: An array of strings extracted from under `## Attached Files / Input Context (Optional)`. (If none or left empty, make it an empty array `[]`).
   - **assertions**: An array of testable strings extracted from under `## Rubric Criteria (Assertions)`. Remove formatting bullets (like `- `) and capture the raw string assertions.
   
3. **Format as JSON**:
   Construct a JSON object matching the `agentskills.io` eval schema. DO NOT include any other keys in the schema.

   ```json
   {
     "skill_name": "<extracted skill name>",
     "evals": [
       {
         "id": "<generate a unique id or use the github issue number if presented, e.g. github-issue-45>",
         "prompt": "<extracted prompt>",
         "expected_output": "<extracted expected output>",
         "files": [
           "<extracted files array>"
         ],
         "assertions": [
           "<extracted assertions array>"
         ]
       }
     ]
   }
   ```

4. **Save the JSON to the Target Skill's Eval Folder**:
   Do NOT simply output the JSON into the chat. You must save it directly into the target skill's benchmark directory.
   - Identify the `skill_name` that was extracted.
   - Target the directory: `./[skill_name]/evals/`. Create the `evals/` folder if it does not already exist.
   - If an `evals.json` file already exists inside this folder, securely append the new eval object into the existing `"evals": []` array. Ensure the JSON syntax remains valid after appending.
   - If `evals.json` does not exist, create a new file and write the full JSON payload.
   - Once saved, inform the user that the evaluation case was successfully added to `<skill_name>/evals/evals.json`.
- If files are mentioned by name but no path is given, extract just the filenames. If a URL to a file is given, include the URL.
