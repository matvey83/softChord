"""Desktop magic-link sign-in.

Passwordless. The Account menu asks for an email, POSTs /api/auth/request-link
with client "desktop" and a verifier hash, then the person pastes the link
from the email. /api/auth/verify exchanges that token plus the saved verifier
for a session token. The menu's email comes from /api/me. Sign out POSTs
/api/auth/logout. Sign out everywhere POSTs /api/auth/logout-all. Both
clear the local session. HTTP runs on a worker; the menu changes on the
GUI thread.

No request is made when the API origin is unset. Tests pass a transport;
JsonEnforcingTransport is the mock that rejects a POST unless it is exactly
Content-Type: application/json and a JSON object ({} when there is nothing
to send).
"""

import atexit
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PyQt6 import QtCore, QtWidgets


REQUEST_LINK_PATH = "/api/auth/request-link"
VERIFY_PATH = "/api/auth/verify"
ME_PATH = "/api/me"
LOGOUT_PATH = "/api/auth/logout"
LOGOUT_ALL_PATH = "/api/auth/logout-all"

# Sent on verify. The server stores it on the session, trimmed to 200.
DEVICE_LABEL = "SoftChord desktop"

# server/src/config.ts LOGIN_TTL_SECONDS at 0775e8211158c57ff0869d1dbcf961c72ef167bd.
# A live login token requires expires_at > now, so this age is already expired.
VERIFIER_TTL_SECONDS = 15 * 60

HTTP_TIMEOUT_SECONDS = 15

CHECK_EMAIL = "Check your email"
NOT_AVAILABLE_TITLE = "Not available yet"
NOT_CONFIGURED = "Sign-in is coming in a later update."
INVALID_EMAIL = "Enter a valid email address."
SEND_FAILED = "Could not send the link."
SIGN_IN_FAILED = "Could not sign in."
# Same sentence the server shows when verify fails.
LINK_FAILED = "Open this link on the device where you requested it."
SIGN_OUT_FAILED = "Could not sign out."
SIGN_OUT_EVERYWHERE_FAILED = "Could not sign out everywhere."

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43,128}$")

