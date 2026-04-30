import subprocess
import sys
from pathlib import Path
from unittest import TestCase


BASE_DIR = Path(__file__).resolve().parent


class MainScriptTests(TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(BASE_DIR / "main.py"), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_script_accepts_firstname_and_lastname(self):
        result = self.run_script("Leia", "Organa")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "Leia\nOrgana\n")

    def test_script_handles_missing_arguments_without_crashing(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage: python main.py <firstname> <lastname>", result.stdout)
