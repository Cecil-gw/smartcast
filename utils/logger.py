import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.system_utils import writable_data_dir


LOG_DIR = writable_data_dir() / "logs"


def setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("smartcast")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOG_DIR / "smartcast.log",
        maxBytes=5_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
