# trip-booking-log-parser

Reads the trip booking log line by line and prints a summary of processed, error-level and malformed lines.

## Normalisation rules

## Summary output

## Testing

## Docker

## Log format notes

`trip_booking.log` is JSON Lines: one JSON object per line, 43 lines.

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

- Every line parses as JSON; there are no syntactically broken lines in this file.
- Line 43 (`trip-dispatch`, `ERROR`) is truncated: it has no `message` and no `duration_ms`.
- Lines 22 and 43 have corrupted `request_id` values (`req_1f76b0d девять`, `req_0d47eb style`).

**A line is usable only if** it is valid JSON, is an object, and has `timestamp`, `level`, `service` and `message` as non-empty strings. Everything else (`host`, `request_id`, `trip_id`, `duration_ms`) is optional because `trip_id`/`duration_ms` are legitimately null and a bad `request_id` doesn't stop the event being counted. Lines that fail this are counted as malformed and skipped, so line 43 is malformed and line 22 is processed.
