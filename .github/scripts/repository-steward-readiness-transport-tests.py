#!/usr/bin/env python3
"""Execute the actual workflow query block with controlled gh/sleep boundaries."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HEAD = "a" * 40
WORKFLOW = ROOT / ".github/workflows/repository-steward-readiness-observer.yml"


def query_block():
    marker = "      - name: Query GitHub-native readiness state\n"
    following = "      - name: Assert report-only decision\n"
    raw = WORKFLOW.read_text()
    if raw.count(marker) != 1 or raw.count(following) != 1:
        raise ValueError("expected unique query and assertion steps")
    section = raw.split(marker, 1)[1].split(following, 1)[0]
    if section.count("        run: |\n") != 1:
        raise ValueError("expected literal query run block")
    lines = section.split("        run: |\n", 1)[1].splitlines()
    if any(line.strip() and not line.startswith("          ") for line in lines):
        raise ValueError("unsupported query run indentation")
    return "\n".join(line[10:] if line.strip() else "" for line in lines) + "\n"


def response(checks="PENDING", head=SOURCE_HEAD, draft=False):
    return {"data": {"repository": {"pullRequest": {
        "number": 156, "state": "OPEN", "isDraft": draft,
        "baseRefName": "main", "headRefName": "fixture", "headRefOid": head,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN" if checks == "SUCCESS" else "UNSTABLE",
        "reviewDecision": None, "statusCheckRollup": {"state": checks},
    }}}}


class TransportRegression(unittest.TestCase):
    def run_case(self, responses, decision, calls, sleeps, *,
                 event="workflow_run", version="v2", failure=False):
        with tempfile.TemporaryDirectory(prefix="steward-transport-") as directory:
            task = Path(directory)
            (task / ".github").mkdir()
            (task / ".github/scripts").symlink_to(ROOT / ".github/scripts",
                                                 target_is_directory=True)
            binary = task / "bin"
            binary.mkdir()
            (task / "responses.json").write_text(json.dumps(responses))
            (binary / "gh").write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import json
                import os
                from pathlib import Path
                import sys
                task = Path(os.environ["TRANSPORT_TASK_DIR"])
                if sys.argv[1:3] != ["api", "graphql"]:
                    sys.exit(91)
                counter = task / "calls"
                index = int(counter.read_text()) if counter.exists() else 0
                counter.write_text(str(index + 1))
                sequence = json.loads((task / "responses.json").read_text())
                if index >= len(sequence):
                    sys.exit(92)
                current = sequence[index]
                if current == "API_ERROR":
                    sys.exit(42)
                print(json.dumps(current))
                """))
            (binary / "sleep").write_text(
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$*" >> "$TRANSPORT_TASK_DIR/sleeps"\n')
            for stub in binary.iterdir():
                stub.chmod(0o755)
            env = dict(os.environ)
            env.update(PATH=str(binary) + os.pathsep + env["PATH"],
                       TRANSPORT_TASK_DIR=str(task), OWNER="controlled", REPO="fixture",
                       PR_NUMBER="156", SOURCE_HEAD=SOURCE_HEAD, READINESS_VERSION=version,
                       GITHUB_EVENT_NAME=event, GITHUB_OUTPUT=str(task / "output"),
                       GITHUB_STEP_SUMMARY=str(task / "summary"))
            result = subprocess.run(["bash", "-c", query_block()], cwd=task, env=env,
                                    text=True, capture_output=True, timeout=10)
            observations = [line for line in result.stdout.splitlines()
                            if line.startswith("OBSERVATION ")]
            output = (task / "output").read_text() if (task / "output").exists() else ""
            requested_sleeps = ((task / "sleeps").read_text().splitlines()
                                if (task / "sleeps").exists() else [])
            self.assertEqual(int((task / "calls").read_text()), calls, result.stderr)
            self.assertEqual(requested_sleeps, ["10"] * sleeps, result.stderr)
            if failure:
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertEqual(len(observations), calls - 1)
                self.assertEqual(output, "")
                self.assertNotIn("READY_FOR_MERGE_CANDIDATE", result.stdout)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(observations), calls)
                self.assertEqual(output, "decision=" + decision + "\n")
                self.assertIn("decision=" + decision + " protocol=" + version +
                              " attempt=" + str(calls - 1), observations[-1])
                if decision != "READY_FOR_MERGE_CANDIDATE":
                    self.assertNotIn("READY_FOR_MERGE_CANDIDATE", result.stdout)
            print("TRANSPORT_CASE name=" + self._testMethodName +
                  " calls=" + str(calls) + " sleeps=" + str(sleeps) +
                  " decision=" + (decision or "API_FAILURE") + " result=PASS")

    def test_pending_then_success(self):
        self.run_case([response(), response("SUCCESS")],
                      "READY_FOR_MERGE_CANDIDATE", 2, 1)

    def test_persistent_pending_budget(self):
        self.run_case([response()] * 7, "NOT_READY_CHECKS", 7, 6)

    def test_head_changed(self):
        self.run_case([response(), response("SUCCESS", head="b" * 40)],
                      "READINESS_UNKNOWN", 2, 1)

    def test_api_error(self):
        self.run_case([response(), "API_ERROR"], None, 2, 1, failure=True)

    def test_missing_field(self):
        incomplete = response("SUCCESS")
        del incomplete["data"]["repository"]["pullRequest"]["reviewDecision"]
        self.run_case([incomplete], "READINESS_UNKNOWN", 1, 0)

    def test_draft(self):
        self.run_case([response(draft=True)], "NOT_READY_DRAFT", 1, 0)

    def test_manual_v2_pending(self):
        self.run_case([response()], "NOT_READY_CHECKS", 1, 0, event="issue_comment")

    def test_automatic_v1_pending(self):
        self.run_case([response()], "NOT_READY_CHECKS", 1, 0, version="v1")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TransportRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun != 8:
        raise SystemExit(1)
    print("TRANSPORT_MATRIX=PASS scope=SYNTHETIC_ACTUAL_WORKFLOW cases=8")
