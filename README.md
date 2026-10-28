# 3am

This tool groups an incident log's ERROR lines into the top 5 repeating failures and prints them as JSON. It needs Docker and nothing else. You don't need to install Python.

## Build

```bash
docker build -t 3am .
```

## Run

From the folder that holds the log:

```bash
docker run --rm -v "$PWD/trip_booking.log:/logs/incident.log:ro" 3am /logs/incident.log
```

The log is mounted read-only at run time. It is never copied into the image, because the Dockerfile copies only the code and the tests and `.dockerignore` excludes `*.log`. To summarise a different log, change only the left side of `-v`.

## Reading the output

- `total_lines_processed`: the lines it could read. Broken lines are skipped and don't stop the run.
- `total_error_lines`: the ERROR lines across all groups, not only the top 5.
- `clusters`: the same failure grouped together, ranked by `count`, with a tie going to the one that started first.
  - The tool swaps IDs, UUIDs, request IDs, numbers and timestamps for `<UUID>`, `<NUM>` and similar tokens, so repeats of one failure land in one cluster.
  - Each cluster has a `service`, a `count`, and a `first_seen` / `last_seen` time in UTC.

**What the top cluster means:** trip-dispatch began failing to assign drivers at 02:53:30 UTC, before every other cluster. Start with trip-dispatch and what it calls upstream. matching-engine-v2 is named in cluster 2, but its own errors only start at 03:06:12, so it's the leading suspect, not the proven cause.

## Verification

Run from a fresh clone on a machine with no Python setup, using the incident log `trip_booking.log` (the trip-booking outage dump, 80 lines, sha256 `cfcf7c74…f3e2`).

```bash
git clone https://github.com/Ashpreet0/trip-booking-log-parser.git && cd trip-booking-log-parser
docker build -t 3am .
docker run --rm -v "$PWD/trip_booking.log:/logs/incident.log:ro" 3am /logs/incident.log
echo "exit status: $?"
```

Full JSON, exactly as the terminal printed it:

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

- Exit status: `0`
- Runtime: `0.36s` wall clock for the `docker run`, container start included.

Pytest inside the same image, with the log mounted where the tests read it:

```bash
docker run --rm -v "$PWD/trip_booking.log:/app/trip_booking.log:ro" --entrypoint python3 3am -m pytest -v -p no:cacheprovider
```

```text
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.1.1, pluggy-1.7.0 -- /usr/local/bin/python3
rootdir: /app
collecting ... collected 24 items

test_parse_log.py::SummarizeTest::test_counts_and_skips_malformed PASSED [  4%]
test_parse_log.py::SummarizeTest::test_real_log_adds_up PASSED           [  8%]
test_summarize.py::test_normalize_table[line50] PASSED                   [ 12%]
test_summarize.py::test_normalize_table[line20] PASSED                   [ 16%]
test_summarize.py::test_normalize_table[line35] PASSED                   [ 20%]
test_summarize.py::test_normalize_table[line38] PASSED                   [ 25%]
test_summarize.py::test_normalize_table[line66] PASSED                   [ 29%]
test_summarize.py::test_normalize_table[line7] PASSED                    [ 33%]
test_summarize.py::test_normalize_table[line2] PASSED                    [ 37%]
test_summarize.py::test_repeats_normalise_identically[line45-line60] PASSED [ 41%]
test_summarize.py::test_repeats_normalise_identically[line50-line57] PASSED [ 45%]
test_summarize.py::test_same_message_in_two_services_is_two_clusters PASSED [ 50%]
test_summarize.py::test_only_valid_error_lines_are_clustered PASSED      [ 54%]
test_summarize.py::test_top_five_sorted_by_count_highest_first PASSED    [ 58%]
test_summarize.py::test_tie_goes_to_earliest_first_seen_whatever_the_input_order PASSED [ 62%]
test_summarize.py::test_first_and_last_seen PASSED                       [ 66%]
test_summarize.py::test_output_keys PASSED                               [ 70%]
test_summarize.py::test_real_log_pinned_result PASSED                    [ 75%]
test_summarize.py::test_broken_lines_are_malformed_and_leave_totals_unchanged PASSED [ 79%]
test_summarize.py::test_every_cluster_in_the_real_run_is_complete PASSED [ 83%]
test_summarize.py::test_cli_prints_only_one_json_object PASSED           [ 87%]
test_summarize.py::test_first_and_last_seen_compare_time_not_text PASSED [ 91%]
test_summarize.py::test_tiebreak_compares_time_not_text PASSED           [ 95%]
test_summarize.py::test_unusable_timestamps_are_malformed_not_a_crash PASSED [100%]

============================== 24 passed in 0.06s ==============================
```

Pytest exit status: `0`. `ls /app/*.log` inside the image finds nothing, so the log is not baked in.
