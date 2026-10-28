# 3am

This tool groups an incident log's ERROR lines into the top 5 repeating failures and prints them as JSON. It needs Docker and nothing else. You don't need to install Python.

## Build

```bash
docker build -t 3am .
```

## Run

Copy the log into this folder as `incident.log`, then run:

```bash
docker run --rm -v "$PWD/incident.log:/logs/incident.log:ro" 3am /logs/incident.log
```

`-v` links that one file from your laptop into the container, read-only. Copy it in first because `-v` splits on `:`, and incident-log downloads often have a colon in their name. The log is never copied into the image: the Dockerfile copies only the script, the tests and `requirements-dev.txt`, `.dockerignore` excludes `*.log`, and `.gitignore` keeps `incident.log` out of git.

## Reading the output

- `total_lines_processed`: the lines it could read. Broken lines are skipped and don't stop the run.
- `total_error_lines`: the ERROR lines across all groups, not only the top 5.
- `clusters`: the same failure grouped together, ranked by `count`, with a tie going to the one that started first.
  - The tool swaps IDs, UUIDs and short hex trip IDs (both shown as `<UUID>`), request IDs, numbers and timestamps for `<UUID>`, `<NUM>` and similar tokens, so repeats of one failure land in one cluster.
  - Each cluster has a `service`, a `count`, and a `first_seen` / `last_seen` time in UTC.

**What the top cluster means (11 March fare-quote log):** fare-quote-service's surge multiplier lookup timed out on Redis 5 times, starting at 01:13:14 UTC, before any other error. The trip-dispatch, rider-app-bff and eta-service errors come later and are on the same trips, so check the surge-pricing Redis shards first.

## Verification

This was run on the **held-out 11 March 2025 fare-quote log**, which the tool had never seen. It was a fresh clone into a brand-new folder, with commit `b9a59ad`. The build adds `--no-cache` so that no step comes from an earlier build. Otherwise it is the README build command.

**Fixes needed: yes, two, both found by the first held-out run. Neither showed up on the 10 March log.**
1. `-v` rejected the downloaded filename with exit 125 and "too many colons", because the name contains a colon. The Run step now copies the log to `incident.log` first.
2. That run exited 0 with five clusters, but the answer was wrong. Short 8-character hex trip IDs like `b2e7c410` weren't normalised, and the number rule cut `7f3a91c2` down to `<NUM>f3a91c2`. So one Redis-timeout failure was split across four clusters, and a downstream trip-dispatch symptom ranked first.
   - Fixed with a short-hex-ID rule. It changes nothing in the 10 March log.
   - It's covered by `test_trip_id_in_any_shape_is_one_cluster`, which goes red when the rule is removed.
   - The correct output is **4 clusters**, because the log holds only 4 distinct failures.

Build output, as printed:

```text
$ git clone https://github.com/Ashpreet0/trip-booking-log-parser.git && cd trip-booking-log-parser
Cloning into 'trip-booking-log-parser'...
$ git log --oneline -1
b9a59ad fix: normalise short hex trip IDs so one failure stays one cluster
$ docker build --no-cache -t 3am .
#0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 394B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.13-slim
#2 DONE 1.3s

#3 [internal] load .dockerignore
#3 transferring context: 87B done
#3 DONE 0.0s

#4 [internal] load build context
#4 transferring context: 14.43kB done
#4 DONE 0.0s

#5 [1/5] FROM docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
#5 resolve docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb done
#5 DONE 0.0s

#6 [2/5] WORKDIR /app
#6 CACHED

#7 [3/5] COPY requirements-dev.txt .
#7 DONE 0.0s

#8 [4/5] RUN pip install --no-cache-dir -r requirements-dev.txt
#8 1.074 Collecting pytest==9.1.1 (from -r requirements-dev.txt (line 1))
#8 1.184   Downloading pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
#8 1.200 Collecting iniconfig>=1.0.1 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.211   Downloading iniconfig-2.3.1-py3-none-any.whl.metadata (2.8 kB)
#8 1.228 Collecting packaging>=22 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.239   Downloading packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
#8 1.257 Collecting pluggy<2,>=1.5 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.273   Downloading pluggy-1.7.0-py3-none-any.whl.metadata (5.0 kB)
#8 1.291 Collecting pygments>=2.7.2 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.305   Downloading pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
#8 1.320 Downloading pytest-9.1.1-py3-none-any.whl (386 kB)
#8 1.365 Downloading pluggy-1.7.0-py3-none-any.whl (27 kB)
#8 1.380 Downloading iniconfig-2.3.1-py3-none-any.whl (7.6 kB)
#8 1.392 Downloading packaging-26.3-py3-none-any.whl (129 kB)
#8 1.408 Downloading pygments-2.21.0-py3-none-any.whl (1.3 MB)
#8 1.453    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 26.8 MB/s  0:00:00
#8 1.531 Installing collected packages: pygments, pluggy, packaging, iniconfig, pytest
#8 2.100 
#8 2.101 Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
#8 2.101 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#8 DONE 2.2s

#9 [5/5] COPY parse_log.py summarize.py test_parse_log.py test_summarize.py ./
#9 DONE 0.0s

#10 exporting to image
#10 exporting layers
#10 exporting layers 0.6s done
#10 exporting manifest sha256:12756a52379b7f961ebaecfe10e40c5369faa66f21c024e9d4c2294d8c9a2382 done
#10 exporting config sha256:8042fe81582cec1f5c306acb62c1259cf40cf2532d0e32114ade71cce5cc91a9 done
#10 exporting attestation manifest sha256:d388127fe00760d2eb72d55a3de7d2abd77b13fdac786bf3ac94ee733f22cb59 done
#10 exporting manifest list sha256:9c7386f767c0f3f4de36ec6ac1feb4009d1db06607fa3cab7ecb75054a51539f done
#10 naming to docker.io/library/3am:latest done
#10 unpacking to docker.io/library/3am:latest
#10 unpacking to docker.io/library/3am:latest 0.3s done
#10 DONE 0.9s

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/mqjag39mjju586fmo4jmg6fvi
build exit status: 0
```

