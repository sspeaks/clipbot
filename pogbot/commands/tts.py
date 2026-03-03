import os
import random
import re
import asyncio

import aiohttp
import discord

from pogbot.config import CLIENT, OPEN_AI_API, dir_path
from pogbot.storage import get_updated_tokens_for_user, remove_one_token_from_user
from pogbot.commands.audio import _listening_sessions

TTS_VOICES = ["alloy", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
TTS_MODEL = "gpt-4o-mini-tts"
MAX_MESSAGE_LENGTH = 500
TTS_API_URL = "https://api.openai.com/v1/audio/speech"


def _find_user_voice_channel(user):
    """Find the voice channel a user is in across all shared guilds."""
    for guild in CLIENT.guilds:
        member = guild.get_member(user.id)
        if member and member.voice:
            return member.voice, guild
    return None, None


async def _generate_tts(text, voice, output_path, instructions=None):
    """Call OpenAI TTS API directly via HTTP and save the result."""
    headers = {
        "Authorization": f"Bearer {OPEN_AI_API}",
        "Content-Type": "application/json",
    }
    payload = {"model": TTS_MODEL, "voice": voice, "input": text}
    if instructions:
        payload["instructions"] = instructions
    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_API_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"OpenAI TTS API returned {resp.status}: {body}")
            with open(output_path, "wb") as f:
                f.write(await resp.read())


async def process_say_command(message):
    m = re.search(r"^!say\s+(.+)", message.content, re.DOTALL)
    if not m:
        await message.channel.send("Usage: `!say <message>`")
        return

    text = m.group(1).strip()
    if len(text) > MAX_MESSAGE_LENGTH:
        await message.channel.send(
            f"Message too long! Max {MAX_MESSAGE_LENGTH} characters (yours is {len(text)})."
        )
        return

    tokens = get_updated_tokens_for_user(message.author)
    if tokens < 1:
        await message.channel.send(
            f"You have {tokens} tokens left and can't use TTS <:mentos:1044740202947678228>"
        )
        return

    voice_state, guild = _find_user_voice_channel(message.author)
    if voice_state is None:
        await message.channel.send(
            "You're not in a voice channel! Join one first, then try again."
        )
        return

    voice = random.choice(TTS_VOICES)
    tmp_path = os.path.join(dir_path, "temp_clips", f"tts_{message.id}.mp3")

    try:
        await _generate_tts(text, voice, tmp_path,
                            instructions="Speak with an overly excited, hyper-enthusiastic tone — like you just won the lottery and can't contain yourself.")
    except Exception as e:
        await message.channel.send(f"TTS generation failed: {e}")
        return

    try:
        guild_id = guild.id
        session = _listening_sessions.get(guild_id)
        # Reuse existing voice client if bot is already listening in the same channel
        if session and session[0].channel.id == voice_state.channel.id:
            vc = session[0]
            vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=tmp_path))
            while vc.is_playing():
                await asyncio.sleep(0.5)
        else:
            vc = await voice_state.channel.connect()
            vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=tmp_path))
            while vc.is_playing():
                await asyncio.sleep(0.5)
            await vc.disconnect()

        remove_one_token_from_user(message.author)
        await message.channel.send(
            f"🗣️ Spoke in voice! You have {tokens - 1} tokens left."
        )
    except Exception as e:
        await message.channel.send(f"Playback failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
