import datetime

import main as main_mod


def test_greeting_has_no_forced_sir():
    fixed = datetime.datetime(
        2026, 8, 5, 10, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    )
    print_text, speech_text = main_mod.make_jarvis_greeting(now_ist=fixed)
    assert "Sir" not in print_text
    assert "Sir" not in speech_text
    assert "good morning" in print_text.lower()
    assert "05-08-2026" in print_text


def test_working_ack_config_present():
    from config import WORKING_ACK

    assert isinstance(WORKING_ACK, str)
