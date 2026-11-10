"""Desktop magic-link sign-in.

Passwordless. The Account menu asks for an email, POSTs /api/auth/request-link
with client "desktop" and a verifier hash, then the person pastes the link
from the email. /api/auth/verify exchanges that token plus the saved verifier
for a session token. The menu's email comes from /api/me. Sign out POSTs
/api/auth/logout and clears the local session.

No request is made when the API origin is unset. Tests pass a transport;
JsonEnforcingTransport is the mock that rejects a POST unless it is exactly
Content-Type: application/json and a JSON object ({} when there is nothing
to send).
"""

import base64
import hashlib
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

from PyQt6 import QtCore, QtWidgets


REQUEST_LINK_PATH = "/api/auth/request-link"
VERIFY_PATH = "/api/auth/verify"
ME_PATH = "/api/me"
LOGOUT_PATH = "/api/auth/logout"

# Sent on verify. The server stores it on the session, trimmed to 200.
DEVICE_LABEL = "SoftChord desktop"

CHECK_EMAIL = "Check your email"
NOT_CONFIGURED = "Sign-in not configured"
INVALID_EMAIL = "Enter a valid email address."
SEND_FAILED = "Could not send the link."
SIGN_IN_FAILED = "Could not sign in."
# Same sentence the server shows when verify fails.
LINK_FAILED = "Open this link on the device where you requested it."
SIGN_OUT_FAILED = "Could not sign out."

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")

_SESSION_KEY = "auth/sessionToken"
_VERIFIER_KEY = "auth/pendingVerifier"
_ORIGIN_KEY = "auth/apiOrigin"


class TransportError(Exception):
    """The HTTP transport could not complete the call."""


class HttpExchange:
    """One request the client would send."""

    def __init__(self, method, url, headers, body):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body


class HttpResult:
    """One response. body is raw bytes."""

    def __init__(self, status, body):
        self.status = status
        self.body = body or b""


def post_is_json(exchange):
    """True when this POST is exactly application/json and a JSON object.

    Header names are matched ignoring case. The value must be exactly
    application/json, with no charset parameter. The body must be a JSON
    object, so a logout with nothing to send is {}.
    """
    if exchange.method != "POST":
        return True
    found = None
    for name, value in exchange.headers.items():
        if name.lower() == "content-type":
            found = value
            break
    if found != "application/json":
        return False
    if not isinstance(exchange.body, (bytes, bytearray)) or not exchange.body:
        return False
    try:
        payload = json.loads(bytes(exchange.body).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict)


class JsonEnforcingTransport:
    """Test double. A POST that is not JSON is 400 and does not use a script.

    responses is a list of HttpResult consumed in order by calls that pass
    the JSON check. A rejected POST is still recorded on calls.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, exchange):
        self.calls.append(exchange)
        if not post_is_json(exchange):
            return HttpResult(400, b'{"error":"invalid_request"}')
        if not self.responses:
            raise AssertionError(
                "no scripted response for %s %s" % (exchange.method, exchange.url))
        return self.responses.pop(0)


def new_verifier():
    """43-character base64url verifier (32 random bytes, no padding)."""
    raw = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    return raw.rstrip("=")


def verifier_hash(verifier):
    """Hex SHA-256 of the verifier, which is what request-link stores."""
    return hashlib.sha256(verifier.encode("utf-8")).hexdigest()


def normalize_email(value):
    """Trimmed, lowercased address, or None when it cannot be one."""
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if not email or len(email) > 254 or not _EMAIL.match(email):
        return None
    return email


def normalize_origin(value):
    """http(s) origin with no path, or None. A trailing slash is dropped."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.rstrip("/")
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        return None
    return "%s://%s" % (parsed.scheme, parsed.netloc)


