"""The softChord desktop version. The one place to change it.

softchord.spec (macOS Info.plist), the app (QApplication version) and the
GitHub Actions build (asset names, tag check) all read this file.
tools/release.sh VERSION rewrites it.
"""

__version__ = "1.1"
