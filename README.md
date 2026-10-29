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

`-v` links that one file from your laptop into the container, read-only. Copy it in first because `-v` splits on `:`, and incident-log downloads often have a colon in their name. The log is never copied into the image: the Dockerfile copies only the script, the tests and `requirements-dev.txt`, `.dockerignore` excludes `*.log` and this README, and `.gitignore` keeps `incident.log` out of git.

## Reading the output

- **stdout** is one JSON object and nothing else, so it can be piped into a JSON parser.
  - `total_lines_processed`: the lines it could read.
  - `total_error_lines`: the readable ERROR lines across all groups, not only the top 5.
  - `clusters`: the same failure grouped together, ranked by `count`, with a tie going to the one that started first.
    - IDs, UUIDs and short hex trip IDs (both shown as `<UUID>`), request IDs, numbers and timestamps become tokens, so repeats of one failure land in one cluster.
    - Each cluster has a `service`, a `count`, and a `first_seen` / `last_seen` time in UTC.
- **stderr** carries one warning if any lines couldn't be read, for example lines cut off mid-record in a dump: `warning: skipped 3 unreadable line(s): 38, 76, 122; the counts above leave them out`.
  - The counts don't include those lines, so **if you see this warning, the real numbers may be higher**. Open those line numbers in the log.
  - The run still exits 0, because the summary of the readable lines is valid.

**What the top cluster means (11 March fare-quote log):** fare-quote-service's surge multiplier lookup timed out on Redis 24 times, on surge-cache shards 14 and 9, from 01:13:14 to 01:39:09 UTC. It's the first error in the window and half of all errors. The trip-dispatch 503s and rider-app-bff errors below it are on the same requests and trips, so they're its downstream symptoms. Check the surge-cache Redis shards first.

## Verification

Run on the **full held-out 11 March 2025 fare-quote log**, from a fresh clone into a brand-new folder. The tool had never seen this log.

**The input was checked before anything ran:**
- 150 lines, ending in a complete record and a newline, 36,268 bytes, sha256 `0e3bde9f…d8d2`.
- The first copy I was given had 50 lines and was cut off mid-record at 01:19:50. I wrongly explained its result before checking it was whole. That copy was replaced, and nothing here comes from it.

### Do the numbers match the log?

| The log file (commands in the transcript) | The output |
|---|---|
| 150 lines (`awk`, `wc -l`) | 147 processed, plus a stderr warning: **3 unreadable, lines 38, 76 and 122** |
| Line 38 is an ERROR cut off mid-record, line 76 is a plain-text Redis traceback, line 122 is blank | These are the 3 malformed lines the brief describes |
| 49 lines say `"level":"ERROR"` (`grep`) | `total_error_lines` 48. The 49th is cut-off line 38 |
| 48 readable ERROR lines, 6 distinct failures | **5 clusters** shown: 24 + 11 + 6 + 4 + 2 = 47. The 6th failure (receipt-service, 1 line) is below the top five but still counted in the 48 |

### Fixes needed: yes

These were found by running the held-out log. The 10 March log showed none of them.
1. `-v` rejected the downloaded filename with exit 125 and "too many colons". The Run step now copies the log to `incident.log` first.
2. Unreadable lines were dropped without a word. A warning on stderr now names them, and stdout stays pure JSON.
   - Covered by `test_cli_warns_on_stderr_about_unreadable_lines`, which goes red when the warning is removed.
   - The warning is also what exposed the cut-off copy: it flagged that file's last line as unreadable.
3. Short hex trip IDs like `b2e7c410` weren't normalised, which split one failure across clusters.
   - Fixed and covered by `test_trip_id_in_any_shape_is_one_cluster`.
   - This full file uses UUID trip IDs only, so the rule doesn't change this run.

### Which commit was tested

Commit `3aeed04`. The commit you open is the one after it, and it changes **only this README**. README.md is listed in `.dockerignore`, so it can't change the build or the image. To check:

```bash
git diff --stat 3aeed04 HEAD   # README.md only
git ls-tree HEAD -- Dockerfile .dockerignore requirements-dev.txt parse_log.py summarize.py test_parse_log.py test_summarize.py
```

The second command prints the same blob hashes as the transcript below. A blob hash is a fingerprint of a file's contents.

The build log says `transferring dockerfile: 394B` for the 355-byte Dockerfile. That's BuildKit's transfer size, which adds 39 bytes of overhead. A 100-byte Dockerfile prints `137B`.

### Build output, as printed

The build adds `--no-cache` so that no step comes from an earlier build. Otherwise it is the README build command.

