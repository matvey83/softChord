"""Source scans that fail when new code writes or reads text without UTF-8.

Run with the desktop suite (test_song.py imports this module) or alone:

    cd src && python test_utf8_guards.py

Three scans, each failing with "file:line: what is wrong. Fix: what to do":

- Desktop (src/*.py): text-mode open() and Path.read_text/write_text need
  encoding='utf-8' (or 'utf-8-sig'); subprocess text needs an encoding;
  no non-UTF-8 .encode()/.decode() codecs or Qt Latin-1/local 8-bit
  conversions; QMimeData text flavors are UTF-8 bytes; QTextStream is UTF-8.
- Web (softChord_web/): text Blob/File types, data: URLs and text MIME types
  say charset=utf-8; no btoa/atob/escape on text; pages declare
  <meta charset="utf-8">.
- iPhone (SoftChord/): String/Data conversions use .utf8 only, no lossy or
  guessed encodings, and pasteboard text uses UTF-8 types.

Binary data is the only exemption: binary open() modes, image/*, wasm,
octet-stream and SQLite types are allowed by rule (see BINARY_* below), and
the few known-binary lines are listed in the *_ALLOWLIST tables with the
reason. The negative tests at the end feed bad snippets to every rule.
"""

import ast
import os
import re
import unittest

__all__ = [
    "TestDesktopUtf8Guard",
    "TestWebUtf8Guard",
    "TestIosUtf8Guard",
]

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SRC_DIR)
WEB_DIR = os.path.join(REPO_DIR, "softChord_web")
IOS_DIR = os.path.join(REPO_DIR, "SoftChord")

_UTF8_NAMES = {"utf-8", "utf8", "utf-8-sig", "utf8-sig"}


def _is_utf8_name(name):
    return isinstance(name, str) and \
        name.strip().lower().replace("_", "-") in _UTF8_NAMES


def _finding(path, line, problem, fix):
    rel = os.path.relpath(path, REPO_DIR) if os.path.isabs(path) else path
    return "%s:%d: %s. Fix: %s" % (rel, line, problem, fix)


# ---------------------------------------------------------------------------
# Desktop (Python)
# ---------------------------------------------------------------------------

# (file name, text on the line, why it is not text). Codecs that are not
# UTF-8 are only allowed here.
PYTHON_CODEC_ALLOWLIST = (
    # Binary: random bytes made URL-safe base64, which is ASCII by definition.
    ("softchord_auth.py", 'secrets.token_bytes(32)).decode("ascii")',
     "base64 of random bytes"),
    # Binary: an SVG icon's '#rrggbb' color name patched into its bytes.
    ("softchord_toolbar.py", 'color.name().encode("ascii")',
     "hex color in SVG bytes"),
)

# Qt conversions that are never UTF-8.
_QT_NON_UTF8_CALLS = {"toLatin1", "toLocal8Bit", "fromLatin1",
                      "fromLocal8Bit"}
# Mac clipboard types that are not UTF-8 (Qt fills the first with Latin-1,
# which is what PR #20 works around).
_NON_UTF8_CLIPBOARD_TYPES = ("com.apple.traditional-mac-plain-text",
                             "public.utf16-plain-text",
                             "public.utf16-external-plain-text")
_SUBPROCESS_CALLS = {"run", "check_output", "Popen", "call", "check_call"}


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _kwarg(call, name):
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _arg(call, index, name):
    value = _kwarg(call, name)
    if value is None and len(call.args) > index:
        value = call.args[index]
    return value


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _is_text_mime(name):
    """A clipboard flavor that holds text (images are binary flavors)."""
    name = name.lower()
    if name.startswith("image/"):
        return False
    return (name.startswith("text/") or "json" in name or "xml" in name
            or "plain-text" in name or name.startswith("public.utf8")
            or name in ("public.html", "public.rtf"))


