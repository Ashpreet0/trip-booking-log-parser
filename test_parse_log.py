import unittest

from parse_log import summarize

OK = '{"timestamp": "t", "level": "%s", "service": "s", "message": "m"}'


class SummarizeTest(unittest.TestCase):
    def test_counts_and_skips_malformed(self):
        lines = [
            "[",                                            # array bracket line
            OK % "INFO" + ",",                              # trailing comma is stripped
            OK % "ERROR",
            OK % " error ",                                 # spelling variant still counts
            "not json",                                     # invalid JSON
            "[1, 2]",                                       # valid JSON, not an object
            '{"timestamp": "t", "level": "ERROR", "service": "s"}',  # missing message
            "",                                             # blank line
        ]
        self.assertEqual(summarize(lines), {"processed": 3, "error": 2, "malformed": 5})

    def test_real_log_adds_up(self):
        with open("trip_booking.log", encoding="utf-8") as f:
            lines = f.readlines()
        counts = summarize(lines)
        self.assertEqual(counts["processed"] + counts["malformed"], len(lines))


if __name__ == "__main__":
    unittest.main()
