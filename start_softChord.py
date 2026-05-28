#!/usr/bin/env python3
"""
start_softChord.py

Convenience launcher for softChord.

- Ensures a Python virtual environment (.venv) exists and is activated.
- Installs dependencies from requirements.txt if needed.
- Runs src/softchord.py, forwarding any arguments (e.g., a songbook file).

Usage:
    python3 start_softChord.py
    python3 start_softChord.py zvuki_neba.songbook
    ./start_softChord.py path/to/songbook.songbook
"""

import os
import sys
import subprocess
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_ROOT / ".venv"

if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP = VENV_DIR / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP = VENV_DIR / "bin" / "pip"

REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
MAIN_SCRIPT = PROJECT_ROOT / "src" / "softchord.py"


def print_header(msg: str):
    print(f"\n=== {msg} ===")


def venv_exists() -> bool:
    return VENV_PYTHON.exists()


def create_venv():
    print_header("Creating virtual environment")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    print(f"Virtual environment created at {VENV_DIR}")


def install_requirements():
    if not REQUIREMENTS_FILE.exists():
        print("No requirements.txt found — skipping dependency installation.")
        return

    print_header("Installing dependencies")
    cmd = [str(VENV_PIP), "install", "-r", str(REQUIREMENTS_FILE)]
    subprocess.check_call(cmd)
    print("Dependencies installed successfully.")


def ensure_venv_and_deps():
    """Create venv if missing and install requirements if needed."""
    if not venv_exists():
        create_venv()

    # Check if PyQt6 is available in the venv
    try:
        subprocess.check_call(
            [str(VENV_PYTHON), "-c", "import PyQt6"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        install_requirements()


def is_running_in_venv() -> bool:
    """Return True if the current Python is the one from our .venv."""
    try:
        return VENV_PYTHON.resolve() == Path(sys.executable).resolve()
    except Exception:
        return False


def main():
    # If we're not already running inside the project venv, re-launch ourselves
    # using the venv's Python interpreter. This ensures PyQt6 is available.
    if not is_running_in_venv():
        ensure_venv_and_deps()

        if not VENV_PYTHON.exists():
            print("ERROR: Could not find venv python after setup.", file=sys.stderr)
            sys.exit(1)

        # Re-execute this script using the venv python
        cmd = [str(VENV_PYTHON), str(__file__)] + sys.argv[1:]
        os.execv(str(VENV_PYTHON), cmd)

    # --- We are now running inside the correct venv ---

    # Final safety check
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("ERROR: PyQt6 is still not available even after venv setup.", file=sys.stderr)
        print("Please try running the following manually:", file=sys.stderr)
        print("    source .venv/bin/activate", file=sys.stderr)
        print("    pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    # Build the command to run the real application
    cmd = [sys.executable, str(MAIN_SCRIPT)] + sys.argv[1:]

    print(f"Launching softChord with: {' '.join(map(str, cmd))}")
    os.execv(sys.executable, cmd)


if __name__ == "__main__":
    main()
