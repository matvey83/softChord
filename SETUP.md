# softChord Development Setup

This document describes how to set up a development environment for softChord using a standard Python virtual environment (recommended approach).

## Prerequisites

- Python 3.10 or newer (3.11+ recommended)
- Git (optional, for cloning)

## 1. Clone the Repository (optional)

```bash
git clone <repository-url>
cd softChord
```

## 2. Create a Virtual Environment

From the project root:

```bash
python3 -m venv .venv
```

## 3. Activate the Virtual Environment

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

You should see `(.venv)` at the beginning of your prompt.

## 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install PyQt6 (which bundles the necessary Qt6 libraries).

## 5. Run the Application

```bash
cd src
python3 softchord.py
```

## 6. Running Tests

Before running tests, the project convention is to first list the test files:

```bash
find . -name "*test*.py" -o -name "test_*.py" | grep -v __pycache__ | sort
```

Then run the tests from the `src` directory:

```bash
cd src

# Run unit tests
python3 test_song.py

# Run integration tests
python3 softchord_test.py
```

## Notes

- A standard Python virtual environment provides a much more stable development experience.
- `.venv` is included in `.gitignore`.
- PyQt6 includes its own Qt6 libraries — no separate Qt installation is required.

## Updating Dependencies

If you modify `requirements.txt`, reinstall with:

```bash
pip install -r requirements.txt
```

To regenerate the requirements file after installing new packages:

```bash
pip freeze > requirements.txt
```
