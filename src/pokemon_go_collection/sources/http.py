import urllib.request

# Some sites refuse requests that do not look like they come from a browser.
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) pokemon-go-collection"


def fetch_bytes(url, timeout_duration=60):
    """Return the body of `url`; `timeout_duration` is in seconds."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_duration) as response:
        return response.read()
