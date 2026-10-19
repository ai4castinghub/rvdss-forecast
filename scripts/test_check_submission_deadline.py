import unittest
from datetime import datetime, timezone

from check_submission_deadline import submission_errors


class SubmissionDeadlineTests(unittest.TestCase):
    path = "model-output/team-model/2026-10-24-team-model.csv"

    def test_accepts_exact_deadline(self):
        # October is still daylight saving time in Toronto.
        timestamp = datetime(2026, 10, 25, 3, 30, tzinfo=timezone.utc)
        self.assertEqual(submission_errors([self.path], timestamp), [])

    def test_rejects_after_deadline(self):
        timestamp = datetime(2026, 10, 25, 3, 30, 1, tzinfo=timezone.utc)
        self.assertEqual(len(submission_errors([self.path], timestamp)), 1)

    def test_accepts_standard_time_deadline(self):
        path = "model-output/team-model/2027-01-09-team-model.csv"
        timestamp = datetime(2027, 1, 10, 4, 30, tzinfo=timezone.utc)
        self.assertEqual(submission_errors([path], timestamp), [])

    def test_rejects_before_window(self):
        timestamp = datetime(2026, 10, 17, 3, 59, tzinfo=timezone.utc)
        self.assertEqual(len(submission_errors([self.path], timestamp)), 1)

    def test_ignores_historical_forecast(self):
        path = "model-output/team-model/2025-10-25-team-model.csv"
        timestamp = datetime(2026, 10, 25, tzinfo=timezone.utc)
        self.assertEqual(submission_errors([path], timestamp), [])


if __name__ == "__main__":
    unittest.main()
