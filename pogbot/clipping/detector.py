import asyncio
import io
import os
import subprocess
import time
import uuid

import openai

from pogbot.config import dir_path

# Base URL for clip trimmer links (set via env, e.g. https://mycatsonfire.com/pogbot)
TRIMMER_BASE_URL = os.getenv("POGBOT_TRIMMER_URL", "http://localhost:8080")

# Cooldown between clip triggers (seconds)
COOLDOWN_SECONDS = 10
CHECK_INTERVAL_SECONDS = 5
WHISPER_WINDOW_SECONDS = 7  # Overlap with previous window to catch phrases at boundaries

# Stores pending clips: clip_id -> {"path": filepath, "text_channel": channel}
pending_clips = {}

_last_trigger_time = 0


async def run_clip_detector(guild_id, get_session_fn):
    """Background task that periodically checks for 'clip that' via Whisper.

    The text_channel used for posting clip links is the channel where
    !listen was originally typed — stored by start_listening() in audio.py.
    """
    global _last_trigger_time

    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        session = get_session_fn(guild_id)
        if session is None:
            break

        # text_channel is the channel where !listen was typed
        vc, sink, text_channel = session

        # Skip if in cooldown
        if time.monotonic() - _last_trigger_time < COOLDOWN_SECONDS:
            continue

        # Get last N seconds of audio
        wav_data = sink.get_last_n_seconds_wav(WHISPER_WINDOW_SECONDS)
        if wav_data is None:
            continue

        # Send to Whisper for transcription
        try:
            transcript = await asyncio.to_thread(
                _transcribe_audio, wav_data
            )
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            continue

        # Check for "clip that" trigger phrase
        if _matches_trigger(transcript):
            _last_trigger_time = time.monotonic()

            # Snapshot the full 30s buffer
            full_wav = sink.snapshot_wav()
            if full_wav is None:
                continue

            clip_id = str(uuid.uuid4())[:8]
            clip_dir = os.path.join(dir_path, "temp_clips")
            os.makedirs(clip_dir, exist_ok=True)
            clip_path = os.path.join(clip_dir, f"{clip_id}.wav")

            with open(clip_path, "wb") as f:
                f.write(full_wav)

            # Create a compressed OGG for fast browser preview (~15x smaller)
            ogg_path = os.path.join(clip_dir, f"{clip_id}.ogg")
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    ["ffmpeg", "-y", "-i", clip_path,
                     "-c:a", "libopus", "-b:a", "96k", "-ac", "1",
                     ogg_path],
                    check=True, capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"OGG encode failed: {e.stderr.decode()}")
                ogg_path = None

            pending_clips[clip_id] = {
                "path": clip_path,
                "ogg_path": ogg_path,
                "text_channel": text_channel,
            }

            await text_channel.send(
                f"🎬 **Clip captured!** Trim it here: {TRIMMER_BASE_URL}/trim/{clip_id}"
            )


def _transcribe_audio(wav_data):
    """Synchronous Whisper API call (run in thread)."""
    audio_file = io.BytesIO(wav_data)
    audio_file.name = "audio.wav"
    result = openai.Audio.transcribe("whisper-1", audio_file)
    return result.get("text", "")


def _matches_trigger(transcript):
    """Check if transcript contains the trigger phrase."""
    normalized = transcript.lower().strip()
    trigger_phrases = ["clip that", "clip it", "save that"]
    return any(phrase in normalized for phrase in trigger_phrases)


async def run_temp_cleanup(interval_seconds=300):
    """Background task to delete untrimmed temp .wav files older than 1 hour."""
    clip_dir = os.path.join(dir_path, "temp_clips")
    while True:
        await asyncio.sleep(interval_seconds)
        if not os.path.exists(clip_dir):
            continue

        now = time.time()
        for filename in os.listdir(clip_dir):
            filepath = os.path.join(clip_dir, filename)
            if os.path.isfile(filepath) and (now - os.path.getmtime(filepath)) > 3600:
                clip_id = os.path.splitext(filename)[0]
                pending_clips.pop(clip_id, None)
                os.remove(filepath)
