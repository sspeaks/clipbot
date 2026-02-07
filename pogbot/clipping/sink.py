import audioop
import io
import threading
import time
import wave

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
    """Maintains a rolling 30-second buffer of mixed audio from all users."""

    def __init__(self):
        super().__init__()
        self._slots = {}  # time_index -> bytearray of mixed PCM
        self._start_time = time.monotonic()
        self._lock = threading.Lock()
        self.last_write_time = time.monotonic()

    def _time_index(self):
        elapsed_ms = (time.monotonic() - self._start_time) * 1000
        return int(elapsed_ms / FRAME_MS)

    def wants_opus(self):
        return False

    def write(self, user, data):
        pcm = data.pcm
        idx = self._time_index()
        self.last_write_time = time.monotonic()

        # Normalize to exactly one frame
        if len(pcm) < FRAME_BYTES:
            pcm = pcm + b"\x00" * (FRAME_BYTES - len(pcm))
        elif len(pcm) > FRAME_BYTES:
            pcm = pcm[:FRAME_BYTES]

        with self._lock:
            if idx in self._slots:
                self._slots[idx] = audioop.add(
                    bytes(self._slots[idx]), pcm, SAMPLE_WIDTH
                )
            else:
                self._slots[idx] = bytearray(pcm)

            # Prune slots older than 30 seconds
            cutoff = idx - MAX_FRAMES
            for k in [k for k in self._slots if k < cutoff]:
                del self._slots[k]

    def snapshot_wav(self):
        """Return the current buffer contents as WAV bytes."""
        with self._lock:
            if not self._slots:
                return None

            indices = sorted(self._slots.keys())
            start = indices[0]
            end = indices[-1]

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)

                silence = b"\x00" * FRAME_BYTES
                for i in range(start, end + 1):
                    wf.writeframes(bytes(self._slots.get(i, silence)))

            return buf.getvalue()

    def get_last_n_seconds_wav(self, seconds=5):
        """Return the last N seconds of audio as WAV bytes (for Whisper)."""
        with self._lock:
            if not self._slots:
                return None

            current = self._time_index()
            start = current - (seconds * 1000 // FRAME_MS)

            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)

                silence = b"\x00" * FRAME_BYTES
                for i in range(start, current + 1):
                    wf.writeframes(bytes(self._slots.get(i, silence)))

            return buf.getvalue()

    def cleanup(self):
        with self._lock:
            self._slots.clear()
