# trip-booking-log-parser

Reads the trip booking log line by line and prints a summary of processed, error-level and malformed lines.

## Normalisation rules

- Each line is trimmed and one trailing `,` is removed before parsing, because the dump is a JSON array written one record per line (`{...},`).
- `level` is compared after `strip().upper()`, so `ERROR`, `error` and ` Error ` all count as error-level. This log only ever spells it `ERROR`.
- A line is malformed if it isn't valid JSON, isn't a JSON object, or is missing any of `timestamp`, `level`, `service`, `message` as a non-empty string (see Log format notes). Blank lines and the array's `[` / `]` lines count as malformed.
- Malformed lines are counted and skipped; the parser never stops on a bad line.

## Summary output

```bash
python3 parse_log.py trip_booking.log
```

```
processed: 42
error-level: 9
malformed: 3
```

Checks against the file itself:

- The file has **45 lines** (`grep -c '' trip_booking.log` → `45`), and processed + malformed = 42 + 3 = 45.
- `wc -l < trip_booking.log` prints `44`, not 45, because `wc` counts newline characters and the last line (`]`) has no newline after it. The file is kept byte-for-byte as downloaded, so that newline was not added.
- The 3 malformed lines are line 1 (`[`), line 44 (truncated record) and line 45 (`]`).
- `level` is only ever spelled `ERROR` (`grep -oiE '"level": *"[^"]*"' trip_booking.log | sort | uniq -c` shows `DEBUG` 2, `ERROR` 10, `INFO` 23, `WARN` 8, no lowercase or other variants).
- The raw file has 10 `ERROR` lines but the parser reports 9: the 10th is line 44, which has no `message` and is skipped as malformed.

## Testing

Python 3 standard library only, no dependencies.

```bash
python3 -m unittest -v
```

The tests cover valid, trailing-comma, array-bracket, invalid-JSON, non-object, missing-field and blank lines, a lowercase `level`, and check that processed + malformed equals the line count of `trip_booking.log`.

## Docker

## Log format notes

`trip_booking.log` is the scenario download `Trip-Booking Outage Incident Log Dump (10 March 2025).jsonl`, copied in unchanged. Despite the `.jsonl` name it is a JSON array split one record per line: line 1 is `[`, lines 2–44 are 43 records each ending in `,` (except the last), and line 45 is `]` with no trailing newline. 45 lines in total.

Fields each line carries:

| Field | Type | Notes |
|---|---|---|
| `timestamp` | string | ISO 8601 UTC, e.g. `2025-03-10T02:45:02.118Z` |
| `level` | string | Values seen: `INFO` (23), `ERROR` (10), `WARN` (8), `DEBUG` (2). All uppercase, no other spellings. |
| `service` | string | e.g. `trip-dispatch`, `payments-authorizer` |
| `host` | string | pod name, e.g. `trip-dispatch-7f9kq` |
| `request_id` | string | normally `req_` + 12 hex chars |
| `trip_id` | string or null | null for requests not tied to a trip |
| `message` | string | free text |
| `duration_ms` | number or null | null for events with no duration |

What the inspection found:

- Read as-is, no record line is valid JSON on its own because of the trailing comma; with the comma removed, all 43 records parse. The `[` and `]` lines are not records.
- Line 44 (`trip-dispatch`, `ERROR`) is truncated: it has no `message` and no `duration_ms`.
- Lines 23 and 44 have corrupted `request_id` values (`req_1f76b0d девять`, `req_0d47eb style`).

**A line is usable only if** it is valid JSON, is an object, and has `timestamp`, `level`, `service` and `message` as non-empty strings. Everything else (`host`, `request_id`, `trip_id`, `duration_ms`) is optional because `trip_id`/`duration_ms` are legitimately null and a bad `request_id` doesn't stop the event being counted. Lines that fail this are counted as malformed and skipped, so line 44 is malformed and line 23 is processed.
