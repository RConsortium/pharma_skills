"""
Unit tests for _automation/issue-to-eval/scripts/import_issue_eval.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "issue-to-eval" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import import_issue_eval as ite  # noqa: E402

# Golden fixture: exact text produced by the benchmark issue template
GOLDEN_BODY = """## Skills
group-sequential-design

## Query
Design a Phase 3 trial for OS in 1L NSCLC.

## Expected Output
A gsd_design.R file using gsSurv() with N <= 450.

## Attached Files / Input Context (Optional)


## Rubric Criteria (Assertions)
- gsd_design.R exists and calls gsSurv()
- gsd_results.json exists and total_N < 450
"""


class TestParseIssueMarkdown(unittest.TestCase):
    def test_parses_skill_name(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertEqual(parsed["skill_name"], "group-sequential-design")

    def test_parses_prompt(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertIn("Phase 3", parsed["prompt"])

    def test_parses_expected_output(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertIn("gsSurv", parsed["expected_output"])

    def test_parses_empty_files_section(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertEqual(parsed["files"], [])

    def test_parses_assertions(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertEqual(len(parsed["assertions"]), 2)
        self.assertIn("gsd_design.R exists and calls gsSurv()", parsed["assertions"])

    def test_skill_name_lowercased_and_hyphenated(self):
        body = GOLDEN_BODY.replace("group-sequential-design", "Group Sequential Design")
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed["skill_name"], "group-sequential-design")

    def test_parses_empty_header(self):
        body = GOLDEN_BODY.replace("Design a Phase 3 trial for OS in 1L NSCLC.", "")
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed["prompt"], "")
        self.assertEqual(parsed["expected_output"], "A gsd_design.R file using gsSurv() with N <= 450.")

    def test_parses_empty_section_without_capturing_next(self):
        body = """## Skills
group-sequential-design

## Query

## Expected Output
Expected output content.

## Rubric Criteria (Assertions)
- assertion 1
"""
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed.get("prompt", ""), "")
        self.assertEqual(parsed.get("expected_output", ""), "Expected output content.")

    def test_warns_on_missing_assertions(self):
        body = GOLDEN_BODY.replace("## Rubric Criteria (Assertions)\n- gsd_design.R exists and calls gsSurv()\n- gsd_results.json exists and total_N < 450\n", "## Rubric Criteria (Assertions)\n\n")
        import io
        with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
            ite.parse_issue_markdown(body)
            self.assertIn("WARNING", mock_err.getvalue())

    def test_warns_on_missing_header(self):
        body = "## Skills\ngroup-sequential-design\n\n## Query\nSome prompt\n"
        import io
        with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
            ite.parse_issue_markdown(body)
            output = mock_err.getvalue()
        # Expected Output, files, and assertions are missing — should warn
        self.assertIn("WARNING", output)


class TestSaveToEvals(unittest.TestCase):
    def _write_evals(self, tmpdir, evals_list):
        evals_dir = Path(tmpdir) / "my-skill" / "evals"
        evals_dir.mkdir(parents=True)
        path = evals_dir / "evals.json"
        path.write_text(json.dumps({"skill_name": "my-skill", "evals": evals_list}))
        return path

    def test_adds_new_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_evals(tmpdir, [])
            entry = {"id": "github-issue-1", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["a"]}
            with patch("import_issue_eval.os.getcwd", return_value=tmpdir):
                orig = Path.cwd
                Path.cwd = lambda: Path(tmpdir)  # type: ignore
                # Patch os.path.join to use tmpdir as base
                import os
                orig_join = os.path.join
                def patched_join(*args):
                    if args and args[0] == "my-skill":
                        return orig_join(tmpdir, *args)
                    return orig_join(*args)
                with patch("import_issue_eval.os.path.join", side_effect=patched_join):
                    with patch("import_issue_eval.os.makedirs"):
                        evals_file = Path(tmpdir) / "my-skill" / "evals" / "evals.json"
                        with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps({"skill_name": "my-skill", "evals": []}))):
                            pass  # just verify it runs — full integration tested below

    def test_add_and_skip_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_evals(tmpdir, [])

            import os
            orig_join = os.path.join

            def patched_join(*args):
                if args and args[0] == "my-skill":
                    return orig_join(tmpdir, *args)
                return orig_join(*args)

            with patch("import_issue_eval.os.path.join", side_effect=patched_join), \
                 patch("import_issue_eval.os.makedirs"):
                entry = {"id": "github-issue-1", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["a"]}
                status = ite.save_to_evals(entry, "my-skill")
                self.assertIn("Added", status)

                # Re-read and confirm
                data = json.loads(path.read_text())
                self.assertEqual(len(data["evals"]), 1)

                # Same content → skip
                status2 = ite.save_to_evals(entry, "my-skill")
                self.assertIn("up to date", status2)

                # Changed content → update
                updated = {**entry, "prompt": "new prompt"}
                status3 = ite.save_to_evals(updated, "my-skill")
                self.assertIn("Updated", status3)

    def test_unknown_skill_returns_error(self):
        result = ite.save_to_evals({"id": "x"}, "")
        self.assertIn("Error", result)


if __name__ == "__main__":
    unittest.main()
