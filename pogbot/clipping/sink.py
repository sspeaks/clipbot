import audioop
import io
import threading
import time
import wave
from collections import deque

from discord.ext.voice_recv import AudioSink
from discord.opus import Decoder as OpusDecoder

SAMPLE_RATE = OpusDecoder.SAMPLING_RATE  # 48000
CHANNELS = OpusDecoder.CHANNELS  # 2
SAMPLE_WIDTH = OpusDecoder.SAMPLE_SIZE // OpusDecoder.CHANNELS  # 2 (16-bit)
FRAME_MS = 20
FRAME_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_MS // 1000  # 3840
BUFFER_SECONDS = 30
MAX_FRAMES = BUFFER_SECONDS * 1000 // FRAME_MS  # 1500


class RollingBufferSink(AudioSink):
    """Maintains a rolling 30-second buffer of mixed audio from all users.

    Stores per-user frame deques and mixes at read time to avoid
    time-slot alignment glitches caused by wall-clock jitter.
    """

    def __init__(self):
        super().__init__()
        self._user_buffers = {}  # user_id -> deque of (monotonic_time, pcm)
        self._lock = threading.Lock()
        self.last_write_time = time.monotonic()

    def wants_opus(self):
        return False

    def write(self, user, data):
        pcm = data.pcm
        now = time.monotonic()
        self.last_write_time = now

        # Normalize to exactly one frame
        if len(pcm) < FRAME_BYTES:
            pcm = pcm + b"\x00" * (FRAME_BYTES - len(pcm))
        elif len(pcm) > FRAME_BYTES:
            pcm = pcm[:FRAME_BYTES]

        uid = user.id if user else 0

        with self._lock:
            if uid not in self._user_buffers:
                self._user_buffers[uid] = deque(maxlen=MAX_FRAMES)
            self._user_buffers[uid].append((now, pcm))

    def _mix_range(self, start_time, end_time):
        """Mix per-user audio into sequential frames for the given time range."""
        num_frames = max(1, round((end_time - start_time) * 1000 / FRAME_MS))
        silence = b"\x00" * FRAME_BYTES
        mixed = [bytearray(silence) for _ in range(num_frames)]

        for buf in self._user_buffers.values():
            for ts, pcm in buf:
                if ts < start_time or ts >= end_time:
                    continue
                idx = min(int((ts - start_time) * 1000 / FRAME_MS), num_frames - 1)
                mixed[idx] = audioop.add(bytes(mixed[idx]), pcm, SAMPLE_WIDTH)

        return mixed

    def _to_wav(self, frames):
        """Encode a list of PCM frames as WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            for frame in frames:
                wf.writeframes(bytes(frame))
        return buf.getvalue()

    def snapshot_wav(self):
        """Return the current buffer contents as WAV bytes."""
        with self._lock:
            earliest = None
            latest = None
            for buf in self._user_buffers.values():
                if buf:
                    earliest = buf[0][0] if earliest is None else min(earliest, buf[0][0])
                    latest = buf[-1][0] if latest is None else max(latest, buf[-1][0])

            if earliest is None:
                return None

            return self._to_wav(self._mix_range(earliest, latest + FRAME_MS / 1000))

    def get_last_n_seconds_wav(self, seconds=5):
        """Return the last N seconds of audio as WAV bytes (for Whisper)."""
        with self._lock:
            if not any(self._user_buffers.values()):
                return None

            now = time.monotonic()
            return self._to_wav(self._mix_range(now - seconds, now))

    def cleanup(self):
        with self._lock:
            self._user_buffers.clear()