def _encodes_utf8(node):
    """True when node contains a .encode('utf-8') (or encode() default)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                and sub.func.attr == "encode":
            codec = _arg(sub, 0, "encoding")
            if codec is None or _is_utf8_name(_const_str(codec)):
                return True
    return False


def _allowed_codec(filename, line_text):
    base = os.path.basename(filename)
    return any(base == name and snippet in line_text
               for name, snippet, _why in PYTHON_CODEC_ALLOWLIST)


def scan_python_source(source, filename):
    """Findings for one Python file (a list of 'file:line: ...' strings)."""
    tree = ast.parse(source, filename)
    lines = source.splitlines()
    findings = []

    def add(node, problem, fix):
        findings.append(_finding(filename, node.lineno, problem, fix))

    # Module-level string constants, e.g. SOFTCHORD_LYRICS_MIME = "...".
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and _const_str(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = node.value.value

    def mime_name(node):
        text = _const_str(node)
        if text is None and isinstance(node, ast.Name):
            text = constants.get(node.id)
        return text

    def check_encoding(call, what, index, has_text):
        if not has_text:
            return
        encoding = _arg(call, index, "encoding")
        if encoding is None:
            add(call, "%s without an encoding (the default is the locale, "
                "e.g. cp1252 on Windows)" % what,
                "pass encoding='utf-8' (or 'utf-8-sig' for files Windows "
                "apps read)")
        elif not _is_utf8_name(_const_str(encoding)):
            add(call, "%s with an encoding that is not UTF-8" % what,
                "use encoding='utf-8' (or 'utf-8-sig')")

    uses_text_stream = False
    sets_stream_utf8 = "Encoding.Utf8" in source

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = _dotted(func) or ""
        attr = func.attr if isinstance(func, ast.Attribute) else None
        line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

        # open(), io.open(), codecs.open(), os.fdopen(), Path.open(mode).
        mode = None
        is_open = False
        if name in ("open", "io.open", "codecs.open", "os.fdopen"):
            is_open = True
            mode = _arg(node, 1, "mode")
        elif attr == "open" and (
                (node.args and re.fullmatch(r"[rwxabtU+]+",
                                            _const_str(node.args[0]) or ""))
                or _kwarg(node, "mode") is not None):
            # Path(...).open("w"); other .open() calls (QBuffer, urllib
            # openers, webbrowser) take no mode string.
            is_open = True
            mode = _arg(node, 0, "mode")
        if is_open:
            mode_text = "r" if mode is None else _const_str(mode)
            if mode_text is None:
                check_encoding(node, "open() with a mode that is not a "
                               "literal", 3 if name != "codecs.open" else 2,
                               True)
            elif "b" not in mode_text:
                # Binary modes are the only exemption: bytes have no
                # encoding.
                index = 2 if name == "codecs.open" else 3
                if attr == "open" and name not in ("io.open", "codecs.open",
                                                   "os.fdopen"):
                    index = 2  # Path.open(mode, buffering, encoding)
                check_encoding(node, "open(..., %r) in text mode"
                               % mode_text, index, True)

        elif attr == "write_text":
            check_encoding(node, "write_text()", 1, True)
        elif attr == "read_text":
            check_encoding(node, "read_text()", 0, True)

        elif attr in _SUBPROCESS_CALLS and name.startswith("subprocess."):
            text = _kwarg(node, "text") or _kwarg(node, "universal_newlines")
            if isinstance(text, ast.Constant) and text.value:
                check_encoding(node, "subprocess text output", 99, True)

        elif attr in ("encode", "decode"):
            codec = _arg(node, 0, "encoding")
            codec_text = _const_str(codec)
            if codec_text is not None and not _is_utf8_name(codec_text) \
                    and not _allowed_codec(filename, line_text):
                add(node, ".%s(%r) is not UTF-8" % (attr, codec_text),
                    ".%s('utf-8'), or list binary data in "
                    "PYTHON_CODEC_ALLOWLIST with the reason" % attr)

        elif attr in _QT_NON_UTF8_CALLS:
            add(node, "%s() is not UTF-8 (Cyrillic and emoji become '?')"
                % attr, "use toUtf8()/fromUtf8() or str.encode('utf-8')")

        elif attr == "setData" and node.args:
            flavor = mime_name(node.args[0])
            if flavor and "/" not in flavor and "." not in flavor:
                flavor = None  # QStandardItem/QAction.setData, not MIME.
            if flavor and flavor.lower() in _NON_UTF8_CLIPBOARD_TYPES:
                add(node, "clipboard flavor %r is not UTF-8" % flavor,
                    "put text on the clipboard with QMimeData.setText() "
                    "(UTF-8 via _Utf8PlainTextClipboardType on macOS)")
            elif flavor and _is_text_mime(flavor) and len(node.args) > 1 \
                    and not _encodes_utf8(node.args[1]):
                add(node, "QMimeData text flavor %r without UTF-8 bytes"
                    % flavor, "pass QByteArray(text.encode('utf-8'))")

        elif attr == "setHtml" and "mime" in (_dotted(func.value) or
                                              "").lower():
            add(node, "QMimeData.setHtml() leaves the charset to the "
                "reader", "setData('text/html', QByteArray(html.encode("
                "'utf-8'))) with <meta charset=\"utf-8\"> in the HTML")

        elif name.endswith("QTextStream"):
            uses_text_stream = True

    if uses_text_stream and not sets_stream_utf8:
        findings.append(_finding(
            filename, 1, "QTextStream without an explicit encoding",
            "call stream.setEncoding(QtCore.QStringConverter.Encoding.Utf8)"))
    return findings


def _is_test_file(name):
    """Tests are not shipped, and some write non-UTF-8 on purpose (cp1250
    import fixtures, a text/plain request the server must refuse)."""
    return name.startswith("test_") or name.endswith(("_test.py",
                                                      ".test.js"))


def scan_python_tree():
    findings = []
    for name in sorted(os.listdir(SRC_DIR)):
        if name.endswith((".py", ".pyw")) and not _is_test_file(name):
            path = os.path.join(SRC_DIR, name)
            with open(path, encoding="utf-8") as fh:
                findings += scan_python_source(fh.read(), path)
    return findings


# ---------------------------------------------------------------------------
# Web (JavaScript and HTML)
# ---------------------------------------------------------------------------

# Vendored emscripten build of SQLite; not our code.
WEB_SKIP_FILES = {"sql-wasm.js"}

# (file name, text on the line, why it is binary).
WEB_ALLOWLIST = (
    ("viewer.js", "btoa(binary)",
     "PKCE verifier: base64 of random bytes, not text"),
)

# Blob/File types that are binary. Anything else must say charset=utf-8.
_BINARY_TYPE = re.compile(
    r"""type\s*:\s*["'](image/|application/(octet-stream|wasm|x-sqlite3|"""
    r"""vnd\.sqlite3|zip|pdf)\b)""")
