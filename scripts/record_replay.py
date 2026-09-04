from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    # Direct script execution otherwise exposes only scripts/ on sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import RuntimeSettings
from backend.core.replay import ReplayArchive, ReplayError, record_job
from backend.storage.database import Database


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record genuine terminal AegisAgent jobs for offline replay"
    )
    parser.add_argument("job_ids", nargs="+", help="terminal job ids to record")
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--replay-dir", type=Path)
    args = parser.parse_args()

    settings = RuntimeSettings()
    database = Database((args.db_path or settings.db_path).resolve())
    connection = database.init_db()
    archive = ReplayArchive((args.replay_dir or settings.replay_dir).resolve())
    try:
        for job_id in args.job_ids:
            job = database.jobs(connection).get(job_id)
            if job is None:
                raise ReplayError(f"job not found: {job_id}")
            recording_id = f"{job.scenario or 'run'}-{job.id.removeprefix('job_')}"
            summary = record_job(
                recording_id,
                job_id,
                archive=archive,
                jobs=database.jobs(connection),
                findings=database.findings(connection),
                attempts=database.attempts(connection),
                events=database.events(connection),
                artifacts=database.artifacts(connection),
            )
            print(
                f"recorded {summary.id}: decision={summary.final_decision} "
                f"attempts={summary.attempts} events={summary.event_count}"
            )
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
