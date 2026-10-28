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
- **stderr** carries one warning if any lines couldn't be read, for example lines cut off mid-record in a dump: `warning: skipped 2 unreadable line(s): 38, 50; the counts above leave them out`.
  - The counts don't include those lines, so **if you see this warning, the real numbers may be higher**. Open those line numbers in the log.
  - The run still exits 0, because the summary of the readable lines is valid.

**What the top cluster means:** pending. The line for the 11 March fare-quote incident is written from its full log, which is blocked (see Verification).

## Verification

### Status: blocked, because the held-out log is truncated

The held-out file "Held-out incident log dump: 11 March 2025 fare-quote incident" has **50 lines**. The brief describes **150 lines, 3 malformed, 5 clusters**.
- It stops mid-record at 01:19:50 UTC, so it covers only 01:10 to 01:19 of the incident window.
- Two downloads (15:06 and 15:30) are byte-identical, so the resource is serving the short file. The download didn't fail.
- Needed: a re-uploaded 150-line copy from the owner of the stage materials.
- **No held-out result is claimed until that copy arrives.** The container will be rerun only once `wc -l` matches 150 and the last line is complete.

Checks on the download:

```text
$ ls -l
-rw-r--r--@ 1 8990 Oct 28 15:30 Held-out incident log dump: 11 March 2025 fare-quote incident.jsonl
$ wc -c
8990
$ wc -l
49
$ tail -n 1
{"timestamp":"2025-03-11T01:19:50.330Z","level":"W
$ shasum -a 256
0d2ba380cc857b463b75b30028557ce08308bffdd1a2b1cf4f46be2484b786c9
$ head -n 1 | cut -c1-40   # first timestamp
{"timestamp":"2025-03-11T01:10:02.145Z",
```

- `wc -l` prints 49 because it counts newline characters, and the last line has none. That makes 50 lines.
- The last record ends at `"level":"W`. A file that ends like that stopped early.

**Where I went wrong:** I first ran the container on this short file and explained its 4 clusters before checking the input was whole. The tool's own warning flagged line 50 as unreadable, and that was the clue.

### Fixes needed so far: yes, three

All three were found while running the short file, and the 10 March log showed none of them. They hold whatever the full file contains.
1. `-v` rejected the downloaded filename with exit 125 and "too many colons", because the name contains a colon. The Run step now copies the log to `incident.log` first.
2. Short hex trip IDs like `b2e7c410` weren't normalised, so one failure was split across several clusters.
   - Fixed with a short-hex-ID rule. It changes nothing in the 10 March log.
   - Covered by `test_trip_id_in_any_shape_is_one_cluster`.
3. Unreadable lines were dropped without a word. A warning on stderr now names them, and stdout stays pure JSON.
   - Covered by `test_cli_warns_on_stderr_about_unreadable_lines`.

### What is verified without the held-out log

This is a fresh clone into a brand-new folder, at commit `f01b67e`. Later commits change only this README, and README.md is listed in `.dockerignore`. To check:

```bash
git diff --stat f01b67e HEAD   # README.md only
git ls-tree HEAD -- Dockerfile .dockerignore requirements-dev.txt parse_log.py summarize.py test_parse_log.py test_summarize.py
```

The second command prints the same blob hashes as the transcript below. A blob hash is a fingerprint of a file's contents.

The build log says `transferring dockerfile: 394B` for the 355-byte Dockerfile. That's BuildKit's transfer size, which adds 39 bytes of overhead. A 100-byte Dockerfile prints `137B`.

Build output, as printed. The build adds `--no-cache` so that no step comes from an earlier build. Otherwise it is the README build command.

```text
$ git clone https://github.com/Ashpreet0/trip-booking-log-parser.git && cd trip-booking-log-parser
Cloning into 'trip-booking-log-parser'...
$ git log --oneline -1
f01b67e fix: warn on stderr about unreadable lines so a cut-off ERROR isn't silently missing
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
#1 transferring dockerfile: 394B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.13-slim
#2 DONE 0.6s

#3 [internal] load .dockerignore
#3 transferring context: 97B done
#3 DONE 0.0s

#4 [internal] load build context
#4 transferring context: 15.53kB done
#4 DONE 0.0s

#5 [1/5] FROM docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
#5 resolve docker.io/library/python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb done
#5 DONE 0.0s

#6 [2/5] WORKDIR /app
#6 CACHED

#7 [3/5] COPY requirements-dev.txt .
#7 DONE 0.0s

#8 [4/5] RUN pip install --no-cache-dir -r requirements-dev.txt
#8 1.013 Collecting pytest==9.1.1 (from -r requirements-dev.txt (line 1))
#8 1.093   Downloading pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
#8 1.109 Collecting iniconfig>=1.0.1 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.127   Downloading iniconfig-2.3.1-py3-none-any.whl.metadata (2.8 kB)
#8 1.142 Collecting packaging>=22 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.153   Downloading packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
#8 1.167 Collecting pluggy<2,>=1.5 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.180   Downloading pluggy-1.7.0-py3-none-any.whl.metadata (5.0 kB)
#8 1.197 Collecting pygments>=2.7.2 (from pytest==9.1.1->-r requirements-dev.txt (line 1))
#8 1.208   Downloading pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
#8 1.219 Downloading pytest-9.1.1-py3-none-any.whl (386 kB)
#8 1.260 Downloading pluggy-1.7.0-py3-none-any.whl (27 kB)
#8 1.273 Downloading iniconfig-2.3.1-py3-none-any.whl (7.6 kB)
#8 1.282 Downloading packaging-26.3-py3-none-any.whl (129 kB)
#8 1.301 Downloading pygments-2.21.0-py3-none-any.whl (1.3 MB)
#8 1.367    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 24.9 MB/s  0:00:00
#8 1.444 Installing collected packages: pygments, pluggy, packaging, iniconfig, pytest
#8 1.980 
#8 1.981 Successfully installed iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
#8 1.981 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#8 DONE 2.0s

#9 [5/5] COPY parse_log.py summarize.py test_parse_log.py test_summarize.py ./
#9 DONE 0.0s

#10 exporting to image
#10 exporting layers
#10 exporting layers 0.5s done
#10 exporting manifest sha256:5b040643b93cd68327a44cd93c98e0c93ef11f13db758376b1634a6f9c5b7f37
#10 exporting manifest sha256:5b040643b93cd68327a44cd93c98e0c93ef11f13db758376b1634a6f9c5b7f37 done
#10 exporting config sha256:4bbba743a8c490c5c8726c17f4f59297f3c404bfdde3fd1a5f97e8b6acd6e0be done
#10 exporting attestation manifest sha256:00bdea8b4c5db806e32f0df2890f58dadc39cf1ba3138157e63664b4212c1481 done
#10 exporting manifest list sha256:d4b9a59ab390a353fd7d420a2a56b3404371f95451c47d748d461f7e262789a7 done
#10 naming to docker.io/library/3am:latest done
#10 unpacking to docker.io/library/3am:latest
#10 unpacking to docker.io/library/3am:latest 0.3s done
#10 DONE 0.9s

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/x9daj41j0gdzoe00j4ig80w73
build exit status: 0
```

Pytest inside the container, and the image contents (no log baked in), as printed:

```text
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

============================== 26 passed in 0.06s ==============================
pytest exit status: 0
$ docker run --rm --entrypoint ls 3am -A /app
parse_log.py
requirements-dev.txt
summarize.py
test_parse_log.py
test_summarize.py
```
