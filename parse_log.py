"""Summarise a trip booking JSON Lines log: processed, error-level and malformed counts."""
import json
import sys

REQUIRED = ("timestamp", "level", "service", "message")


def parse_line(line):
    """Return the record if the line is usable, else None."""
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    if not all(isinstance(record.get(k), str) and record[k].strip() for k in REQUIRED):
        return None
    return record


def summarize(lines):
    counts = {"processed": 0, "error": 0, "malformed": 0}
    for line in lines:
        record = parse_line(line)
        if record is None:
            counts["malformed"] += 1
            continue
        counts["processed"] += 1
        # normalise so "error" / " Error " would still count; this log only uses "ERROR"
        if record["level"].strip().upper() == "ERROR":
            counts["error"] += 1
    return counts


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 parse_log.py <log-file>")
    with open(sys.argv[1], encoding="utf-8") as f:
        counts = summarize(f)  # iterates the file one line at a time
    print(f"processed: {counts['processed']}")
    print(f"error-level: {counts['error']}")
    print(f"malformed: {counts['malformed']}")


if __name__ == "__main__":
    main()
