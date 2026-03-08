from pathlib import Path

from lairn.learn_log import LearnLogMessage, custom_json_decoder


def test_custom_json_decoder_allows_latex_like_backslashes():
    raw = (
        '{"User": "carlo.barth", "timestamp": "2026-03-07T11:56:02.000Z", '
        '"text": "Mathematik:\\nRechnen mit Zehnerpotenzen: 60 \\cdot 700"}'
    )

    decoded = custom_json_decoder(raw)

    assert decoded["User"] == "carlo.barth"
    assert decoded["text"] == "Mathematik:\nRechnen mit Zehnerpotenzen: 60 \\cdot 700"


def test_learn_log_message_from_json_file_handles_invalid_escape(tmp_path: Path):
    log_file = tmp_path / "bad-log.json"
    log_file.write_text(
        '{"User": "carlo.barth", "timestamp": "2026-03-07T11:56:02.000Z", '
        '"text": "Zahlen zerlegen:\\n3 \\cdot 3400 = 3 \\cdot 3000 + 3 \\cdot 400"}',
        encoding="utf-8",
    )

    message = LearnLogMessage.from_json_file(log_file)

    assert message.user == "carlo.barth"
    assert "3 \\cdot 3400" in message.text
