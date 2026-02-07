import os
import random
import re
import asyncio

import discord
import numpy
from discord.ext import voice_recv

from pogbot.config import CLIENT, dir_path
from pogbot.storage import get_updated_tokens_for_user, remove_one_token_from_user
from pogbot.clipping.sink import RollingBufferSink
from pogbot.clipping.detector import run_clip_detector

# Active listening sessions: guild_id -> (voice_client, sink, text_channel)
_listening_sessions = {}


async def start_listening(message):
    voice_channel = message.author.voice
    if voice_channel is None:
        await message.channel.send("You're not in a voice channel!")
        return

    guild_id = message.guild.id
    if guild_id in _listening_sessions:
        await message.channel.send("Already listening! Use !leave to stop.")
        return

    sink = RollingBufferSink()
    vc = await voice_channel.channel.connect(cls=voice_recv.VoiceRecvClient)
    vc.listen(sink)
    # Store the text channel where !listen was typed for clip notifications
    _listening_sessions[guild_id] = (vc, sink, message.channel)

    # Start the background clip detector
    asyncio.create_task(run_clip_detector(guild_id, get_listening_session))

    await message.channel.send("🎙️ Listening! Say **\"clip that\"** to save a clip, or type `!leave` to stop.")


async def stop_listening(message):
    guild_id = message.guild.id
    session = _listening_sessions.pop(guild_id, None)
    if session is None:
        await message.channel.send("Not currently listening in this server.")
        return

    vc, sink, _ = session
    vc.stop()
    sink.cleanup()
    await vc.disconnect()
    await message.channel.send("👋 Stopped listening.")


def get_listening_session(guild_id):
    """Get the active listening session for a guild, or None."""
    return _listening_sessions.get(guild_id)


async def play_unmodified_audio_file(message, source_path):
    voice_channel = message.author.voice
    if voice_channel is not None:
        vc = await voice_channel.channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=source_path))
        while vc.is_playing():
            await asyncio.sleep(0.5)
        await vc.disconnect()
        return True
    else:
        await message.author.send(
            "You're not in a channel. Daddy can't pog people that aren't in a channel."
        )
        return False


async def play_pog_file(message):
    for vc in CLIENT.voice_clients:
        await vc.disconnect()
        await asyncio.sleep(0.5)
    audio_path = os.path.join(dir_path, "assets", "audio")
    choices = [os.path.abspath(os.path.join(audio_path, item)) for item in os.listdir(audio_path)]
    source_path = random.choice(choices)

    # Get speed/frequency multipliers
    sigma = 0.1
    mu = 1
    [speed_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)
    [frequency_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)

    voice_channel = message.author.voice
    if voice_channel is not None:
        vc = await voice_channel.channel.connect()
        vc.play(
            discord.FFmpegPCMAudio(
                executable="ffmpeg",
                source=source_path,
                options=f'-filter:a "atempo={1 / frequency_mult},asetrate=44100*{frequency_mult},atempo={speed_mult}"',
            )
        )
        while vc.is_playing():
            await asyncio.sleep(0.5)
        await vc.disconnect()
    else:
        await message.author.send(
            "You're not in a channel. Daddy can't pog people that aren't in a channel."
        )
    await message.delete()


async def play_file(message, tokens):
    if tokens < 1:
        await message.channel.send(
            f"You have {tokens} tokens left and can't play a clip <:mentos:1044740202947678228>"
        )
    else:
        m = re.search(r"^!playclip\s+(.+)", message.content)
        if m:
            file_name = m.group(1)
            audio_path = os.path.join(dir_path, "assets", "audio")
            choices = os.listdir(audio_path)
            if file_name in choices:
                if await play_unmodified_audio_file(
                    message, os.path.join(audio_path, file_name)
                ):
                    remove_one_token_from_user(message.author)
                    await message.channel.send(
                        f"File played! You have {tokens - 1} tokens left. You'll get another one in a week!"
                    )
            else:
                await message.channel.send(
                    f"'{file_name}' is not a valid file. To see a list of files, type !files in a private message with Pogbot"
                )
        else:
            await message.channel.send("You need to type !playclip {filename}")


async def process_get_files(message):
    header = (
        "The files are returned in descending order of date added (most recent are at the top).\n"
        "They are also sent in multiple batches because a discord message cannot exceed 2000 characters in length."
    )
    await message.channel.send(header)
    audio_path = os.path.join(dir_path, "assets", "audio")
    full_path_choices = [os.path.join(audio_path, item) for item in os.listdir(audio_path)]
    full_path_choices.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    path_len = len(audio_path) + 1
    choices = [x[path_len:] for x in full_path_choices]
    if sum(len(x) for x in choices) + len(choices) < 2000:
        await message.channel.send("\n".join(choices))
    else:
        message_items = []
        for i in range(0, len(choices)):
            choice = choices[i]
            if len("\n".join(message_items)) + 1 + len(choice) >= 2000:
                await message.channel.send("\n".join(message_items))
                message_items = [choice]
            else:
                message_items.append(choice)
        await message.channel.send("\n".join(message_items))


async def process_tokens_command(message, tokens):
    await message.channel.send(
        f"You're a big nerd and have {tokens} left!! <:mentos:1044740202947678228>"
    )
