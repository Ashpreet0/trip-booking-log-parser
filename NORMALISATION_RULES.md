# Normalisation rules

Spec for turning an error `message` into a stable **cluster key**. Each rule swaps one kind of changing part for a fixed placeholder token, so errors that describe the same failure get the same key and the incident summarizer can group and count them. The summarizer applies these rules exactly as written: same patterns, same tokens, same order.

## Source

- File: [`trip_booking.log`](trip_booking.log), the resource download `Trip-Booking Outage Incident Log Dump (10 March 2025).jsonl`, byte-identical (SHA-256 `cfcf7c74fa968b5d7cff6640f5dab4efa11e6563425a42dd53f67d234c34f3e2`).
- 80 events, 24 at `ERROR`.
- The stage brief describes 43 events. The download currently served is this 80-event version; an earlier download of the same resource (43 events, JSON-array format) had only 10 ERROR lines. This spec is built on the current 80-event file.
- Every example below is copied from the file by script, with its line number, and checked against it.

## ERROR lines, sorted by message

Printed with the Stage 1 parser's own `parse_line`, so only lines it accepts are included. Run from the repo root:

```bash
python3 -c 'import parse_log
rows = [r for r in map(parse_log.parse_line, open("trip_booking.log", encoding="utf-8")) if r and r["level"].strip().upper() == "ERROR"]
for r in sorted(rows, key=lambda r: r["message"]): print(r["service"], "|", r["message"])
print(len(rows), "ERROR lines")'
```

Output, as printed:

```
rider-booking-api | Booking request req_2c8f15a9d04e failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30
rider-booking-api | Booking request req_3e7b0f19c2d8 failed for trip b1a59e3d-7f02-4c68-9d4e-0a8f2c6b5e13 status=503 retry_after=60
rider-booking-api | Booking request req_47c0d9a3e1f6 failed for trip c6b14f8e-0d32-4a59-8e7c-1f9a3d5b2c40 status=503 retry_after=30
rider-booking-api | Booking request req_7a1c58e03b9f rejected: dispatch unavailable (503)
rider-booking-api | Booking request req_a95d2c47b08e failed for trip 9d0e3b6c-4f21-4a87-8c5d-e1f72a0b9c64 status=503 retry_after=30
matching-engine-v2 | Candidate pool query exceeded deadline deadline=2025-03-10T03:06:07.774Z elapsed_ms=4998 pool_size=412
matching-engine-v2 | Candidate pool query exceeded deadline deadline=2025-03-10T03:09:22.412Z elapsed_ms=5003 pool_size=389
matching-engine-v2 | Candidate pool query exceeded deadline deadline=2025-03-10T03:14:25.618Z elapsed_ms=5011 pool_size=451
payments-authorizer | Card auth call timed out for req_1b77e0a95c3f after 2500ms
payments-authorizer | Card auth call timed out for req_9c04e71b2a6d after 2500ms
trip-dispatch | Dispatch failed for trip 3c9a7e2f-1b50-4d84-a6c3-f8e0d2b1a796: upstream matching-engine-v2 timeout after 5000ms (attempt 1/3)
trip-dispatch | Dispatch failed for trip a71d4c02-8e3f-4b19-b6d2-5f0e9c7a3b18: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
trip-dispatch | Dispatch failed for trip c3f81e5d-27a0-4b96-9d4c-0e6b2a8f17d3: upstream matching-engine-v2 timeout after 5000ms (attempt 2/3)
trip-dispatch | Dispatch failed for trip f04b7a2c-6d81-4e39-b2a5-9c3e0d1f8b47: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
trip-dispatch | Dispatch timeout for trip 5b8e2d63-a1f4-47c9-8d0e-9c3f6a2b1e58 after 5000ms waiting on matching-engine-v2 (attempt 1/3)
trip-dispatch | Dispatch timeout for trip a7d41c92-3e5f-4b80-8c16-2f9e0d7b4a31 after 5000ms waiting on matching-engine-v2 (attempt 3/3)
trip-dispatch | Failed to assign driver for trip 21a9f60d-3c85-4b71-8e49-6a0d7b2c5f13 after 3 retries: upstream timeout 5000ms
trip-dispatch | Failed to assign driver for trip 4c9f20b8-7a61-4e35-8d0c-1b93e6a5c724 after 3 retries: upstream timeout 5000ms
trip-dispatch | Failed to assign driver for trip 8e51c74b-0f28-4a96-b3d7-5c81a2e40f9b after 2 retries: upstream timeout 4500ms
trip-dispatch | Failed to assign driver for trip d6208af1-9b43-4c07-a58e-3f7d1c90b62a after 3 retries: upstream timeout 5000ms
trip-dispatch | Failed to assign driver for trip f30c8b47-2a91-4d68-95b2-0e7c1a86d4f5 after 3 retries: upstream matching-engine-v2 timeout 5000ms
payments-authorizer | Payment hold failed for trip 0e5d8b3c-9a47-4f21-b6e8-2c1f7a0d4b93 amount=31.20 code=GATEWAY_TIMEOUT
payments-authorizer | Payment hold failed for trip 48d2f0a6-5c1e-4b93-87af-1e9c3b6d2a05 amount=18.75 code=GATEWAY_TIMEOUT
driver-location | Stale location for driver d_48213 age=91s
24 ERROR lines
```