```text
$ git clone https://github.com/Ashpreet0/trip-booking-log-parser.git && cd trip-booking-log-parser
Cloning into 'trip-booking-log-parser'...
$ git log --oneline -1
3aeed04 docs: verification blocked on the truncated held-out log
$ git ls-tree HEAD -- Dockerfile .dockerignore requirements-dev.txt parse_log.py summarize.py test_parse_log.py test_summarize.py
100644 blob 7dd3e5aecabf5edc63cfc684ee38bfe2200ff4b1	.dockerignore
100644 blob 66515a8deb5b8056831e24b7a86d1be84c84f5f2	Dockerfile
100644 blob 7903980eef44d119852906c0d3b22802a2edaf9a	parse_log.py
100644 blob 7345f250f23f668c1016f96cf5ba9a21d0869119	requirements-dev.txt
100644 blob 6c140a5d3907af430854611c8c829941da2fea24	summarize.py
100644 blob 020e0a84c284fcc66cd28ff781ac2fa4348902cc	test_parse_log.py
100644 blob 6019cdced4a0623e22e57dee71079f36afe255fe	test_summarize.py
$ wc -c Dockerfile .dockerignore
     355 Dockerfile
      57 .dockerignore
     412 total
$ docker build --no-cache -t 3am .
#0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 394B 0.0s done
#1 DONE 0.1s

#2 [internal] load metadata for docker.io/library/python:3.13-slim
#2 ...

#3 [auth] library/python:pull token for registry-1.docker.io
#3 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.13-slim
#2 DONE 8.5s

#4 [internal] load .dockerignore
#4 transferring context: 97B done
#4 DONE 0.0s

#5 [1/5] FROM docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
#5 resolve docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb 0.0s done
#5 DONE 0.0s

#6 [2/5] WORKDIR /app
#6 CACHED

#7 [internal] load build context
#7 transferring context: 15.53kB 0.0s done
#7 DONE 0.0s

#8 [3/5] COPY requirements-dev.txt .
#8 DONE 0.0s

#9 [4/5] RUN pip install --no-cache-dir -r requirements-dev.txt
#9 4.364 Collecting pytest==9.1.1 (from -r requirements-dev.txt (line 1))
#9 4.446   Downloading pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
#9 4.466 Collecting iniconfig>=1.0.1 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#9 4.477   Downloading iniconfig-2.3.1-py3-none-any.whl.metadata (2.8 kB)
#9 4.495 Collecting packaging>=22 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#9 4.509   Downloading packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
#9 4.526 Collecting pluggy<2,>=1.5 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#9 4.539   Downloading pluggy-1.7.0-py3-none-any.whl.metadata (5.0 kB)
#9 4.556 Collecting pygments>=2.7.2 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#9 4.571   Downloading pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
#9 4.589 Downloading pytest-9.1.1-py3-none-any.whl (386 kB)
#9 4.639 Downloading pluggy-1.7.0-py3-none-any.whl (27 kB)
#9 4.652 Downloading iniconfig-2.3.1-py3-none-any.whl (7.6 kB)
#9 4.663 Downloading packaging-26.3-py3-none-any.whl (129 kB)
#9 4.678 Downloading pygments-2.21.0-py3-none-any.whl (1.3 MB)
#9 4.717    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 35.8 MB/s  0:00:00
#9 4.849 Installing collected packages: pygments, pluggy, packaging, iniconfig, pytest
#9 6.124 
#9 6.125 Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
#9 6.125 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#9 DONE 6.3s

#10 [5/5] COPY parse_log.py summarize.py test_parse_log.py test_summarize.py ./
#10 DONE 0.1s

#11 exporting to image
#11 exporting layers
#11 exporting layers 1.1s done
#11 exporting manifest sha256:a90a0ae0548d5ee851bc21502cc4a23b23e1c600a347e8c8d3f6dd4c09668bf0 done
#11 exporting config sha256:47ba57d534c0f85ce10ad9788cef19d3c9e1c73b7e710246a83cff20ef058337 done
#11 exporting attestation manifest sha256:ee1fa015d1b569cef64ab4fe1d37225552b34169c5a4ebb66f749a0d21966a44 done
#11 exporting manifest list sha256:0c713f4105944239a2e0325cf7a297c1b1358b240087bbbdfc51be9d6120a4bf done
#11 naming to docker.io/library/3am:latest done
#11 unpacking to docker.io/library/3am:latest
#11 unpacking to docker.io/library/3am:latest 0.7s done
#11 DONE 1.9s

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/ok64c4n68e3pbd5hxau98ms5u
build exit status: 0
```

### Run, exit status, runtime, parse check, reconciliation, pytest in the container, image contents, as printed

