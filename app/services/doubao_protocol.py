"""豆包/火山引擎双向 TTS WebSocket 二进制帧协议。

YQ 项目中的 Java 客户端和豆包双向流式语音合成共用这套 4 字节头协议：
客户端事件帧携带 event，服务端音频帧可能是原始 PCM，也可能是带 base64
音频数据的 JSON。这里仅实现 Demo 所需的 TTS 子集，不暴露任意工具或文件能力。
"""

from __future__ import annotations

import gzip
import json
import struct
from dataclasses import dataclass
from typing import Any


class DoubaoProtocolError(ValueError):
    """豆包二进制帧格式错误。"""


@dataclass(slots=True)
class ParsedDoubaoFrame:
    valid: bool = False
    message_type: int = 0
    flags: int = 0
    serialization: int = 0
    compression: int = 0
    sequence: int = 0
    event: int | None = None
    session_id: str | None = None
    connect_id: str | None = None
    error_code: int | None = None
    payload: bytes = b""

    @property
    def is_final(self) -> bool:
        sequence_flags = self.flags & 0x3
        return sequence_flags in {0x2, 0x3}


class DoubaoBinaryFrame:
    """构建客户端事件帧并解析服务端帧。"""

    MSG_FULL_CLIENT = 0x1
    MSG_AUDIO_SERVER = 0xB
    MSG_FULL_SERVER = 0x9
    MSG_ERROR = 0xF
    FLAG_EVENT = 0x4
    FLAG_POSITIVE_SEQ = 0x1
    FLAG_NEGATIVE_SEQ = 0x2

    EVENT_START_CONNECTION = 1
    EVENT_FINISH_CONNECTION = 2
    EVENT_START_SESSION = 100
    EVENT_FINISH_SESSION = 102
    EVENT_TASK_REQUEST = 200

    EVENT_CONNECTION_STARTED = 50
    EVENT_SESSION_STARTED = 150
    EVENT_SESSION_FINISHED = 152
    EVENT_RESPONSE = 352

    @classmethod
    def build_event_json(
        cls,
        event: int,
        session_id: str | None,
        payload: dict[str, Any] | bytes,
    ) -> bytes:
        if isinstance(payload, dict):
            payload_bytes = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        else:
            payload_bytes = payload

        output = bytearray((0x11, (cls.MSG_FULL_CLIENT << 4) | cls.FLAG_EVENT, 0x10, 0x00))
        output.extend(struct.pack(">I", event))
        if session_id:
            session_bytes = session_id.encode("utf-8")
            output.extend(struct.pack(">I", len(session_bytes)))
            output.extend(session_bytes)
        output.extend(struct.pack(">I", len(payload_bytes)))
        output.extend(payload_bytes)
        return bytes(output)

    @classmethod
    def parse(cls, data: bytes) -> ParsedDoubaoFrame:
        frame = ParsedDoubaoFrame()
        if not data or len(data) < 4:
            return frame

        header_units = data[0] & 0x0F
        header_size = header_units * 4
        if header_size <= 0 or len(data) < header_size:
            return frame

        frame.message_type = (data[1] >> 4) & 0x0F
        frame.flags = data[1] & 0x0F
        frame.serialization = (data[2] >> 4) & 0x0F
        frame.compression = data[2] & 0x0F
        offset = header_size

        if cls._has_sequence_field(frame.message_type, frame.flags):
            frame.sequence, offset = cls._read_int(data, offset)

        if frame.flags & cls.FLAG_EVENT:
            frame.event, offset = cls._read_int(data, offset)
            if cls._has_session_id_field(frame.event):
                frame.session_id, offset = cls._read_string(data, offset)
            elif cls._has_connect_id_field(frame.event):
                frame.connect_id, offset = cls._read_string(data, offset)

        if frame.message_type == cls.MSG_ERROR:
            frame.error_code, offset = cls._read_int(data, offset)

        payload_size, offset = cls._read_int(data, offset)
        if payload_size < 0 or offset + payload_size > len(data):
            raise DoubaoProtocolError("invalid_payload_size")
        payload = data[offset : offset + payload_size]
        if frame.compression == 0x1 and payload:
            try:
                payload = gzip.decompress(payload)
            except OSError:
                # 与 YQ Java 客户端保持一致：压缩标记异常时保留原始 payload，
                # 由上层错误处理决定是否继续。
                pass
        frame.payload = payload
        frame.valid = True
        return frame

    @staticmethod
    def _read_int(data: bytes, offset: int) -> tuple[int, int]:
        if offset + 4 > len(data):
            raise DoubaoProtocolError("truncated_integer")
        return struct.unpack_from(">I", data, offset)[0], offset + 4

    @staticmethod
    def _read_string(data: bytes, offset: int) -> tuple[str, int]:
        length, offset = DoubaoBinaryFrame._read_int(data, offset)
        if offset + length > len(data):
            raise DoubaoProtocolError("truncated_string")
        return data[offset : offset + length].decode("utf-8"), offset + length

    @staticmethod
    def _has_sequence_field(message_type: int, flags: int) -> bool:
        sequence_flags = flags & 0x3
        return sequence_flags in {0x1, 0x2, 0x3}

    @staticmethod
    def _has_session_id_field(event: int) -> bool:
        return event not in {1, 2, 50, 51, 52}

    @staticmethod
    def _has_connect_id_field(event: int) -> bool:
        return event in {50, 51, 52}

