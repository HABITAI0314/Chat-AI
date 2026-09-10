from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import wave
from pathlib import Path
from uuid import uuid4

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from app.config import settings
from app.services.doubao_protocol import (
    DoubaoBinaryFrame,
    DoubaoProtocolError,
    ParsedDoubaoFrame,
)
from app.services.llm_config_service import tts_config_service

logger = logging.getLogger(__name__)


class TTSUnavailableError(RuntimeError):
    pass


class DoubaoBidirectionalTTS:
    """一轮文本对应一条豆包双向 TTS WebSocket。"""

    def __init__(self, app_settings):
        self.settings = app_settings

    async def synthesize(self, text: str, *, speaker: str, uid: str) -> tuple[bytes, str, int]:
        session_id = str(uuid4())
        connect_id = str(uuid4())
        timeout = max(1.0, float(self.settings.tts_timeout_seconds))
        connect_timeout = max(1.0, float(self.settings.tts_connect_timeout_seconds))
        headers = {
            "X-Api-App-Key": self.settings.tts_app_id,
            "X-Api-Access-Key": self.settings.tts_api_key,
            "X-Api-Resource-Id": self.settings.tts_resource_id,
            "X-Api-Connect-Id": connect_id,
        }
        audio_chunks: list[bytes] = []
        session_finished = False

        try:
            async with websockets.connect(
                self.settings.tts_websocket_url,
                additional_headers=headers,
                open_timeout=connect_timeout,
                close_timeout=connect_timeout,
                max_size=8 * 1024 * 1024,
            ) as websocket:
                await websocket.send(
                    DoubaoBinaryFrame.build_event_json(
                        DoubaoBinaryFrame.EVENT_START_CONNECTION,
                        None,
                        {"namespace": "BidirectionalTTS"},
                    )
                )
                await self._wait_for_event(
                    websocket,
                    DoubaoBinaryFrame.EVENT_CONNECTION_STARTED,
                    timeout=timeout,
                )

                await websocket.send(
                    DoubaoBinaryFrame.build_event_json(
                        DoubaoBinaryFrame.EVENT_START_SESSION,
                        session_id,
                        {
                            "user": {"uid": uid},
                            "event": DoubaoBinaryFrame.EVENT_START_SESSION,
                            "req_params": {
                                "speaker": speaker,
                                "audio_params": {
                                    "format": self.settings.tts_output_format,
                                    "sample_rate": self.settings.tts_output_sample_rate,
                                },
                            },
                        },
                    )
                )
                await self._wait_for_event(
                    websocket,
                    DoubaoBinaryFrame.EVENT_SESSION_STARTED,
                    timeout=timeout,
                )

                await websocket.send(
                    DoubaoBinaryFrame.build_event_json(
                        DoubaoBinaryFrame.EVENT_TASK_REQUEST,
                        session_id,
                        {
                            "user": {"uid": uid},
                            "event": DoubaoBinaryFrame.EVENT_TASK_REQUEST,
                            "req_params": {"text": text},
                        },
                    )
                )
                await websocket.send(
                    DoubaoBinaryFrame.build_event_json(
                        DoubaoBinaryFrame.EVENT_FINISH_SESSION,
                        session_id,
                        {},
                    )
                )

                while not session_finished:
                    frame = await self._receive_frame(websocket, timeout=timeout)
                    self._raise_for_error(frame)
                    audio = self._extract_audio(frame)
                    if audio:
                        audio_chunks.append(audio)
                    if frame.event == DoubaoBinaryFrame.EVENT_SESSION_FINISHED:
                        session_finished = True

                # Java 版本在收到会话结束后发送连接结束事件；这里也按相同顺序
                # 完成握手，WebSocket 上下文退出时再关闭底层连接。
                await websocket.send(
                    DoubaoBinaryFrame.build_event_json(
                        DoubaoBinaryFrame.EVENT_FINISH_CONNECTION,
                        None,
                        {},
                    )
                )
        except TTSUnavailableError:
            raise
        except (ConnectionClosed, TimeoutError) as exc:
            raise TTSUnavailableError("doubao_tts_connection_timeout_or_closed") from exc
        except (DoubaoProtocolError, UnicodeError, json.JSONDecodeError) as exc:
            raise TTSUnavailableError("doubao_tts_protocol_error") from exc
        except Exception as exc:
            # 不把鉴权信息写入用户可见错误，但保留异常原因便于服务端排查。
            raise TTSUnavailableError(f"doubao_tts_request_failed: {exc}") from exc

        audio = b"".join(audio_chunks)
        if not audio:
            raise TTSUnavailableError("doubao_tts_empty_audio")
        return audio, self.settings.tts_output_format.lower(), self.settings.tts_output_sample_rate

    async def _wait_for_event(self, websocket, event: int, *, timeout: float) -> None:
        while True:
            frame = await self._receive_frame(websocket, timeout=timeout)
            self._raise_for_error(frame)
            if frame.event == event:
                return

    async def _receive_frame(self, websocket, *, timeout: float) -> ParsedDoubaoFrame:
        raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        if isinstance(raw, str):
            raise DoubaoProtocolError("unexpected_text_frame")
        frame = DoubaoBinaryFrame.parse(raw)
        if not frame.valid:
            raise DoubaoProtocolError("invalid_binary_frame")
        return frame

    @staticmethod
    def _raise_for_error(frame: ParsedDoubaoFrame) -> None:
        if frame.message_type != DoubaoBinaryFrame.MSG_ERROR:
            return
        raise TTSUnavailableError("doubao_tts_provider_error")

    @staticmethod
    def _extract_audio(frame: ParsedDoubaoFrame) -> bytes:
        if frame.message_type == DoubaoBinaryFrame.MSG_AUDIO_SERVER:
            return frame.payload
        if frame.event != DoubaoBinaryFrame.EVENT_RESPONSE or not frame.payload:
            return b""
        if frame.serialization == 0:
            return frame.payload
        if frame.serialization != 1:
            return b""
        payload = json.loads(frame.payload.decode("utf-8"))
        encoded = payload.get("data")
        if not encoded:
            return b""
        return base64.b64decode(encoded)


