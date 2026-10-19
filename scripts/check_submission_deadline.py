"""Enforce the 2026-27 submission window using the PR event timestamp."""

import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


FIRST_REFERENCE_DATE = date(2026, 10, 24)
LAST_REFERENCE_DATE = date(2027, 5, 29)
TIMEZONE = ZoneInfo("America/Toronto")
FORECAST_PATH = re.compile(r"^model-output/[^/]+/(\d{4}-\d{2}-\d{2})-[^/]+\.csv$")


def submission_errors(paths, event_timestamp):
    """Return errors for changed 2026-27 forecast files at a PR event time."""
    event_time = event_timestamp.astimezone(TIMEZONE)
    errors = []
    for path in paths:
        match = FORECAST_PATH.fullmatch(path)
        if not match:
            continue
        reference_date = date.fromisoformat(match.group(1))
        if not FIRST_REFERENCE_DATE <= reference_date <= LAST_REFERENCE_DATE:
            continue
        opening = datetime.combine(reference_date - timedelta(days=6), time.min, TIMEZONE)
        deadline = datetime.combine(reference_date, time(23, 30), TIMEZONE)
        if not opening <= event_time <= deadline:
            errors.append(
                f"{path}: PR opened/updated at {event_time.isoformat()} outside "
                f"{opening.isoformat()} to {deadline.isoformat()}"
            )
    return errors


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    pull_request = event["pull_request"]
    # The webhook payload records the PR state when this check was triggered.
    event_timestamp = datetime.fromisoformat(pull_request["updated_at"].replace("Z", "+00:00"))
    paths = Path("changed_files.txt").read_text(encoding="utf-8").splitlines()
    errors = submission_errors(paths, event_timestamp)
    if errors:
        print("Submission deadline check failed:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("2026-27 submission deadline check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
