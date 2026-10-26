import errno
import socket
import urllib.error
from email.message import Message

import pytest

from pokemon_go_collection.sources import http as http_m


def get_is_unsent_request_error_test_data():
    test_cases = [
        {
            "id": "unresolved-name",
            "error": urllib.error.URLError(
                socket.gaierror(-3, "Temporary failure in name resolution")
            ),
            "expected_output": True,
        },
        {
            "id": "network-unreachable",
            "error": urllib.error.URLError(
                OSError(errno.ENETUNREACH, "Network is unreachable")
            ),
            "expected_output": True,
        },
        {
            "id": "connection-refused",
            "error": urllib.error.URLError(
                ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused")
            ),
            "expected_output": True,
        },
        {
            "id": "connection-reset",
            "error": urllib.error.URLError(
                ConnectionResetError(errno.ECONNRESET, "Connection reset by peer")
            ),
            "expected_output": False,
        },
        {
            "id": "timeout",
            "error": urllib.error.URLError(TimeoutError("timed out")),
            "expected_output": False,
        },
        {
            "id": "bare-timeout",
            "error": TimeoutError("The read operation timed out"),
            "expected_output": False,
        },
        {
            "id": "error-response",
            "error": urllib.error.HTTPError(
                "https://example.com", 502, "Bad Gateway", Message(), None
            ),
            "expected_output": False,
        },
    ]

    return [
        pytest.param(
            test_case["error"],
            test_case["expected_output"],
            id=test_case["id"],
        )
        for test_case in test_cases
    ]


@pytest.mark.parametrize(
    "error,expected_output", get_is_unsent_request_error_test_data()
)
def test_is_unsent_request_error(error, expected_output):
    assert http_m.is_unsent_request_error(error) == expected_output
