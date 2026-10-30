# Packaging and releasing

How the desktop editor is built, signed and released. For setup and tests see [development.md](development.md).

## Building

Standalone builds use [PyInstaller](https://pyinstaller.org/) 6 from `softchord.spec`. The version is `__version__` in `src/softchord_version.py`, the one place it is set; the spec, the app and the CI build read it (`python build_softChord.py --version` prints it).

GitHub Actions (`.github/workflows/build.yml`) builds Apple Silicon and Intel macOS `.dmg`s plus a Windows `.zip` and `.exe` when a `v*` tag is pushed, or on demand via **Actions → Build → Run workflow** (leave *release_tag* empty to only build; the files are on the run page under *Artifacts*). A tag must be `v` plus the version in `softchord_version.py`. If the tag has no GitHub release yet, the workflow creates a draft one with `docs/release_notes/<tag>.md` as its notes.

You can also build locally. Build **on the OS you want to ship** (a Mac cannot produce the Windows `.exe`, and vice versa).

```bash
./build_softChord.py
packaging/macos/sign_and_package.sh "$(./build_softChord.py --version)" arm64   # optional: the DMG
```

On Windows:

```bat
python build_softChord.py
```

The helper uses `.venv`, installs `requirements.txt` and `requirements-build.txt`, then runs PyInstaller. Equivalent manual steps:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean softchord.spec
```

| Platform | Local output | CI release asset |
|---|---|---|
| macOS (Apple Silicon) | `dist/softChord.app` | `softChord-<version>-macos-arm64.dmg` |
| macOS (Intel) | `dist/softChord.app` | `softChord-<version>-macos-x86_64.dmg` |
| Windows | `dist/softChord.exe` | `softChord-<version>-windows.zip` (exe + `How to open softChord on Windows.txt`) and `softChord-<version>-windows.exe` |

## File associations

`.songbook` files are associated with the app:

- **macOS:** the bundle `Info.plist` declares the type so Finder can open `.songbook` files with softChord.
- **Windows:** the frozen exe registers the extension for the current user on launch (no installer or admin rights). Double-clicking a `.songbook` then starts this copy of `softChord.exe`.

## Signing

**macOS.** `packaging/macos/sign_and_package.sh` signs the app with the hardened runtime (`packaging/macos/entitlements.plist`), builds the DMG (the app plus an Applications link), signs it, notarizes it with `notarytool` and staples the ticket, when these repository secrets are set:

| Secret | Value |
|---|---|
| `MACOS_CERT_P12` | base64 of a `.p12` holding the *Developer ID Application* certificate and its private key |
| `MACOS_CERT_PASSWORD` | the `.p12` password |
| `APPLE_ID` | the Apple ID email used for notarization |
| `APPLE_APP_PASSWORD` | an app-specific password for that Apple ID |
| `APPLE_TEAM_ID` | `BP4KJ52H3T` |

`tools/setup_mac_signing_secrets.sh` sets all five from a Mac that has the certificate in its login keychain (or pass a `.p12` you exported from Keychain Access). It checks the Apple ID and app-specific password with `notarytool` before storing them; `--notary-only` updates just the three Apple values (for example after a notarization 401 in the build, then `gh run rerun --failed <run id>`). Without the secrets the build still succeeds with a warning: the app keeps PyInstaller's ad-hoc signature and the DMG is not notarized, so macOS asks the user to allow it under **System Settings → Privacy & Security → Open Anyway**.

**Windows.** The `.exe` is unsigned, so SmartScreen shows *Windows protected your PC* (**More info → Run anyway**); `packaging/windows/How to open softChord on Windows.txt` ships next to the exe in the zip. An Authenticode certificate would remove the warning.

## Making a release

1. Write `docs/release_notes/v<version>.md` (copy the previous one) and commit it.
2. Run `tools/release.sh <version>` (for example `tools/release.sh 1.2`). It checks that master matches GitHub and the build files are committed, sets the version in `src/softchord_version.py` and commits it, pushes master, creates the draft release with the notes and pushes the tag. The tag starts the build, which attaches the files to the draft.
3. When the run is green, check the assets and publish the draft on GitHub.

The Mac jobs wait up to 10 minutes for Apple. If notarization is still running then (a first submission can take hours), the signed DMG is attached anyway with a `NAME.dmg.notarization-pending` file holding the submission ID, and the build only warns. Once Apple accepts it, run **Actions → Staple → Run workflow** with the tag, or `tools/release.sh --staple <version>` on a Mac with the `softchord-notary` notarytool profile. It staples the DMG, re-uploads it and removes the pending file. Publish after that.

Do not commit `build/` or `dist/` (they are gitignored).