_TEXT_MIME_LITERAL = re.compile(
    r"""(["'`])((?:text/[\w.+-]+|application/(?:json|xml|javascript)"""
    r"""|image/svg\+xml)[^"'`]*)\1""")
_CHARSET_UTF8 = re.compile(r"charset\s*=\s*[\"']?utf-8", re.I)


def _strip_js_comment(line):
    stripped = line.lstrip()
    if stripped.startswith(("//", "*", "/*")):
        return ""
    return re.sub(r"(^|\s)//.*$", "", line)


def _call_text(text, start):
    """The text of a call from start to its closing parenthesis."""
    depth = 0
    for index in range(text.index("(", start), len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return text[start:]


def _allowed_web(filename, line):
    base = os.path.basename(filename)
    return any(base == name and snippet in line
               for name, snippet, _why in WEB_ALLOWLIST)


def scan_js_source(source, filename):
    findings = []
    lines = [_strip_js_comment(line) for line in source.split("\n")]
    code = "\n".join(lines)

    def add(offset, problem, fix):
        findings.append(_finding(filename, code.count("\n", 0, offset) + 1,
                                 problem, fix))

    for match in re.finditer(r"\bnew\s+(Blob|File)\s*\(", code):
        call = _call_text(code, match.start())
        if _CHARSET_UTF8.search(call) or _BINARY_TYPE.search(call):
            continue
        add(match.start(), "new %s without a charset=utf-8 type"
            % match.group(1),
            "pass { type: \"text/plain;charset=utf-8\" } (images and other "
            "binary types are fine)")

    offset = 0
    for line in lines:
        line_offset, offset = offset, offset + len(line) + 1
        for match in _TEXT_MIME_LITERAL.finditer(line):
            value = match.group(2)
            after = line[match.end():].lstrip()
            before = line[:match.start()]
            if _CHARSET_UTF8.search(value):
                continue
            if after.startswith(":"):
                continue  # An object key (ClipboardItem flavors take no params).
            if re.search(r"(getData|types|accept|includes|indexOf|hasFormat)"
                         r"\s*[\(\.=\[]?\s*$", before) or \
                    re.search(r"(===|!==|==|!=)\s*$", before):
                continue  # Reading or comparing a type, not writing text.
            if value.startswith(("application/json", "application/xml",
                                 "image/svg+xml")) and \
                    "data:" not in before[-6:]:
                continue  # JSON/XML say their own encoding (UTF-8).
            add(line_offset + match.start(), "text type %r without charset=utf-8"
                % value, "write %r" % (value + ";charset=utf-8"))
        for match in re.finditer(r"data:(text/[\w.+-]+|application/json|"
                                 r"image/svg\+xml)([^\"'`,]*)", line):
            if not _CHARSET_UTF8.search(match.group(2)):
                add(line_offset + match.start(), "data: URL %r without "
                    "charset=utf-8" % match.group(0),
                    "use data:%s;charset=utf-8,..." % match.group(1))
        for match in re.finditer(r"(?<![\w.$])(btoa|atob|escape|unescape)"
                                 r"\s*\(", line):
            if _allowed_web(filename, line):
                continue
            add(line_offset + match.start(), "%s() is Latin-1 only"
                % match.group(1),
                "encode text with TextEncoder (UTF-8) first, or list binary "
                "data in WEB_ALLOWLIST with the reason")
        for match in re.finditer(r"(new\s+TextDecoder|readAsText)\s*\("
                                 r"[^,)]*,?\s*[\"']([\w-]+)[\"']", line):
            if not _is_utf8_name(match.group(2)):
                add(line_offset + match.start(), "%s with %r" % match.groups(),
                    "decode as \"utf-8\"")
    return findings


def scan_html_source(source, filename):
    head = source[:1024]
    if re.search(r"<meta\s+charset=[\"']?utf-8[\"']?\s*/?>", head, re.I):
        return []
    return [_finding(filename, 1, "no <meta charset=\"utf-8\"> in the first "
                     "1024 bytes", "add <meta charset=\"utf-8\"> as the "
                     "first element of <head>")]


def scan_web_tree():
    findings = []
    # softChord_web/tests is not shipped (see _is_test_file).
    for folder in (WEB_DIR, ):
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if name in WEB_SKIP_FILES or not os.path.isfile(path):
                continue
            if name.endswith(".js"):
                with open(path, encoding="utf-8") as fh:
                    findings += scan_js_source(fh.read(), path)
            elif name.endswith(".html"):
                with open(path, encoding="utf-8") as fh:
                    findings += scan_html_source(fh.read(), path)
    return findings


# ---------------------------------------------------------------------------
# iPhone (Swift)
# ---------------------------------------------------------------------------

_SWIFT_ENCODING = re.compile(
    r"\b(encoding|using)\s*:\s*(?:String\.Encoding)?\.(\w+)")
_SWIFT_ENCODING_CALL = re.compile(
    r"(String\s*\(|NSString\s*\(|\.data\s*\(|\.cString\s*\(|"
    r"\.write\s*\(|lengthOfBytes\s*\(|canBeConverted\s*\()")
_SWIFT_NON_UTF8 = re.compile(
    r"\b(String\.Encoding\s*\(\s*rawValue|CFStringConvertEncoding|"
    r"NS(ASCII|ISOLatin1|ISOLatin2|WindowsCP125\d|MacOSRoman|NonLossyASCII|"
    r"UTF16)StringEncoding|allowLossyConversion\s*:\s*true|usedEncoding\s*:)")
_SWIFT_CONTENTS_OF = re.compile(
    r"\b(String|NSString)\s*\(\s*contentsOf(File)?\s*:")
_SWIFT_PASTEBOARD = re.compile(
    r"(UIPasteboard|NSPasteboard|NSItemProvider|setItems|setValue|setData|"
    r"forPasteboardType|registerDataRepresentation|registerItem)")
_SWIFT_NON_UTF8_TEXT_TYPE = re.compile(
    r"(UTType\.(plainText|text|utf16PlainText|utf16ExternalPlainText)\b|"
    r"\"public\.(plain-text|text|utf16-plain-text|utf16-external-plain-text)\""
    r"|kUTType(PlainText|Text|UTF16PlainText)\b|"
    r"\"com\.apple\.traditional-mac-plain-text\")")
# Pasteboard writes whose whole call (it may span lines) is scanned.
_SWIFT_PASTEBOARD_WRITE = re.compile(
    r"\b(setItems|setData|setValue|setObjects|addItems|"
    r"registerDataRepresentation|registerItem)\s*\(")
# plain-text is allowed only beside UTF-8 bytes in the same write, so that
# .string reads keep working.
_SWIFT_PLAIN_TEXT_TYPE = re.compile(
    r"^(UTType\.plainText|\"public\.plain-text\")$")
_SWIFT_UTF8_TEXT_TYPE = re.compile(
    r"(UTType\.utf8PlainText\b|\"public\.utf8-plain-text\")")
_SWIFT_UTF8_DATA = re.compile(r"\bData\s*\([^()]*\.utf8\s*\)")


def _strip_swift_comment(line):
    stripped = line.lstrip()
    if stripped.startswith(("//", "*", "/*")):
        return ""
    return re.sub(r"(^|\s)//.*$", "", line)


def scan_swift_source(source, filename):
    findings = []
    lines = [_strip_swift_comment(line) for line in source.split("\n")]
    code = "\n".join(lines)
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)
    flagged_types = set()

    def add(index, problem, fix):
        findings.append(_finding(filename, index + 1, problem, fix))

    def check_pasteboard_types(start, text):
        """Flag text types in a pasteboard write, at the line they are on."""
        allow_plain = bool(_SWIFT_UTF8_TEXT_TYPE.search(text)
                           and _SWIFT_UTF8_DATA.search(text))
        for match in _SWIFT_NON_UTF8_TEXT_TYPE.finditer(text):
            offset = start + match.start()
            if offset in flagged_types:
                continue
            flagged_types.add(offset)
            if allow_plain and _SWIFT_PLAIN_TEXT_TYPE.match(match.group(0)):
                continue
            add(code.count("\n", 0, offset),
                "pasteboard text type %s does not say UTF-8" % match.group(0),
                "write Data(text.utf8) as UTType.utf8PlainText (plainText "
                "is allowed only beside it in the same setItems item)")

    for index, line in enumerate(lines):
        for match in _SWIFT_ENCODING.finditer(line):
            # "encoding:" is always a text encoding; "using:" only in the
            # String/Data conversion calls.
            if match.group(2) != "utf8" and (
                    match.group(1) == "encoding"
                    or _SWIFT_ENCODING_CALL.search(line)):
                add(index, "%s: .%s is not UTF-8" % match.groups(),
                    "use .utf8")
        if _SWIFT_NON_UTF8.search(line):
            add(index, "non-UTF-8 or lossy encoding (%s)"
                % _SWIFT_NON_UTF8.search(line).group(0),
                "use .utf8 and handle a nil result")
        for match in _SWIFT_CONTENTS_OF.finditer(line):
            call = _call_text("\n".join(lines[index:index + 5]),
                              match.start())
            if "encoding:" not in call:
                add(index, "%s(contentsOf:) guesses the encoding"
                    % match.group(1), "pass encoding: .utf8")
        for match in _SWIFT_PASTEBOARD_WRITE.finditer(line):
            start = line_starts[index] + match.start()
            check_pasteboard_types(start, _call_text(code, start))
        if _SWIFT_PASTEBOARD.search(line):
            check_pasteboard_types(line_starts[index], line)
        header = re.search(r"\"([^\"]*)\"\s*,\s*forHTTPHeaderField\s*:\s*"
                           r"\"Content-Type\"", line, re.I)
        if header and header.group(1).lower().startswith("text/") and \
                not _CHARSET_UTF8.search(header.group(1)):
            add(index, "Content-Type %r without charset=utf-8"
                % header.group(1), "add ;charset=utf-8")
    return findings