def login_token_from_text(value):
    """Token from a pasted login link, a softchord:// URL, or the token itself.

    The email link carries the token in the fragment (#t=), never in the query.
    The server's Open in SoftChord button uses softchord://login?token=.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if _TOKEN.fullmatch(text):
        return text
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme == "softchord":
        found = urllib.parse.parse_qs(parsed.query).get("token", [])
    elif parsed.scheme in ("http", "https"):
        found = urllib.parse.parse_qs(parsed.fragment).get("t", [])
    else:
        return None
    if len(found) == 1 and _TOKEN.fullmatch(found[0]):
        return found[0]
    return None


def default_account_settings():
    """Ini QSettings for org softChord, app softChord."""
    return QtCore.QSettings(
        QtCore.QSettings.Format.IniFormat,
        QtCore.QSettings.Scope.UserScope,
        "softChord",
        "softChord")


def urllib_transport(exchange):
    """Send one request with urllib. HTTP errors become HttpResult."""
    request = urllib.request.Request(
        exchange.url,
        data=exchange.body,
        headers=dict(exchange.headers),
        method=exchange.method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return HttpResult(response.status, response.read())
    except urllib.error.HTTPError as error:
        return HttpResult(error.code, error.read())
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TransportError(str(error))


def _dumps(payload):
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _read_json(result):
    try:
        return json.loads(result.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _setting_text(settings, key):
    value = settings.value(key, "")
    if value is None:
        return ""
    return str(value)


class AccountController:
    """Session token, the pending verifier, and the Account menu label."""

    def __init__(self, session, settings=None, transport=None, env=None,
                 verifier_factory=None):
        self.session = session
        self.settings = settings or default_account_settings()
        self.transport = transport or urllib_transport
        # None reads os.environ. Tests pass a dict so the process env is ignored.
        self.env = env
        self.verifier_factory = verifier_factory or new_verifier
        self.refresh()

    def origin(self):
        """SOFTCHORD_API_ORIGIN, else QSettings auth/apiOrigin, else None."""
        source = os.environ if self.env is None else self.env
        raw = source.get("SOFTCHORD_API_ORIGIN", "")
        origin = normalize_origin(raw)
        if origin:
            return origin
        return normalize_origin(_setting_text(self.settings, _ORIGIN_KEY))

    def session_token(self):
        return _setting_text(self.settings, _SESSION_KEY)

    def pending_verifier(self):
        return _setting_text(self.settings, _VERIFIER_KEY)

    def sign_in(self, checked=False):
        """Sign In.... Unset origin shows a message and does not connect."""
        if self.origin() is None:
            self._tell("Sign in", NOT_CONFIGURED)
            return
        dialog = SignInDialog(self, self.session.win)
        dialog.exec()

    def sign_out(self, checked=False):
        """POST /api/auth/logout, then drop the local session.

        With no origin, or no token, nothing is sent. The local session is
        still cleared. A failed call leaves the token so the person can retry.
        """
        origin = self.origin()
        token = self.session_token()
        if origin and token:
            try:
                result = self._send(
                    origin, "POST", LOGOUT_PATH, {}, bearer=token)
            except TransportError:
                self._tell("Sign out", SIGN_OUT_FAILED)
                return
            if result.status not in (200, 401):
                self._tell("Sign out", SIGN_OUT_FAILED)
                return
        self._clear_local()
        self.show_signed_in(None)

    def request_link(self, email):
        """POST request-link. Returns ok, invalid, unconfigured, or error."""
        origin = self.origin()
        if origin is None:
            return "unconfigured"
        normalized = normalize_email(email)
        if normalized is None:
            return "invalid"
        verifier = self.verifier_factory()
        body = {
            "email": normalized,
            "client": "desktop",
            "verifier_hash": verifier_hash(verifier),
        }
        try:
            result = self._send(origin, "POST", REQUEST_LINK_PATH, body)
        except TransportError:
            return "error"
        payload = _read_json(result)
        if result.status != 200 or not isinstance(payload, dict) or payload.get("ok") is not True:
            return "error"
        self.settings.setValue(_VERIFIER_KEY, verifier)
        self.settings.sync()
        return "ok"

    def complete_sign_in(self, pasted):
        """Verify the pasted link, then load the email from /api/me.

        Returns ok, invalid, unconfigured, or error. The menu label is the
        email from /api/me.
        """
        origin = self.origin()
        if origin is None:
            return "unconfigured"
        token = login_token_from_text(pasted)
        verifier = self.pending_verifier()
        if not token or not verifier:
            return "invalid"
        body = {
            "token": token,
            "verifier": verifier,
            "device_label": DEVICE_LABEL,
        }
        try:
            result = self._send(origin, "POST", VERIFY_PATH, body)
        except TransportError:
            return "error"
        payload = _read_json(result)
        if (result.status != 200 or not isinstance(payload, dict)
                or not isinstance(payload.get("token"), str)
                or not payload["token"].strip()):
            return "invalid"
        session_token = payload["token"].strip()
        self.settings.setValue(_SESSION_KEY, session_token)
        self.settings.remove(_VERIFIER_KEY)
        self.settings.sync()
        email = self._email_from_me(origin, session_token)
        if email is None:
            return "error"
        if email == "":
            return "invalid"
        self.show_signed_in(email)
        return "ok"

    def refresh(self):
        """Show the signed-in email when a stored token and an origin exist.

        No origin or no token: signed-out menu, and no request. 401 clears
        the stored token. Any other failure leaves the token and shows
        signed out.
        """
        origin = self.origin()
        token = self.session_token()
        if not origin or not token:
            self.show_signed_in(None)
            return
        email = self._email_from_me(origin, token)
        if email:
            self.show_signed_in(email)
        else:
            self.show_signed_in(None)

    def show_signed_in(self, email):
        """Email label and Sign Out, or Sign In when email is empty."""
        ui = self.session.ui
        signed_in = bool(email)
        ui.signedInEmailLabel.setText(email or "")
        ui.actionSignedInEmail.setText(email or "")
        ui.actionSignedInEmail.setVisible(signed_in)
        ui.actionSignIn.setVisible(not signed_in)
        ui.actionSignOut.setVisible(signed_in)

    def _email_from_me(self, origin, token):
        """Email string, '' when the session is rejected, None on any other failure."""
        try:
            result = self._send(origin, "GET", ME_PATH, bearer=token)
        except TransportError:
            return None
        payload = _read_json(result)
        if result.status == 401:
            self._clear_local()
            return ""
        if result.status != 200 or not isinstance(payload, dict):
            return None
        email = payload.get("email")
        if not isinstance(email, str) or not email:
            return None
        return email

    def _clear_local(self):
        self.settings.remove(_SESSION_KEY)
        self.settings.remove(_VERIFIER_KEY)
        self.settings.sync()

    def _send(self, origin, method, path, payload=None, bearer=None):
        headers = {}
        body = None
        if method == "POST":
            if payload is None:
                payload = {}
            headers["Content-Type"] = "application/json"
            body = _dumps(payload)
        if bearer:
            headers["Authorization"] = "Bearer %s" % bearer
        exchange = HttpExchange(method, origin + path, headers, body)
        return self.transport(exchange)

    def _tell(self, title, message):
        # Imported here so this module does not import the menu module at load.
        from softchord_menus import show_not_available
        show_not_available(self.session.win, title, message)


class SignInDialog(QtWidgets.QDialog):
    """Email, then paste the link. There is no password field."""

    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.setWindowTitle("Sign in")
        self.setModal(True)
        self.email_edit = QtWidgets.QLineEdit(self)
        self.email_edit.setObjectName("signInEmail")
        self.email_edit.setPlaceholderText("Email")
        self.send_button = QtWidgets.QPushButton("Email me a link", self)
        self.send_button.setObjectName("signInSend")
        self.send_button.setDefault(True)
        self.send_button.clicked.connect(self.send_link)
        self.status_label = QtWidgets.QLabel("", self)
        self.status_label.setObjectName("signInStatus")
        self.status_label.setWordWrap(True)
        self.link_edit = QtWidgets.QLineEdit(self)
        self.link_edit.setObjectName("signInLink")
        self.link_edit.setPlaceholderText("Paste the link from the email")
        self.complete_button = QtWidgets.QPushButton("Complete sign-in", self)
        self.complete_button.setObjectName("signInComplete")
        self.complete_button.clicked.connect(self.complete)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.email_edit)
        layout.addWidget(self.send_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.link_edit)
        layout.addWidget(self.complete_button)
        self.link_edit.hide()
        self.complete_button.hide()
        if account.pending_verifier():
            self.status_label.setText(CHECK_EMAIL)
            self._show_paste()

    def send_link(self, checked=False):
        result = self.account.request_link(self.email_edit.text())
        if result == "ok":
            self.status_label.setText(CHECK_EMAIL)
            self._show_paste()
        elif result == "invalid":
            self.status_label.setText(INVALID_EMAIL)
        elif result == "unconfigured":
            self.status_label.setText(NOT_CONFIGURED)
        else:
            self.status_label.setText(SEND_FAILED)

    def complete(self, checked=False):
        result = self.account.complete_sign_in(self.link_edit.text())
        if result == "ok":
            self.accept()
            return
        if result == "invalid" or result == "unconfigured":
            self.status_label.setText(LINK_FAILED)
            return
        self.status_label.setText(SIGN_IN_FAILED)

    def _show_paste(self):
        self.link_edit.show()
        self.complete_button.show()
        self.complete_button.setDefault(True)