_SESSION_KEY = "auth/sessionToken"
_VERIFIER_KEY = "auth/pendingVerifier"
_VERIFIER_AT_KEY = "auth/pendingVerifierAt"
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
    """https origin, or http://localhost / http://127.0.0.1. A trailing slash is dropped.

    Any other http origin is unset. No userinfo, path, query, or fragment.
    A port on the two local hosts is kept.
    """
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
    host = parsed.hostname
    if not host:
        return None
    local = host == "localhost" or host == "127.0.0.1"
    if parsed.scheme == "http" and not local:
        return None
    if parsed.scheme != "https" and not local:
        return None
    port = parsed.port
    netloc = host if port is None else "%s:%s" % (host, port)
    return "%s://%s" % (parsed.scheme, netloc)


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


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow a redirect, so Authorization is never copied to the next URL."""

    def http_error_302(self, req, fp, code, msg, headers):
        try:
            fp.read()
        except Exception:
            pass
        try:
            fp.close()
        except Exception:
            pass
        raise TransportError("redirect")

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def _opener():
    return urllib.request.build_opener(_RefuseRedirect())


def urllib_transport(exchange, opener=None):
    """Send one request. A 3xx is an error. The timeout is 15 seconds."""
    opener = opener or _opener()
    request = urllib.request.Request(
        exchange.url,
        data=exchange.body,
        headers=dict(exchange.headers),
        method=exchange.method)
    try:
        with opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            status = response.status
            if 300 <= status < 400:
                raise TransportError("redirect")
            body = response.read()
    except TransportError:
        raise
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            raise TransportError("redirect")
        return HttpResult(error.code, error.read())
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TransportError(str(error))
    return HttpResult(status, body)


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


def _valid_session_token(value):
    """True when value is a token this client may store or send as Bearer."""
    return isinstance(value, str) and _TOKEN.fullmatch(value) is not None


def _log_failure(exc):
    """Record the failure type only.

    The message and the traceback are not written: either one can carry
    the Authorization header.
    """
    try:
        sys.stderr.write("softChord auth: %s\n" % type(exc).__name__)
    except Exception:
        pass


class _TaskSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)


class _Flight:
    """One worker's signal. close() happens before Qt teardown, under the lock.

    The worker only emits while holding that lock, so it cannot call into a
    QObject that quit has already dropped.
    """

    def __init__(self, signals):
        self._lock = threading.Lock()
        self._signals = signals

    def emit(self, result):
        with self._lock:
            signals = self._signals
            if signals is None:
                return
            signals.finished.emit(result)

    def close(self):
        with self._lock:
            self._signals = None


_FLIGHTS_LOCK = threading.Lock()
_FLIGHTS = []
_SILENCE_REGISTERED = False


def _track_flight(flight):
    with _FLIGHTS_LOCK:
        _FLIGHTS.append(flight)


def _drop_flight(flight):
    with _FLIGHTS_LOCK:
        try:
            _FLIGHTS.remove(flight)
        except ValueError:
            pass


def _close_flights():
    """Stop workers from emitting. Does not touch Qt and does not wait."""
    with _FLIGHTS_LOCK:
        flights = list(_FLIGHTS)
        _FLIGHTS.clear()
    for flight in flights:
        flight.close()


def _register_worker_silence():
    """Register _close_flights with atexit as a fallback only.

    atexit order relative to Qt teardown is not guaranteed, and the hook
    may run too late or not at all (softchord.main() ends with os._exit,
    which skips atexit). Workers are silenced before teardown by
    aboutToQuit -> abandon_pending -> _close_flights. This hook covers a
    worker started after aboutToQuit, or an exit that does not go
    through QApplication.
    """
    global _SILENCE_REGISTERED
    if _SILENCE_REGISTERED:
        return
    atexit.register(_close_flights)
    _SILENCE_REGISTERED = True


def release_thread_pool():
    """Drop queued pool work without waiting for a request that is still running.

    QThreadPool's destructor waits forever for active workers. waitForDone(0)
    returns immediately, so shutdown is not held for the HTTP timeout.
    Auth requests themselves run on daemon threads and are not in this pool.
    """
    pool = QtCore.QThreadPool.globalInstance()
    pool.clear()
    pool.waitForDone(0)


class AccountController(QtCore.QObject):
    """Session token, the pending verifier, and the Account menu label.

    HTTP runs on a daemon thread. settled is emitted on the GUI thread
    after each call's widgets and settings have been updated. Quit closes
    those emitters before Qt tears the objects down.
    """

    settled = QtCore.pyqtSignal()

    def __init__(self, session, settings=None, transport=None, env=None,
                 verifier_factory=None):
        super().__init__()
        self.session = session
        self.settings = settings or default_account_settings()
        self.transport = transport or urllib_transport
        # None reads os.environ. Tests pass a dict so the process env is ignored.
        self.env = env
        self.verifier_factory = verifier_factory or new_verifier
        # Tests replace this so the verifier TTL does not depend on the clock.
        self.now = time.time
        # Bumped when Esc/Cancel should drop a dialog request, and on quit.
        self._request_generation = 0
        # Bumped when the saved session changes, so a late response cannot
        # clear a newer token or sign the menu back in.
        self._session_generation = 0
        self._dialog = None
        _register_worker_silence()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.abandon_pending)
        self.refresh()

    def abandon_pending(self):
        """Drop in-flight results when the process is leaving.

        Workers are silenced first, so they do not emit into objects Qt is
        about to delete. The thread pool is not waited on.
        """
        _close_flights()
        self._request_generation += 1
        self._session_generation += 1
        release_thread_pool()

    def cancel_inflight(self):
        """Ignore dialog requests that have not been applied yet."""
        self._request_generation += 1

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
        """The saved verifier, or "" once it is as old as the server login token."""
        verifier = _setting_text(self.settings, _VERIFIER_KEY)
        if not verifier:
            return ""
        raw = self.settings.value(_VERIFIER_AT_KEY, None)
        try:
            stored = int(raw)
        except (TypeError, ValueError):
            stored = None
        if stored is None or int(self.now()) - stored >= VERIFIER_TTL_SECONDS:
            self._clear_verifier()
            self.settings.sync()
            return ""
        return verifier

    def sign_in(self, checked=False):
        """Sign In.... Unset origin shows a message and does not connect.

        A second call while the dialog is open raises that dialog instead
        of opening another one.
        """
        try:
            if self._dialog is not None:
                self._dialog.raise_()
                self._dialog.activateWindow()
                return
            if self.origin() is None:
                self._tell(NOT_AVAILABLE_TITLE, NOT_CONFIGURED)
                return
            dialog = SignInDialog(self, self.session.win)
            self._dialog = dialog
            try:
                dialog.exec()
            finally:
                if self._dialog is dialog:
                    self._dialog = None
        except Exception as exc:
            _log_failure(exc)

    def sign_out(self, checked=False):
        """POST /api/auth/logout, then drop the local session."""
        try:
            self._end_session(LOGOUT_PATH, "Sign out", SIGN_OUT_FAILED)
        except Exception as exc:
            _log_failure(exc)

    def sign_out_everywhere(self, checked=False):
        """POST /api/auth/logout-all, then drop the local session."""
        try:
            self._end_session(
                LOGOUT_ALL_PATH, "Sign out everywhere",
                SIGN_OUT_EVERYWHERE_FAILED)
        except Exception as exc:
            _log_failure(exc)

    def _end_session(self, path, title, failure):
        """POST {} with the bearer token. 200 or 401 clears the local session.

        With no origin, or no token, nothing is sent. The local session is
        still cleared. Any other result leaves the token so the person can retry.
        """
        origin = self.origin()
        token = self.session_token()
        if not origin or not token:
            self._clear_local()
            self.show_signed_in(None)
            self.settled.emit()
            return

        def work():
            try:
                return self._send(origin, "POST", path, {}, bearer=token)
            except Exception as exc:
                _log_failure(exc)
                return None

        def done(result):
            if result is None or result.status not in (200, 401):
                self._tell(title, failure)
                return
            self._clear_local()
            self.show_signed_in(None)

        self._start(work, done)

    def request_link(self, email, done):
        """POST request-link. done(status) runs on the GUI thread."""
        try:
            origin = self.origin()
            if origin is None:
                self._finish_now(done, "unconfigured")
                return
            normalized = normalize_email(email)
            if normalized is None:
                self._finish_now(done, "invalid")
                return
            verifier = self.verifier_factory()
            issued = int(self.now())
            body = {
                "email": normalized,
                "client": "desktop",
                "verifier_hash": verifier_hash(verifier),
            }

            # Set on the worker when the POST succeeded. A superseded
            # session reports "error" to the dialog, but the link was
            # emailed, so its verifier is still saved for a later paste.
            sent = []

            def work():
                try:
                    result = self._send(origin, "POST", REQUEST_LINK_PATH, body)
                except Exception as exc:
                    _log_failure(exc)
                    return "error"
                payload = _read_json(result)
                if (result.status == 200 and isinstance(payload, dict)
                        and payload.get("ok") is True):
                    sent.append(True)
                    return "ok"
                return "error"

            def after(status):
                if sent:
                    self.settings.setValue(_VERIFIER_KEY, verifier)
                    self.settings.setValue(_VERIFIER_AT_KEY, issued)
                    self.settings.sync()
                done(status if status else "error")

            self._start(work, after, dialog=True)
        except Exception as exc:
            _log_failure(exc)
            self._finish_now(done, "error")

    def complete_sign_in(self, pasted, done):
        """Verify the pasted link, then load the email from /api/me.

        done receives ok, invalid, unconfigured, or error on the GUI thread.
        The menu label is the email from /api/me.
        """
        try:
            origin = self.origin()
            if origin is None:
                self._finish_now(done, "unconfigured")
                return
            token = login_token_from_text(pasted)
            verifier = self.pending_verifier()
            if not token or not verifier:
                self._finish_now(done, "invalid")
                return
            body = {
                "token": token,
                "verifier": verifier,
                "device_label": DEVICE_LABEL,
            }

            def work():
                try:
                    verified = self._send(origin, "POST", VERIFY_PATH, body)
                except Exception as exc:
                    _log_failure(exc)
                    return ("error", None)
                payload = _read_json(verified)
                session_token = payload.get("token") if isinstance(payload, dict) else None
                if verified.status != 200 or not _valid_session_token(session_token):
                    return ("invalid", None)
                try:
                    me = self._send(
                        origin, "GET", ME_PATH, bearer=session_token)
                except Exception as exc:
                    _log_failure(exc)
                    return ("me-error", session_token)
                return ("me", session_token, me)

            def after(result):
                if not isinstance(result, tuple) or not result:
                    done("error")
                    return
                kind = result[0]
                if kind in ("invalid", "error"):
                    done(kind)
                    return
                session_token = result[1]
                if not _valid_session_token(session_token):
                    done("invalid")
                    return
                self._store_session(session_token)
                if kind == "me-error":
                    done("error")
                    return
                email = self._apply_me(result[2])
                if email:
                    self.show_signed_in(email)
                    done("ok")
                elif email == "":
                    done("invalid")
                else:
                    done("error")

            self._start(work, after, dialog=True)
        except Exception as exc:
            _log_failure(exc)
            self._finish_now(done, "error")

    def refresh(self):
        """Show the signed-in email when a stored token and an origin exist.

        No origin or no token: signed-out menu, and no request. 401 clears
        the stored token. Any other failure leaves the token and shows
        signed out.
        """
        try:
            self._refresh()
        except Exception as exc:
            _log_failure(exc)
            self.settled.emit()

    def _refresh(self):
        origin = self.origin()
        token = self.session_token()
        if not origin or not token:
            self.show_signed_in(None)
            self.settled.emit()
            return

        def work():
            try:
                return self._send(origin, "GET", ME_PATH, bearer=token)
            except Exception as exc:
                _log_failure(exc)
                return None

        def done(result):
            email = self._apply_me(result)
            if email:
                self.show_signed_in(email)
            else:
                self.show_signed_in(None)

        self._start(work, done)

    def show_signed_in(self, email):
        """Email label and Sign Out, or Sign In when email is empty."""
        ui = self.session.ui
        signed_in = bool(email)
        ui.signedInEmailLabel.setText(email or "")
        ui.actionSignedInEmail.setText(email or "")
        ui.actionSignedInEmail.setVisible(signed_in)
        ui.actionSignIn.setVisible(not signed_in)
        ui.actionSignOut.setVisible(signed_in)
        ui.actionSignOutEverywhere.setVisible(signed_in)

    def _apply_me(self, result):
        """Email string, '' when the session is rejected, None on any other failure.

        A 401 clears the local session. This runs on the GUI thread.
        """
        if result is None:
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

    def _clear_verifier(self):
        self.settings.remove(_VERIFIER_KEY)
        self.settings.remove(_VERIFIER_AT_KEY)

    def _store_session(self, token):
        """Save a verified session token and drop any older in-flight result."""
        self._session_generation += 1
        self.settings.setValue(_SESSION_KEY, token)
        self._clear_verifier()
        self.settings.sync()

    def _clear_local(self):
        """Drop the saved session and any older in-flight result."""
        self._session_generation += 1
        self.settings.remove(_SESSION_KEY)
        self._clear_verifier()
        self.settings.sync()

    def _start(self, work, done, dialog=False):
        """Run work on a pool thread. done runs on the GUI thread, then settled.

        dialog requests are ignored after Esc, Cancel, or quit. A dialog
        request whose session generation has moved on (a startup refresh
        401, for example) does not change the session, but the dialog is
        told so its button comes back and a message is shown. Other stale
        results are ignored. The worker is a daemon thread, so process
        exit does not wait for it.
        """
        signals = _TaskSignals(self)
        flight = _Flight(signals)
        _track_flight(flight)
        dialog_generation = self._request_generation if dialog else None
        session_generation = self._session_generation

        def on_finished(result):
            try:
                if (dialog_generation is not None
                        and dialog_generation != self._request_generation):
                    return
                if session_generation != self._session_generation:
                    if dialog_generation is not None:
                        done("error")
                    return
                done(result)
            except Exception as exc:
                _log_failure(exc)
            finally:
                flight.close()
                _drop_flight(flight)
                try:
                    signals.deleteLater()
                except Exception as exc:
                    _log_failure(exc)
                try:
                    self.settled.emit()
                except Exception as exc:
                    _log_failure(exc)

        def run():
            try:
                result = work()
            except Exception as exc:
                _log_failure(exc)
                result = None
            try:
                flight.emit(result)
            except Exception as exc:
                _log_failure(exc)

        signals.finished.connect(
            on_finished, QtCore.Qt.ConnectionType.QueuedConnection)
        threading.Thread(target=run, daemon=True).start()

    def _finish_now(self, done, result):
        """A result that did not need the network, still on the GUI thread."""
        try:
            done(result)
        except Exception as exc:
            _log_failure(exc)
        try:
            self.settled.emit()
        except Exception as exc:
            _log_failure(exc)

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
        self._alive = True
        if account.pending_verifier():
            self.status_label.setText(CHECK_EMAIL)
            self._show_paste()

    def closeEvent(self, event):
        self._alive = False
        super().closeEvent(event)

    def reject(self):
        """Esc and Cancel. An in-flight verify must not save a session."""
        self._alive = False
        try:
            self.account.cancel_inflight()
        except Exception as exc:
            _log_failure(exc)
        super().reject()

    def send_link(self, checked=False):
        try:
            self.send_button.setEnabled(False)
            self.account.request_link(self.email_edit.text(), self._on_link)
        except Exception as exc:
            _log_failure(exc)
            self.send_button.setEnabled(True)

    def complete(self, checked=False):
        try:
            self.complete_button.setEnabled(False)
            self.account.complete_sign_in(self.link_edit.text(), self._on_complete)
        except Exception as exc:
            _log_failure(exc)
            self.complete_button.setEnabled(True)

    def _on_link(self, result):
        try:
            if not self._alive:
                return
            self.send_button.setEnabled(True)
            if result == "ok":
                self.status_label.setText(CHECK_EMAIL)
                self._show_paste()
            elif result == "invalid":
                self.status_label.setText(INVALID_EMAIL)
            elif result == "unconfigured":
                self.status_label.setText(NOT_CONFIGURED)
            else:
                self.status_label.setText(SEND_FAILED)
        except Exception as exc:
            _log_failure(exc)

    def _on_complete(self, result):
        try:
            if not self._alive:
                return
            self.complete_button.setEnabled(True)
            if result == "ok":
                self.accept()
                return
            if result == "invalid" or result == "unconfigured":
                self.status_label.setText(LINK_FAILED)
                return
            self.status_label.setText(SIGN_IN_FAILED)
        except Exception as exc:
            _log_failure(exc)

    def _show_paste(self):
        self.link_edit.show()
        self.complete_button.show()
        self.complete_button.setDefault(True)