## Changing parts

One row per part of a message that changes between lines describing the same failure.

| Changing part | What it looks like | Token | Real example (line: raw → token) |
|---|---|---|---|
| UUID (36-character trip ID) | 36 chars: 8-4-4-4-12 lowercase hex | `<uuid>` | line 20 (`trip-dispatch`): `4c9f20b8-7a61-4e35-8d0c-1b93e6a5c724` → `<uuid>` |
| Numeric ID (rider, driver) | one letter, `_`, digits | `<id>` | line 38 (`driver-location`): `d_48213` → `<id>` |
| Number value | integer or decimal, often with a unit (`ms`, `s`) or after `=` | `<n>` | line 35 (`payments-authorizer`): `2500` → `<n>` |
| ISO 8601 timestamp | `YYYY-MM-DDTHH:MM:SS[.mmm]Z` inside the text | `<ts>` | line 50 (`matching-engine-v2`): `2025-03-10T03:06:07.774Z` → `<ts>` |
| Request ID | `req_` + hex | `<req>` | line 35 (`payments-authorizer`): `req_1b77e0a95c3f` → `<req>` |

The request ID row is an addition to the four required rows: `req_1b77e0a95c3f` isn't a plain number or a UUID, so without its own rule every `Card auth call timed out for req_…` error would stay its own key.

## Rule order

Most specific first: fixed shapes with literal anchors (`T`, `Z`, dashes, `req_`) run before the catch-all number rule.

| Rank | Rule | Token | Pattern |
|---|---|---|---|
| 1 | ISO 8601 timestamp | `<ts>` | `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z` |
| 2 | UUID (36-character trip ID) | `<uuid>` | `\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b` |
| 3 | Request ID | `<req>` | `\breq_[0-9a-f]+\b` |
| 4 | Numeric ID (rider, driver) | `<id>` | `\b[a-z]_\d+\b` |
| 5 | Number value | `<n>` | `(?<![\w.-])\d+(?:\.\d+)?` |

Why each rule is in its spot:

1. **ISO 8601 timestamp → `<ts>`.** Its digits would be cut up if it ran after rule 5. Moved last, 6 keys change; line 16 becomes `Heartbeat window advanced to <n>-03-10T02:<n>:<n>Z drivers=<n>` instead of `Heartbeat window advanced to <ts> drivers=<n>`. It has no overlap with rules 2–4, so its place among them doesn't change any key; it goes first as the most specific shape.
2. **UUID (36-character trip ID) → `<uuid>`.** If it ran after rule 5, the UUID's leading digits would be replaced first and the rest left behind. Moved last, 18 keys change; line 2 becomes `Booking request <req> accepted for trip <n>f2c9a1e-6b7d-4e08-9a55-0c1d2e3f4a5b status=<n>` instead of `Booking request <req> accepted for trip <uuid> status=<n>`, a key no other trip shares.
3. **Request ID → `<req>`.** Placed before rule 5 so a request ID is replaced whole. In this dump moving it later changes 0 keys, because rule 5 skips digits glued to `_` or a letter; it runs here so it doesn't depend on that. If it ran after rule 5 and rule 5 lost that guard, `req_1b77e0a95c3f` would come out half-replaced.
4. **Numeric ID (rider, driver) → `<id>`.** Same reason as rule 3: replaces `d_48213` whole as `<id>`. Moving it after rule 5 changes 0 keys in this dump (rule 5 skips digits after `_`), but it must stay before rule 5 rather than rely on that guard.
5. **Number value → `<n>`.** The catch-all, so it runs last. Moved first, it eats the start of timestamps and UUIDs before rules 1 and 2 see them: 24 keys change.

