import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import parse_log
from parse_log import parse_line
from summarize import normalize, summarize

HERE = Path(__file__).parent
LOG = HERE / "trip_booking.log"
LOG_LINES = LOG.read_text(encoding="utf-8").splitlines()


def message(n):
    """The `message` of line n of trip_booking.log (1-based)."""
    return json.loads(LOG_LINES[n - 1])["message"]


def line(service, msg, ts="2025-03-10T03:00:00.000Z", level="ERROR"):
    return json.dumps({"timestamp": ts, "level": level, "service": service, "message": msg})


# Normalisation table: real messages from the log, run through the script's own normalize().
NORMALISE_TABLE = [
    (50, "Candidate pool query exceeded deadline deadline=<TS> elapsed_ms=<NUM> pool_size=<NUM>"),  # ISO timestamp
    (20, "Failed to assign driver for trip <UUID> after <NUM> retries: upstream timeout <NUM>ms"),  # UUID
    (35, "Card auth call timed out for <REQ> after <NUM>ms"),  # request ID
    (38, "Stale location for driver <ID> age=<NUM>s"),  # prefixed numeric ID
    (66, "Payment hold failed for trip <UUID> amount=<NUM> code=GATEWAY_TIMEOUT"),  # decimal taken whole
    (7, "Upstream p99 latency <NUM>ms above target <NUM>ms path=/v2/trips/dispatch"),  # p99, /v2/ kept
    (2, "Booking request <REQ> accepted for trip <UUID> status=<NUM>"),  # UUID starting with a digit not chopped
]


@pytest.mark.parametrize("n, expected", NORMALISE_TABLE, ids=[f"line{n}" for n, _ in NORMALISE_TABLE])
def test_normalize_table(n, expected):
    assert normalize(message(n)) == expected


def test_repeats_normalise_identically():
    assert normalize(message(20)) == normalize(message(31)) == normalize(message(37))


def test_same_message_in_two_services_is_two_clusters():
    m = message(35)
    out = summarize([line("payments-authorizer", m), line("payments-authorizer", m), line("payments-ledger", m)])
    assert [(c["service"], c["count"]) for c in out["clusters"]] == [("payments-authorizer", 2), ("payments-ledger", 1)]


def test_only_valid_error_lines_are_clustered():
    out = summarize([line("a", "boom"), line("a", "fine", level="INFO"), line("a", "loud", level=" error "), "not json", ""])
    assert out["total_lines_processed"] == 3
    assert out["total_error_lines"] == 2


def test_top_five_sorted_by_count_highest_first():
    lines = [line(f"svc{i}", "x") for i in range(1, 7) for _ in range(i)]  # svc1 x1 ... svc6 x6
    out = summarize(lines)
    assert [c["count"] for c in out["clusters"]] == [6, 5, 4, 3, 2]
    assert out["total_error_lines"] == 21  # all groups, not just the top five


def test_tie_goes_to_earliest_first_seen_whatever_the_input_order():
    late = line("late", "x", ts="2025-03-10T03:10:00.000Z")
    early = line("early", "x", ts="2025-03-10T03:00:00.000Z")
    assert [c["service"] for c in summarize([late, early])["clusters"]] == ["early", "late"]


def test_first_and_last_seen():
    out = summarize([line("a", "x", ts=t) for t in ("2025-03-10T03:00:05.000Z", "2025-03-10T03:00:01.000Z", "2025-03-10T03:00:09.000Z")])
    c = out["clusters"][0]
    assert (c["first_seen"], c["last_seen"]) == ("2025-03-10T03:00:01.000Z", "2025-03-10T03:00:09.000Z")


def test_output_keys():
    out = summarize([line("a", "x")])
    assert list(out) == ["total_lines_processed", "total_error_lines", "clusters"]
    assert list(out["clusters"][0]) == ["normalised_message", "service", "count", "first_seen", "last_seen"]


def test_real_log_pinned_result():
    assert hashlib.sha256(LOG.read_bytes()).hexdigest() == "cfcf7c74fa968b5d7cff6640f5dab4efa11e6563425a42dd53f67d234c34f3e2"
    out = summarize(LOG_LINES)
    assert (out["total_lines_processed"], out["total_error_lines"]) == (80, 24)
    assert [(c["service"], c["count"]) for c in out["clusters"]] == [
        ("trip-dispatch", 4), ("trip-dispatch", 4), ("rider-booking-api", 4), ("matching-engine-v2", 3), ("payments-authorizer", 2),
    ]
    assert out["clusters"][0]["first_seen"] == "2025-03-10T02:53:30.905Z"


def test_broken_lines_are_malformed_and_leave_totals_unchanged():
    plain = "03:14:02.133 ERROR payments auth timed out after 3000ms req=e19b4d0 trip=T55119"  # plain-text format from the incident brief
    cut = LOG_LINES[19][: len(LOG_LINES[19]) // 2]  # real ERROR line 20, cut off halfway
    assert parse_line(plain) is None and parse_line(cut) is None
    assert parse_log.summarize([plain, cut]) == {"processed": 0, "error": 0, "malformed": 2}
    clean = summarize(LOG_LINES)
    broken = summarize(LOG_LINES[:40] + [plain, cut] + LOG_LINES[40:])  # no exception mid-stream
    assert (broken["total_lines_processed"], broken["total_error_lines"]) == (80, 24)
    assert broken == clean


def test_every_cluster_in_the_real_run_is_complete():
    out = summarize(LOG_LINES)
    clusters = out["clusters"]
    assert len(clusters) == 5
    counts = [c["count"] for c in clusters]
    assert counts == sorted(counts, reverse=True)
    records = [json.loads(x) for x in LOG_LINES]
    for c in clusters:
        assert isinstance(c["normalised_message"], str) and c["normalised_message"]
        assert c["service"] in {r["service"] for r in records}
        assert isinstance(c["count"], int) and c["count"] >= 1
        group = [r["timestamp"] for r in records
                 if r["level"] == "ERROR" and r["service"] == c["service"] and normalize(r["message"]) == c["normalised_message"]]
        assert c["count"] == len(group)
        assert (c["first_seen"], c["last_seen"]) == (min(group), max(group))
    assert sum(counts) <= out["total_error_lines"]


def test_cli_prints_only_one_json_object():
    run = subprocess.run([sys.executable, "summarize.py", "trip_booking.log"], cwd=HERE, capture_output=True, text=True, check=True)
    assert json.loads(run.stdout)["total_error_lines"] == 24
    assert run.stderr == ""


@pytest.mark.xfail(strict=True, reason="known bug: first_seen compares timestamps as text, so 00.500Z sorts before 00Z")
def test_first_seen_with_mixed_timestamp_precision():
    out = summarize([line("a", "x", ts="2025-03-10T03:00:00.500Z"), line("a", "x", ts="2025-03-10T03:00:00Z")])
    assert out["clusters"][0]["first_seen"] == "2025-03-10T03:00:00Z"