class TTSService:
    def __init__(self):
        pass

    @property
    def settings(self):
        return tts_config_service.runtime_config()

    @property
    def provider(self) -> str:
        return (self.settings.tts_provider or "doubao_bidirection").strip().lower()

    @property
    def enabled(self) -> bool:
        if not self.settings.tts_enabled_effective:
            return False
        if self.provider in {"doubao", "doubao_bidirection", "doubao_bidirectional", "volcengine"}:
            return bool(
                self.settings.tts_websocket_url
                and self.settings.tts_api_key
                and self.settings.tts_app_id
                and self.settings.tts_resource_id
                and self.settings.tts_speaker
            )
        return bool(self.settings.resolved_tts_base_url and self.settings.resolved_tts_api_key)

    @staticmethod
    def clean_text(text: str) -> str:
        cleaned = re.sub(r"https?://\S+", "", text or "")
        cleaned = re.sub(r"[*_#>{}\[\]]", "", cleaned)
        return " ".join(cleaned.split()).strip()

    async def synthesize(self, text: str, *, voice_id: str, conversation_id: int) -> dict:
        if not self.enabled:
            raise TTSUnavailableError("tts_disabled_or_not_configured")
        clean_text = self.clean_text(text)[: self.settings.tts_max_chars]
        if not clean_text:
            raise TTSUnavailableError("tts_text_empty")

        max_retries = max(1, min(3, int(self.settings.tts_max_retries)))
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                if self.provider in {
                    "doubao",
                    "doubao_bidirection",
                    "doubao_bidirectional",
                    "volcengine",
                }:
                    speaker = self.resolve_speaker(voice_id)
                    audio, output_format, sample_rate = await DoubaoBidirectionalTTS(
                        self.settings
                    ).synthesize(
                        clean_text,
                        speaker=speaker,
                        uid=f"conversation_{conversation_id}",
                    )
                    output_file, duration_ms = self._save_doubao_audio(
                        audio,
                        output_format=output_format,
                        sample_rate=sample_rate,
                        conversation_id=conversation_id,
                    )
                    return {
                        "audio_path": self._public_audio_path(conversation_id, output_file),
                        "audio_duration_ms": duration_ms,
                        "transcript": clean_text,
                        "voice_id": speaker,
                        "format": output_file.suffix.lstrip("."),
                    }

                response = await self._request_openai_compatible(clean_text, voice_id)
                extension = self.settings.tts_format.lower()
                if extension not in {"mp3", "ogg", "wav"}:
                    extension = "mp3"
                output_file = self._save_bytes(response, conversation_id, extension)
                duration_ms = max(800, min(30_000, len(clean_text) * 180))
                return {
                    "audio_path": self._public_audio_path(conversation_id, output_file),
                    "audio_duration_ms": duration_ms,
                    "transcript": clean_text,
                    "voice_id": voice_id,
                    "format": extension,
                }
            except TTSUnavailableError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
            logger.warning(
                "tts request failed attempt=%s/%s provider=%s error=%s: %s",
                attempt,
                max_retries,
                self.provider,
                type(last_error).__name__ if last_error else "unknown",
                last_error,
            )
            if attempt < max_retries:
                await asyncio.sleep(0.3)
        raise TTSUnavailableError("tts_request_failed") from last_error

    def resolve_speaker(self, voice_id: str | None) -> str:
        """把 Demo 角色的本地别名映射到可用的豆包音色。

        角色卡可以直接填写豆包真实音色 ID（当前以 zh_/en_ 开头的音色），
        未配置或旧 Demo 的 fictional-* 别名则使用 DOUBAO_BIDIRECTION_TTS_SPEAKER，避免把
        本地 UI 标签误发给供应商。
        """
        candidate = (voice_id or "").strip()
        if candidate.startswith(("zh_", "en_", "multi_")):
            return candidate
        return self.settings.tts_speaker

    async def _request_openai_compatible(self, text: str, voice_id: str) -> bytes:
        endpoint = f"{self.settings.resolved_tts_base_url}/audio/speech"
        headers = {"Authorization": f"Bearer {self.settings.resolved_tts_api_key}"}
        payload = {
            "model": self.settings.tts_model,
            "voice": voice_id,
            "input": text,
            "response_format": self.settings.tts_format,
        }
        async with httpx.AsyncClient(timeout=self.settings.tts_timeout_seconds) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.content

    def _save_doubao_audio(
        self,
        audio: bytes,
        *,
        output_format: str,
        sample_rate: int,
        conversation_id: int,
    ) -> tuple[Path, int]:
        normalized = output_format.lower()
        if normalized == "pcm":
            # 豆包双向流式接口返回裸 PCM；浏览器不能直接播放裸 PCM，
            # 因此只在本地文件层补一个 WAV 头，不改动服务端音频数据。
            output_file = self._next_audio_file(conversation_id, "wav")
            with wave.open(str(output_file), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio)
            duration_ms = max(800, int(len(audio) * 1000 / (sample_rate * 2)))
            return output_file, min(30_000, duration_ms)

        extension = "ogg" if normalized == "ogg_opus" else normalized
        if extension not in {"mp3", "ogg"}:
            raise TTSUnavailableError("unsupported_doubao_audio_format")
        output_file = self._next_audio_file(conversation_id, extension)
        output_file.write_bytes(audio)
        return output_file, max(800, min(30_000, len(audio) // 48))

    def _save_bytes(self, content: bytes, conversation_id: int, extension: str) -> Path:
        output_file = self._next_audio_file(conversation_id, extension)
        output_file.write_bytes(content)
        return output_file

    def _next_audio_file(self, conversation_id: int, extension: str) -> Path:
        output_dir = settings.audio_dir / str(conversation_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{uuid4().hex}.{extension}"

    @staticmethod
    def _public_audio_path(conversation_id: int, output_file: Path) -> str:
        return f"/static/audio/{conversation_id}/{output_file.name}"
