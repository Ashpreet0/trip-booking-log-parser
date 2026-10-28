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

**What the top cluster means (11 March fare-quote log):** fare-quote-service's surge multiplier lookup timed out on Redis at least 5 times, starting at 01:13:14 UTC, before any other error. The trip-dispatch, rider-app-bff and eta-service errors come later and are on the same trips, so check the surge-pricing Redis shards first.

## Verification

Being re-run from a fresh clone; the transcript lands in the next commit.
