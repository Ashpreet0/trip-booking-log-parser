# trip-booking-log-parser

Streams the trip booking incident log one line at a time and prints how many lines were processed, how many are error-level, and how many were malformed and skipped.

## Normalisation rules

Message normalisation for clustering (UUIDs, timestamps, request IDs, numeric IDs, numbers → placeholder tokens) is specified in [NORMALISATION_RULES.md](NORMALISATION_RULES.md). The rules below are the parser's line-validity rules.

- Each line is parsed on its own with `json.loads`; nothing is joined across lines and the file is never loaded whole.
- A line is **malformed** if it is not valid JSON on its own, is not a JSON object, or is missing any of `timestamp`, `level`, `service`, `message` as a non-empty string. Blank lines are malformed too.
- Malformed lines are counted in their own total and skipped; the parser never stops on a bad line.
- `level` is compared after `strip().upper()`, so `ERROR`, `error` and ` Error ` would all count as error-level. This log only ever spells it `ERROR`.

## Summary output

Command, run from the repo root:

```bash
python3 parse_log.py trip_booking.log
```

Output, copied as-is:

```
processed: 80
error-level: 24
malformed: 0
```

Line count of the same file:

```bash
wc -l trip_booking.log
```

```
      80 trip_booking.log
```

- **Total lines: 80**
- **Processed: 80**
- **Malformed: 0**
- Processed + malformed = 80 + 0 = 80 = total lines.

The same sum, computed from the parser's output rather than typed:

```bash
python3 parse_log.py trip_booking.log | awk -F': ' '/^processed/{p=$2} /^malformed/{m=$2} END{print "processed + malformed = " p " + " m " = " p+m}'; wc -l < trip_booking.log | awk '{print "wc -l = " $1}'
```

```
processed + malformed = 80 + 0 = 80
wc -l = 80
```

- Error-level: 24, which matches `grep -c '"level": "ERROR"' trip_booking.log` → `24`.

## Incident summary

[`summarize.py`](summarize.py) streams the log line by line through the Stage 1 `parse_line`, keeps only `ERROR` lines, cleans each message with `normalize()` (the rules in [NORMALISATION_RULES.md](NORMALISATION_RULES.md)), groups by **cleaned message + service**, and prints the five biggest groups as one JSON object. Groups are sorted by count, highest first; equal counts go to the earliest `first_seen`. Only the JSON goes to stdout.

### Repeats come out identical

Three `trip-dispatch` errors for different trips, run through `normalize()`:

```bash
python3 -c 'import json
from summarize import normalize
lines = open("trip_booking.log", encoding="utf-8").readlines()
for n in (20, 31, 37):
    m = json.loads(lines[n - 1])["message"]
    print(f"line {n} raw:  {m}")
    print(f"line {n} norm: {normalize(m)}")'
```

```
line 20 raw:  Failed to assign driver for trip 4c9f20b8-7a61-4e35-8d0c-1b93e6a5c724 after 3 retries: upstream timeout 5000ms
line 20 norm: Failed to assign driver for trip <UUID> after <NUM> retries: upstream timeout <NUM>ms
line 31 raw:  Failed to assign driver for trip d6208af1-9b43-4c07-a58e-3f7d1c90b62a after 3 retries: upstream timeout 5000ms
line 31 norm: Failed to assign driver for trip <UUID> after <NUM> retries: upstream timeout <NUM>ms
line 37 raw:  Failed to assign driver for trip 21a9f60d-3c85-4b71-8e49-6a0d7b2c5f13 after 3 retries: upstream timeout 5000ms
line 37 norm: Failed to assign driver for trip <UUID> after <NUM> retries: upstream timeout <NUM>ms
```

All three clean to the same text.

### Same message, two services → two groups

No cleaned message appears under two services anywhere in `trip_booking.log`, so this check feeds the real message from line 35 in under two service names (`payments-authorizer` twice, `payments-ledger` once):

```bash
python3 -c 'import json
from summarize import summarize
m = json.loads(open("trip_booking.log", encoding="utf-8").readlines()[34])["message"]
row = lambda svc, ts: json.dumps({"timestamp": ts, "level": "ERROR", "service": svc, "message": m})
lines = [row("payments-authorizer", "2025-03-10T03:00:55.409Z"), row("payments-authorizer", "2025-03-10T03:02:27.734Z"), row("payments-ledger", "2025-03-10T03:01:00.000Z")]
for c in summarize(lines)["clusters"]: print(c["service"], c["count"], c["normalised_message"])'
```

```
payments-authorizer 2 Card auth call timed out for <REQ> after <NUM>ms
payments-ledger 1 Card auth call timed out for <REQ> after <NUM>ms
```

Two groups, each with its own count.

### Run on the outage log

```bash
python3 summarize.py trip_booking.log
```

