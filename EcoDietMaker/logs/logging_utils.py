"""Logging configuration helpers for the CLI and tests."""

import logging


def setup_logging(
    verbosity: int,
    log_file: str | None = None,
) -> None:
    """Configure logging based on verbosity and optional log file.

    Parameters
    ----------
    verbosity : int
        Count of ``-v`` flags; higher means more verbose.
    log_file : str or None
        Path to a log file to write to, or ``None`` to log to stderr only.
    """

    level = logging.WARNING if verbosity <= 0 else (logging.INFO if verbosity == 1 else logging.DEBUG)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(
            logging.FileHandler(
                log_file,
                encoding="utf-8",
            )
        )
    # Reset prior basicConfig (tests or multiple CLI invocations may have configured logging already)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname).1s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,  # reset prior basicConfig runs
    )