def scan_swift_tree():
    findings = []
    for root, dirs, files in os.walk(IOS_DIR):
        # The test targets are not shipped (see _is_test_file).
        dirs[:] = sorted(d for d in dirs
                         if not d.endswith((".xcodeproj", "Tests")))
        for name in sorted(files):
            if name.endswith(".swift"):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as fh:
                    findings += scan_swift_source(fh.read(), path)
    return findings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _report(findings):
    return "\nText must be written and read as UTF-8:\n  " + \
        "\n  ".join(findings)


class _GuardCase(unittest.TestCase):

    def assertFlags(self, findings, name, line, words):
        """Findings only at name:line, each with a fix; one mentions words."""
        self.assertTrue(findings, "the bad sample was not flagged")
        for finding in findings:
            self.assertTrue(finding.startswith("%s:%d: " % (name, line)),
                            finding)
            self.assertIn(". Fix: ", finding)
        self.assertTrue(any(words in finding for finding in findings),
                        findings)


class TestDesktopUtf8Guard(_GuardCase):

    def test_desktop_sources_write_text_as_utf8(self):
        findings = scan_python_tree()
        self.assertEqual(findings, [], _report(findings))

    def scan(self, code):
        return scan_python_source(code, "bad.py")

    def test_flags_text_open_without_encoding(self):
        self.assertFlags(self.scan("x = 1\nfh = open(path, 'w')\n"),
                         "bad.py", 2, "encoding='utf-8'")
        self.assertFlags(self.scan("open(path, mode='a').close()\n"),
                         "bad.py", 1, "text mode")
        self.assertFlags(self.scan("data = open(path).read()\n"),
                         "bad.py", 1, "without an encoding")
        self.assertFlags(self.scan("open(path, 'w', encoding='cp1252')\n"),
                         "bad.py", 1, "not UTF-8")
        self.assertFlags(self.scan("Path(p).open('w')\n"), "bad.py", 1,
                         "text mode")
        self.assertFlags(self.scan("codecs.open(p, 'w')\n"), "bad.py", 1,
                         "text mode")

    def test_allows_utf8_and_binary_open(self):
        self.assertEqual(self.scan(
            "open(p, 'w', encoding='utf-8')\n"
            "open(p, 'a', encoding='utf-8-sig')\n"
            "open(p, encoding='UTF_8')\n"
            "open(p, 'rb')\nopen(p, 'wb')\n"
            "Path(p).open('w', encoding='utf-8')\n"
            "buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)\n"
            "opener.open(request, timeout=5)\n"), [])

    def test_flags_path_text_helpers_without_encoding(self):
        self.assertFlags(self.scan("Path(p).write_text(text)\n"), "bad.py",
                         1, "write_text()")
        self.assertFlags(self.scan("Path(p).read_text()\n"), "bad.py", 1,
                         "read_text()")
        self.assertEqual(self.scan(
            "Path(p).write_text(text, encoding='utf-8')\n"
            "Path(p).read_text('utf-8')\n"), [])

    def test_flags_subprocess_text_without_encoding(self):
        self.assertFlags(self.scan(
            "subprocess.run(cmd, capture_output=True, text=True)\n"),
            "bad.py", 1, "subprocess text output")
        self.assertEqual(self.scan(
            "subprocess.run(cmd, text=True, encoding='utf-8')\n"
            "subprocess.run(cmd)\n"), [])

    def test_flags_codecs_that_are_not_utf8(self):
        self.assertFlags(self.scan("data = text.encode('latin-1')\n"),
                         "bad.py", 1, ".encode('latin-1')")
        self.assertFlags(self.scan("text = raw.decode('cp1251')\n"),
                         "bad.py", 1, "PYTHON_CODEC_ALLOWLIST")
        self.assertFlags(self.scan("data = text.toLatin1()\n"), "bad.py", 1,
                         "toUtf8")
        self.assertEqual(self.scan(
            "text.encode('utf-8')\nraw.decode('utf-8-sig')\n"
            "text.encode()\nraw.decode(encoding)\n"), [])
        # Only the listed binary line may use ascii.
        self.assertEqual(scan_python_source(
            'data = data.replace(b"#000000", color.name().encode("ascii"))\n',
            "softchord_toolbar.py"), [])
        self.assertEqual(len(scan_python_source(
            'data = title.encode("ascii")\n', "softchord_toolbar.py")), 1)

    def test_flags_clipboard_text_that_bypasses_utf8(self):
        self.assertFlags(self.scan(
            "mime = QtCore.QMimeData()\n"
            "mime.setData('text/plain', QtCore.QByteArray(text.encode("
            "'latin-1')))\n"), "bad.py", 2, "'text/plain'")
        self.assertFlags(self.scan(
            "LYRICS = 'application/x-lyrics+json'\n"
            "mime.setData(LYRICS, QtCore.QByteArray(payload))\n"),
            "bad.py", 2, "without UTF-8 bytes")
        self.assertFlags(self.scan(
            "mime.setData('com.apple.traditional-mac-plain-text', data)\n"),
            "bad.py", 1, "is not UTF-8")
        self.assertFlags(self.scan("mime.setHtml(html)\n"), "bad.py", 1,
                         "setHtml")
        self.assertEqual(self.scan(
            "LYRICS = 'application/x-lyrics+json'\n"
            "mime.setData(LYRICS, QtCore.QByteArray(json.dumps(p)"
            ".encode('utf-8')))\n"
            "mime.setData('image/png', png)\n"
            "mime.setData('image/svg+xml', svg)\n"
            "mime.setText(text)\n"
            "action.setData(song_id)\n"
            "item.setData(value, Qt.ItemDataRole.UserRole)\n"
            "doc.setHtml(html)\n"), [])

    def test_flags_text_stream_without_utf8(self):
        self.assertFlags(self.scan(
            "stream = QtCore.QTextStream(file)\nstream << text\n"),
            "bad.py", 1, "setEncoding")
        self.assertEqual(self.scan(
            "stream = QtCore.QTextStream(file)\n"
            "stream.setEncoding(QtCore.QStringConverter.Encoding.Utf8)\n"),
            [])


