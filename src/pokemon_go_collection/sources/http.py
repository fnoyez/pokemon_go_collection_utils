import errno
import json
import socket
import urllib.error
import urllib.request

# Some sites refuse requests that do not look like they come from a browser.
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) pokemon-go-collection"
# The failures to connect that leave no request sent, besides an unresolved
# name: no network, no route to the host, a refused connection.
_UNSENT_REQUEST_ERRNOS = {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ECONNREFUSED}


def fetch_bytes(url, timeout_duration=60):
    """Return the body of `url`; `timeout_duration` is in seconds."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_duration) as response:
        return response.read()


def fetch_json(url, body=None, headers=None, timeout_duration=60):
    """Return the JSON content of `url`, or None for an empty response.

    A `body` is sent as JSON, in a POST. `timeout_duration` is in seconds.
    """
    request_headers = {"User-Agent": _USER_AGENT}
    if headers is not None:
        request_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout_duration) as response:
        content = response.read()
    return json.loads(content) if content else None


def is_unsent_request_error(error):
    """Tell whether `error` stopped a request before it reached the server.

    A name not resolved, as on a computer waking up before its network, is one;
    an error response or a timeout, which the server may have seen the request
    of, is not.
    """
    if not isinstance(error, urllib.error.URLError) or isinstance(
        error, urllib.error.HTTPError
    ):
        return False
    return isinstance(error.reason, socket.gaierror) or (
        isinstance(error.reason, OSError)
        and error.reason.errno in _UNSENT_REQUEST_ERRNOS
    )
