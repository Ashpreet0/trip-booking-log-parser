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

## Testing

Python 3 standard library only, no dependencies.

```bash
python3 -m unittest -v
```

The tests feed valid lines, a trailing-comma line, invalid JSON, a non-object, a line missing `message`, a blank line and a lowercase ` error ` level, and check that processed + malformed equals the line count of `trip_booking.log`.

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
