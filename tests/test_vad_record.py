from stt.vad_record import decide_vad_action


def test_vad_waits_before_speech():
    assert (
        decide_vad_action(
            rms=0.001,
            speech_started=False,
            silence_ms=0,
            speech_rms=0.01,
            silence_needed_ms=800,
        )
        == "continue"
    )


def test_vad_starts_on_speech():
    assert (
        decide_vad_action(
            rms=0.05,
            speech_started=False,
            silence_ms=0,
            speech_rms=0.01,
            silence_needed_ms=800,
        )
        == "speech"
    )


def test_vad_stops_after_silence():
    assert (
        decide_vad_action(
            rms=0.001,
            speech_started=True,
            silence_ms=800,
            speech_rms=0.01,
            silence_needed_ms=800,
        )
        == "stop"
    )


def test_vad_resets_silence_on_more_speech():
    assert (
        decide_vad_action(
            rms=0.05,
            speech_started=True,
            silence_ms=400,
            speech_rms=0.01,
            silence_needed_ms=800,
        )
        == "speech"
    )
