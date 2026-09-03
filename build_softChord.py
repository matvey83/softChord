#!/usr/bin/env python3
"""
Build a standalone softChord app with PyInstaller.

macOS:   dist/softChord.app
Windows: dist/softChord.exe

Usage:
    ./build_softChord.py
    python build_softChord.py
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_DIR = PROJECT_ROOT / ".venv"

if sys.platform == "win32":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP = VENV_DIR / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP = VENV_DIR / "bin" / "pip"

REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
BUILD_REQUIREMENTS_FILE = PROJECT_ROOT / "requirements-build.txt"
SPEC_FILE = PROJECT_ROOT / "softchord.spec"


def is_running_in_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except Exception:
        return False


def ensure_venv():
    if not VENV_PYTHON.exists():
        print("Creating virtual environment at", VENV_DIR)
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])


def pip_install(requirements: Path):
    if not requirements.exists():
        return
    print("Installing", requirements.name)
    subprocess.check_call(
        [str(VENV_PIP), "install", "-r", str(requirements)])


def main():
    if not is_running_in_venv():
        ensure_venv()
        if not VENV_PYTHON.exists():
            print("ERROR: Could not find venv python.", file=sys.stderr)
            sys.exit(1)
        os.execv(str(VENV_PYTHON),
                 [str(VENV_PYTHON), str(__file__)] + sys.argv[1:])

    pip_install(REQUIREMENTS_FILE)
    pip_install(BUILD_REQUIREMENTS_FILE)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)

    if sys.platform == "darwin":
        artifact = PROJECT_ROOT / "dist" / "softChord.app"
    elif sys.platform == "win32":
        artifact = PROJECT_ROOT / "dist" / "softChord.exe"
    else:
        artifact = PROJECT_ROOT / "dist" / "softChord"

    if not artifact.exists():
        print("ERROR: Expected build output missing:", artifact, file=sys.stderr)
        sys.exit(1)

    print("Built", artifact)


if __name__ == "__main__":
    main()
