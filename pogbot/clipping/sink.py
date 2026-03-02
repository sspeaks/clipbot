import io
import threading
import time
import wave
from collections import deque

import numpy as np

from discord.ext.voice_recv import AudioSink
from discord.opus import Decoder as OpusDecoder

SAMPLE_RATE = OpusDecoder.SAMPLING_RATE  # 48000
CHANNELS = OpusDecoder.CHANNELS  # 2
SAMPLE_WIDTH = OpusDecoder.SAMPLE_SIZE // OpusDecoder.CHANNELS  # 2 (16-bit)
FRAME_MS = 20
FRAME_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * FRAME_MS // 1000  # 3840
BUFFER_SECONDS = 30
MAX_FRAMES = BUFFER_SECONDS * 1000 // FRAME_MS  # 1500


def _soft_limit(samples):
    """Soft-limit int32 samples to int16 range using tanh compression.

    Applies transparent compression above a knee threshold so that
    overlapping voices are attenuated smoothly instead of hard-clipped.
    """
    KNEE = 24000
    MAX_VAL = 32767
    headroom = float(MAX_VAL - KNEE)

    if np.max(np.abs(samples)) <= KNEE:
        return samples.astype(np.int16)

    fsamples = samples.astype(np.float64)
    magnitude = np.abs(fsamples)
    compressed = np.where(
        magnitude > KNEE,
        KNEE + headroom * np.tanh((magnitude - KNEE) / headroom),
        magnitude,
    )
    return np.clip(np.copysign(compressed, fsamples), -MAX_VAL, MAX_VAL).astype(np.int16)


# 5 ms fade expressed in stereo samples
_FADE_SAMPLES = SAMPLE_RATE * CHANNELS * 5 // 1000  # 480 samples = 5 ms


def _fade_edges(frames):
    """Apply a 5 ms linear fade-in and fade-out to prevent boundary clicks."""
    if not frames:
        return frames

    # Build a contiguous int16 array from all frames
    pcm = np.concatenate([np.frombuffer(f, dtype=np.int16) for f in frames])
    n = min(_FADE_SAMPLES, len(pcm) // 2)
    if n > 0:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        pcm[:n] = (pcm[:n].astype(np.float32) * ramp).astype(np.int16)
        pcm[-n:] = (pcm[-n:].astype(np.float32) * ramp[::-1]).astype(np.int16)

    # Re-split into frame-sized byte chunks
    samples_per_frame = FRAME_BYTES // SAMPLE_WIDTH
    return [pcm[i:i + samples_per_frame].tobytes()
            for i in range(0, len(pcm), samples_per_frame)]


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
            # Extend with the last sample to avoid a click from zero-padding
            sample_size = SAMPLE_WIDTH * CHANNELS  # 4 bytes per stereo sample
            if len(pcm) >= sample_size:
                last_sample = pcm[-sample_size:]
                pad_len = FRAME_BYTES - len(pcm)
                pcm = pcm + (last_sample * (pad_len // sample_size + 1))[:pad_len]
            else:
                pcm = pcm + b"\x00" * (FRAME_BYTES - len(pcm))
        elif len(pcm) > FRAME_BYTES:
            pcm = pcm[:FRAME_BYTES]

        uid = user.id if user else 0

        with self._lock:
            if uid not in self._user_buffers:
                self._user_buffers[uid] = deque(maxlen=MAX_FRAMES)
            self._user_buffers[uid].append((now, pcm))

    def _mix_range(self, start_time, end_time):
        """Mix per-user audio at sample-level precision.

        Each frame is placed at its exact sample offset derived from its
        timestamp, eliminating the 20 ms slot-quantisation that caused
        jitter artifacts.  Soft limiting is applied once to the entire
        continuous signal so the compressor can't pump between frames.
        """
        total_samples = max(1, round((end_time - start_time) * SAMPLE_RATE)) * CHANNELS
        samples_per_frame = FRAME_BYTES // SAMPLE_WIDTH  # 1920
        mixed = np.zeros(total_samples, dtype=np.int32)

        for buf in self._user_buffers.values():
            frames = [(ts, pcm) for ts, pcm in buf
                      if start_time <= ts < end_time]
            if not frames:
                continue

            # Place each frame at its exact sample position.
            # Consecutive frames from the same user are spaced at exactly
            # one frame width to eliminate jitter; only genuine pauses
            # (>30 ms gap) advance the write cursor by the real gap.
            first_offset = round((frames[0][0] - start_time) * SAMPLE_RATE) * CHANNELS
            write_pos = max(0, first_offset)

            for i, (ts, pcm) in enumerate(frames):
                if i > 0:
                    gap_sec = ts - frames[i - 1][0]
                    if gap_sec > 0.030:
                        # Real pause — jump the cursor forward
                        write_pos = max(0, round((ts - start_time) * SAMPLE_RATE) * CHANNELS)
                    else:
                        # Normal frame — advance by exactly one frame
                        write_pos += samples_per_frame

                samples = np.frombuffer(pcm, dtype=np.int16).astype(np.int32)
                end = min(write_pos + len(samples), total_samples)
                count = end - write_pos
                if count > 0 and write_pos >= 0:
                    mixed[write_pos:end] += samples[:count]

        # One-pass soft limiting on the full signal avoids per-frame pumping
        limited = _soft_limit(mixed)

        return [limited[i:i + samples_per_frame].tobytes()
                for i in range(0, len(limited), samples_per_frame)]

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

            frames = self._mix_range(earliest, latest + FRAME_MS / 1000)

            # Apply short fade-in/out to prevent boundary clicks
            return self._to_wav(_fade_edges(frames))

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
