"""Logging in to pogocoordinates.com, as docs/spawn_watch.md, *Login*, describes it."""

import logging
import time

import playwright.sync_api

from pokemon_go_collection import secret_files as secret_files_m
from pokemon_go_collection.sources import pogocoordinates as pogocoordinates_m

logger = logging.getLogger(__name__)


def log_in_with_browser(
    profile_folder_path, token_file_path, timeout_duration=600, poll_duration=3
):
    """Open Chrome for the user to log in, and store the token once the service accepts it.

    Returns the account's name. Raises TimeoutError when no accepted login
    appears within `timeout_duration`, in seconds.
    """
    with playwright.sync_api.sync_playwright() as playwright_driver:
        context = playwright_driver.chromium.launch_persistent_context(
            str(profile_folder_path), channel="chrome", headless=False
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(f"{pogocoordinates_m.SITE_URL}/search", wait_until="load")
            rejected_tokens = set()
            deadline = time.monotonic() + timeout_duration
            while time.monotonic() < deadline:
                token = _read_site_token(context, pogocoordinates_m.SITE_URL)
                if token is not None and token not in rejected_tokens:
                    try:
                        account = pogocoordinates_m.fetch_account(token)
                    except pogocoordinates_m.PogocoordinatesAuthError:
                        rejected_tokens.add(token)
                    else:
                        secret_files_m.write_secret(token_file_path, token)
                        logger.info("pogocoordinates.com login stored")
                        return account["display_name"]
                time.sleep(poll_duration)
        finally:
            context.close()
    raise TimeoutError("No login accepted by pogocoordinates.com")


def _read_site_token(context, site_url):
    """Return the token a tab of the site holds, or None.

    A login navigates to Discord and back, possibly in another tab, and a
    navigation destroys the page an evaluation runs in: every tab on the site
    is tried, and a failed evaluation is not an error.
    """
    for page in context.pages:
        if not page.url.startswith(site_url):
            continue
        try:
            token = page.evaluate("() => localStorage.getItem('jwt')")
        except playwright.sync_api.Error:
            continue
        if token:
            return token
    return None
