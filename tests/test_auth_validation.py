import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "frontend"


def run_validation(form):
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "-e",
            "import { validate } from './src/auth-validation.ts'; console.log(JSON.stringify(validate(JSON.parse(process.argv[1]))));",
            json.dumps(form),
        ],
        cwd=FRONTEND,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class AuthValidationTests(unittest.TestCase):
    def test_empty_fields_are_silent_during_live_validation(self):
        result = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                "-e",
                "import { passwordError, usernameError } from './src/auth-validation.ts'; console.log(JSON.stringify([usernameError(''), passwordError('')]));",
            ],
            cwd=FRONTEND,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(result.stdout), ["", ""])

    def test_empty_credentials_fail_submit_validation(self):
        self.assertEqual(run_validation({"username": "", "password": ""}), {
            "errors": {
                "username": "At least 3 characters",
                "password": "At least 8 characters",
            },
            "valid": False,
        })


    def test_valid_credentials_pass_submit_validation(self):
        self.assertEqual(run_validation({"username": "table_player", "password": "correct-horse"}), {
            "errors": {"username": "", "password": ""},
            "valid": True,
        })
