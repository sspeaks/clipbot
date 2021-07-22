#!/user/bin/env python
import os
import json
import random
import discord
from dotenv import load_dotenv
from time import sleep
import aiohttp
import numpy

dir_path = os.path.dirname(os.path.realpath(__file__))

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GIPHY_API_KEY = os.getenv('GIPHY_API_KEY')

clip_channel = "clipbot"

CLIENT = discord.Client()

@CLIENT.event
async def on_ready():
    for guild in CLIENT.guilds:
        if guild.name == GUILD:
            print(
                f'{CLIENT.user} is connected to the following guild:\n'
                f'{guild.name}(id: {guild.id})'
            )
            break


@CLIENT.event
async def on_message(message):
    if should_process_clipmedaddy_message(message):
        await play_clip_file(message)
    if should_process_help_message(message):
        await print_help_message(message)


async def get_random_image_url(high_word, low_word, score):
    session = aiohttp.ClientSession()
    keyword = high_word if score > 5 else low_word
    response = await session.get(f'http://api.giphy.com/v1/gifs/random?tag={keyword}&api_key={GIPHY_API_KEY}')
    data = json.loads(await response.text())
    await session.close()
    return data['data']['images']['original']['url']

def should_process_clipmedaddy_message(message):
    if message.author == CLIENT.user:
        return False
    if message.channel.name != clip_channel:
        return False
    if message.content == '!clipmedaddy':
        return True
    return False

async def play_clip_file(message):
    audioPath=dir_path+"/assets/audio"
    choices = [os.path.abspath(audioPath+"/"+item) for item in os.listdir(audioPath)]
    sourcePath = random.choice(choices)

    # Get speed/frequency multipliers
    sigma = 0.1
    mu = 1
    [speed_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)
    [frequency_mult] = numpy.clip(numpy.random.normal(mu, sigma, 1), 0.5, 2)

    voice_channel = message.author.voice
    if voice_channel != None:
        vc = await voice_channel.channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=sourcePath, options=f'-filter:a "atempo='+str(1/frequency_mult)+',asetrate=44100*'+str(frequency_mult)+',atempo='+str(speed_mult)+'"'))
        while vc.is_playing():
            sleep(.1)
        await vc.disconnect()
    else:
            await message.author.send("You're is not in a channel. Daddy can't play clips for people that aren't in a channel.")
    # Delete command after the audio is done playing.
    await message.delete()

def should_process_help_message(message):
    if message.author == CLIENT.user:
        return False
    if message.channel.name != clip_channel:
        return False
    if message.content == '!help':
        return True
    return False

async def print_help_message(message):
    msg = '''
    ```
    !clipmedaddy - Plays an audio file from your favorite cast of characters.
    !help - Displays this help text.
    ```
    '''
    await message.channel.send(msg)

CLIENT.run(TOKEN)

#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python38Packages.discordpy python38Packages.python-dotenv python38Packages.aiohttp python38Packages.pynacl ffmpeg

