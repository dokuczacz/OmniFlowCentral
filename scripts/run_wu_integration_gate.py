from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def _run_command(command: list[str], timeout_seconds: float) -> None:
    print(f"\n$ {' '.join(command)}")
    started = time.monotonic()
    completed = subprocess.run(command, check=False, timeout=timeout_seconds)
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode} after {elapsed:.2f}s: {' '.join(command)}"
        )
    print(f"OK ({elapsed:.2f}s)")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run post-WU integration gate checks.")
    parser.add_argument(
        "--golden-timeout",
        type=float,
        default=30.0,
        help="Timeout for WP2 MCP golden suite in seconds.",
    )
    parser.add_argument(
        "--pytest-timeout",
        type=float,
        default=120.0,
        help="Timeout for targeted pytest command in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    python_bin = sys.executable

    print("== WU Integration Gate start ==")
    _run_command(
        [
            python_bin,
            str(repo_root / "scripts" / "wp2_mcp_golden_suite.py"),
            "--timeout-seconds",
            str(args.golden_timeout),
        ],
        timeout_seconds=args.golden_timeout + 5,
    )
    _run_command(
        [
            python_bin,
            "-m",
            "pytest",
            str(repo_root / "tests" / "unit" / "test_tools_call.py"),
            str(repo_root / "tests" / "unit" / "test_query_dataset_lookup.py"),
            str(repo_root / "tests" / "unit" / "test_mcp_contract_search_fetch.py"),
            "-q",
        ],
        timeout_seconds=args.pytest_timeout,
    )
    print("== WU Integration Gate: SUCCESS ==")


if __name__ == "__main__":
    main()
