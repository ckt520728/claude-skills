#!/usr/bin/env python3
"""Audit an HHSA closed-loop prototype without requiring project imports."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


REQUIRED_PATHS = (
    "hhsa/emd.py",
    "hhsa/holo.py",
    "hhsa/instantaneous.py",
    "closedloop/controller.py",
    "closedloop/phase.py",
    "closedloop/supervisor.py",
    "closedloop/stimulator.py",
    "closedloop/hardware.py",
    "tests",
    "validate_ground_truth.py",
)


def run_stage(name: str, command: list[str], root: Path, timeout: int) -> dict:
    started = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "name": name,
            "status": "pass" if result.returncode == 0 else "fail",
            "returncode": result.returncode,
            "seconds": round(time.perf_counter() - started, 3),
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "status": "timeout",
            "returncode": None,
            "seconds": round(time.perf_counter() - started, 3),
            "command": command,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", type=Path)
    parser.add_argument(
        "--profile",
        choices=("static", "core", "full"),
        default="core",
        help="static checks files; core adds ground truth and tests; full adds the quick demo",
    )
    parser.add_argument("--timeout", type=int, default=180, help="seconds per command")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    missing = [item for item in REQUIRED_PATHS if not (root / item).exists()]
    report = {
        "project": str(root),
        "profile": args.profile,
        "python": sys.version.split()[0],
        "static": {"status": "pass" if not missing else "fail", "missing": missing},
        "stages": [],
        "notes": [],
    }

    if missing:
        report["notes"].append("Core project paths are missing; command stages were skipped.")
    elif args.profile != "static":
        report["stages"].append(
            run_stage(
                "synthetic ground truth",
                [sys.executable, "validate_ground_truth.py", "--no-plot"],
                root,
                args.timeout,
            )
        )
        report["stages"].append(
            run_stage(
                "pytest",
                [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
                root,
                args.timeout,
            )
        )
        if args.profile == "full":
            report["notes"].append(
                "The quick demonstration may rewrite closed_loop_demo.png; inspect git status."
            )
            report["stages"].append(
                run_stage(
                    "quick closed-loop demonstration",
                    [sys.executable, "demo_closed_loop.py", "--quick"],
                    root,
                    args.timeout,
                )
            )

    failed = report["static"]["status"] != "pass" or any(
        stage["status"] != "pass" for stage in report["stages"]
    )
    report["status"] = "fail" if failed else "pass"

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_output:
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
