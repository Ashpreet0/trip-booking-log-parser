import json
import unittest

from summarize import normalize, summarize


def line(service, message, ts="2025-03-10T03:00:00.000Z", level="ERROR"):
    return json.dumps({"timestamp": ts, "level": level, "service": service, "message": message})


class SummarizeTest(unittest.TestCase):
    def test_normalize_collapses_same_failure(self):
        # lines 45 and 60 of trip_booking.log
        a = normalize("Booking request req_2c8f15a9d04e failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30")
        b = normalize("Booking request req_3e7b0f19c2d8 failed for trip b1a59e3d-7f02-4c68-9d4e-0a8f2c6b5e13 status=503 retry_after=60")
        self.assertEqual(a, b)
        self.assertEqual(a, "Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>")

    def test_groups_by_service_and_message_sorted_by_count(self):
        lines = [
            line("a", "timed out after 100ms", ts="2025-03-10T03:00:02.000Z"),
            line("b", "timed out after 200ms", ts="2025-03-10T03:00:01.000Z"),  # same message, other service
            line("a", "timed out after 300ms", ts="2025-03-10T03:00:03.000Z"),
            line("a", "ok", level="INFO"),
            "not json",
        ]
        out = summarize(lines)
        self.assertEqual(out["lines_processed"], 4)
        self.assertEqual(out["error_lines"], 3)
        self.assertEqual([(c["service"], c["count"]) for c in out["clusters"]], [("a", 2), ("b", 1)])
        self.assertEqual(out["clusters"][0]["first_seen"], "2025-03-10T03:00:02.000Z")
        self.assertEqual(out["clusters"][0]["last_seen"], "2025-03-10T03:00:03.000Z")


if __name__ == "__main__":
    unittest.main()
