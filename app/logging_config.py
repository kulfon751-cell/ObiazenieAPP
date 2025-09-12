import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: str | Path | None = None, level: int = logging.INFO):
    """Configure root logger. If log_file is provided, enable rotating file handler.

    Keep this minimal so it works in CI and in packaged exe.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        fh.setFormatter(formatter)
        root.addHandler(fh)

    root.setLevel(level)
