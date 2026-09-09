import gzip
import json
import struct
import wave
from types import SimpleNamespace

import app.services.tts_service as tts_service_module
from app.services.doubao_protocol import DoubaoBinaryFrame
from app.services.tts_service import TTSService


def _server_frame(*, message_type: int, flags: int, serialization: int, payload: bytes) -> bytes:
    output = bytearray((0x11, (message_type << 4) | flags, serialization << 4, 0x00))
    if flags & 0x3:
        output.extend(struct.pack(">i", -1 if flags & 0x2 else 1))
    output.extend(struct.pack(">I", len(payload)))
    output.extend(payload)
    return bytes(output)


def test_build_event_frame_matches_java_protocol_shape():
    frame = DoubaoBinaryFrame.build_event_json(
        DoubaoBinaryFrame.EVENT_START_SESSION,
        "session-1",
        {"event": 100, "text": "你好"},
    )

    assert frame[:4] == bytes((0x11, 0x14, 0x10, 0x00))
    parsed = DoubaoBinaryFrame.parse(frame)
    assert parsed.valid is True
    assert parsed.event == 100
    assert parsed.session_id == "session-1"
    assert json.loads(parsed.payload) == {"event": 100, "text": "你好"}


def test_parse_raw_and_gzip_server_audio_frames():
    raw = _server_frame(
        message_type=DoubaoBinaryFrame.MSG_AUDIO_SERVER,
        flags=DoubaoBinaryFrame.FLAG_NEGATIVE_SEQ,
        serialization=0,
        payload=b"pcm-bytes",
    )
    parsed = DoubaoBinaryFrame.parse(raw)
    assert parsed.valid is True
    assert parsed.is_final is True
    assert parsed.payload == b"pcm-bytes"

    compressed = gzip.compress(b"compressed-pcm")
    gzipped = bytes((0x11, 0x90, 0x11, 0x00)) + struct.pack(">I", len(compressed)) + compressed
    assert DoubaoBinaryFrame.parse(gzipped).payload == b"compressed-pcm"


def test_demo_voice_alias_maps_to_configured_doubao_speaker():
    service = TTSService()
    assert service.resolve_speaker("fictional-female-soft") == service.settings.tts_speaker
    assert service.resolve_speaker("zh_female_custom_bigtts") == "zh_female_custom_bigtts"


def test_pcm_audio_is_wrapped_as_browser_playable_wav(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tts_service_module,
        "settings",
        SimpleNamespace(audio_dir=tmp_path),
    )
    service = TTSService()
    output_file, duration_ms = service._save_doubao_audio(
        b"\x00\x00" * 240,
        output_format="pcm",
        sample_rate=24000,
        conversation_id=7,
    )

    with wave.open(str(output_file), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 24000
        assert wav_file.getnframes() == 240
    assert duration_ms == 800
