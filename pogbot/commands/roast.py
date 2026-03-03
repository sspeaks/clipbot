import os
import random
import re
import asyncio

import discord
import openai

from pogbot.config import CLIENT, dir_path
from pogbot.storage import get_updated_tokens_for_user, remove_one_token_from_user
from pogbot.commands.audio import _listening_sessions
from pogbot.commands.tts import TTS_VOICES, _generate_tts, _find_user_voice_channel

ROAST_TOKEN_COST = 2

ROAST_SYSTEM_PROMPT = (
    "You are a savage but funny roast comedian performing for a group of friends. "
    "Generate a short, punchy roast (2-3 sentences max) about the person named below. "
    "Be creative, absurd, and hilarious. Keep it light-hearted — these are friends roasting each other. "
    "Do not use slurs or anything truly hurtful. Address the person directly."
)


def _find_member_by_name(guild, name):
    """Case-insensitive lookup of a guild member by display name or username."""
    lower = name.lower()
    for member in guild.members:
        if member.display_name.lower() == lower or member.name.lower() == lower:
            return member
    return None


async def process_roast_command(message):
    raw = message.content[len("!roast"):].strip()
    if not raw:
        await message.channel.send("Usage: `!roast <name> [optional context]`")
        return

    voice_state, guild = _find_user_voice_channel(message.author)
    if voice_state is None:
        await message.channel.send(
            "You're not in a voice channel! Join one first, then try again."
        )
        return

    # Use Discord's parsed mentions if available, otherwise look up by name
    if message.mentions:
        target_member = message.mentions[0]
        target_name = target_member.display_name
        # Strip the mention from raw to get context
        context = re.sub(r"<@!?\d+>", "", raw, count=1).strip().strip('\u201c\u201d"\'')
    else:
        parts = raw.split(maxsplit=1)
        search_name = parts[0].lstrip("@")
        context = parts[1].strip().strip('\u201c\u201d"\'') if len(parts) > 1 else ""
        target_member = _find_member_by_name(guild, search_name)
        target_name = target_member.display_name if target_member else search_name

    tokens = get_updated_tokens_for_user(message.author)
    if tokens < ROAST_TOKEN_COST:
        await message.channel.send(
            f"You need {ROAST_TOKEN_COST} tokens to roast someone but only have {tokens} <:mentos:1044740202947678228>"
        )
        return

    user_prompt = f"Roast {target_name}."
    if context:
        user_prompt += f" Context: {context}"

    # Generate the roast text via ChatGPT (run in thread to avoid blocking)
    try:
        completion = await asyncio.to_thread(
            openai.ChatCompletion.create,
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": ROAST_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        roast_text = completion.choices[0].message.content
    except Exception as e:
        await message.channel.send(f"Roast generation failed: {e}")
        return

    # Speak the roast via TTS
    voice = random.choice(TTS_VOICES)
    tmp_path = os.path.join(dir_path, "temp_clips", f"roast_{message.id}.mp3")

    try:
        await _generate_tts(roast_text, voice, tmp_path,
                            instructions="Speak with an overly excited, hyper-enthusiastic tone — like you just won the lottery and can't contain yourself.")
    except Exception as e:
        await message.channel.send(f"TTS generation failed: {e}")
        return

    try:
        guild_id = guild.id
        session = _listening_sessions.get(guild_id)
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

        for _ in range(ROAST_TOKEN_COST):
            remove_one_token_from_user(message.author)
        await message.channel.send(
            f"🔥 Roast delivered! You have {tokens - ROAST_TOKEN_COST} tokens left."
        )
    except Exception as e:
        await message.channel.send(f"Playback failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