Run, exit status, runtime, parse check, pytest inside the container, and the image contents, as printed:

```text
$ cp "Held-out incident log dump: 11 March 2025 fare-quote incident.jsonl" incident.log
$ shasum -a 256 incident.log
0d2ba380cc857b463b75b30028557ce08308bffdd1a2b1cf4f46be2484b786c9  incident.log
$ docker run --rm -v "$PWD/incident.log:/logs/incident.log:ro" 3am /logs/incident.log | tee out.json
{
  "total_lines_processed": 48,
  "total_error_lines": 9,
  "clusters": [
    {
      "normalised_message": "surge multiplier lookup failed for trip <UUID> after <NUM>ms: redis timeout on shard <NUM>",
      "service": "fare-quote-service",
      "count": 5,
      "first_seen": "2025-03-11T01:13:14.902Z",
      "last_seen": "2025-03-11T01:19:02.140Z"
    },
    {
      "normalised_message": "fare quote unavailable for request <REQ>, returning <NUM>",
      "service": "trip-dispatch",
      "count": 2,
      "first_seen": "2025-03-11T01:14:02.209Z",
      "last_seen": "2025-03-11T01:16:50.884Z"
    },
    {
      "normalised_message": "upstream fare-quote <NUM> for rider <NUM> after <NUM>ms",
      "service": "rider-app-bff",
      "count": 1,
      "first_seen": "2025-03-11T01:16:26.559Z",
      "last_seen": "2025-03-11T01:16:26.559Z"
    },
    {
      "normalised_message": "eta model call timed out after <NUM>ms for trip <UUID>",
      "service": "eta-service",
      "count": 1,
      "first_seen": "2025-03-11T01:18:26.318Z",
      "last_seen": "2025-03-11T01:18:26.318Z"
    }
  ]
}
exit status: 0
runtime: 0.31s
$ docker run -i --rm --entrypoint python3 3am -m json.tool --compact < out.json > /dev/null && echo "parses as JSON"
parses as JSON
$ docker run -i --rm --entrypoint python3 3am -c 'import json,sys; d=json.load(sys.stdin); print(len(d["clusters"]), "clusters", [c["count"] for c in d["clusters"]])' < out.json
4 clusters [5, 2, 1, 1]
$ docker run --rm -v "$PWD/trip_booking.log:/app/trip_booking.log:ro" --entrypoint python3 3am -m pytest -v -p no:cacheprovider
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.1.1, pluggy-1.7.0 -- /usr/local/bin/python3
rootdir: /app
collecting ... collected 25 items

test_parse_log.py::SummarizeTest::test_counts_and_skips_malformed PASSED [  4%]
test_parse_log.py::SummarizeTest::test_real_log_adds_up PASSED           [  8%]
test_summarize.py::test_normalize_table[line50] PASSED                   [ 12%]
test_summarize.py::test_normalize_table[line20] PASSED                   [ 16%]
test_summarize.py::test_normalize_table[line35] PASSED                   [ 20%]
test_summarize.py::test_normalize_table[line38] PASSED                   [ 24%]
test_summarize.py::test_normalize_table[line66] PASSED                   [ 28%]
test_summarize.py::test_normalize_table[line7] PASSED                    [ 32%]
test_summarize.py::test_normalize_table[line2] PASSED                    [ 36%]
test_summarize.py::test_repeats_normalise_identically[line45-line60] PASSED [ 40%]
test_summarize.py::test_repeats_normalise_identically[line50-line57] PASSED [ 44%]
test_summarize.py::test_trip_id_in_any_shape_is_one_cluster PASSED       [ 48%]
test_summarize.py::test_same_message_in_two_services_is_two_clusters PASSED [ 52%]
test_summarize.py::test_only_valid_error_lines_are_clustered PASSED      [ 56%]
test_summarize.py::test_top_five_sorted_by_count_highest_first PASSED    [ 60%]
test_summarize.py::test_tie_goes_to_earliest_first_seen_whatever_the_input_order PASSED [ 64%]
test_summarize.py::test_first_and_last_seen PASSED                       [ 68%]
test_summarize.py::test_output_keys PASSED                               [ 72%]
test_summarize.py::test_real_log_pinned_result PASSED                    [ 76%]
test_summarize.py::test_broken_lines_are_malformed_and_leave_totals_unchanged PASSED [ 80%]
test_summarize.py::test_every_cluster_in_the_real_run_is_complete PASSED [ 84%]
test_summarize.py::test_cli_prints_only_one_json_object PASSED           [ 88%]
test_summarize.py::test_first_and_last_seen_compare_time_not_text PASSED [ 92%]
test_summarize.py::test_tiebreak_compares_time_not_text PASSED           [ 96%]
test_summarize.py::test_unusable_timestamps_are_malformed_not_a_crash PASSED [100%]

============================== 25 passed in 0.13s ==============================
pytest exit status: 0
$ docker run --rm --entrypoint ls 3am -A /app
parse_log.py
requirements-dev.txt
summarize.py
test_parse_log.py
test_summarize.py
```

The log holds 50 lines, of which 48 were processed. Lines 38 and 50 are cut off mid-record, so they're skipped. That leaves 9 ERROR lines. The image holds only the script, the tests and `requirements-dev.txt`, with no log.
