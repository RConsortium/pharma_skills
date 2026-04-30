# GSDBench intake app

GSDBench Intake is a static web application for collecting one group sequential design benchmark example per submission from statisticians. It helps contributors prepare a GitHub issue title and GitHub-flavored Markdown issue body with both human-readable sections and a machine-readable JSON block.

The app does not submit to GitHub. It makes no GitHub API calls, stores no secrets, and sends no telemetry. Drafts are saved only in the browser's `localStorage`.

## Open locally

Open `gsdbench-intake/index.html` directly in a browser. No server, build step, package manager, or backend is required.

Use **Load synthetic example** to populate a clearly fake Phase 3 PFS/OS group sequential design example and verify the generated issue output.

## Contributor workflow

1. Complete the intake form for one benchmark example.
2. Resolve validation warnings in the generated issue panel.
3. Copy the generated issue title.
4. Copy the generated issue body.
5. Paste both into a new GitHub issue in the benchmark repository.

Do not submit PHI, patient-level data, confidential protocol text, trade secrets, or proprietary company information. Generalize or de-identify examples before public sharing.

## Maintainer parsing

The generated issue body begins with a JSON object between extraction markers:

````markdown
<!-- GSDBENCH_CASE_JSON_BEGIN -->
```json
{ "...": "..." }
```
<!-- GSDBENCH_CASE_JSON_END -->
````

Automation can extract the content between `GSDBENCH_CASE_JSON_BEGIN` and `GSDBENCH_CASE_JSON_END`, strip the Markdown code fence, and parse the result as JSON. The schema version is currently `gsdbench.case.v0.1`.

## GitHub Pages deployment

The repository includes `.github/workflows/deploy-pages.yml`, which uses the official GitHub Pages actions and uploads the repository root as a static artifact. There is no build step.

To deploy:

1. Enable GitHub Pages for the repository and select **GitHub Actions** as the source.
2. Push to `main` or run the workflow manually.
3. Open the deployed URL and navigate to `/gsdbench-intake/`.

## Implementation notes

The implementation is vanilla HTML, CSS, and JavaScript because GitHub Pages has no backend and all validation, rendering, autosave, dynamic rows, copy actions, and Markdown generation are client-side.
