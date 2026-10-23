"""Logging: a plain text file in logs/ (easy to send to Claude) plus a queue for the GUI."""

from __future__ import annotations

import logging
import logging.handlers
import os
import queue

from .config import LOGS_DIR

gui_queue: "queue.Queue[str]" = queue.Queue()


class _QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            gui_queue.put_nowait(self.format(record))
        except Exception:
            pass


def setup(level=logging.INFO) -> str:
    os.makedirs(LOGS_DIR, exist_ok=True)
    path = os.path.join(LOGS_DIR, "beeline.log")
    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.handlers.RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    qh = _QueueHandler()
    qh.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    root.addHandler(qh)
    return path
