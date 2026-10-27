import unittest

from parse_log import summarize

OK = '{"timestamp": "2025-03-10T03:00:00.000Z", "level": "%s", "service": "s", "message": "m"}'


class SummarizeTest(unittest.TestCase):
    def test_counts_and_skips_malformed(self):
        lines = [
            OK % "INFO",
            OK % "INFO" + ",",                              # trailing comma: not standalone JSON
            OK % "ERROR",
            OK % " error ",                                 # spelling variant still counts
            "not json",                                     # invalid JSON
            "[1, 2]",                                       # valid JSON, not an object
            '{"timestamp": "2025-03-10T03:00:00.000Z", "level": "ERROR", "service": "s"}',  # missing message
            "",                                             # blank line
            '{"timestamp": "yesterday", "level": "ERROR", "service": "s", "message": "m"}',  # not ISO 8601
            '{"timestamp": "2025-03-10T03:00:00", "level": "ERROR", "service": "s", "message": "m"}',  # no timezone
        ]
        self.assertEqual(summarize(lines), {"processed": 3, "error": 2, "malformed": 7})

    def test_real_log_adds_up(self):
        with open("trip_booking.log", encoding="utf-8") as f:
            lines = f.readlines()
        counts = summarize(lines)
        self.assertEqual(counts["processed"] + counts["malformed"], len(lines))


if __name__ == "__main__":
    unittest.main()
