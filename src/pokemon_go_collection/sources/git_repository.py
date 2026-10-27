"""The sibling repositories the sources are cloned in, such as `../game_masters`."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def pull_repository(repository_folder_path):
    """Fast-forward the repository; return an error message, or None."""
    completed_process = subprocess.run(
        ["git", "-C", str(repository_folder_path), "pull", "--ff-only"],
        capture_output=True,
        text=True,
    )
    if completed_process.returncode != 0:
        return f"git pull of {repository_folder_path} failed: {completed_process.stderr.strip()}"
    logger.info(f"{repository_folder_path} pulled: {completed_process.stdout.strip()}")
    return None
