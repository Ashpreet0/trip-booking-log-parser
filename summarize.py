"""Summarise ERROR lines of a JSON Lines incident log into the top five clusters, as one JSON object on stdout."""
import json
import re
import sys
from datetime import datetime

from parse_log import parse_line

# NORMALISATION_RULES.md, in order: specific shapes first, the catch-all number rule last.
RULES = [
    (re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"), "<TS>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<UUID>"),
    (re.compile(r"\breq_[0-9a-f]+\b"), "<REQ>"),
    (re.compile(r"\b[a-z]_\d+\b"), "<ID>"),
    (re.compile(r"(?<![\w.-])\d+(?:\.\d+)?"), "<NUM>"),
]


def normalize(message):
    """Swap the changing parts of a message for placeholder tokens."""
    for pattern, token in RULES:
        message = pattern.sub(token, message)
    return message


def summarize(lines, top=5):
    processed = 0
    clusters = {}
    times = {}  # key -> [first, last] as datetimes; the output keeps the original strings
    for line in lines:
        record = parse_line(line)
        if record is None:
            continue
        processed += 1
        if record["level"].strip().upper() != "ERROR":
            continue
        key = (record["service"], normalize(record["message"]))
        ts = record["timestamp"]
        when = datetime.fromisoformat(ts)  # parse_line guarantees ISO 8601 with a timezone
        c = clusters.get(key)
        if c is None:
            clusters[key] = {"normalised_message": key[1], "service": key[0], "count": 1, "first_seen": ts, "last_seen": ts}
            times[key] = [when, when]
            continue
        c["count"] += 1
        t = times[key]
        if when < t[0]:
            t[0], c["first_seen"] = when, ts
        if when > t[1]:
            t[1], c["last_seen"] = when, ts
    ranked = sorted(clusters, key=lambda k: (-clusters[k]["count"], times[k][0]))  # ties: earliest first
    return {
        "total_lines_processed": processed,
        "total_error_lines": sum(c["count"] for c in clusters.values()),
        "clusters": [clusters[k] for k in ranked[:top]],
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 summarize.py <log-file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        print(json.dumps(summarize(f), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
