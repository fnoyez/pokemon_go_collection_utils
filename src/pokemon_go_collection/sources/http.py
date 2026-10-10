import json
import urllib.request

# Some sites refuse requests that do not look like they come from a browser.
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) pokemon-go-collection"


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