class TestWebUtf8Guard(_GuardCase):

    def test_web_sources_write_text_as_utf8(self):
        findings = scan_web_tree()
        self.assertEqual(findings, [], _report(findings))

    def scan(self, code):
        return scan_js_source(code, "bad.js")

    def test_flags_text_blobs_without_charset(self):
        self.assertFlags(self.scan(
            "var a = 1;\nvar blob = new Blob([text], { type: \"text/plain\" });\n"),
            "bad.js", 2, "charset=utf-8")
        self.assertEqual(len(self.scan("var blob = new Blob([text]);\n")), 1)
        self.assertEqual(len(self.scan(
            "var f = new File([text], name, {\n  type: 'text/html',\n});\n")),
            2)  # The Blob/File, and its text type literal.
        self.assertEqual(self.scan(
            "new Blob([text], { type: \"text/plain;charset=utf-8\" });\n"
            "new Blob([bytes], { type: \"image/png\" });\n"
            "new Blob([bytes], { type: \"application/x-sqlite3\" });\n"
            "new ClipboardItem({ \"text/plain\": text });\n"), [])

    def test_flags_text_downloads_and_headers_without_charset(self):
        self.assertFlags(self.scan(
            "link.href = \"data:text/plain,\" + encodeURIComponent(text);\n"),
            "bad.js", 1, "data: URL")
        self.assertFlags(self.scan(
            "fetch(url, { headers: { \"content-type\": \"text/plain\" } });\n"),
            "bad.js", 1, "text/plain;charset=utf-8")
        self.assertEqual(self.scan(
            "link.href = \"data:text/plain;charset=utf-8,\" + t;\n"
            "headers: { \"content-type\": \"application/json\" },\n"
            "if (event.clipboardData.getData(\"text/plain\")) {}\n"
            "// new Blob([text], { type: \"text/plain\" })\n"), [])

    def test_flags_latin1_only_helpers(self):
        self.assertFlags(self.scan("var b64 = btoa(text);\n"), "bad.js", 1,
                         "TextEncoder")
        self.assertFlags(self.scan("var s = unescape(encodeURIComponent(t));\n"),
                         "bad.js", 1, "unescape")
        self.assertFlags(self.scan(
            "var s = new TextDecoder(\"windows-1251\").decode(b);\n"),
            "bad.js", 1, "utf-8")
        self.assertEqual(scan_js_source(
            "var verifier = btoa(binary).replace(/=+$/g, \"\");\n",
            "viewer.js"), [])
        self.assertEqual(self.scan(
            "new TextDecoder(\"utf-8\").decode(b);\nCSS.escape(id);\n"), [])

    def test_flags_pages_without_meta_charset(self):
        self.assertFlags(scan_html_source(
            "<!doctype html><html><head><title>x</title>", "bad.html"),
            "bad.html", 1, "<meta charset")
        self.assertEqual(scan_html_source(
            "<!doctype html><head><meta charset=\"utf-8\">", "ok.html"), [])