```json
{
  "total_lines_processed": 80,
  "total_error_lines": 24,
  "clusters": [
    {
      "normalised_message": "Failed to assign driver for trip <UUID> after <NUM> retries: upstream timeout <NUM>ms",
      "service": "trip-dispatch",
      "count": 4,
      "first_seen": "2025-03-10T02:53:30.905Z",
      "last_seen": "2025-03-10T03:01:14.208Z"
    },
    {
      "normalised_message": "Dispatch failed for trip <UUID>: upstream matching-engine-v2 timeout after <NUM>ms (attempt <NUM>/<NUM>)",
      "service": "trip-dispatch",
      "count": 4,
      "first_seen": "2025-03-10T03:03:06.412Z",
      "last_seen": "2025-03-10T03:12:04.851Z"
    },
    {
      "normalised_message": "Booking request <REQ> failed for trip <UUID> status=<NUM> retry_after=<NUM>",
      "service": "rider-booking-api",
      "count": 4,
      "first_seen": "2025-03-10T03:03:58.640Z",
      "last_seen": "2025-03-10T03:22:03.982Z"
    },
    {
      "normalised_message": "Candidate pool query exceeded deadline deadline=<TS> elapsed_ms=<NUM> pool_size=<NUM>",
      "service": "matching-engine-v2",
      "count": 3,
      "first_seen": "2025-03-10T03:06:12.774Z",
      "last_seen": "2025-03-10T03:14:30.618Z"
    },
    {
      "normalised_message": "Card auth call timed out for <REQ> after <NUM>ms",
      "service": "payments-authorizer",
      "count": 2,
      "first_seen": "2025-03-10T03:00:55.409Z",
      "last_seen": "2025-03-10T03:02:27.734Z"
    }
  ]
}
```

Count order check:

```bash
python3 summarize.py trip_booking.log | python3 -c 'import json, sys
counts = [c["count"] for c in json.load(sys.stdin)["clusters"]]
print(len(counts), "clusters, counts", counts, "highest first:", counts == sorted(counts, reverse=True))'
```

```
5 clusters, counts [4, 4, 4, 3, 2] highest first: True
```

### Verdict

Yes, `trip-dispatch` really fails: it has the top two clusters (4 + 4 = 8 of the 24 error lines) and the earliest error in the summary, first seen 02:53:30 UTC, before `payments-authorizer` (03:00:55), `rider-booking-api` (03:03:58) and `matching-engine-v2` (03:06:12). The summary does not show what made it fail: cluster 1's messages only say "upstream timeout" without naming the upstream, the first cluster in the summary that names `matching-engine-v2` (cluster 2) starts at 03:03:06, and `matching-engine-v2`'s own errors (cluster 4, 3) start 03:06:12, about 13 minutes after dispatch began failing. Start the investigation at trip-dispatch's upstream calls from 02:53:30; `matching-engine-v2` is the leading suspect, not a proven cause.

## Testing

The suite is pytest (version pinned in [`requirements-dev.txt`](requirements-dev.txt)). [`test_summarize.py`](test_summarize.py) calls the script's own `normalize()` and `summarize()` directly: a normalisation table of real messages from `trip_booking.log` (one row per rule, plus the decimal and UUID-not-chopped cases), repeats collapsing, the same message in two services giving two clusters, only valid ERROR lines counted, top five sorted by count, the earliest-`first_seen` tiebreak, the exact output keys, the CLI printing only JSON, and the real log's pinned result (file hash, 80 / 24, the five cluster counts). [`test_parse_log.py`](test_parse_log.py) covers the Stage 1 line checks.

Each test was checked against a deliberately broken `summarize.py` (no tiebreak, grouping by message only, number rule first, integer-only numbers, request-ID rule removed, top four instead of five); every break makes at least one test fail.

```bash
pip install -r requirements-dev.txt
python3 -m pytest -v
```

Passing run, as printed:

```
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.7.0 -- /private/tmp/claude-501/-Users-ashpreetsinghanand/d42ef64e-bc97-4fef-99e1-e7293bc729da/scratchpad/venv/bin/python3
rootdir: /Users/ashpreetsinghanand/Desktop/zero/trip-booking-log-parser
collecting ... collected 19 items

test_parse_log.py::SummarizeTest::test_counts_and_skips_malformed PASSED [  5%]
test_parse_log.py::SummarizeTest::test_real_log_adds_up PASSED           [ 10%]
test_summarize.py::test_normalize_table[line50] PASSED                   [ 15%]
test_summarize.py::test_normalize_table[line20] PASSED                   [ 21%]
test_summarize.py::test_normalize_table[line35] PASSED                   [ 26%]
test_summarize.py::test_normalize_table[line38] PASSED                   [ 31%]
test_summarize.py::test_normalize_table[line66] PASSED                   [ 36%]
test_summarize.py::test_normalize_table[line7] PASSED                    [ 42%]
test_summarize.py::test_normalize_table[line2] PASSED                    [ 47%]
test_summarize.py::test_repeats_normalise_identically PASSED             [ 52%]
test_summarize.py::test_same_message_in_two_services_is_two_clusters PASSED [ 57%]
test_summarize.py::test_only_valid_error_lines_are_clustered PASSED      [ 63%]
test_summarize.py::test_top_five_sorted_by_count_highest_first PASSED    [ 68%]
test_summarize.py::test_tie_goes_to_earliest_first_seen_whatever_the_input_order PASSED [ 73%]
test_summarize.py::test_first_and_last_seen PASSED                       [ 78%]
test_summarize.py::test_output_keys PASSED                               [ 84%]
test_summarize.py::test_real_log_pinned_result PASSED                    [ 89%]
test_summarize.py::test_cli_prints_only_one_json_object PASSED           [ 94%]
test_summarize.py::test_first_seen_with_mixed_timestamp_precision XFAIL  [100%]

======================== 18 passed, 1 xfailed in 0.06s =========================
```

