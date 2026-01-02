#!/usr/bin/env python3
"""
run_local.py

Cross-platform (Windows-focused) replacement for scripts/run_local.ps1
- stops processes listening on given ports
- creates logs and .azurite directories
- optionally runs setup_venv.ps1
- opens new PowerShell windows to run Azurite, Azure Functions (func start) and Streamlit

Usage:
  python scripts/run_local.py [--skip-install] [--ports 7071 8501 10000]

Note: this script is intended to be run on Windows where PowerShell and Azure Functions Core Tools are available.
"""
from __future__ import annotations
import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_dirs(repo_root: Path):
    logs = repo_root / "logs"
    azurite = repo_root / ".azurite"
    logs.mkdir(parents=True, exist_ok=True)
    azurite.mkdir(parents=True, exist_ok=True)
    return logs, azurite


def find_pids_on_port_windows(port: int) -> list[int]:
    # Uses netstat -ano and parses lines with LISTENING and the port
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
        # Unix: use lsof
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
    # Use cmd start to open new window with PowerShell
    # Compose powershell command to run
    ps_command = f"$host.UI.RawUI.WindowTitle = '{title}'; Set-Location -LiteralPath '{working_directory}'; {command}"
    if os.name == 'nt':
        cmd = ["cmd.exe", "/c", "start", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", ps_command]
        subprocess.Popen(cmd)
    else:
        # On non-Windows just spawn a shell in background
        subprocess.Popen(["/bin/sh", "-c", command], cwd=str(working_directory))


def available_executable(name: str) -> bool:
    return shutil.which(name) is not None


def main():
    repo_root = get_repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ports", nargs="*", type=int, default=[7071, 8501, 3000, 10000, 10001, 10002])
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()

    logs_dir, azurite_location = ensure_dirs(repo_root)
    azurite_debug_log = logs_dir / "azurite-debug.log"
    func_log = logs_dir / f"func-{subprocess.check_output(['powershell','-NoProfile','-Command','(Get-Date).ToString(\"yyyyMMdd-HHmmss\")'], text=True).strip()}.log"

    print("Stopping processes on ports:", args.ports)
    stop_processes_on_ports(args.ports)

    if not args.skip_install:
        setup_script = repo_root / 'scripts' / 'setup_venv.ps1'
        if setup_script.exists():
            print("Running setup_venv.ps1...")
            try:
                subprocess.check_call(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(setup_script)])
            except subprocess.CalledProcessError:
                print("setup_venv.ps1 failed (continue if venv already exists)")

    venv_path = repo_root / '.venv'
    activate = venv_path / 'Scripts' / 'Activate.ps1'
    if not activate.exists():
        print("Venv not found. Run: powershell -ExecutionPolicy Bypass -File scripts/setup_venv.ps1")



    # Prepare commands
    azurite_cmd = None
    if available_executable('azurite'):
        azurite_cmd = f"azurite --location '{azurite_location}' --debug '{azurite_debug_log}'"
    elif available_executable('npx'):
        azurite_cmd = f"npx --yes azurite --location '{azurite_location}' --debug '{azurite_debug_log}'"
    else:
        azurite_cmd = "Write-Host 'Azurite not found. Install it (npm i -g azurite) or ensure npx is available.'; exit 1"

    func_command = f"& '{activate}'; if (-not (Get-Command func -ErrorAction SilentlyContinue)) {{ throw 'Azure Functions Core Tools (`func`) not found. Install it, then re-run.' }}; func start --verbose 2>&1 | Tee-Object -FilePath '{func_log}' -Append"

    # Start windows
    print("Starting Azurite window...")
    start_powershell_window('Azurite', azurite_cmd, repo_root)

    functions_root = repo_root / 'OmniFlowCentral'
    if not functions_root.exists():
        print("Azure Functions directory not found at OmniFlowCentral/. Ensure the directory exists before running this helper.")
    print("Starting Azure Functions window...")
    start_powershell_window('Azure Functions (func start)', func_command, functions_root)

    print("Started:")
    print(f"  - Azurite (debug): {azurite_debug_log}")
    print(f"  - Functions log:   {func_log}")


if __name__ == '__main__':
    main()
