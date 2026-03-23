import logging


def configure_logging() -> None:
    # Use a consistent log format so each message shows time, level, and module source.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
