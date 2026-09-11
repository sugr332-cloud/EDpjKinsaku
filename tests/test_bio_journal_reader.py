import json

import pytest

from app.bio.journal_reader import (
    latest_journal_event,
    read_journal_events,
    read_status,
)


def _write_journal(tmp_path, events: list[dict]) -> str:
    path = tmp_path / "Journal.2026-09-11T000000.01.log"
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    return str(path)


def test_reads_fsdjump_loadout_and_saa_signals_found(tmp_path):
    path = _write_journal(
        tmp_path,
        [
            {
                "timestamp": "2026-09-11T00:00:01Z",
                "event": "FSDJump",
                "StarSystem": "Test System",
                "StarPos": [1.0, 2.0, 3.0],
                "MaxJumpRange": 42.5,
            },
            {
                "timestamp": "2026-09-11T00:00:03Z",
                "event": "Loadout",
                "Ship": "Dolphin",
                "ShipID": 7,
            },
            {
                "timestamp": "2026-09-11T00:00:05Z",
                "event": "SAASignalsFound",
                "BodyName": "Test System A 1",
                "Signals": [{"Type": "Biological", "Count": 3}],
            },
        ],
    )

    events = read_journal_events(path)

    assert [event["event"] for event in events] == [
        "FSDJump",
        "Loadout",
        "SAASignalsFound",
    ]
    assert events[0]["StarPos"] == [1.0, 2.0, 3.0]
    assert events[0]["MaxJumpRange"] == 42.5
    assert events[1]["Ship"] == "Dolphin"
    assert events[2]["Signals"][0]["Type"] == "Biological"


def test_returns_latest_matching_event(tmp_path):
    path = _write_journal(
        tmp_path,
        [
            {"event": "FSDJump", "StarSystem": "First"},
            {"event": "FSDJump", "StarSystem": "Second"},
            {"event": "Loadout", "Ship": "Dolphin"},
        ],
    )

    assert latest_journal_event(path, "FSDJump")["StarSystem"] == "Second"
    assert latest_journal_event(path, "SAASignalsFound") is None


def test_blank_lines_are_ignored(tmp_path):
    path = tmp_path / "Journal.log"
    path.write_text(
        '\n{"event":"FSDJump","StarSystem":"Sol"}\n\n',
        encoding="utf-8",
    )

    assert len(read_journal_events(path)) == 1


def test_malformed_journal_line_is_not_silently_dropped(tmp_path):
    path = tmp_path / "Journal.log"
    path.write_text('{"event":"FSDJump"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        read_journal_events(path)


def test_status_json_requires_object(tmp_path):
    path = tmp_path / "Status.json"
    path.write_text(
        json.dumps(
            {
                "event": "Status",
                "Flags": 123,
                "Pips": [4, 4, 4],
                "FireGroup": 1,
            }
        ),
        encoding="utf-8",
    )

    status = read_status(path)

    assert status["event"] == "Status"
    assert status["Flags"] == 123
    assert status["Pips"] == [4, 4, 4]


def test_status_json_rejects_non_object(tmp_path):
    path = tmp_path / "Status.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        read_status(path)
