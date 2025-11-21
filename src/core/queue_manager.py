"""Background processing queue for documents."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..utils.config import MAX_WORKERS
from ..utils.logger import logger

StatusCallback = Callable[[str, Path], None]

@dataclass(frozen=True)
class ProcessingJob:
    """Represents a document to be processed."""

    file_path: Path
    mode: str  # "online" or "local"

class ProcessingQueue:
    """Thread-based queue that processes documents sequentially."""

    def __init__(
        self,
        processor,
        *,
        workers: int | None = None,
        on_started: StatusCallback | None = None,
        on_finished: StatusCallback | None = None,
        on_failed: Callable[[Path, Exception | None, None]] = None,
    ) -> None:
        self.processor = processor
        self.workers = max(1, workers or MAX_WORKERS)
        self.on_started = on_started
        self.on_finished = on_finished
        self.on_failed = on_failed

        self._queue: queue.Queue[ProcessingJob] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start worker threads."""
        if self._threads:
            return
        logger.info("Starting processing queue with %s worker(s)", self.workers)
        for index in range(self.workers):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"ProcessorWorker-{index + 1}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        """Signal workers to stop and wait for completion."""
        logger.info("Stopping processing queue")
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=1.0)
        self._threads.clear()

    def enqueue(self, file_path: Path, *, mode: str = "online") -> None:
        """Add a document to the processing queue."""
        job = ProcessingJob(file_path=file_path, mode=mode)
        logger.info("Queued document: %s", file_path)
        self._queue.put(job)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self.on_started:
                self.on_started("started", job.file_path)

            try:
                # Forward the chosen mode to the processor
                self.processor.process(job.file_path, mode=job.mode)
                if self.on_finished:
                    self.on_finished("finished", job.file_path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Processing failed for %s", job.file_path)
                if self.on_failed:
                    self.on_failed(job.file_path, exc)
            finally:
                self._queue.task_done()
