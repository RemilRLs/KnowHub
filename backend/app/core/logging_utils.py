import logging
import os

from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  
_LOGGER_INITIALIZED = False


def init_logging(
    *,
    log_file: str = os.path.join(BASE_DIR, "logs/app.log"),
    level: str = os.getenv("LOG_LEVEL", "INFO"),
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Initializes the logging configuration for the application.
    This function sets up a rotating file handler and a console stream handler
    for logging. It ensures that logs are written to both a file and the console
    with a consistent format. The log file is automatically rotated when it
    reaches a specified size, and a limited number of backup files are kept.
    Args:
        log_file (str): The path to the log file. Defaults to "logs/app.log".
        level (str): The logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
            Defaults to the value of the "LOG_LEVEL" environment variable, or "INFO" if not set.
        max_bytes (int): The maximum size (in bytes) of the log file before it is rotated.
            Defaults to 10 MB.
        backup_count (int): The number of backup log files to keep. Defaults to 5.
    Returns:
        None
    Notes:
        - This function ensures that the logging configuration is only initialized once.
        - The log directory is created automatically if it does not exist.
    """
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level.upper())

    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)

    _LOGGER_INITIALIZED = True