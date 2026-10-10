import datetime
import logging


class UtcFormatter(logging.Formatter):
    """Render each record's timestamp in UTC, with its offset."""

    def formatTime(self, record, datefmt=None):
        record_time = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        )
        return record_time.isoformat(sep=" ", timespec="milliseconds")


def setup_logging(logging_level=logging.INFO, display_logger_name=False):
    """Set the root level and apply the shared format to every root handler.

    The level is set on the root logger directly, and a handler is added only
    when there is none, because `logging.basicConfig` does nothing once a
    handler exists.
    """
    format_parts = ["%(asctime)s"]
    if display_logger_name:
        format_parts.append("%(name)-15s")
    format_parts.extend(["%(levelname)-8s", "%(message)s"])
    formatter = UtcFormatter(" :: ".join(format_parts))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
