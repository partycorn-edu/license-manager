"""Для HEALTHCHECK: воркер жив, если файл-маячок обновлялся недавно."""
import pathlib
import sys
import time

from common.config import settings

f = pathlib.Path("/tmp/worker.alive")
limit = settings.worker_interval * 3 + 30
sys.exit(0 if f.exists() and time.time() - f.stat().st_mtime < limit else 1)