class TestIosUtf8Guard(_GuardCase):

    def test_ios_sources_convert_text_as_utf8(self):
        findings = scan_swift_tree()
        self.assertEqual(findings, [], _report(findings))

    def scan(self, code):
        return scan_swift_source(code, "Bad.swift")

    def test_flags_non_utf8_conversions(self):
        self.assertFlags(self.scan(
            "let a = 1\nlet s = String(data: data, encoding: .ascii)\n"),
            "Bad.swift", 2, ".ascii is not UTF-8")
        self.assertFlags(self.scan(
            "let d = text.data(using: .isoLatin1)\n"),
            "Bad.swift", 1, ".isoLatin1")
        self.assertFlags(self.scan(
            "let d = text.data(using: String.Encoding.windowsCP1251)\n"),
            "Bad.swift", 1, "windowsCP1251")
        self.assertFlags(self.scan(
            "try text.write(to: url, atomically: true, encoding: .utf16)\n"),
            "Bad.swift", 1, ".utf16")
        self.assertFlags(self.scan(
            "let d = text.data(using: .utf8, allowLossyConversion: true)\n"),
            "Bad.swift", 1, "allowLossyConversion")
        self.assertFlags(self.scan("let s = try String(contentsOf: url)\n"),
                         "Bad.swift", 1, "encoding: .utf8")
        self.assertEqual(self.scan(
            "let s = String(data: data, encoding: .utf8)\n"
            "let d = text.data(using: .utf8)\n"
            "let s2 = try String(contentsOf: url, encoding: .utf8)\n"
            "let d2 = Data(text.utf8)\n"
            "var c = Array(\"x\".utf16)\n"
            "// String(data: d, encoding: .ascii)\n"), [])

    def test_flags_pasteboard_text_types_that_are_not_utf8(self):
        self.assertFlags(self.scan(
            "UIPasteboard.general.setData(data, forPasteboardType: "
            "UTType.plainText.identifier)\n"), "Bad.swift", 1, "plainText")
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\"public.utf16-plain-text\": data]])\n"),
            "Bad.swift", 1, "utf16-plain-text")
        # plainText alone, across lines, is still flagged.
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\n"
            "    UTType.plainText.identifier: text,\n"
            "]])\n"), "Bad.swift", 2, "plainText")
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\"public.plain-text\": text]])\n"),
            "Bad.swift", 1, "public.plain-text")
        # Naming utf8PlainText without UTF-8 bytes does not excuse plainText.
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\n"
            "    UTType.utf8PlainText.identifier: data,\n"
            "    UTType.plainText.identifier: text,\n"
            "]])\n"), "Bad.swift", 3, "plainText")
        # UTF-8 bytes beside utf16 or traditional-mac text do not excuse them.
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\n"
            "    UTType.utf8PlainText.identifier: Data(text.utf8),\n"
            "    UTType.utf16PlainText.identifier: text,\n"
            "]])\n"), "Bad.swift", 3, "utf16PlainText")
        self.assertFlags(self.scan(
            "pasteboard.setItems([[\"public.utf8-plain-text\": "
            "Data(text.utf8), \"com.apple.traditional-mac-plain-text\": "
            "text]])\n"), "Bad.swift", 1, "traditional-mac")
        self.assertEqual(self.scan(
            "UIPasteboard.general.string = text\n"
            "pasteboard.setItems([[UTType.png.identifier: data]])\n"
            "pasteboard.setData(Data(text.utf8), forPasteboardType: "
            "UTType.utf8PlainText.identifier)\n"
            "pasteboard.setItems([[\n"
            "    UTType.utf8PlainText.identifier: Data(text.utf8),\n"
            "    UTType.plainText.identifier: text,\n"
            "]])\n"
            "pasteboard.setItems([[\"public.utf8-plain-text\": "
            "Data(text.utf8), \"public.plain-text\": text]])\n"), [])

    def test_flags_text_content_type_without_charset(self):
        self.assertFlags(self.scan(
            "request.setValue(\"text/plain\", forHTTPHeaderField: "
            "\"Content-Type\")\n"), "Bad.swift", 1, "charset=utf-8")
        self.assertEqual(self.scan(
            "request.setValue(\"application/json\", forHTTPHeaderField: "
            "\"Content-Type\")\n"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
