# Normalisation rules

These rules turn an error message into a stable **cluster key**. Each rule swaps one kind of changing part for a fixed placeholder token, so two errors describing the same failure end up with the same key and the summarizer can group and count them.

The incident summarizer applies these rules exactly as written: same patterns, same tokens, same order. Every example below is a real `message` from [`trip_booking.log`](trip_booking.log), copied from the file by script with its line number.

## How the rules are applied

- Applied to the `message` field only. `service` is grouped on separately and is never rewritten.
- Applied in order 1 → 5, each rule to the output of the one before. **The order is part of the spec** (see [Why the order matters](#why-the-order-matters)).
- Patterns are Python `re` syntax, applied with `re.sub(pattern, token, message)`, case-sensitive.
- Anything not matched is kept exactly as is: words, punctuation, units, `key=` names.

| # | Changing part | Token | Pattern |
|---|---|---|---|
| 1 | ISO 8601 timestamp | `<ts>` | `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z` |
| 2 | UUID (trip IDs) | `<uuid>` | `\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b` |
| 3 | Request ID | `<req>` | `\breq_[0-9a-f]+\b` |
| 4 | Prefixed numeric ID (rider, driver) | `<id>` | `\b[a-z]_\d+\b` |
| 5 | Number (counts, durations, amounts, status codes) | `<n>` | `(?<![\w.-])\d+(?:\.\d+)?` |

## Rule 1: ISO 8601 timestamp → `<ts>`

Pattern: `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z`

Timestamps embedded in the message (deadlines, snapshot times, window marks) change on every line. Milliseconds are optional, so both `02:50:40Z` and `03:06:07.774Z` match. Runs first so rule 5 never splits its digits.

Line 16 (`driver-location`, `DEBUG`):

```
before: Heartbeat window advanced to 2025-03-10T02:50:40Z drivers=1842
after:  Heartbeat window advanced to <ts> drivers=1842
```

Line 50 (`matching-engine-v2`, `ERROR`):

```
before: Candidate pool query exceeded deadline deadline=2025-03-10T03:06:07.774Z elapsed_ms=4998 pool_size=412
after:  Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=4998 pool_size=412
```

Matches 6 of 80 messages.

## Rule 2: UUID (trip IDs) → `<uuid>`

Pattern: `\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b`

Every trip has its own UUID, so without this rule each failed trip would be its own cluster. Lowercase hex in 8-4-4-4-12 groups, the only UUID form in the dump. Runs before rule 5, which would otherwise eat its leading digits.

Line 20 (`trip-dispatch`, `ERROR`):

```
before: Failed to assign driver for trip 4c9f20b8-7a61-4e35-8d0c-1b93e6a5c724 after 3 retries: upstream timeout 5000ms
after:  Failed to assign driver for trip <uuid> after 3 retries: upstream timeout 5000ms
```

Line 43 (`trip-dispatch`, `ERROR`):

```
before: Dispatch failed for trip a71d4c02-8e3f-4b19-b6d2-5f0e9c7a3b18: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
after:  Dispatch failed for trip <uuid>: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
```

Matches 32 of 80 messages.

## Rule 3: Request ID → `<req>`

Pattern: `\breq_[0-9a-f]+\b`

`req_` plus hex, unique per request. It isn't a pure number, so rule 5 can't catch it. The rule takes any run of hex after `req_` rather than exactly 12 characters.

Line 35 (`payments-authorizer`, `ERROR`):

```
before: Card auth call timed out for req_1b77e0a95c3f after 2500ms
after:  Card auth call timed out for <req> after 2500ms
```

Line 45 (`rider-booking-api`, `ERROR`):

```
before: Booking request req_2c8f15a9d04e failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30
after:  Booking request <req> failed for trip 5be09f3a-1c74-4d2e-8f61-7a30b9e2c4d5 status=503 retry_after=30
```

Matches 17 of 80 messages.

## Rule 4: Prefixed numeric ID (rider, driver) → `<id>`

Pattern: `\b[a-z]_\d+\b`

A one-letter prefix, underscore, then digits: `r_772913` (rider), `d_48213` (driver). Replaced whole, so the prefix doesn't leave a stray `d_<n>`. Runs before rule 5.

Line 11 (`rider-profile`, `INFO`):

```
before: Profile fetch completed rider=r_772913 cache=hit
after:  Profile fetch completed rider=<id> cache=hit
```

Line 17 (`driver-location`, `WARN`):

```
before: Stale location for driver d_48213 age=41s
after:  Stale location for driver <id> age=41s
```

Matches 4 of 80 messages.

## Rule 5: Number (counts, durations, amounts, status codes) → `<n>`

Pattern: `(?<![\w.-])\d+(?:\.\d+)?`

Any integer or decimal not glued to a letter, `.` or `-` in front. It replaces `214`, `3` in `3s`, `842.6` and `500` in `500ms`, but keeps names that contain digits: `p99`, `/v2/`, `matching-engine-v2`, `us-east-1c`. Units stay (`<n>ms`, `<n>s`) because they say what kind of number it was. Runs last.

Line 3 (`driver-location`, `INFO`):

```
before: Location batch flushed count=214 lag=3s
after:  Location batch flushed count=<n> lag=<n>s
```

Line 7 (`api-gateway`, `WARN`):

```
before: Upstream p99 latency 842.6ms above target 500ms path=/v2/trips/dispatch
after:  Upstream p99 latency <n>ms above target <n>ms path=/v2/trips/dispatch
```

Matches 78 of 80 messages.

## Why the order matters

If rule 5 ran first it would break IDs apart instead of replacing them. Line 2 with **only rule 5** applied:

Line 2 (`rider-booking-api`, `INFO`):

```
before: Booking request req_1a0d73f5c98b accepted for trip 3f2c9a1e-6b7d-4e08-9a55-0c1d2e3f4a5b status=201
wrong:  Booking request req_1a0d73f5c98b accepted for trip <n>f2c9a1e-6b7d-4e08-9a55-0c1d2e3f4a5b status=<n>
```

The UUID's leading `3` became `<n>`, leaving `<n>f2c9a1e-…`, which no other trip shares, so the cluster splits. In the correct order rules 2 and 3 take the IDs out first:

Line 2 (`rider-booking-api`, `INFO`):

```
before: Booking request req_1a0d73f5c98b accepted for trip 3f2c9a1e-6b7d-4e08-9a55-0c1d2e3f4a5b status=201
after:  Booking request <req> accepted for trip <uuid> status=<n>
```

## All rules together

Different trips, hosts, requests and timings, same failure, one key:

Line 43 (`trip-dispatch`, `ERROR`):

```
before: Dispatch failed for trip a71d4c02-8e3f-4b19-b6d2-5f0e9c7a3b18: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
after:  Dispatch failed for trip <uuid>: upstream matching-engine-v2 timeout after <n>ms (attempt <n>/<n>)
```

Line 54 (`trip-dispatch`, `ERROR`):

```
before: Dispatch failed for trip f04b7a2c-6d81-4e39-b2a5-9c3e0d1f8b47: upstream matching-engine-v2 timeout after 5000ms (attempt 3/3)
after:  Dispatch failed for trip <uuid>: upstream matching-engine-v2 timeout after <n>ms (attempt <n>/<n>)
```

Line 50 (`matching-engine-v2`, `ERROR`):

```
before: Candidate pool query exceeded deadline deadline=2025-03-10T03:06:07.774Z elapsed_ms=4998 pool_size=412
after:  Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=<n> pool_size=<n>
```

Line 57 (`matching-engine-v2`, `ERROR`):

```
before: Candidate pool query exceeded deadline deadline=2025-03-10T03:09:22.412Z elapsed_ms=5003 pool_size=389
after:  Candidate pool query exceeded deadline deadline=<ts> elapsed_ms=<n> pool_size=<n>
```

## Result on the dump

Applied to the 24 ERROR lines, the rules produce 10 distinct keys (service + normalised message):

| Count | Service | Normalised message |
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

Names with digits that survive normalisation, checked across all 80 messages: `fs-gbm-v14`, `geo-index-v3`, `matching-engine-v2`, `nyc-midtown-07`, `p99`, `p99_ms`, `us-east-1a`, `us-east-1c`, `v2`. None of them is a changing value.

## Known limits

- **Same failure, different wording.** `trip-dispatch` reports the matching-engine timeout three ways: `Failed to assign driver …` (lines 20, 31, 33, 37, 39), `Dispatch failed for trip …` and `Dispatch timeout for trip …` (lines 43, 47, 54, 62, 73, 78). They stay separate keys. The rules swap changing values; they never rewrite wording.
- **Text codes aren't normalised.** `code=GATEWAY_TIMEOUT` stays as text. A different code would be a different key, which is intended.
- **Only these ID shapes are caught.** The corrupted `req_1f76b0d девять` is in the `request_id` field of line 22, not in any message, so it never reaches these rules.