"""
TRIPPY Backend — Trip Persistence Repository

Provides durable persistence for planned trips.
Supports in-memory caching with atomic file-based persistence,
gracefully handling read-only or restricted environments.
"""

import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from app.config import settings
from app.schemas.trip import TripResult

logger = logging.getLogger("trippy.storage")


class TripRepository:
    """
    Thread-safe repository for persisting and retrieving TripResult objects.
    Stores trips in-memory and mirrors to disk (JSON) when filesystem is writable.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self._lock = Lock()
        self._trips: Dict[str, TripResult] = {}
        self.storage_dir = Path(storage_dir or settings.storage_dir)
        self.storage_file = self.storage_dir / "trips.json"
        self._is_writable = False
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Sets up storage directory and loads any existing persisted trips."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = self.storage_dir / ".perm_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            self._is_writable = True
        except Exception as exc:
            logger.warning(
                f"Storage directory '{self.storage_dir}' is not writable ({exc}). "
                "Falling back to in-memory persistence only."
            )
            self._is_writable = False

        if self._is_writable and self.storage_file.exists():
            try:
                raw_data = self.storage_file.read_text(encoding="utf-8")
                loaded = json.loads(raw_data)
                for item in loaded:
                    try:
                        trip = TripResult.model_validate(item)
                        self._trips[trip.trip_id] = trip
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse stored trip: {parse_err}")
                logger.info(f"Loaded {len(self._trips)} trips from persistent storage.")
            except Exception as read_err:
                logger.warning(f"Could not read persistence file: {read_err}")

    def save(self, trip: TripResult) -> TripResult:
        """Saves a trip in memory and writes to disk if writable."""
        with self._lock:
            self._trips[trip.trip_id] = trip
            self._flush_to_disk()
            return trip

    def get(self, trip_id: str) -> Optional[TripResult]:
        """Retrieves a trip by its unique ID."""
        with self._lock:
            return self._trips.get(trip_id)

    def list_recent(self, limit: int = 10) -> List[TripResult]:
        """Returns the most recently planned trips up to limit."""
        with self._lock:
            # Return in reverse chronological order
            trips_list = list(self._trips.values())
            return trips_list[-limit:]

    def count(self) -> int:
        """Returns total count of stored trips."""
        with self._lock:
            return len(self._trips)

    def _flush_to_disk(self) -> None:
        """Atomically flushes in-memory trips to JSON on disk."""
        if not self._is_writable:
            return
        try:
            temp_file = self.storage_dir / f"trips_{os.getpid()}.tmp"
            data = [trip.model_dump(mode="json") for trip in self._trips.values()]
            temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_file.replace(self.storage_file)
        except Exception as exc:
            logger.error(f"Failed to flush trips to disk: {exc}")

    def health_status(self) -> dict:
        """Returns storage health metrics for readiness checks."""
        return {
            "status": "ok",
            "storage_dir": str(self.storage_dir),
            "is_writable": self._is_writable,
            "total_trips": self.count(),
        }


# Global repository instance
trip_repository = TripRepository()