**Checked:** all 120 possible orders were run over all 80 messages. 40 give the same keys as this order, and every one of them has `ts before n` and `uuid before n`. So the hard constraints are timestamps and UUIDs before numbers; the rest of the order is by specificity.

## Collapse check

Line 45 and line 60 say the same thing (`rider-booking-api`: a booking failed with 503) but differ in request ID, trip UUID and `retry_after`. Each is run through the rules in order:

Line 45:

```
raw:    Booking request req_2c8f15a9d04e failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30
rule 1: Booking request req_2c8f15a9d04e failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30   (no change)
rule 2: Booking request req_2c8f15a9d04e failed for trip <uuid> status=503 retry_after=30
rule 3: Booking request <req> failed for trip <uuid> status=503 retry_after=30
rule 4: Booking request <req> failed for trip <uuid> status=503 retry_after=30   (no change)
rule 5: Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>
```

Line 60:

```
raw:    Booking request req_3e7b0f19c2d8 failed for trip b1a59e3d-7f02-4c68-9d4e-0a8f2c6b5e13 status=503 retry_after=60
rule 1: Booking request req_3e7b0f19c2d8 failed for trip b1a59e3d-7f02-4c68-9d4e-0a8f2c6b5e13 status=503 retry_after=60   (no change)
rule 2: Booking request req_3e7b0f19c2d8 failed for trip <uuid> status=503 retry_after=60
rule 3: Booking request <req> failed for trip <uuid> status=503 retry_after=60
rule 4: Booking request <req> failed for trip <uuid> status=503 retry_after=60   (no change)
rule 5: Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>
```

Final strings:

```
line 45: Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>
line 60: Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>
```

They match exactly: `True` from `norm(line_45) == norm(line_60)`.

A second pair that exercises the timestamp rule, lines 50 and 57 (`matching-engine-v2`):

```
raw 50:  Candidate pool query exceeded deadline deadline=2025-03-10T03:06:07.774Z elapsed_ms=4998 pool_size=412
raw 57:  Candidate pool query exceeded deadline deadline=2025-03-10T03:09:22.412Z elapsed_ms=5003 pool_size=389
final 50: Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=<n> pool_size=<n>
final 57: Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=<n> pool_size=<n>
```

## Result on all ERROR lines

The 24 ERROR lines become 10 keys (service + normalised message):

| Count | Service | Key |
|---|---|---|
| 4 | `trip-dispatch` | `Failed to assign driver for trip <uuid> after <n> retries: upstream timeout <n>ms` |
| 4 | `trip-dispatch` | `Dispatch failed for trip <uuid>: upstream matching-engine-v2 timeout after <n>ms (attempt <n>/<n>)` |
| 4 | `rider-booking-api` | `Booking request <req> failed for trip <uuid> status=<n> retry_after=<n>` |
| 3 | `matching-engine-v2` | `Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=<n> pool_size=<n>` |
| 2 | `payments-authorizer` | `Card auth call timed out for <req> after <n>ms` |
| 2 | `payments-authorizer` | `Payment hold failed for trip <uuid> amount=<n> code=GATEWAY_TIMEOUT` |
| 2 | `trip-dispatch` | `Dispatch timeout for trip <uuid> after <n>ms waiting on matching-engine-v2 (attempt <n>/<n>)` |
| 1 | `rider-booking-api` | `Booking request <req> rejected: dispatch unavailable (<n>)` |
| 1 | `driver-location` | `Stale location for driver <id> age=<n>s` |
| 1 | `trip-dispatch` | `Failed to assign driver for trip <uuid> after <n> retries: upstream matching-engine-v2 timeout <n>ms` |

Names containing digits that survive, across all 80 messages: `fs-gbm-v14`, `geo-index-v3`, `matching-engine-v2`, `nyc-midtown-07`, `p99`, `p99_ms`, `us-east-1a`, `us-east-1c`, `v2`. None is a changing value.

## Known limits

- **Same failure, different wording stays split.** `trip-dispatch` words the matching-engine timeout three ways (`Failed to assign driver…`, `Dispatch failed…`, `Dispatch timeout…`). The rules replace values, they never rewrite text.
- **Text codes stay as text.** `code=GATEWAY_TIMEOUT` is kept; a different code is meant to be a different key.
- **Only these ID shapes are caught.** The corrupted `req_1f76b0d девять` is only in line 22's `request_id` field, never in a message.