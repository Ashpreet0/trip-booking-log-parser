"""Summarise ERROR lines of a JSON Lines incident log into the top five clusters, as one JSON object on stdout."""
import json
import re
import sys

from parse_log import parse_line

# NORMALISATION_RULES.md, in order: specific shapes first, the catch-all number rule last.
RULES = [
    (re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"), "<ts>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<uuid>"),
    (re.compile(r"\breq_[0-9a-f]+\b"), "<req>"),
    (re.compile(r"\b[a-z]_\d+\b"), "<id>"),
    (re.compile(r"(?<![\w.-])\d+(?:\.\d+)?"), "<n>"),
]


def normalize(message):
    """Swap the changing parts of a message for placeholder tokens."""
    for pattern, token in RULES:
        message = pattern.sub(token, message)
    return message


def summarize(lines, top=5):
    processed = 0
    clusters = {}
    for line in lines:
        record = parse_line(line)
        if record is None:
            continue
        processed += 1
        if record["level"].strip().upper() != "ERROR":
            continue
        key = (record["service"], normalize(record["message"]))
        ts = record["timestamp"]
        c = clusters.get(key)
        if c is None:
            clusters[key] = {"message": key[1], "service": key[0], "count": 1, "first_seen": ts, "last_seen": ts}
        else:
            c["count"] += 1
            c["first_seen"] = min(c["first_seen"], ts)  # ISO 8601 UTC strings sort in time order
            c["last_seen"] = max(c["last_seen"], ts)
    ranked = sorted(clusters.values(), key=lambda c: (-c["count"], c["first_seen"]))  # ties: earliest first
    return {
        "lines_processed": processed,
        "error_lines": sum(c["count"] for c in clusters.values()),
        "clusters": ranked[:top],
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 summarize.py <log-file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        print(json.dumps(summarize(f), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