```text
$ cp ~/Downloads/uber_fare_quote_incident_log_2025-03-11.jsonl incident.log
$ shasum -a 256 incident.log
0e3bde9f34a5b085b13c800648fbdfb2e20d6815b6c99bfda482efd7baafd8d2  incident.log
$ docker run --rm -v "$PWD/incident.log:/logs/incident.log:ro" 3am /logs/incident.log > out.json
warning: skipped 3 unreadable line(s): 38, 76, 122; the counts above leave them out
exit status: 0
runtime: 1.02s
$ cat out.json
{
  "total_lines_processed": 147,
  "total_error_lines": 48,
  "clusters": [
    {
      "normalised_message": "surge multiplier lookup failed for trip <UUID> after <NUM>ms: redis timeout on shard <NUM>",
      "service": "fare-quote-service",
      "count": 24,
      "first_seen": "2025-03-11T01:13:14.902Z",
      "last_seen": "2025-03-11T01:39:09.651Z"
    },
    {
      "normalised_message": "fare quote unavailable for request <REQ>, returning <NUM>",
      "service": "trip-dispatch",
      "count": 11,
      "first_seen": "2025-03-11T01:14:02.209Z",
      "last_seen": "2025-03-11T01:36:53.905Z"
    },
    {
      "normalised_message": "upstream fare-quote <NUM> for rider <NUM> after <NUM>ms",
      "service": "rider-app-bff",
      "count": 6,
      "first_seen": "2025-03-11T01:16:26.559Z",
      "last_seen": "2025-03-11T01:34:46.340Z"
    },
    {
      "normalised_message": "eta model call timed out after <NUM>ms for trip <UUID>",
      "service": "eta-service",
      "count": 4,
      "first_seen": "2025-03-11T01:18:26.318Z",
      "last_seen": "2025-03-11T01:31:37.502Z"
    },
    {
      "normalised_message": "road graph tile fetch failed for tile <NUM>: s3 <NUM> after <NUM>ms",
      "service": "map-matcher",
      "count": 2,
      "first_seen": "2025-03-11T01:32:15.627Z",
      "last_seen": "2025-03-11T01:35:49.107Z"
    }
  ]
}
$ docker run -i --rm --entrypoint python3 3am -m json.tool --compact < out.json > /dev/null && echo "stdout parses as JSON"
stdout parses as JSON
$ awk "END{print NR, \"lines in the file\"}" incident.log
150 lines in the file
$ grep -c "\"level\":\"ERROR\"" incident.log
49
$ wc -l < incident.log
     150
$ tail -n 1 incident.log | cut -c1-60
{"timestamp":"2025-03-11T01:39:47.284Z","level":"WARN","serv
$ sed -n "38p;76p;122p" incident.log
{"timestamp":"2025-03-11T01:17:26.418Z","level":"ERROR","service":"fare-quote-service","host":"fareq-usw2-11","request_id":"req_7d2a
redis.exceptions.TimeoutError: Timeout reading from socket (surge-cache shard 14)

$ docker run --rm -v "$PWD/trip_booking.log:/app/trip_booking.log:ro" --entrypoint python3 3am -m pytest -v -p no:cacheprovider
============================= test session starts ==============================
platform linux -- Python 3.13.18, pytest-9.1.1, pluggy-1.7.0 -- /usr/local/bin/python3
rootdir: /app
collecting ... collected 26 items

test_parse_log.py::SummarizeTest::test_counts_and_skips_malformed PASSED [  3%]
test_parse_log.py::SummarizeTest::test_real_log_adds_up PASSED           [  7%]
test_summarize.py::test_normalize_table[line50] PASSED                   [ 11%]
test_summarize.py::test_normalize_table[line20] PASSED                   [ 15%]
test_summarize.py::test_normalize_table[line35] PASSED                   [ 19%]
test_summarize.py::test_normalize_table[line38] PASSED                   [ 23%]
test_summarize.py::test_normalize_table[line66] PASSED                   [ 26%]
test_summarize.py::test_normalize_table[line7] PASSED                    [ 30%]
test_summarize.py::test_normalize_table[line2] PASSED                    [ 34%]
test_summarize.py::test_repeats_normalise_identically[line45-line60] PASSED [ 38%]
test_summarize.py::test_repeats_normalise_identically[line50-line57] PASSED [ 42%]
test_summarize.py::test_trip_id_in_any_shape_is_one_cluster PASSED       [ 46%]
test_summarize.py::test_same_message_in_two_services_is_two_clusters PASSED [ 50%]
test_summarize.py::test_only_valid_error_lines_are_clustered PASSED      [ 53%]
test_summarize.py::test_top_five_sorted_by_count_highest_first PASSED    [ 57%]
test_summarize.py::test_tie_goes_to_earliest_first_seen_whatever_the_input_order PASSED [ 61%]
test_summarize.py::test_first_and_last_seen PASSED                       [ 65%]
test_summarize.py::test_output_keys PASSED                               [ 69%]
test_summarize.py::test_real_log_pinned_result PASSED                    [ 73%]
test_summarize.py::test_broken_lines_are_malformed_and_leave_totals_unchanged PASSED [ 76%]
test_summarize.py::test_every_cluster_in_the_real_run_is_complete PASSED [ 80%]
test_summarize.py::test_cli_prints_only_one_json_object PASSED           [ 84%]
test_summarize.py::test_cli_warns_on_stderr_about_unreadable_lines PASSED [ 88%]
test_summarize.py::test_first_and_last_seen_compare_time_not_text PASSED [ 92%]
test_summarize.py::test_tiebreak_compares_time_not_text PASSED           [ 96%]
test_summarize.py::test_unusable_timestamps_are_malformed_not_a_crash PASSED [100%]

============================== 26 passed in 0.12s ==============================
pytest exit status: 0
$ docker run --rm --entrypoint ls 3am -A /app
parse_log.py
requirements-dev.txt
summarize.py
test_parse_log.py
test_summarize.py
```
