"""Immutable, self-describing storage for generation runs.

Written after several results had to be recomputed and one had to be retracted
because stored data could not be trusted. Three failures drove the design:

1. **Answers were truncated at 2000 chars** (30% of them), so they could not be
   re-scored later — a clipped answer fails every length constraint.
2. **Metrics were frozen into run outputs.** When the extractor changed, every
   stored summary silently became stale, and one comparison mixed two instruments.
3. **Runs overwrote each other** and carried no record of the model, sampling
   parameters or code version that produced them.

The rules this enforces:

* **Generations are raw and complete.** Full prompt, full reasoning, full answer.
  Nothing derived is stored alongside them.
* **Metrics are never stored here.** Anything computable from the generations is
  recomputed downstream, so a change in analysis code cannot leave stale numbers
  on disk.
* **Every run is self-describing.** Model, sampling parameters, git commit,
  host, and timestamps travel with the data.
* **Runs are immutable.** A run id may not be written twice.

Layout::

    runs/<run_id>/meta.json          provenance
    runs/<run_id>/generations.jsonl  one row per generation, full text
"""
from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import time
from typing import Any, Iterator

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"


def git_state() -> dict:
    """Record the exact code that produced a run, including uncommitted work."""
    def _run(*args: str) -> str | None:
        try:
            return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                                  timeout=10).stdout.strip() or None
        except Exception:  # noqa: BLE001
            return None

    sha = _run("git", "rev-parse", "HEAD")
    dirty = _run("git", "status", "--porcelain")
    return {"git_sha": sha, "git_dirty": bool(dirty),
            "git_dirty_files": len(dirty.splitlines()) if dirty else 0}


class RunWriter:
    """Append-only writer for one run. Refuses to overwrite an existing run."""

    def __init__(self, run_id: str, meta: dict[str, Any], root: pathlib.Path | None = None):
        self.dir = (root or RUNS_DIR) / run_id
        if self.dir.exists():
            raise FileExistsError(
                f"run {run_id!r} already exists at {self.dir}. Runs are immutable; "
                "use a new run id rather than overwriting evidence."
            )
        self.dir.mkdir(parents=True)
        self.run_id = run_id
        self.n = 0
        self._t0 = time.time()
        self._meta = {
            "run_id": run_id,
            "host": socket.gethostname(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **git_state(),
            **meta,
        }
        (self.dir / "meta.json").write_text(json.dumps(self._meta, indent=2))
        self._fh = open(self.dir / "generations.jsonl", "w", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        """Store one generation. Text fields must NOT be pre-truncated."""
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.n += 1
        if self.n % 500 == 0:
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def close(self, extra: dict[str, Any] | None = None) -> pathlib.Path:
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()
        self._meta.update({
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_s": round(time.time() - self._t0, 1),
            "n_generations": self.n,
            **(extra or {}),
        })
        (self.dir / "meta.json").write_text(json.dumps(self._meta, indent=2))
        return self.dir

    def __enter__(self) -> "RunWriter":
        return self

    def __exit__(self, *exc) -> None:
        if not self._fh.closed:
            self.close()


def read_run(run_id: str, root: pathlib.Path | None = None
             ) -> tuple[dict, Iterator[dict]]:
    """-> (meta, generator over generation records)."""
    d = (root or RUNS_DIR) / run_id
    meta = json.loads((d / "meta.json").read_text())

    def _iter() -> Iterator[dict]:
        with open(d / "generations.jsonl", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

    return meta, _iter()


def list_runs(root: pathlib.Path | None = None) -> list[dict]:
    base = root or RUNS_DIR
    if not base.exists():
        return []
    out = []
    for d in sorted(base.iterdir()):
        f = d / "meta.json"
        if f.exists():
            try:
                out.append(json.loads(f.read_text()))
            except ValueError:
                continue
    return out


def verify_run(run_id: str, root: pathlib.Path | None = None) -> dict:
    """Integrity check. Run this before analysing any run.

    A silent process collision once produced a 22,301-row file of interleaved
    JSON that would otherwise have been analysed as valid data.
    """
    meta, records = read_run(run_id, root)
    seen: set[tuple] = set()
    n = dupes = malformed = truncated = 0
    for r in records:
        n += 1
        key = (r.get("item_key"), r.get("condition"), r.get("sample"))
        if key in seen:
            dupes += 1
        seen.add(key)
        if not r.get("answer") and not r.get("reasoning"):
            malformed += 1
        if r.get("finish_reason") == "length":
            truncated += 1
    expected = meta.get("n_generations")
    return {
        "run_id": run_id,
        "rows": n,
        "expected": expected,
        "count_matches": expected is None or n == expected,
        "duplicate_keys": dupes,
        "empty_records": malformed,
        "hit_token_limit": truncated,
        "ok": (expected is None or n == expected) and dupes == 0,
    }
