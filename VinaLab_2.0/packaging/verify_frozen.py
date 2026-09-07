"""Run both frozen exit modes and require complete JSON service evidence."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

REQUIRED_STEPS = {"conversion", "reference", "vina", "vinardo", "xtb_gfn2", "xtb_gfnff"}


def verify(executable, report_directory, *, runner=subprocess.run):
    executable, report_directory = Path(executable).resolve(), Path(report_directory).resolve()
    report_directory.mkdir(parents=True, exist_ok=True)
    reports = []
    for flag, output_flag, timeout in (
        ("--check-runtime", "--runtime-check-output", 120),
        ("--smoke-test", "--smoke-test-output", 1200),
    ):
        report = report_directory / f"{flag.lstrip('-')}-{uuid4()}.json"
        with TemporaryDirectory(prefix="vinalab-qa-cwd-") as directory:
            result = runner(
                [str(executable), flag, output_flag, str(report)], cwd=directory,
                timeout=timeout, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        if result.returncode != 0:
            raise RuntimeError(f"{flag} exited {result.returncode}; report: {report}")
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("ok") is not True:
            raise RuntimeError(f"{flag} report failed: {report}")
        if flag == "--smoke-test":
            steps = data.get("steps", [])
            if (len(steps) != len(REQUIRED_STEPS)
                    or {step.get("name") for step in steps} != REQUIRED_STEPS
                    or any(step.get("ok") is not True for step in steps)):
                raise RuntimeError(f"Service evidence incomplete or failed: {report}")
        reports.append(report)
    return tuple(reports)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--report-directory", default="artifacts", type=Path)
    args = parser.parse_args()
    for report in verify(args.executable, args.report_directory):
        print(f"Frozen QA passed: {report}")
