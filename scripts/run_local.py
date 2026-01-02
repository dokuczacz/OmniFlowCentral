#!/usr/bin/env python3
"""
run_local.py for OmniFlowCentral

Starts the Azure Functions host for the `OmniFlowCentral` function app in a new
PowerShell window, captures logs, waits for the health endpoint, and can run
integration tests writing output to a log file.

Usage:
  python scripts/run_local.py [--ports 7071] [--run-tests]

This script is Windows-focused but will try to be tolerant on other platforms.
"""
from __future__ import annotations
import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
import time


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_dirs(repo_root: Path):
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def find_pids_on_port_windows(port: int) -> list[int]:
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            proto = parts[0]
            local = parts[1]
            state = parts[3] if len(parts) >= 4 else ""
            pid = parts[-1]
            if proto.lower().startswith("tcp") and state.upper() == "LISTENING":
                if local.endswith(f":{port}") or local.endswith(f".{port}"):
                    try:
                        pids.add(int(pid))
                    except Exception:
                        continue
    return list(pids)


def kill_pid_windows(pid: int):
    try:
        subprocess.check_call(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Stopped PID {pid}")
    except subprocess.CalledProcessError:
        print(f"Failed to stop PID {pid}")


def stop_processes_on_ports(ports: list[int]):
    if os.name == 'nt':
        for port in ports:
            pids = find_pids_on_port_windows(port)
            if not pids:
                continue
            for pid in pids:
                kill_pid_windows(pid)
    else:
        # non-Windows fallback: try lsof
        for port in ports:
            try:
                out = subprocess.check_output(["lsof", "-i", f":{port}", "-t"], text=True)
                for line in out.splitlines():
                    try:
                        pid = int(line.strip())
                        os.kill(pid, 9)
                        print(f"Stopped PID {pid} on port {port}")
                    except Exception:
                        pass
            except Exception:
                pass


def start_powershell_window(title: str, command: str, working_directory: Path):
    ps_command = f"$host.UI.RawUI.WindowTitle = '{title}'; Set-Location -LiteralPath '{working_directory}'; {command}"
    if os.name == 'nt':
        cmd = ["cmd.exe", "/c", "start", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", ps_command]
        subprocess.Popen(cmd)
    else:
        # non-Windows: spawn in background
        subprocess.Popen(command, cwd=str(working_directory), shell=True)


def find_activate_candidates(repo_root: Path):
    candidates = [
        repo_root / '.venv' / 'Scripts' / 'Activate.ps1',
        repo_root / 'OmniFlowCentral' / '.venv' / 'Scripts' / 'Activate.ps1',
        repo_root / '..' / '.venv' / 'Scripts' / 'Activate.ps1',
    ]
    return [str(p) for p in candidates if p.exists()]


def wait_for_health(url: str, timeout: int = 60) -> bool:
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    repo_root = get_repo_root()
    # Recommend Python 3.11 for Azure Functions runtime compatibility
    if sys.version_info[:2] != (3, 11):
        print(f"Warning: running with Python {sys.version_info.major}.{sys.version_info.minor}. Recommended: Python 3.11.")
        print("Proceeding, but consider creating a 3.11 venv (use `py -3.11 -m venv .venv`) and re-run.")
    parser = argparse.ArgumentParser()
    parser.add_argument('--ports', nargs='*', type=int, default=[7071])
    parser.add_argument('--run-tests', action='store_true')
    parser.add_argument('--port', type=int, default=7071)
    args = parser.parse_args()

    logs_dir = ensure_dirs(repo_root)
    func_log = logs_dir / f"omniflowcentral-func-{int(time.time())}.log"
    tests_log = logs_dir / 'tests-integration.log'

    print("Stopping processes on ports:", args.ports)
    stop_processes_on_ports(args.ports)

    # Determine activate script if present
    activates = find_activate_candidates(repo_root)
    if activates:
        activate = activates[0]
        print(f"Found venv activate: {activate}")
        activate_fragment = f"& '{activate}'; "
    else:
        activate_fragment = ""
        print("No venv Activate.ps1 found; continuing without activating venv.")

    # Build func command that tees output to log file
    func_command = f"{activate_fragment} if (-not (Get-Command func -ErrorAction SilentlyContinue)) {{ Write-Error 'Azure Functions Core Tools (func) not found on PATH.'; exit 2 }}; func start --port {args.port} --verbose 2>&1 | Tee-Object -FilePath '{func_log}' -Append"

    functions_dir = repo_root / 'OmniFlowCentral'
    if not functions_dir.exists():
        print(f"Functions app folder not found: {functions_dir}")
        sys.exit(2)

    print("Starting Azure Functions in a new PowerShell window...")
    start_powershell_window('OmniFlowCentral - func start', func_command, functions_dir)

    if args.run_tests:
        print("Waiting for health endpoint before running tests...")
        base = f"http://localhost:{args.port}"
        healthy = wait_for_health(f"{base}/api/health", timeout=60)
        if not healthy:
            print("Health check failed; aborting tests. Check function logs.")
            sys.exit(3)

        print("Running integration tests (this process). Output ->", tests_log)
        env = os.environ.copy()
        env['OMNIFLOWCENTRAL_BASE_URL'] = base
        # run pytest and write output to file
        with open(tests_log, 'w', encoding='utf-8') as fh:
            proc = subprocess.Popen([sys.executable, '-m', 'pytest', 'tests/integration', '-q'], cwd=str(repo_root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                print(line, end='')
                fh.write(line)
            proc.wait()
            if proc.returncode != 0:
                print(f"Integration tests failed (exit {proc.returncode}). See {tests_log}")
                sys.exit(proc.returncode)
            print("Integration tests passed")

    print(f"Started Functions host. Logs are in: {func_log}")


if __name__ == '__main__':
    main()
