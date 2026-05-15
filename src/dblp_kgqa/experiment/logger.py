import logging
from pathlib import Path

from rich.logging import RichHandler

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s >> %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_file_path: Path,
    logger_name: str = "experiment",
    append: bool = False,
) -> logging.Logger:
    
    log_file_path = Path(log_file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

    # File handler
    file_handler = logging.FileHandler(
        log_file_path,
        mode="a" if append else "w",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Stream handler
    stream_handler = RichHandler(rich_tracebacks=True)
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(logging.Formatter("%(name)s >> %(message)s"))

    # Root logger
    logging.basicConfig(
        level=logging.WARNING,
        force=True,
        handlers=[stream_handler, file_handler],
    )

    # logging level for package and main
    logging.getLogger("dblp_kgqa").setLevel(logging.DEBUG)
    logging.getLogger(logger_name).setLevel(logging.DEBUG)

    logger = logging.getLogger(logger_name)
    logger.info("Logging initialized")

    return logger