**Known bug:** `first_seen`/`last_seen` compare timestamps as text, so a mixed-precision log puts `03:00:00.500Z` before `03:00:00Z`; every timestamp in this log has milliseconds, so this run is unaffected (pinned by the `xfail` test).

## Docker

## Log format notes

`trip_booking.log` is the scenario download `Trip-Booking Outage Incident Log Dump (10 March 2025).jsonl`, copied in unchanged. It is JSON Lines: one JSON object per line, 80 lines, ending in a newline. It covers 2025-03-10 02:45:02Z to 03:29:59Z across 15 services.

### Fields

Every one of the 80 lines carries the same 8 fields, in this order:

| Field | Type | Present / null | Notes |
|---|---|---|---|
| `timestamp` | string | 80 / 0 | ISO 8601 UTC with milliseconds, e.g. `2025-03-10T02:45:02.118Z` |
| `level` | string | 80 / 0 | see below |
| `service` | string | 80 / 0 | 15 distinct, e.g. `trip-dispatch`, `matching-engine-v2`, `payments-authorizer` |
| `host` | string | 80 / 0 | pod name, `<service>-<suffix>`, e.g. `trip-dispatch-7f9kq` |
| `request_id` | string or null | 71 / 9 | normally `req_` + 12 hex chars; null on background events |
| `trip_id` | string or null | 50 / 30 | UUID; null when the event isn't tied to a trip |
| `message` | string | 80 / 0 | free text with embedded IDs, durations and key=value pairs |
| `duration_ms` | integer or null | 59 / 21 | null for events with no duration |

### Values of `level`

Found with `grep -oE '"level": *"[^"]*"' trip_booking.log | sort | uniq -c`:

| Value | Lines |
|---|---|
| `INFO` | 36 |
| `ERROR` | 24 |
| `WARN` | 14 |
| `DEBUG` | 6 |

All uppercase. There are no other spellings (no `error`, `Error`, `ERR` or `WARNING`), so a case-sensitive `ERROR` match and the parser's normalised match give the same 24.

### Invalid JSON

None. Every one of the 80 lines parses as a standalone JSON object, so malformed is 0 for this file. The parser still counts and skips bad lines; the tests prove that path.

### Other findings

- Line 22 has a corrupted `request_id`. The exact line, from `sed -n '22p' trip_booking.log`:

  ```
  {"timestamp": "2025-03-10T02:54:52.618Z", "level": "WARN", "service": "api-gateway", "host": "api-gateway-2r6ks", "request_id": "req_1f76b0d девять", "trip_id": null, "message": "Upstream p99 latency 1210.4ms above target 500ms path=/v2/trips/dispatch", "duration_ms": null}
  ```

  The `request_id` is `req_1f76b0d девять`: 7 hex chars instead of 12, then a space, then the Cyrillic word `девять` (Russian for "nine"; code points U+0434 U+0435 U+0432 U+044F U+0442 U+044C). It sits inside a properly quoted JSON string, so the line is still valid JSON. Proof:

  ```bash
  sed -n '22p' trip_booking.log | python3 -c 'import sys, json; r = json.loads(sys.stdin.read()); print(type(r).__name__, repr(r["request_id"]))'
  ```

  ```
  dict 'req_1f76b0d девять'
  ```

  It parses to an object with `timestamp`, `level`, `service` and `message` all present, so the parser counts it as processed, not malformed (it is one of the 80 processed). `request_id` is not a required field, so the bad value doesn't disqualify it. Treat it as untrustworthy for joining with other lines by request ID.
- 9 lines have `request_id: null`: `matching-engine-v2` 4, `driver-location` 3, `surge-pricing` 1, `trip-dispatch` 1. These are background events (pool queries, location lag, index rebuilds, config reloads), not rider requests.
- Errors by service: `trip-dispatch` 11, `rider-booking-api` 5, `payments-authorizer` 4, `matching-engine-v2` 3, `driver-location` 1.

### What a line must have to be usable

`timestamp`, `level`, `service` and `message`, each a non-empty string. Those four are what the later clustering needs (when, how bad, who, what). `host`, `request_id`, `trip_id` and `duration_ms` are optional because they are legitimately null on many lines, and a bad `request_id` doesn't make the event any less real.
