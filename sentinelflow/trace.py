"""Per-run trace logging. Every agent call, verdict, and transition is one
JSONL event so a run can be replayed and shown step by step."""

import json
from datetime import datetime, timezone
from pathlib import Path


class Tracer:
    def __init__(self, runs_dir: str, case_id: str):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = Path(runs_dir) / case_id / stamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._file = open(self.run_dir / "trace.jsonl", "a")

    def event(self, kind: str, **data) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            **data,
        }
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()

    def write_artifact(self, name: str, content: str) -> Path:
        path = self.run_dir / name
        path.write_text(content)
        return path

    def close(self) -> None:
        self._file.close()
