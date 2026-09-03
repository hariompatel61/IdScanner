"""
Persistent Scan Logger — Records detailed telemetry and extraction results for every scan.
Logs are persisted to logs/scan_history.jsonl and cached in memory for instant retrieval.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "scan_history.jsonl")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)


class ScanLogger:
    def __init__(self, max_in_memory: int = 100):
        self._max_in_memory = max_in_memory
        self._history: deque = deque(maxlen=max_in_memory)
        self._lock = threading.Lock()
        self._load_existing_logs()

    def _load_existing_logs(self):
        """Loads last N logs from disk on startup."""
        if not os.path.exists(LOG_FILE):
            return
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-self._max_in_memory:]:
                    line = line.strip()
                    if line:
                        try:
                            self._history.append(json.loads(line))
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Failed to load scan history logs: {e}")

    def _redact_value(self, key: str, value: Any) -> Any:
        if not value or not isinstance(value, str): return value
        key = key.lower()
        if 'aadhaar' in key and len(value) >= 4:
            return 'X' * (len(value)-4) + value[-4:]
        if 'pan' in key and len(value) >= 4:
            return 'X' * (len(value)-4) + value[-4:]
        if 'passport' in key and len(value) >= 4:
            return 'X' * (len(value)-4) + value[-4:]
        return value

    def log_scan(
        self,
        request_id: str,
        document_type: str,
        identifier: Optional[str],
        fields: Dict[str, Any],
        confidence: float,
        processing_time_ms: int,
        overall_status: str,
        client_ip: Optional[str] = None,
        error_code: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records a scan event both in memory and persistently to disk.
        """
        redacted_fields = {}
        for k, v in fields.items():
            if hasattr(v, "value"): # if it's a FieldResult
                redacted_fields[k] = self._redact_value(k, v.value)
            else:
                redacted_fields[k] = self._redact_value(k, v)
            
        redacted_identifier = self._redact_value(document_type, identifier) if identifier else identifier
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "document_type": document_type,
            "identifier": redacted_identifier,
            "fields": redacted_fields,
            "confidence": round(confidence, 4),
            "processing_time_ms": processing_time_ms,
            "overall_status": overall_status,
            "client_ip": client_ip or "127.0.0.1",
            "error_code": error_code,
            "message": message,
        }

        with self._lock:
            self._history.appendleft(entry)
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write scan log to {LOG_FILE}: {e}")

        return entry

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent scan logs (newest first)."""
        with self._lock:
            return list(self._history)[:limit]

    def clear_logs(self):
        """Clears in-memory and persistent log history."""
        with self._lock:
            self._history.clear()
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "w", encoding="utf-8") as f:
                        f.write("")
                except Exception as e:
                    logger.error(f"Failed to clear log file: {e}")


scan_logger = ScanLogger()
