from __future__ import annotations

import sys
from pathlib import Path

from streamlit.web import cli


def main() -> None:
    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).resolve().parent / "demo.py"),
        "--server.address=0.0.0.0",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.serverAddress=localhost",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(cli.main())
