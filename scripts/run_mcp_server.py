from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_path() -> None:
    root = Path(__file__).resolve().parents[1]
    package_root = root / "OmniFlowCentral"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))


def main() -> None:
    _bootstrap_path()
    from OmniFlowCentral.mcp_app.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
