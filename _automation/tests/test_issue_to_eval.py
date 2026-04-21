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

## Language (Optional)
R

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
        self.assertEqual(parsed["target_skills"], ["group-sequential-design"])

    def test_parses_multiple_target_skills(self):
        body = GOLDEN_BODY.replace(
            "group-sequential-design",
            "Group Sequential Design, survival-analysis\n- dose-finding"
        )
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(
            parsed["target_skills"],
            ["group-sequential-design", "survival-analysis", "dose-finding"],
        )
        self.assertEqual(parsed["skill_name"], "group-sequential-design")

    def test_parses_language(self):
        parsed = ite.parse_issue_markdown(GOLDEN_BODY)
        self.assertEqual(parsed["language"], "R")

    def test_language_is_optional(self):
        # Body with no language signals (no .R, .py, etc)
        body = """## Skills
some-skill

## Query
Some query.

## Expected Output
Some output.

## Rubric Criteria (Assertions)
- some assertion
"""
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed.get("language", ""), "")

    def test_language_heuristic_detects_r(self):
        # Remove Language header but keep .R signal
        body = GOLDEN_BODY.replace("## Language (Optional)\nR\n\n", "")
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed.get("language"), "R")

    def test_language_heuristic_detects_python(self):
        body = """## Skills
some-skill

## Query
Some query.

## Expected Output
A script in python.

## Rubric Criteria (Assertions)
- gsd_results.json exists
"""
        parsed = ite.parse_issue_markdown(body)
        self.assertEqual(parsed.get("language"), "Python")

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

    def test_assertions_keep_commas(self):
        body = GOLDEN_BODY.replace(
            "- gsd_results.json exists and total_N < 450",
            "- power is 90%, alpha is 0.025, and N < 450",
        )
        parsed = ite.parse_issue_markdown(body)
        self.assertIn("power is 90%, alpha is 0.025, and N < 450", parsed["assertions"])

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

## Language

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
    def _write_eval(self, tmpdir, eval_id, eval_dict):
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir(parents=True, exist_ok=True)
        path = evals_dir / f"{eval_id}.json"
        path.write_text(json.dumps(eval_dict))
        return path

    def test_adds_new_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = {"id": "github-issue-1", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["a"], "language": "R"}
            
            import os
            orig_join = os.path.join
            def patched_join(*args):
                if len(args) >= 2 and args[0] == "_automation" and args[1] == "evals":
                    return orig_join(tmpdir, *args)
                return orig_join(*args)
                
            with patch("import_issue_eval.os.path.join", side_effect=patched_join):
                status = ite.save_to_evals(entry, "my-skill")
                self.assertIn("Success", status)
                
                # Verify file was created
                path = Path(tmpdir) / "_automation" / "evals" / "github-issue-1.json"
                self.assertTrue(path.exists())
                data = json.loads(path.read_text())
                self.assertEqual(data["target_skills"], ["my-skill"])
                self.assertEqual(data["language"], "R")

    def test_adds_multiple_target_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = {"id": "github-issue-1", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["a"]}

            import os
            orig_join = os.path.join
            def patched_join(*args):
                if len(args) >= 2 and args[0] == "_automation" and args[1] == "evals":
                    return orig_join(tmpdir, *args)
                return orig_join(*args)

            with patch("import_issue_eval.os.path.join", side_effect=patched_join):
                status = ite.save_to_evals(entry, ["my-skill", "other_skill"])
                self.assertIn("Success", status)
                path = Path(tmpdir) / "_automation" / "evals" / "github-issue-1.json"
                data = json.loads(path.read_text())
                self.assertEqual(data["target_skills"], ["my-skill", "other-skill"])

    def test_add_and_skip_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_join = os.path.join
            def patched_join(*args):
                if len(args) >= 2 and args[0] == "_automation" and args[1] == "evals":
                    return orig_join(tmpdir, *args)
                return orig_join(*args)

            with patch("import_issue_eval.os.path.join", side_effect=patched_join):
                entry = {"id": "github-issue-1", "prompt": "p", "expected_output": "e", "files": [], "assertions": ["a"]}
                
                # First save should add
                status = ite.save_to_evals(entry, "my-skill")
                self.assertIn("Added", status)

                path = Path(tmpdir) / "_automation" / "evals" / "github-issue-1.json"
                
                # Same content → skip
                status2 = ite.save_to_evals(entry, "my-skill")
                self.assertIn("up to date", status2)

                # Changed content → update
                updated = {**entry, "prompt": "new prompt"}
                status3 = ite.save_to_evals(updated, "my-skill")
                self.assertIn("Updated", status3)

                # Changed language → update
                status4 = ite.save_to_evals({**updated, "language": "R"}, "my-skill")
                self.assertIn("Updated", status4)

    def test_unknown_skill_returns_error(self):
        result = ite.save_to_evals({"id": "x"}, "")
        self.assertIn("Error", result)


if __name__ == "__main__":
    unittest.main()
