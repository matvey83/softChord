#!/usr/bin/env python3
"""
Build a standalone softChord app with PyInstaller.

macOS:   dist/softChord.app
Windows: dist/softChord.exe
Linux:   dist/softChord (packaging/linux/package.sh makes the AppImage)

Usage:
    ./build_softChord.py
    python build_softChord.py
    python build_softChord.py --version   # print the version and exit

The version is __version__ in src/softchord_version.py.
"""

import os
import re
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
VERSION_FILE = PROJECT_ROOT / "src" / "softchord_version.py"


def read_version() -> str:
    """Return __version__ from src/softchord_version.py without importing it."""
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"ERROR: no __version__ in {VERSION_FILE}")
    return match.group(1)


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
    if "--version" in sys.argv[1:]:
        print(read_version())
        return

    if not is_running_in_venv():
        ensure_venv()
        if not VENV_PYTHON.exists():
            print("ERROR: Could not find venv python.", file=sys.stderr)
            sys.exit(1)
        # Use subprocess, not os.execv: on Windows execv spawns a child and
        # exits immediately, which makes GitHub Actions think the step is done.
        raise SystemExit(
            subprocess.call(
                [str(VENV_PYTHON), str(__file__)] + sys.argv[1:]))

    pip_install(REQUIREMENTS_FILE)
    pip_install(BUILD_REQUIREMENTS_FILE)

    print("Building softChord", read_version())
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
