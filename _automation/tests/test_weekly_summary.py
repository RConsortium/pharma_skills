"""
Unit tests for _automation/weekly-summary/scripts/get_weekly_data.py
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "weekly-summary" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import get_weekly_data as gwd  # noqa: E402


class TestRunCommand(unittest.TestCase):
    @patch("get_weekly_data.subprocess.run")
    def test_returns_stdout(self, mock_run):
        mock_run.return_value = MagicMock(stdout="hello\n", returncode=0)
        result = gwd.run_command("echo hello")
        self.assertEqual(result, "hello")

    @patch("get_weekly_data.subprocess.run")
    def test_exits_on_failure(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "bad-cmd", stderr="oops")
        with self.assertRaises(SystemExit):
            gwd.run_command("bad-cmd")


class TestLoadConfig(unittest.TestCase):
    def test_returns_defaults_when_no_file(self):
        with patch("get_weekly_data.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            config = gwd.load_config()
        self.assertEqual(config, {})

    def test_reads_config_file(self):
        config_data = {"max_words": 200, "lookback_days": 14, "slack_channel": "C123"}
        with patch("get_weekly_data.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = True
            import io
            with patch("builtins.open", unittest.mock.mock_open(read_data=json.dumps(config_data))):
                config = gwd.load_config()
        self.assertEqual(config["lookback_days"], 14)
        self.assertEqual(config["max_words"], 200)


class TestGetWeeklyData(unittest.TestCase):
    @patch("get_weekly_data.load_config", return_value={"lookback_days": 7})
    @patch("get_weekly_data.run_command")
    def test_structure(self, mock_cmd, _):
        issues = [{"number": 1, "title": "Fix bug", "state": "OPEN", "updatedAt": "2026-04-18T00:00:00Z"}]
        prs = [{"number": 2, "title": "Add feature", "state": "MERGED", "updatedAt": "2026-04-17T00:00:00Z", "mergedAt": "2026-04-17T00:00:00Z"}]

        mock_cmd.side_effect = [
            "abc123 feat: initial commit",  # git log
            json.dumps(issues),              # gh issue list
            json.dumps(prs),                 # gh pr list
        ]

        data = gwd.get_weekly_data()
        self.assertIn("commits", data)
        self.assertIn("issues", data)
        self.assertIn("pull_requests", data)
        self.assertEqual(data["commits"]["total_count"], 1)
        self.assertEqual(data["issues"]["total_updated"], 1)
        self.assertEqual(data["pull_requests"]["list"][0]["merged"], True)

    @patch("get_weekly_data.load_config", return_value={"lookback_days": 14})
    @patch("get_weekly_data.run_command")
    def test_lookback_days_from_config(self, mock_cmd, _):
        mock_cmd.return_value = ""
        mock_cmd.side_effect = ["", "[]", "[]"]
        data = gwd.get_weekly_data()
        # With 14-day lookback, week_starting should be 14 days ago
        from datetime import datetime, timedelta
        expected_start = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        self.assertEqual(data["week_starting"], expected_start)


if __name__ == "__main__":
    unittest.main()
