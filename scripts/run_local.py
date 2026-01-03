#!/usr/bin/env python3
"""
run_local.py (OmniFlowCentralRepo / App2)

Double-click friendly Windows helper:
- ensures Python 3.11 venv exists at .venv (recreates if wrong version)
- installs OmniFlowCentral/requirements.txt into that venv
- writes a .pth into venv site-packages so `import OmniFlowCentral.shared.*` works for local Functions host
- stops processes on common ports
- starts Azurite and `func start` in separate PowerShell windows

Usage (optional):
  python scripts/run_local.py [--skip-install] [--ports 7071 10000 10001 10002]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_dirs(repo_root: Path) -> tuple[Path, Path]:
    logs = repo_root / "logs"
    azurite = repo_root / ".azurite"
    logs.mkdir(parents=True, exist_ok=True)
    azurite.mkdir(parents=True, exist_ok=True)
    return logs, azurite


def find_pids_on_port_windows(port: int) -> list[int]:
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    pids: set[int] = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto = parts[0]
        local = parts[1]
        state = parts[3]
        pid = parts[-1]
        if proto.lower().startswith("tcp") and state.upper() == "LISTENING":
            if local.endswith(f":{port}") or local.endswith(f".{port}"):
                try:
                    pids.add(int(pid))
                except Exception:
                    continue
    return list(pids)


def kill_pid_windows(pid: int) -> None:
    try:
        subprocess.check_call(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Stopped PID {pid}")
    except subprocess.CalledProcessError:
        print(f"Failed to stop PID {pid}")


def stop_processes_on_ports(ports: list[int]) -> None:
    if os.name != "nt":
        return
    for port in ports:
        for pid in find_pids_on_port_windows(port):
            kill_pid_windows(pid)


def _venv_python(venv_path: Path) -> Path:
    return venv_path / "Scripts" / "python.exe"


def _find_site_packages_dir(venv_path: Path) -> Path | None:
    candidate = venv_path / "Lib" / "site-packages"
    if candidate.exists():
        return candidate
    lib_root = venv_path / "lib"
    if not lib_root.exists():
        return None
    for python_dir in sorted(lib_root.glob("python*")):
        sp = python_dir / "site-packages"
        if sp.exists():
            return sp
    return None


def ensure_python311_venv(repo_root: Path, *, skip_install: bool) -> Path:
    venv_path = repo_root / ".venv"
    python_exe = _venv_python(venv_path)

    def current_venv_is_311() -> bool:
        if not python_exe.exists():
            return False
        try:
            out = subprocess.check_output(
                [str(python_exe), "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
                text=True,
            ).strip()
            return out == "3.11"
        except Exception:
            return False

    if not current_venv_is_311():
        if venv_path.exists():
            print("Removing existing .venv (wrong/missing Python)...")
            shutil.rmtree(venv_path, ignore_errors=True)

        if os.name != "nt":
            raise SystemExit("This helper is Windows-focused; create the venv manually on non-Windows.")

        if shutil.which("py") is None:
            raise SystemExit('Python launcher "py" not found; install Python 3.11 and ensure "py" is available.')

        print("Creating .venv with Python 3.11...")
        subprocess.check_call(["py", "-3.11", "-m", "venv", str(venv_path)])
        python_exe = _venv_python(venv_path)

    if not skip_install:
        requirements = repo_root / "OmniFlowCentral" / "requirements.txt"
        if not requirements.exists():
            raise SystemExit(f"Missing requirements.txt: {requirements}")
        print("Installing dependencies into .venv...")
        subprocess.check_call([str(python_exe), "-m", "pip", "install", "-r", str(requirements)])

    return venv_path


def ensure_repo_on_sys_path(venv_path: Path, repo_root: Path) -> None:
    """Make repo_root importable in local Functions worker via a .pth file."""
    site_packages = _find_site_packages_dir(venv_path)
    if site_packages is None:
        raise SystemExit(f"Cannot locate venv site-packages under: {venv_path}")
    pth = site_packages / "omniflowcentralrepo.pth"
    pth.write_text(str(repo_root), encoding="utf-8")
    print(f"Wrote import path file: {pth}")


def start_powershell_window(title: str, command: str, working_directory: Path) -> None:
    ps_command = f"$host.UI.RawUI.WindowTitle = '{title}'; Set-Location -LiteralPath '{working_directory}'; {command}"
    cmd = ["cmd.exe", "/c", "start", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", ps_command]
    subprocess.Popen(cmd)


def available_executable(name: str) -> bool:
    return shutil.which(name) is not None


def verify_paths(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise SystemExit(f"Required path missing: {path}")


def main() -> None:
    repo_root = get_repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ports", nargs="*", type=int, default=[7071, 10000, 10001, 10002])
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()

    verify_paths([repo_root, repo_root / "OmniFlowCentral"])
    logs_dir, azurite_location = ensure_dirs(repo_root)

    print("Stopping processes on ports:", args.ports)
    stop_processes_on_ports(args.ports)

    venv_path = ensure_python311_venv(repo_root, skip_install=args.skip_install)
    ensure_repo_on_sys_path(venv_path, repo_root)

    activate = venv_path / "Scripts" / "Activate.ps1"
    if not activate.exists():
        raise SystemExit(f"Venv activation script missing: {activate}")

    azurite_debug_log = logs_dir / "azurite-debug.log"
    timestamp = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", "(Get-Date).ToString(\"yyyyMMdd-HHmmss\")"],
        text=True,
    ).strip()
    func_log = logs_dir / f"func-{timestamp}.log"

    if available_executable("azurite"):
        azurite_cmd = f"azurite --location '{azurite_location}' --debug '{azurite_debug_log}'"
    elif available_executable("npx"):
        azurite_cmd = f"npx --yes azurite --location '{azurite_location}' --debug '{azurite_debug_log}'"
    else:
        azurite_cmd = "Write-Host 'Azurite not found. Install it (npm i -g azurite) or ensure npx is available.'; exit 1"

    app2_path = repo_root / "OmniFlowCentral"
    shared_path = app2_path / "shared"
    verify_paths([app2_path, shared_path])

    # Belt-and-suspenders: set PYTHONPATH too (the .pth should already solve it).
    py_path_value = ";".join(str(p) for p in [repo_root, app2_path, shared_path])
    func_command = (
        f"$env:PYTHONPATH='{py_path_value}'; "
        f"& '{activate}'; "
        "if (-not (Get-Command func -ErrorAction SilentlyContinue)) { "
        "throw 'Azure Functions Core Tools (`func`) not found. Install it, then re-run.' }; "
        "Write-Host ('PYTHONPATH=' + $env:PYTHONPATH); "
        f"func start --verbose 2>&1 | Tee-Object -FilePath '{func_log}' -Append"
    )

    print("Starting Azurite window...")
    start_powershell_window("Azurite", azurite_cmd, repo_root)

    print("Starting Azure Functions window...")
    start_powershell_window("Azure Functions (func start)", func_command, app2_path)

    print("Started:")
    print(f"  - Azurite (debug): {azurite_debug_log}")
    print(f"  - Functions log:   {func_log}")


if __name__ == "__main__":
    main()
